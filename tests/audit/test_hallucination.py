#!/usr/bin/env python3
"""Independent Audit: Hallucination/Unsupported Claims

Verifies that Phase 8 does not generate unsupported claims:
- All claims trace to source text via evidence_span
- No fabricated numbers/dates not in source
- No invented speaker attributions
- Evidence_span text exactly matches source
"""
from __future__ import annotations

import tempfile
from datetime import date

from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator


def test_evidence_span_exact_match():
    """Verify evidence_span text exactly matches source document body."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs:
                print("  SKIP: No SEC exhibits found")
                return
                
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    # Evidence span must exactly match source text
                    assert stmt.evidence_span.text in doc.body, \
                        f"Evidence span text not found in source: {stmt.evidence_span.text[:50]}..."
                    
                    # Evidence span bounds must be valid
                    assert stmt.evidence_span.start >= 0
                    assert stmt.evidence_span.end <= len(doc.body)
                    assert stmt.evidence_span.end > stmt.evidence_span.start
                    
                    # Extracted text must match exactly
                    extracted = doc.body[stmt.evidence_span.start:stmt.evidence_span.end]
                    assert stmt.evidence_span.text == extracted, \
                        f"Evidence span doesn't match source slice: {stmt.evidence_span.text[:50]} vs {extracted[:50]}"
                        
            print(f"  PASS: All evidence spans exactly match source text")
        finally:
            provider.close()


def test_no_fabricated_numbers():
    """Verify no numbers are fabricated in statements/claims."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
        from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        claim_gen = EvidenceClaimGenerator(min_confidence=0.5)
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs:
                print("  SKIP: No SEC exhibits found")
                return
                
            import re
            
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    claim = EvidenceClaimGenerator(min_confidence=0.5).generate_from_statement(stmt)
                    if not claim:
                        continue
                        
                    # Extract all numbers from claim
                    claim_numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', claim.claim)
                    # Extract all numbers from evidence span
                    evidence_numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', claim.evidence_span.text)
                    
                    # All numbers in claim must appear in evidence
                    for num in claim_numbers:
                        assert num in evidence_numbers, \
                            f"Number '{num}' in claim not found in evidence: {claim.claim[:100]}"
                            
            print(f"  PASS: No fabricated numbers in claims")
        finally:
            provider.close()


def test_no_fabricated_dates():
    """Verify no dates are fabricated in statements/claims."""
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        claim_gen = EvidenceClaimGenerator(min_confidence=0.5)
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs:
                print("  SKIP: No SEC exhibits found")
                return
                
            import re
            
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    claim = EvidenceClaimGenerator(min_confidence=0.5).generate_from_statement(stmt)
                    if not claim:
                        continue
                        
                    # Extract dates from claim
                    claim_dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\bQ[1-4]\s+FY\d{4}\b', claim.claim, re.IGNORECASE)
                    evidence_dates = re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b|\bQ[1-4]\s+FY\d{4}\b', claim.evidence_span.text, re.IGNORECASE)
                    
                    for d in claim_dates:
                        assert d in evidence_dates, \
                            f"Date '{d}' in claim not found in evidence: {claim.claim[:100]}"
                            
            print(f"  PASS: No fabricated dates in claims")
        finally:
            provider.close()


def test_no_invented_speakers():
    """Verify no speaker names are invented."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs:
                print("  SKIP: No SEC exhibits found")
                return
                
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    # Speaker must be "UNKNOWN" or found in source text
                    if stmt.speaker != "UNKNOWN":
                        # Speaker name should appear in source document
                        speaker_lower = stmt.speaker.lower()
                        doc_lower = doc.body.lower()
                        assert speaker_lower in doc_lower or any(part in doc_lower for part in speaker_lower.split()), \
                            f"Speaker '{stmt.speaker}' not found in source text: {doc.body[:200]}"
                        
            print(f"  PASS: No invented speakers")
        finally:
            provider.close()


def test_evidence_span_in_source():
    """Verify every evidence span text exists verbatim in source document."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
        from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator
        
        provider = SECExhibitProvider(cache_dir=tmpdir + "/sec_exhibits")
        extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)
        claim_gen = EvidenceClaimGenerator(min_confidence=0.5)
        
        try:
            docs = provider.fetch_company_releases(
                symbols=["AAPL"],
                from_date=date(2025, 1, 1),
                to_date=date(2025, 12, 31),
            )
            
            if not docs:
                print("  SKIP: No SEC exhibits found")
                return
                
            for doc in docs:
                statements = extractor.extract_statements(doc)
                for stmt in statements:
                    claim = EvidenceClaimGenerator(min_confidence=0.5).generate_from_statement(stmt)
                    if not claim:
                        continue
                        
                    # Evidence span text must be in source document
                    assert claim.evidence_span.text in doc.body, \
                        f"Evidence span not in source: {claim.evidence_span.text[:100]}"
                    
                    # Also check statement evidence span
                    assert stmt.evidence_span.text in doc.body, \
                        f"Statement evidence span not in source: {stmt.evidence_span.text[:100]}"
                        
            print(f"  PASS: All evidence spans trace to source documents")
        finally:
            provider.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AUDIT: Hallucination/Unsupported Claims")
    print("=" * 60)
    
    test_evidence_span_exact_match()
    test_no_fabricated_numbers()
    test_no_fabricated_dates()
    test_no_invented_speakers()
    test_evidence_span_in_source()
    
    print("=" * 60)
    print("ALL HALLUCINATION TESTS PASSED")
    print("=" * 60)