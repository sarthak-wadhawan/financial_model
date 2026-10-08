"""Unit tests for EarningsIntelligenceProvider."""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest

from trading_copilot.models.events import EventImportance, EventStatus, EventType
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.models.sources import SourceDocument


class TestEarningsIntelligenceProvider:
    """Tests for EarningsIntelligenceProvider."""

    @pytest.fixture
    def mock_event_store(self):
        """Create a mock event store."""
        store = Mock()
        store.upsert_event = Mock(return_value=EventType.EARNINGS_RESULT)
        store.get_event_by_source_id = Mock(return_value=None)
        return store

    @pytest.fixture
    def mock_transport(self):
        """Create a mock SEC transport."""
        transport = Mock()
        transport.get = Mock()
        transport.close = Mock()
        return transport

    @pytest.fixture
    def mock_cik_map(self):
        """Create a mock CIK map."""
        cik_map = Mock()
        cik_map.get_cik = Mock(return_value="0000320193")  # AAPL CIK
        return cik_map

    @pytest.fixture
    def provider(self, mock_event_store, mock_transport, mock_cik_map):
        """Create an earnings intelligence provider with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = EarningsIntelligenceProvider(
                event_store=mock_event_store,
                cache_dir=tmpdir,
                transport=mock_transport,
                cik_map=mock_cik_map,
            )
            yield provider
            provider.close()

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert provider.event_store is not None
        assert provider.transport is not None
        assert provider.cik_map is not None
        assert provider.errors == []

    def test_extract_eps_revenue_from_text(self):
        """Test EPS and revenue extraction from earnings text."""
        from trading_copilot.providers.earnings_parsers import extract_eps_revenue
        
        text = """
        Apple Inc. reported diluted earnings per share of $1.55 for the quarter.
        Revenue was $89,500,000,000. Consensus estimate EPS was $1.42.
        Analysts expected revenue of $89,200,000,000.
        """
        result = extract_eps_revenue(text)
        
        assert result["eps_actual"] == "1.55"
        assert result["eps_consensus"] == "1.42"
        assert result["revenue_actual"] == "89500000000"
        assert result["revenue_consensus"] == "89200000000"

    def test_extract_eps_revenue_missing_values(self):
        """Test extraction when some values are missing."""
        from trading_copilot.providers.earnings_parsers import extract_eps_revenue
        
        text = "Apple reported EPS of $1.55."
        result = extract_eps_revenue(text)
        
        assert result["eps_actual"] == "1.55"
        assert result["eps_consensus"] is None
        assert result["revenue_actual"] is None
        assert result["revenue_consensus"] is None

    def test_compute_surprise(self):
        """Test surprise calculation."""
        from trading_copilot.providers.earnings_parsers import compute_surprise
        
        surprise, surprise_pct = compute_surprise("1.55", "1.42")
        assert surprise == "0.13"
        assert surprise_pct == "9.15"
        
        # Test with None inputs
        surprise, surprise_pct = compute_surprise(None, "1.42")
        assert surprise is None
        assert surprise_pct is None
        
        surprise, surprise_pct = compute_surprise("1.55", None)
        assert surprise is None
        assert surprise_pct is None

    def test_compute_surprise_zero_consensus(self):
        """Test surprise calculation with zero consensus."""
        from trading_copilot.providers.earnings_parsers import compute_surprise
        
        surprise, surprise_pct = compute_surprise("1.55", "0")
        assert surprise == "1.55"
        assert surprise_pct is None  # Division by zero handled

    def test_extract_guidance_details(self):
        """Test guidance extraction."""
        from trading_copilot.providers.earnings_parsers import extract_guidance_details
        
        text = "We expect Q4 FY2026 EPS of $1.60 to $1.70 and revenue of $91,000,000,000 to $93,000,000,000. We raised guidance."
        result = extract_guidance_details(text)
        
        assert result is not None
        assert result["eps_guidance_low"] == "1.60"
        assert result["eps_guidance_high"] == "1.70"
        assert result["revenue_guidance_low"] == "91000000000"
        assert result["revenue_guidance_high"] == "93000000000"
        assert result["guidance_change"] == "raised"

    def test_extract_guidance_details_lowered(self):
        """Test guidance extraction with lowered guidance."""
        from trading_copilot.providers.earnings_parsers import extract_guidance_details
        
        text = "We expect Q4 FY2026 EPS of $1.40 to $1.50. We lowered our guidance."
        result = extract_guidance_details(text)
        
        assert result is not None
        assert result["guidance_change"] == "lowered"

    def test_extract_guidance_details_maintained(self):
        """Test guidance extraction with maintained guidance."""
        from trading_copilot.providers.earnings_parsers import extract_guidance_details
        
        text = "We expect Q4 FY2026 EPS of $1.50 to $1.60. We maintain our guidance."
        result = extract_guidance_details(text)
        
        assert result is not None
        assert result["guidance_change"] == "maintained"

    def test_extract_guidance_details_no_range(self):
        """Test guidance extraction when no explicit range."""
        from trading_copilot.providers.earnings_parsers import extract_guidance_details
        
        text = "We are optimistic about the future."
        result = extract_guidance_details(text)
        
        assert result is None

    def test_filing_rows_filters_earnings_forms(self, provider):
        """Test that _filing_rows filters for earnings forms."""
        # Mock the SEC submissions response
        mock_response = Mock()
        mock_response.content = b'{"filings":{"recent":{"accessionNumber":["0000320193-26-000123","0000320193-26-000124"],"filingDate":["2026-10-29","2026-07-30"],"form":["8-K","10-Q"],"primaryDocument":["aapl-20261029.htm","aapl-20260730.htm"],"items":["2.02",""],"reportDate":["2026-09-26","2026-06-27"]},"files":[]}}'
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-26-000123", "0000320193-26-000124"],
                    "filingDate": ["2026-10-29", "2026-07-30"],
                    "form": ["8-K", "10-Q"],
                    "primaryDocument": ["aapl-20261029.htm", "aapl-20260730.htm"],
                    "items": ["2.02", ""],
                    "reportDate": ["2026-09-26", "2026-06-27"],
                },
                "files": []
            }
        }
        provider.transport.get.return_value = mock_response
        
        rows = provider._filing_rows("AAPL", "0000320193", date(2026, 1, 1), date(2026, 12, 31))
        
        # Should include 8-K with Item 2.02 and 10-Q
        assert len(rows) == 2
        assert rows[0]["form"] == "8-K"
        assert rows[1]["form"] == "10-Q"

    def test_filing_rows_excludes_non_earnings_8k(self, provider):
        """Test that 8-K without Item 2.02 is excluded."""
        mock_response = Mock()
        mock_response.content = b'{"filings":{"recent":{"accessionNumber":["0000320193-26-000123","0000320193-26-000124"],"filingDate":["2026-10-29","2026-10-28"],"form":["8-K","8-K"],"primaryDocument":["aapl-20261029.htm","aapl-20261028.htm"],"items":["2.02","5.02"],"reportDate":["2026-09-26","2026-09-26"]},"files":[]}}'
        mock_response.json.return_value = {
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-26-000123", "0000320193-26-000124"],
                    "filingDate": ["2026-10-29", "2026-10-28"],
                    "form": ["8-K", "8-K"],
                    "primaryDocument": ["aapl-20261029.htm", "aapl-20261028.htm"],
                    "items": ["2.02", "5.02"],  # Only first has 2.02
                    "reportDate": ["2026-09-26", "2026-09-26"],
                },
                "files": []
            }
        }
        provider.transport.get.return_value = mock_response
        
        rows = provider._filing_rows("AAPL", "0000320193", date(2026, 1, 1), date(2026, 12, 31))
        
        # Should only include the 8-K with Item 2.02
        assert len(rows) == 1
        assert rows[0]["items"] == "2.02"

    def test_extract_earnings_facts_creates_correct_structure(self, provider):
        """Test that extracted earnings facts include timestamp semantics."""
        # Create a mock document with earnings text
        doc = SourceDocument(
            source_id="0000320193-26-000123",
            symbol="AAPL",
            source_type="8-k",
            title="AAPL 8-K 0000320193-26-000123",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            url="https://www.sec.gov/...",
            provider="sec_edgar",
            text="Apple reported diluted earnings per share of $1.55. Revenue was $89,500,000,000. Consensus estimate EPS was $1.42. Analysts expected revenue of $89,200,000,000.",
            retrieval_time=datetime.now(timezone.utc),
            content_hash="abc123",
            metadata={
                "form": "8-K",
                "filing_date": "2026-10-29",
                "report_date": "2026-09-26",
                "items": ["2.02"],
            },
        )
        
        facts = provider._extract_earnings_facts(doc)
        
        assert facts is not None
        assert facts["eps_actual"] == "1.55"
        assert facts["revenue_actual"] == "89500000000"
        assert facts["eps_consensus"] == "1.42"
        assert facts["revenue_consensus"] == "89200000000"
        assert facts["eps_surprise"] == "0.13"
        assert facts["eps_surprise_pct"] == "9.15"
        
        # Check timestamp semantics
        assert "filing_accepted_at" in facts
        assert "announcement_released_at" in facts
        assert "release_time_source" in facts
        assert "release_time_precision" in facts
        assert facts["release_time_source"] == "sec_filing_accepted"
        assert facts["release_time_precision"] == "filing_accepted"
        # announcement_released_at should be None since we don't have it
        assert facts["announcement_released_at"] is None

    def test_extract_earnings_facts_no_actuals_returns_none(self, provider):
        """Test that filings without actual EPS/revenue return None."""
        doc = SourceDocument(
            source_id="0000320193-26-000123",
            symbol="AAPL",
            source_type="8-k",
            title="AAPL 8-K 0000320193-26-000123",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            url="https://www.sec.gov/...",
            provider="sec_edgar",
            text="Apple announced a new product.",
            retrieval_time=datetime.now(timezone.utc),
            content_hash="abc123",
            metadata={
                "form": "8-K",
                "filing_date": "2026-10-29",
                "items": ["2.02"],
            },
        )
        
        facts = provider._extract_earnings_facts(doc)
        assert facts is None

    def test_create_earnings_result_event_uses_announcement_released_at(self, provider):
        """Test that released_at uses announcement_released_at when available."""
        facts = {
            "fiscal_quarter": "3",
            "fiscal_year": "2026",
            "eps_actual": "1.55",
            "eps_consensus": "1.42",
            "eps_surprise": "0.13",
            "eps_surprise_pct": "9.15",
            "revenue_actual": "89500000000",
            "revenue_consensus": "89200000000",
            "revenue_surprise": "300000000",
            "revenue_surprise_pct": "0.34",
            "report_date": "2026-09-26",
            "source_document_id": "sec_edgar:0000320193-26-000123",
            "source_document_type": "8-K",
            "items": ["2.02"],
            "retrieved_at": "2026-10-29T21:15:00Z",
            "filing_accepted_at": "2026-10-29T21:00:00Z",
            "announcement_released_at": "2026-10-29T20:30:00Z",
            "release_time_source": "press_release",
            "release_time_precision": "minute",
        }
        
        doc = SourceDocument(
            source_id="0000320193-26-000123",
            symbol="AAPL",
            source_type="8-k",
            title="AAPL 8-K 0000320193-26-000123",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            url="https://www.sec.gov/...",
            provider="sec_edgar",
            text="...",
            retrieval_time=datetime.now(timezone.utc),
            content_hash="abc123",
            metadata={"raw_path": "/path/to/raw"},
        )
        
        event = provider._create_earnings_result_event("AAPL", facts, doc)
        
        # Should use announcement_released_at as released_at
        assert event.released_at is not None
        assert event.released_at == datetime(2026, 10, 29, 20, 30, tzinfo=timezone.utc)
        assert event.metadata["announcement_released_at"] == "2026-10-29T20:30:00Z"
        assert event.metadata["filing_accepted_at"] == "2026-10-29T21:00:00Z"

    def test_create_earnings_result_event_no_announcement_time(self, provider):
        """Test that released_at is None when no announcement time available."""
        facts = {
            "fiscal_quarter": "3",
            "fiscal_year": "2026",
            "eps_actual": "1.55",
            "retrieved_at": "2026-10-29T21:15:00Z",
            "filing_accepted_at": "2026-10-29T21:00:00Z",
            "announcement_released_at": None,
            "release_time_source": "sec_filing_accepted",
            "release_time_precision": "filing_accepted",
        }
        
        doc = SourceDocument(
            source_id="0000320193-26-000123",
            symbol="AAPL",
            source_type="8-k",
            title="AAPL 8-K 0000320193-26-000123",
            published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            url="https://www.sec.gov/...",
            provider="sec_edgar",
            text="...",
            retrieval_time=datetime.now(timezone.utc),
            content_hash="abc123",
            metadata={"raw_path": "/path/to/raw"},
        )
        
        event = provider._create_earnings_result_event("AAPL", facts, doc)
        
        # released_at should be None when no announcement time
        assert event.released_at is None
        assert event.metadata["filing_accepted_at"] == "2026-10-29T21:00:00Z"
        assert event.metadata["announcement_released_at"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])