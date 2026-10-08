"""Deterministic Management Statement Extractor — extracts attributable statements from documents.

Zero-LLM core: uses regex, sentence segmentation, keyword matching, and attribution rules.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from trading_copilot.models.news import (
    EvidenceSpan,
    ManagementStatement,
    NewsDocument,
    NewsSourceType,
    StatementType,
    ExtractionMethod,
    detect_statement_type,
    detect_speaker_role,
    extract_speaker_name,
)

logger = logging.getLogger(__name__)

# Sentence splitting pattern
SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

# Quote patterns for direct quotes
QUOTE_PATTERNS = [
    r'"([^"]{20,500})"',  # Double quotes
    r"'([^']{20,500})'",  # Single quotes
]

# Attribution patterns: "X said", "said X", "X stated", etc.
# Verb part is case-insensitive, name part is case-sensitive (uses [A-Z][a-z]+)
ATTRIBUTION_VERBS = r"(?i:said|stated|noted|commented|added|explained|mentioned|indicated|observed|remarked)"
ATTRIBUTION_VERBS_NO_CAPTURE = r"(?:said|stated|noted|commented|added|explained|mentioned|indicated|observed|remarked)"

ATTRIBUTION_PATTERNS = [
    # "John Smith said..." (case-sensitive for name)
    rf"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+{ATTRIBUTION_VERBS}\b",
    # "said John Smith..." (case-sensitive for name)
    rf"{ATTRIBUTION_VERBS}\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
    # "According to John Smith..."
    r"(?i:according to)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
    # "John Smith, CEO, said..."
    r"([A-Z][a-z]+\s+[A-Z][a-z]+),\s+(?:CEO|CFO|COO|CTO|President|Chairman|VP|SVP|EVP|director|executive)\b",
    # "CEO John Smith said..."
    r"(?:CEO|CFO|COO|CTO|President|Chairman|VP|SVP|EVP|director|executive)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
]


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ManagementExtractor:
    """
    Deterministic extraction of management statements from documents.

    Uses regex, sentence segmentation, and attribution rules.
    No LLM required - this is the zero-LLM baseline.
    """

    def __init__(
        self,
        known_executives: dict[str, dict[str, str]] | None = None,
        min_statement_length: int = 30,
        max_statement_length: int = 1000,
    ):
        self.known_executives = known_executives or {}  # symbol -> {name: role}
        self.min_length = min_statement_length
        self.max_length = max_statement_length
        self.errors: list[dict[str, str]] = []

    def _error(self, symbol: str, stage: str, source_id: str, exc: Exception):
        self.errors.append({
            "symbol": symbol,
            "stage": stage,
            "source_id": source_id,
            "error": type(exc).__name__,
            "message": str(exc)[:300],
        })

    def extract_statements(self, document: NewsDocument) -> list[ManagementStatement]:
        """Extract management statements from a NewsDocument."""
        if not document.body or len(document.body) < self.min_length:
            return []

        symbol = document.symbol or "UNKNOWN"
        statements: list[ManagementStatement] = []

        try:
            # Find all attribution matches in the full text
            all_matches = []
            for pattern in ATTRIBUTION_PATTERNS:
                for match in re.finditer(pattern, document.body):
                    speaker_name = match.group(1).strip()
                    if speaker_name:
                        all_matches.append({
                            'speaker': speaker_name,
                            'start': match.start(),
                            'end': match.end(),
                            'pattern': pattern,
                        })

            # Sort matches by position in text
            all_matches.sort(key=lambda x: x['start'])

            # Deduplicate: same speaker within 50 chars = same attribution
            deduped_matches = []
            for match in all_matches:
                if not deduped_matches:
                    deduped_matches.append(match)
                else:
                    last = deduped_matches[-1]
                    if match['speaker'] == last['speaker'] and match['start'] - last['start'] < 50:
                        continue  # Skip duplicate
                    deduped_matches.append(match)

            # Extract statement for each unique attribution
            for i, match_info in enumerate(deduped_matches):
                statement = self._extract_from_match(
                    match_info=match_info,
                    match_index=i,
                    all_matches=deduped_matches,
                    document=document,
                )
                if statement:
                    statements.append(statement)

            # Also check for direct quotes
            quote_statements = self._extract_quotes(document)
            statements.extend(quote_statements)

        except Exception as exc:
            self._error(symbol, "extract", document.document_id, exc)

        return statements

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle common abbreviations to avoid false splits
        text = re.sub(r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|Inc|Corp|Ltd|Co|vs|etc|e\.g|i\.e)\.', lambda m: m.group(0).replace('.', '<DOT>'), text)
        sentences = SENTENCE_SPLIT.split(text)
        # Restore dots
        sentences = [s.replace('<DOT>', '.').strip() for s in sentences]
        return [s for s in sentences if len(s) >= self.min_length]

    def _extract_from_match(
        self,
        match_info: dict,
        match_index: int,
        all_matches: list[dict],
        document: NewsDocument,
    ) -> ManagementStatement | None:
        """Extract management statement from a match in the full text."""
        speaker_name = match_info['speaker']
        match_start = match_info['start']
        match_end = match_info['end']

        # FIRST: Check known executives for this speaker
        speaker_role = None
        if document.symbol:
            known = self.known_executives.get(document.symbol, {})
            for name, role in known.items():
                if name.lower() in speaker_name.lower() or speaker_name.lower() in name.lower():
                    speaker_role = role
                    break

        # SECOND: If not found in known executives, detect from context BEFORE the match
        if not speaker_role:
            # Only look at text BEFORE the match for role detection
            context_start = max(0, match_start - 60)
            context = document.body[context_start:match_start]
            speaker_role = detect_speaker_role(context)

            # Also check text immediately AFTER match start (for "CEO Name" patterns where role precedes name)
            if not speaker_role:
                after_context = document.body[match_start:match_start + 30]
                speaker_role = detect_speaker_role(after_context)

        # Determine statement text: from match end to next match start (or end of text)
        statement_start = match_end
        if match_index + 1 < len(all_matches):
            statement_end = all_matches[match_index + 1]['start']
        else:
            statement_end = len(document.body)

        statement_text = document.body[statement_start:statement_end].strip()
        
        # Also include the attribution part for context
        full_statement = document.body[match_start:statement_end].strip()
        
        if len(full_statement) > self.max_length:
            full_statement = full_statement[:self.max_length]

        if len(full_statement) < self.min_length:
            return None

        # Determine statement type
        statement_type = detect_statement_type(full_statement)

        # Find evidence span in original document
        evidence_span = self._find_evidence_span(full_statement, document.body)

        # Generate IDs
        content_hash = _sha256(full_statement)
        stmt_id = f"stmt:{document.symbol}:{content_hash[:16]}"

        return ManagementStatement(
            statement_id=stmt_id,
            symbol=document.symbol or "UNKNOWN",
            speaker=speaker_name,
            speaker_role=speaker_role,
            statement=full_statement,
            statement_type=statement_type,
            source_document_id=document.document_id,
            source_url=document.source_url,
            published_at=document.published_at,
            event_date=document.published_at,
            retrieved_at=document.retrieved_at,
            evidence_span=evidence_span,
            extraction_method=ExtractionMethod.DETERMINISTIC,
            confidence=0.8 if speaker_role else 0.6,
            source_type=document.source_type,
            provider_id=document.provider_id,
        )

    def _extract_quotes(self, document: NewsDocument) -> list[ManagementStatement]:
        """Extract direct quotes from document."""
        statements: list[ManagementStatement] = []

        for pattern in QUOTE_PATTERNS:
            for match in re.finditer(pattern, document.body):
                quote_text = match.group(1).strip()
                if len(quote_text) < self.min_length or len(quote_text) > self.max_length:
                    continue

                # Look for attribution near the quote
                speaker_name = "UNKNOWN"
                speaker_role = None

                # Check text before quote
                before_text = document.body[max(0, match.start() - 300):match.start()]
                for pattern in ATTRIBUTION_PATTERNS:
                    attr_match = re.search(pattern, before_text)
                    if attr_match:
                        speaker_name = attr_match.group(1).strip()
                        break

                # Check text after quote
                if speaker_name == "UNKNOWN":
                    after_text = document.body[match.end():match.end() + 300]
                    for pattern in ATTRIBUTION_PATTERNS:
                        attr_match = re.search(pattern, after_text)
                        if attr_match:
                            speaker_name = attr_match.group(1).strip()
                            break

                speaker_role = detect_speaker_role(before_text + " " + after_text)
                if not speaker_role and document.symbol:
                    known = self.known_executives.get(document.symbol, {})
                    for name, role in known.items():
                        if name.lower() in speaker_name.lower() or speaker_name.lower() in name.lower():
                            speaker_role = role
                            break

                statement_type = detect_statement_type(quote_text)

                evidence_span = EvidenceSpan(
                    start=match.start(1),
                    end=match.end(1),
                    text=quote_text
                )

                content_hash = _sha256(quote_text)
                stmt_id = f"quote:{document.symbol}:{content_hash[:16]}"

                statements.append(ManagementStatement(
                    statement_id=stmt_id,
                    symbol=document.symbol or "UNKNOWN",
                    speaker=speaker_name,
                    speaker_role=speaker_role,
                    statement=quote_text,
                    statement_type=statement_type,
                    source_document_id=document.document_id,
                    source_url=document.source_url,
                    published_at=document.published_at,
                    event_date=document.published_at,
                    retrieved_at=document.retrieved_at,
                    evidence_span=evidence_span,
                    extraction_method=ExtractionMethod.DETERMINISTIC,
                    confidence=0.7,
                    source_type=document.source_type,
                    provider_id=document.provider_id,
                ))

        return statements

    def _find_evidence_span(self, statement: str, full_text: str) -> Optional[EvidenceSpan]:
        """Find character span of statement in full text."""
        # Try exact match first
        idx = full_text.find(statement)
        if idx >= 0:
            return EvidenceSpan(start=idx, end=idx + len(statement), text=statement)

        # Try fuzzy match (first 50 chars)
        prefix = statement[:50]
        idx = full_text.find(prefix)
        if idx >= 0:
            end_idx = idx + len(statement)
            if end_idx <= len(full_text):
                return EvidenceSpan(start=idx, end=end_idx, text=full_text[idx:end_idx])

        return None


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# Common executive database (can be extended/updated from Phase 6 leadership data)
COMMON_EXECUTIVES = {
    "AAPL": {"Tim Cook": "CEO", "Luca Maestri": "CFO"},
    "MSFT": {"Satya Nadella": "CEO", "Amy Hood": "CFO"},
    "GOOGL": {"Sundar Pichai": "CEO", "Ruth Porat": "CFO"},
    "AMZN": {"Andy Jassy": "CEO", "Brian Olsavsky": "CFO"},
    "META": {"Mark Zuckerberg": "CEO", "Susan Li": "CFO"},
    "NVDA": {"Jensen Huang": "CEO", "Colette Kress": "CFO"},
    "TSLA": {"Elon Musk": "CEO", "Vaibhav Taneja": "CFO"},
    "JPM": {"Jamie Dimon": "CEO", "Jeremy Barnum": "CFO"},
    "V": {"Ryan McInerney": "CEO", "Vasant Prabhu": "CFO"},
    "MA": {"Michael Miebach": "CEO", "Sachin Mehra": "CFO"},
}


if __name__ == "__main__":
    # Quick test
    extractor = ManagementExtractor(known_executives=COMMON_EXECUTIVES)

    # Create a test document
    from trading_copilot.models.news import NewsDocument, NewsSourceType

    test_doc = NewsDocument(
        document_id="test:1",
        symbol="AAPL",
        headline="Apple Reports Q3 Results",
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

    statements = extractor.extract_statements(test_doc)
    for stmt in statements:
        print(f"Speaker: {stmt.speaker} ({stmt.speaker_role})")
        print(f"Type: {stmt.statement_type}")
        print(f"Statement: {stmt.statement[:100]}")
        print(f"Evidence: {stmt.evidence_span}")
        print("---")