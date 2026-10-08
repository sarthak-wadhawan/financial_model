"""Models package exports."""

from trading_copilot.models.market import DailyBar, MarketSnapshot, SymbolInfo
from trading_copilot.models.features import EligibilityResult, FeatureRow, QuantScore
from trading_copilot.models.sources import EvidenceClaim as SourceEvidenceClaim, SourceDocument
from trading_copilot.models.analysis import CatalystAnalysis
from trading_copilot.models.results import FinalCandidate, ResearchBrief, RunManifest
from trading_copilot.models.events import (
    EventType,
    EventStatus,
    EventImportance,
    UpsertResult,
    MarketEvent,
    EventRevision,
    EventQueryResult,
)
from trading_copilot.models.news import (
    NewsDocument,
    ManagementStatement,
    EvidenceClaim,
    NewsSourceType,
    StatementType,
    ExtractionMethod,
    ClaimType,
    VerificationStatus,
    EvidenceSpan,
    DeduplicationResult,
    detect_statement_type,
    detect_speaker_role,
    extract_speaker_name,
)

__all__ = [
    "SymbolInfo",
    "DailyBar",
    "MarketSnapshot",
    "FeatureRow",
    "QuantScore",
    "EligibilityResult",
    "SourceDocument",
    "SourceEvidenceClaim",
    "CatalystAnalysis",
    "FinalCandidate",
    "ResearchBrief",
    "RunManifest",
    "EventType",
    "EventStatus",
    "EventImportance",
    "UpsertResult",
    "MarketEvent",
    "EventRevision",
    "EventQueryResult",
    "NewsDocument",
    "ManagementStatement",
    "EvidenceClaim",
    "NewsSourceType",
    "StatementType",
    "ExtractionMethod",
    "ClaimType",
    "VerificationStatus",
    "EvidenceSpan",
    "DeduplicationResult",
    "detect_statement_type",
    "detect_speaker_role",
    "extract_speaker_name",
]