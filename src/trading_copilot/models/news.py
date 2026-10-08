"""News and Evidence models for Phase 8 — structured evidence layer."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class NewsSourceType(str, Enum):
    """Type of news/source document."""
    SEC_EXHIBIT = "sec_exhibit"           # SEC filing exhibit (99.1, etc.)
    COMPANY_IR = "company_ir"              # Company investor relations release
    NEWS_RSS = "news_rss"                  # RSS feed from news publisher
    STRUCTURED_PROVIDER = "structured_provider"  # Free structured news API


class StatementType(str, Enum):
    """Categorization of management statements."""
    GUIDANCE = "guidance"
    DEMAND = "demand"
    MARGINS = "margins"
    COSTS = "costs"
    CAPEX = "capital_spending"
    COMPETITION = "competition"
    PRODUCT = "product"
    REGULATION = "regulation"
    SUPPLY = "supply"
    PRICING = "pricing"
    STRATEGY = "strategy"
    RISKS = "risks"
    MACRO = "macro_conditions"
    OTHER = "other"


class ExtractionMethod(str, Enum):
    """How the claim/statement was extracted."""
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class ClaimType(str, Enum):
    """Type of claim for evidence model."""
    FACT = "fact"
    ATTRIBUTED_STATEMENT = "attributed_statement"
    DETERMINISTIC_DERIVATION = "deterministic_derivation"
    AI_EXTRACTION = "ai_extraction"


class VerificationStatus(str, Enum):
    """Verification status of evidence claim."""
    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"


class EvidenceSpan(BaseModel):
    """Character span of evidence in source text."""
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: int, info) -> int:
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be greater than start")
        return v


class NewsDocument(BaseModel):
    """Normalized news/company release document."""

    document_id: str
    symbol: Optional[str] = None
    headline: str
    body: str
    summary: Optional[str] = None
    publisher: str
    published_at: datetime
    retrieved_at: datetime
    source_url: str
    source_type: NewsSourceType
    author: Optional[str] = None
    provider_id: str
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Deduplication
    dedup_key: Optional[str] = None  # canonical key for cross-source dedup
    related_documents: list[str] = Field(default_factory=list)  # other document_ids this relates to

    # SEC linkage
    sec_filing_id: Optional[str] = None  # e.g., "sec_edgar:0000320193-26-000123"
    exhibit_number: Optional[str] = None  # e.g., "99.1"

    def __hash__(self) -> int:
        return hash(self.document_id)


class ManagementStatement(BaseModel):
    """Attributable management statement with evidence."""

    statement_id: str
    symbol: str
    speaker: str
    speaker_role: Optional[str] = None
    statement: str
    statement_type: StatementType
    source_document_id: str
    source_url: str
    published_at: datetime
    event_date: Optional[datetime] = None  # when statement was made (may differ from published)
    retrieved_at: datetime
    evidence_span: Optional[EvidenceSpan] = None
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    # Provenance
    source_type: NewsSourceType
    provider_id: str


class EvidenceClaim(BaseModel):
    """Structured evidence claim for Phase 9 consumption."""

    claim_id: str
    symbol: str
    claim: str
    category: StatementType
    claim_type: ClaimType
    speaker: Optional[str] = None
    speaker_role: Optional[str] = None
    source_document_id: str
    source_url: str
    published_at: datetime
    event_date: Optional[datetime] = None
    evidence_span: Optional[EvidenceSpan] = None
    extraction_method: ExtractionMethod = ExtractionMethod.DETERMINISTIC
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_status: VerificationStatus = VerificationStatus.PENDING

    # Provenance
    source_type: NewsSourceType
    provider_id: str

    # For deterministic derivations
    derivation: Optional[str] = None  # e.g., "surprise = actual - consensus"

    def __hash__(self) -> int:
        return hash(self.claim_id)


class DeduplicationResult(BaseModel):
    """Result of deduplication check."""
    is_duplicate: bool
    canonical_document_id: Optional[str] = None
    match_type: Optional[str] = None  # "url" | "content_hash" | "headline_date" | "similarity"
    similarity_score: Optional[float] = None


# Statement type detection patterns (for deterministic extraction)
STATEMENT_TYPE_PATTERNS = {
    StatementType.GUIDANCE: [
        r"(?:expect|anticipate|project|forecast|guidance|outlook).*?(?:revenue|sales|earnings|EPS|margin).*?(?:\$|percent|%)",
        r"(?:guidance|outlook).*?(?:raise|lower|maintain|reaffirm)",
    ],
    StatementType.DEMAND: [
        r"(?:demand|order|booking|backlog).*?(?:strong|weak|accelerat|decelerat|soft|robust)",
        r"(?:customer|client).*?(?:demand|spend|budget)",
    ],
    StatementType.MARGINS: [
        r"(?:margin|profitability).*?(?:expand|contract|improv|degrad|pressure|headwind|tailwind)",
        r"(?:gross margin|operating margin|EBITDA margin)",
    ],
    StatementType.COSTS: [
        r"(?:cost|expense|spending).*?(?:increas|decreas|higher|lower|inflation|deflation)",
        r"(?:raw material|labor|freight|logistics|supply chain).*?cost",
    ],
    StatementType.CAPEX: [
        r"(?:capital expenditure|capex|investment).*?(?:increas|decreas|\$|billion|million)",
        r"(?:factory|plant|facility|capacity).*?(?:expand|build|invest)",
    ],
    StatementType.COMPETITION: [
        r"(?:competitor|competition|market share).*?(?:gain|lose|intensify|rational)",
        r"(?:pricing pressure|competitive landscape)",
    ],
    StatementType.PRODUCT: [
        r"(?:product|launch|release|innovation|pipeline).*?(?:new|upcoming|delay|accelerat)",
        r"(?:R&D|research|development).*?(?:invest|spend|focus)",
    ],
    StatementType.REGULATION: [
        r"(?:regulatory|regulation|FDA|SEC|antitrust|compliance).*?(?:approv|deny|investigat|chang|impact)",
    ],
    StatementType.SUPPLY: [
        r"(?:supply chain|supplier|inventory|shortage|constraint).*?(?:improv|degrad|resolv|persist)",
    ],
    StatementType.PRICING: [
        r"(?:pricing|price).*?(?:increas|decreas|hike|cut|pressure|power|flexibility)",
    ],
    StatementType.STRATEGY: [
        r"(?:strategic|strategy|acquisition|divestiture|partnership|joint venture).*?(?:announc|complet|explor|pursu)",
    ],
    StatementType.RISKS: [
        r"(?:risk|uncertainty|challenge|headwind).*?(?:material|significant|elevat|increas)",
        r"(?:guidance|outlook).*?(?:risk|assum|depend)",
    ],
    StatementType.MACRO: [
        r"(?:macro|economic|inflation|interest rate|GDP|consumer|recession).*?(?:impact|affect|environ|condition)",
        r"(?:foreign exchange|FX|currency).*?(?:impact|headwind|tailwind)",
    ],
}


def detect_statement_type(text: str) -> StatementType:
    """Detect statement type from text using keyword patterns."""
    text_lower = text.lower()
    scores = {st: 0 for st in StatementType}

    for stmt_type, patterns in STATEMENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            import re
            if re.search(pattern, text_lower, re.IGNORECASE):
                scores[stmt_type] += 1

    # Return highest scoring type, default to OTHER
    best_type = max(scores, key=scores.get)
    return best_type if scores[best_type] > 0 else StatementType.OTHER


# Speaker role detection patterns
SPEAKER_ROLE_PATTERNS = [
    (r"\b(?:chief executive officer|CEO)\b", "CEO"),
    (r"\b(?:chief financial officer|CFO)\b", "CFO"),
    (r"\b(?:chief operating officer|COO)\b", "COO"),
    (r"\b(?:chief technology officer|CTO)\b", "CTO"),
    (r"\b(?:president)\b", "President"),
    (r"\b(?:chairman|chair)\b", "Chairman"),
    (r"\b(?:vice president|VP)\b", "VP"),
    (r"\b(?:director|board member)\b", "Director"),
    (r"\b(?:senior vice president|SVP)\b", "SVP"),
    (r"\b(?:executive vice president|EVP)\b", "EVP"),
]


def detect_speaker_role(text: str) -> Optional[str]:
    """Detect speaker role from text."""
    import re
    text_lower = text.lower()
    for pattern, role in SPEAKER_ROLE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return role
    return None


def extract_speaker_name(text: str, known_executives: dict[str, str] | None = None) -> Optional[str]:
    """Extract speaker name from text. Returns UNKNOWN if not found."""
    import re

    # Look for patterns like "John Smith, CEO, said..." or "said John Smith, CEO"
    patterns = [
        r"([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:CEO|CFO|COO|CTO|President|Chairman|VP|SVP|EVP|director|executive)\b",
        r"(?:said|stated|noted|commented|added)\s+([A-Z][a-z]+\s+[A-Z][a-z]+),?\s+(?:CEO|CFO|COO|CTO|President|Chairman|VP|SVP|EVP|director|executive)",
        r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:said|stated|noted|commented|added)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Validate against known executives if provided
            if known_executives:
                for exec_name in known_executives:
                    if exec_name.lower() in name.lower() or name.lower() in exec_name.lower():
                        return exec_name
            return name

    return "UNKNOWN"


if __name__ == "__main__":
    # Quick test
    test_text = "CEO Tim Cook said we expect revenue growth to accelerate in Q4."
    print(f"Speaker: {extract_speaker_name(test_text)}")
    print(f"Role: {detect_speaker_role(test_text)}")
    print(f"Type: {detect_statement_type(test_text)}")