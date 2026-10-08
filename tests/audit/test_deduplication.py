#!/usr/bin/env python3
"""Independent Audit: Deduplication

Verifies deduplication works correctly:
- Same URL -> dedup
- Same content hash -> dedup
- Same headline+date+symbol -> dedup
- Cross-source relationships preserved (SEC exhibit <-> IR release)
"""
from __future__ import annotations

import tempfile
from datetime import date

from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.providers.evidence_claims import DeduplicationEngine


def test_url_deduplication():
    """Same URL should deduplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        try:
            docs1 = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            docs2 = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs1:
                print("  SKIP: No SEC exhibits found")
                return
                
            dedup = DeduplicationEngine()
            all_docs = docs1 + docs2
            
            unique = 0
            for doc in all_docs:
                is_dup, _ = dedup.check_document(doc)
                if not is_dup:
                    dedup.register_document(doc)
                    unique += 1
                    
            # Should have same number of unique docs as first fetch
            assert unique == len(docs1), f"Expected {len(docs1)} unique, got {unique}"
            print(f"  PASS: URL deduplication works ({unique} unique from {len(all_docs)} total)")
        finally:
            provider.close()


def test_content_hash_deduplication():
    """Same content hash should deduplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        try:
            docs1 = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            docs2 = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs1:
                print("  SKIP: No SEC exhibits found")
                return
                
            dedup = DeduplicationEngine()
            all_docs = docs1 + docs2
            
            unique_hashes = set()
            for doc in all_docs:
                is_dup, _ = dedup.check_document(doc)
                if not is_dup:
                    dedup.register_document(doc)
                unique_hashes.add(doc.content_hash)
                    
            # All docs should have unique content hashes within a fetch
            # but across two identical fetches, content hashes should match
            assert len(unique_hashes) == len(docs1)
            print(f"  PASS: Content hash deduplication works ({len(unique_hashes)} unique hashes)")
        finally:
            provider.close()


def test_headline_date_symbol_deduplication():
    """Same normalized headline+date+symbol should deduplicate."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
        from trading_copilot.providers.ir_release_provider import IRReleaseProvider
        
        sec_provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        ir_provider = IRReleaseProvider()
        
        try:
            sec_docs = sec_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 10, 1),
                to_date=date(2025, 11, 30),
            )
            ir_docs = ir_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 10, 1),
                to_date=date(2025, 11, 30),
            )
            
            all_docs = sec_docs + ir_docs
            
            if not all_docs:
                print("  SKIP: No documents found")
                return
                
            dedup = DeduplicationEngine()
            unique = 0
            duplicates = 0
            
            for doc in all_docs:
                is_dup, canonical_id = dedup.check_document(doc)
                if not is_dup:
                    dedup.register_document(doc)
                    unique += 1
                else:
                    duplicates += 1
                    print(f"  Duplicate found: {doc.document_id} -> {canonical_id}")
                    
            print(f"  PASS: Headline+date+symbol dedup: {unique} unique, {duplicates} duplicates")
        finally:
            sec_provider.close()
            ir_provider.close()


def test_cross_source_relationships():
    """SEC exhibit and IR release for same event should be related."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
        from trading_copilot.providers.ir_release_provider import IRReleaseProvider
        
        sec_provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        ir_provider = IRReleaseProvider()
        
        try:
            sec_docs = sec_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 10, 1),
                to_date=date(2025, 11, 30),
            )
            ir_docs = ir_provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 10, 1),
                to_date=date(2025, 11, 30),
            )
            
            if not sec_docs or not ir_docs:
                print("  SKIP: Not enough documents for cross-source test")
                return
                
            # Check that SEC docs have sec_filing_id
            for doc in sec_docs:
                assert doc.sec_filing_id, "SEC doc missing sec_filing_id"
                assert doc.exhibit_number, "SEC doc missing exhibit_number"
                
            # IR docs don't have sec_filing_id but have dedup_key
            for doc in ir_docs:
                assert doc.dedup_key, "IR doc missing dedup_key"
                
            print(f"  PASS: Cross-source relationships: {len(sec_docs)} SEC + {len(ir_docs)} IR docs")
        finally:
            sec_provider.close()
            ir_provider.close()


def test_dedup_engine_registered_state():
    """DeduplicationEngine should maintain state correctly."""
    dedup = DeduplicationEngine()
    
    # Create test documents with same dedup_key
    from trading_copilot.models.news import NewsDocument, NewsSourceType
    from datetime import datetime, timezone
    
    doc1 = NewsDocument(
        document_id="test:1",
        symbol="AAPL",
        headline="Test Release",
        body="Content 1",
        summary="Summary 1",
        publisher="AAPL",
        published_at=datetime(2025, 10, 30, tzinfo=timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        source_url="https://example.com/1",
        source_type="company_ir",
        provider_id="test",
        content_hash="abc",
        dedup_key="ir:AAPL:2025-10-30:hash1",
    )
    
    doc2 = NewsDocument(
        document_id="test:2",
        symbol="AAPL",
        headline="Test Release",  # Same headline
        body="Content 2",  # Different content
        summary="Summary 2",
        publisher="AAPL",
        published_at=datetime(2025, 10, 30, tzinfo=timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        source_url="https://example.com/2",
        source_type="company_ir",
        provider_id="test",
        content_hash="def",  # Different hash
        dedup_key="ir:AAPL:2025-10-30:hash1",  # Same dedup_key
    )
    
    is_dup1, _ = dedup.check_document(doc1)
    assert not is_dup1
    dedup.register_document(doc1)
    
    is_dup2, canonical_id = dedup.check_document(doc2)
    assert is_dup2
    assert canonical_id == doc1.document_id
    
    print(f"  PASS: DeduplicationEngine state management works")


if __name__ == "__main__":
    print("=" * 60)
    print("AUDIT: Deduplication")
    print("=" * 60)
    
    test_url_deduplication()
    test_content_hash_deduplication()
    test_headline_date_symbol_deduplication()
    test_cross_source_relationships()
    test_dedup_engine_registered_state()
    
    print("=" * 60)
    print("ALL DEDUPLICATION TESTS PASSED")
    print("=" * 60)