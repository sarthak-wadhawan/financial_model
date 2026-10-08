"""Unit tests for ManagementExtractor."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
from trading_copilot.models.news import (
    NewsDocument,
    NewsSourceType,
    StatementType,
    ExtractionMethod,
    EvidenceSpan,
)


class TestManagementExtractor:
    """Tests for ManagementExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a management extractor with known executives."""
        with tempfile.TemporaryDirectory() as tmpdir:
            extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
            yield extractor

    def test_extractor_initialization(self, extractor):
        """Test extractor initializes correctly."""
        assert extractor is not None
        assert "AAPL" in extractor.known_executives
        assert extractor.known_executives["AAPL"]["Tim Cook"] == "CEO"

    def test_extract_statements_basic(self, extractor):
        """Test basic statement extraction."""
        doc = NewsDocument(
            document_id="test:1",
            symbol="AAPL",
            headline="Apple Q3 Results",
            body='CEO Tim Cook said "We are very pleased with our results." CFO Luca Maestri noted that revenue grew 5%. The company expects continued growth.',
            summary="Test",
            publisher="AAPL",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            source_type=NewsSourceType.COMPANY_IR,
            provider_id="test",
            content_hash="abc",
        )

        statements = extractor.extract_statements(doc)
        assert len(statements) >= 2

        # Check first statement (Tim Cook)
        cook_stmt = next(s for s in statements if s.speaker == "Tim Cook")
        assert cook_stmt.speaker_role == "CEO"
        assert "pleased" in cook_stmt.statement
        assert cook_stmt.confidence > 0.5

        # Check second statement (Luca Maestri)
        maestri_stmt = next(s for s in statements if s.speaker == "Luca Maestri")
        assert maestri_stmt.speaker_role == "CFO"
        assert "revenue grew" in maestri_stmt.statement

    def test_extract_quotes(self, extractor):
        """Test direct quote extraction."""
        doc = NewsDocument(
            document_id="test:2",
            symbol="AAPL",
            headline="Apple Q3 Results",
            body='Tim Cook said "We expect strong demand in Q4." The company is optimistic.',
            summary="Test",
            publisher="AAPL",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            source_type=NewsSourceType.COMPANY_IR,
            provider_id="test",
            content_hash="abc",
        )

        statements = extractor.extract_statements(doc)
        quote_stmts = [s for s in statements if s.evidence_span and '"' in s.evidence_span.text]
        assert len(quote_stmts) >= 1

    def test_statement_type_detection(self, extractor):
        """Test statement type detection."""
        from trading_copilot.providers.management_extractor import detect_statement_type

        assert detect_statement_type("We expect revenue to grow") == StatementType.GUIDANCE
        assert detect_statement_type("Demand is strong") == StatementType.DEMAND
        assert detect_statement_type("Margins are expanding") == StatementType.MARGINS
        assert detect_statement_type("Costs are increasing") == StatementType.COSTS
        assert detect_statement_type("We are investing in new factory") == StatementType.CAPEX
        assert detect_statement_type("Competition is intense") == StatementType.COMPETITION
        assert detect_statement_type("New product launch next quarter") == StatementType.PRODUCT
        assert detect_statement_type("Regulatory approval pending") == StatementType.REGULATION
        assert detect_statement_type("Supply chain constraints") == StatementType.SUPPLY
        assert detect_statement_type("Pricing power remains") == StatementType.PRICING
        assert detect_statement_type("Strategic acquisition announced") == StatementType.STRATEGY
        assert detect_statement_type("Risk of recession") == StatementType.RISKS
        assert detect_statement_type("Macro environment challenging") == StatementType.MACRO
        assert detect_statement_type("Random text") == StatementType.OTHER

    def test_speaker_role_detection(self, extractor):
        """Test speaker role detection."""
        from trading_copilot.providers.management_extractor import detect_speaker_role

        assert detect_speaker_role("CEO Tim Cook said") == "CEO"
        assert detect_speaker_role("CFO Luca Maestri noted") == "CFO"
        assert detect_speaker_role("COO Jeff Williams explained") == "COO"
        assert detect_speaker_role("President John Doe stated") == "President"
        assert detect_speaker_role("VP Jane Smith mentioned") == "VP"
        assert detect_speaker_role("SVP Bob Jones added") == "SVP"
        assert detect_speaker_role("EVP Mary Brown indicated") == "EVP"
        assert detect_speaker_role("Director Alice White remarked") == "Director"
        assert detect_speaker_role("Executive James Black said") == "Executive"
        assert detect_speaker_role("Random person said") is None

    def test_speaker_name_extraction(self, extractor):
        """Test speaker name extraction."""
        from trading_copilot.providers.management_extractor import extract_speaker_name

        assert extract_speaker_name("Tim Cook said", {"AAPL": {"Tim Cook": "CEO"}}) == "Tim Cook"
        assert extract_speaker_name("said Tim Cook", {"AAPL": {"Tim Cook": "CEO"}}) == "Tim Cook"
        assert extract_speaker_name("Tim Cook, CEO, said", {"AAPL": {"Tim Cook": "CEO"}}) == "Tim Cook"
        assert extract_speaker_name("CEO Tim Cook said", {"AAPL": {"Tim Cook": "CEO"}}) == "Tim Cook"
        assert extract_speaker_name("Random person said", {"AAPL": {"Tim Cook": "CEO"}}) == "UNKNOWN"

    def test_evidence_span_finding(self, extractor):
        """Test evidence span finding in document."""
        doc = NewsDocument(
            document_id="test:3",
            symbol="AAPL",
            headline="Test",
            body="CEO Tim Cook said we expect strong growth. The company is doing well.",
            summary="Test",
            publisher="AAPL",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            source_type=NewsSourceType.COMPANY_IR,
            provider_id="test",
            content_hash="abc",
        )

        statements = extractor.extract_statements(doc)
        for stmt in statements:
            if stmt.evidence_span:
                # Verify span is valid
                assert stmt.evidence_span.start >= 0
                assert stmt.evidence_span.end > stmt.evidence_span.start
                assert stmt.evidence_span.text in doc.body


class TestManagementExtractorIntegration:
    """Integration tests using synthetic SEC fixtures."""

    @pytest.fixture
    def synthetic_exhibit(self):
        return Path(__file__).parents[1] / "fixtures" / "sec" / "synthetic_exhibit_991.htm"

    def test_exhibit_statement_extraction(self, synthetic_exhibit):
        """Test statement extraction from synthetic exhibit."""
        from trading_copilot.providers.sec_parsers import filing_text

        html = synthetic_exhibit.read_text()
        text = filing_text(html)

        doc = NewsDocument(
            document_id="sec_exhibit:test",
            symbol="SYN",
            headline="Synthetic Corp Q3 Results",
            body=text,
            summary=text[:500],
            publisher="SYN",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            source_url="https://example.com",
            source_type=NewsSourceType.SEC_EXHIBIT,
            provider_id="test",
            content_hash="abc",
        )

        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        statements = extractor.extract_statements(doc)

        assert len(statements) >= 2

        # Check for CEO statement
        ceo_stmts = [s for s in statements if s.speaker_role == "CEO"]
        assert len(ceo_stmts) >= 1
        assert "strong Q3" in ceo_stmts[0].statement or "pleased" in ceo_stmts[0].statement

        # Check for CFO statement
        cfo_stmts = [s for s in statements if s.speaker_role == "CFO"]
        assert len(cfo_stmts) >= 1
        assert "1.55" in cfo_stmts[0].statement or "guidance" in cfo_stmts[0].statement.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
