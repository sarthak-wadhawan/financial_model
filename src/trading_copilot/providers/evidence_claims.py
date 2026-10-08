"""Evidence Claims Generator — converts management statements into structured evidence claims for Phase 9."""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from trading_copilot.models.news import (
    EvidenceClaim,
    EvidenceSpan,
    ManagementStatement,
    NewsDocument,
    NewsSourceType,
    StatementType,
    ExtractionMethod,
    ClaimType,
    VerificationStatus,
    detect_statement_type,
)

logger = logging.getLogger(__name__)


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class EvidenceClaimGenerator:
    """
    Generates structured evidence claims from management statements and documents.

    Evidence claims are the primary output of Phase 8, consumed by Phase 9.
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        require_speaker: bool = True,
    ):
        self.min_confidence = min_confidence
        self.require_speaker = require_speaker

    def generate_from_statement(self, statement: ManagementStatement) -> Optional[EvidenceClaim]:
        """Convert a management statement into an evidence claim."""
        if statement.confidence < self.min_confidence:
            return None

        if self.require_speaker and statement.speaker == "UNKNOWN":
            return None

        # Determine claim type
        claim_type = self._determine_claim_type(statement)

        # Generate claim text
        claim_text = self._format_claim(statement)

        # Find evidence span if not already present
        evidence_span = statement.evidence_span
        if evidence_span is None and statement.source_document_id:
            # Would need access to source document body
            pass

        content_hash = _sha256(claim_text + statement.source_document_id)
        claim_id = f"claim:{statement.symbol}:{content_hash[:16]}"

        return EvidenceClaim(
            claim_id=claim_id,
            symbol=statement.symbol,
            claim=claim_text,
            category=statement.statement_type,
            claim_type=claim_type,
            speaker=statement.speaker,
            speaker_role=statement.speaker_role,
            source_document_id=statement.source_document_id,
            source_url=statement.source_url,
            published_at=statement.published_at,
            event_date=statement.event_date,
            evidence_span=evidence_span,
            extraction_method=statement.extraction_method,
            confidence=statement.confidence,
            verification_status=VerificationStatus.PENDING,
            source_type=statement.source_type,
            provider_id=statement.provider_id,
        )

    def generate_from_document(self, document: NewsDocument) -> list[EvidenceClaim]:
        """Generate evidence claims directly from a document (fact extraction)."""
        claims: list[EvidenceClaim] = []

        if not document.body:
            return claims

        # Extract factual claims from document
        fact_claims = self._extract_factual_claims(document)
        claims.extend(fact_claims)

        return claims

    def _determine_claim_type(self, statement: ManagementStatement) -> ClaimType:
        """Determine the claim type from statement metadata."""
        if statement.extraction_method == ExtractionMethod.LLM:
            return ClaimType.AI_EXTRACTION
        elif statement.speaker and statement.speaker != "UNKNOWN":
            return ClaimType.ATTRIBUTED_STATEMENT
        else:
            return ClaimType.FACT

    def _format_claim(self, statement: ManagementStatement) -> str:
        """Format statement into a structured claim."""
        parts = []

        if statement.speaker and statement.speaker != "UNKNOWN":
            role_str = f" ({statement.speaker_role})" if statement.speaker_role else ""
            parts.append(f"{statement.speaker}{role_str} stated:")

        parts.append(statement.statement)
        return " ".join(parts)

    def _extract_factual_claims(self, document: NewsDocument) -> list[EvidenceClaim]:
        """Extract verifiable factual claims from document (deterministic)."""
        claims: list[EvidenceClaim] = []

        # This would extract things like:
        # - Specific numerical guidance
        # - Product launch dates
        # - Acquisition announcements
        # - etc.

        # For now, return empty - Phase 8 focuses on management statements
        return claims


class DeduplicationEngine:
    """
    Deduplicates documents and statements across sources.

    Uses multiple signals:
    1. Canonical URL match (primary)
    2. Content hash match (primary)
    3. Normalized headline + symbol + date (secondary)
    4. Text similarity (tertiary)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
    ):
        self.similarity_threshold = similarity_threshold
        self._canonical_urls: dict[str, str] = {}  # url -> canonical_doc_id
        self._content_hashes: dict[str, str] = {}  # hash -> canonical_doc_id
        self._headline_keys: dict[str, str] = {}  # normalized_headline -> canonical_doc_id

    def check_document(self, document: NewsDocument) -> tuple[bool, Optional[str]]:
        """
        Check if document is a duplicate.

        Returns (is_duplicate, canonical_document_id).
        """
        # 1. Check canonical URL
        if document.source_url in self._canonical_urls:
            return True, self._canonical_urls[document.source_url]

        # 2. Check content hash
        if document.content_hash in self._content_hashes:
            return True, self._content_hashes[document.content_hash]

        # 3. Check normalized headline key
        headline_key = self._normalize_headline_key(document)
        if headline_key in self._headline_keys:
            # Verify it's the same symbol and close date
            canonical_id = self._headline_keys[headline_key]
            return True, canonical_id

        return False, None

    def register_document(self, document: NewsDocument):
        """Register a document as canonical."""
        self._canonical_urls[document.source_url] = document.document_id
        self._content_hashes[document.content_hash] = document.document_id
        headline_key = self._normalize_headline_key(document)
        self._headline_keys[headline_key] = document.document_id

        # Also register dedup_key if present
        if document.dedup_key:
            self._headline_keys[document.dedup_key] = document.document_id

    def _normalize_headline_key(self, document: NewsDocument) -> str:
        """Create normalized key for headline-based deduplication."""
        import re
        # Normalize headline: lowercase, remove punctuation, remove common words
        headline = document.headline.lower()
        headline = re.sub(r"[^\w\s]", "", headline)
        headline = re.sub(r"\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b", "", headline)
        headline = re.sub(r"\s+", " ", headline).strip()

        symbol = (document.symbol or "unknown").upper()
        date_str = document.published_at.date().isoformat()

        return f"{symbol}:{date_str}:{headline[:100]}"

    def get_relationships(self, document: NewsDocument) -> list[str]:
        """Get related document IDs for cross-source relationships."""
        # This would find other documents that are related (same event, different source)
        related = []

        # Check if this is an SEC exhibit and there's an IR release for same event
        if document.source_type.value == "sec_exhibit" and document.sec_filing_id:
            # Could look up related IR release
            pass

        return related


def create_evidence_claim_generator(
    min_confidence: float = 0.5,
    require_speaker: bool = True,
) -> EvidenceClaimGenerator:
    return EvidenceClaimGenerator(min_confidence=min_confidence, require_speaker=require_speaker)


def create_deduplication_engine(
    similarity_threshold: float = 0.85,
) -> DeduplicationEngine:
    return DeduplicationEngine(similarity_threshold=similarity_threshold)


if __name__ == "__main__":
    # Quick test
    from trading_copilot.models.news import (
        ManagementStatement,
        NewsDocument,
        NewsSourceType,
        StatementType,
        ExtractionMethod,
        EvidenceSpan,
    )

    generator = create_evidence_claim_generator()

    stmt = ManagementStatement(
        statement_id="test:1",
        symbol="AAPL",
        speaker="Tim Cook",
        speaker_role="CEO",
        statement="We expect revenue growth to accelerate in Q4.",
        statement_type=StatementType.GUIDANCE,
        source_document_id="test:doc1",
        source_url="https://example.com",
        published_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
        event_date=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
        retrieved_at=datetime.now(timezone.utc),
        evidence_span=EvidenceSpan(start=100, end=150, text="We expect revenue growth to accelerate in Q4."),
        extraction_method=ExtractionMethod.DETERMINISTIC,
        confidence=0.9,
        source_type=NewsSourceType.COMPANY_IR,
        provider_id="test",
    )

    claim = generator.generate_from_statement(stmt)
    if claim:
        print(f"Claim: {claim.claim}")
        print(f"Category: {claim.category}")
        print(f"Type: {claim.claim_type}")
        print(f"Speaker: {claim.speaker}")
        print(f"Confidence: {claim.confidence}")