"""Live integration tests for Phase 8 News + Management providers.

Gated by RUN_LIVE_TESTS=1 environment variable.
"""
import os
import tempfile
from datetime import date

import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.providers.news_rss_provider import NewsRSSProvider
from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator
from trading_copilot.providers.llm_provider import create_llm_provider


pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 and SEC_USER_AGENT",
)


def test_sec_exhibit_live_aapl():
    """Test live SEC exhibit extraction for AAPL."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live SEC tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2026, 1, 1),
                to_date=date(2026, 12, 31),
            )
            
            # May have 0 results if no earnings in window
            print(f"SEC exhibit docs: {len(docs)}")
            
            for doc in docs:
                assert doc.symbol == "AAPL"
                assert doc.source_type.value == "sec_exhibit"
                assert doc.content_hash
                assert doc.source_url
                
        finally:
            provider.close()


def test_ir_release_live_aapl():
    """Test live IR RSS feed ingestion for AAPL."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("Network required for live IR tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        provider = IRReleaseProvider()
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL", "MSFT"],
                from_date=date(2026, 1, 1),
                to_date=date(2026, 12, 31),
            )
            
            print(f"IR release docs: {len(docs)}")
            
            for doc in docs:
                assert doc.symbol in ("AAPL", "MSFT")
                assert doc.source_type.value == "company_ir"
                assert doc.content_hash
                assert doc.source_url
                assert doc.published_at
                
        finally:
            provider.close()


def test_news_rss_live_filtered():
    """Test live news RSS ingestion with symbol filtering."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("Network required for live news tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        provider = NewsRSSProvider()
        
        try:
            docs = provider.fetch_news(
                symbols=["AAPL", "MSFT"],
                from_date=date(2026, 10, 1),
                to_date=date(2026, 11, 30),
            )
            
            print(f"News RSS docs (filtered): {len(docs)}")
            
            for doc in docs:
                assert doc.symbol in ("AAPL", "MSFT")
                assert doc.source_type.value == "news_rss"
                assert doc.content_hash
                assert doc.source_url
                
        finally:
            provider.close()


def test_management_extraction_live_aapl():
    """Test management statement extraction on live AAPL data."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Fetch from SEC exhibits
        sec_provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        
        try:
            docs = sec_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2026, 1, 1),
                to_date=date(2026, 12, 31),
            )
            
            if not docs:
                pytest.skip("No SEC exhibits found for AAPL in window")
            
            extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
            all_statements = []
            
            for doc in docs:
                statements = extractor.extract_statements(doc)
                all_statements.extend(statements)
            
            print(f"Management statements extracted: {len(all_statements)}")
            
            for stmt in all_statements:
                assert stmt.symbol == "AAPL"
                assert stmt.statement
                assert stmt.statement_type
                assert stmt.confidence > 0
                assert stmt.evidence_span
                
        finally:
            sec_provider.close()


def test_evidence_claim_generation_live():
    """Test evidence claim generation on live data."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        sec_provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        
        try:
            docs = sec_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2026, 1, 1),
                to_date=date(2026, 12, 31),
            )
            
            if not docs:
                pytest.skip("No SEC exhibits found")
            
            extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
            claim_gen = EvidenceClaimGenerator(min_confidence=0.6)
            
            all_claims = []
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    claim = claim_gen.generate_from_statement(stmt)
                    if claim:
                        all_claims.append(claim)
            
            print(f"Evidence claims generated: {len(all_claims)}")
            
            for claim in all_claims:
                assert claim.claim
                assert claim.category
                assert claim.claim_type
                assert claim.confidence >= 0.6
                assert claim.evidence_span
                assert claim.source_document_id
                
        finally:
            sec_provider.close()


def test_llm_provider_disabled():
    """Test that DisabledLLMProvider works correctly."""
    provider = create_llm_provider()
    
    assert provider.health_check() is True
    assert hasattr(provider, 'extract_statements')
    assert hasattr(provider, 'close')
    
    # Should return empty list when disabled
    from trading_copilot.models.news import NewsDocument, NewsSourceType
    from datetime import datetime, timezone
    
    doc = NewsDocument(
        document_id="test:1",
        symbol="AAPL",
        headline="Test",
        body="CEO Tim Cook said we expect growth.",
        summary="Test",
        publisher="AAPL",
        published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        source_url="https://example.com",
        source_type=NewsSourceType.COMPANY_IR,
        provider_id="test",
        content_hash="abc",
    )
    
    statements = provider.extract_statements(doc)
    assert statements == []
    
    provider.close()


def test_deduplication_engine_live():
    """Test deduplication engine on live data."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live tests")

    from trading_copilot.providers.evidence_claims import DeduplicationEngine
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Fetch from multiple sources
        sec_provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        ir_provider = IRReleaseProvider()
        
        try:
            sec_docs = sec_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2026, 10, 1),
                to_date=date(2026, 11, 30),
            )
            
            ir_docs = ir_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2026, 10, 1),
                to_date=date(2026, 11, 30),
            )
            
            all_docs = sec_docs + ir_docs
            print(f"Total docs before dedup: {len(all_docs)}")
            
            dedup = DeduplicationEngine()
            unique_docs = []
            
            for doc in all_docs:
                is_dup, canonical_id = dedup.check_document(doc)
                if not is_dup:
                    dedup.register_document(doc)
                    unique_docs.append(doc)
                else:
                    print(f"Duplicate found: {doc.document_id} -> {canonical_id}")
            
            print(f"Unique docs after dedup: {len(unique_docs)}")
            assert len(unique_docs) <= len(all_docs)
            
        finally:
            sec_provider.close()
            ir_provider.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])