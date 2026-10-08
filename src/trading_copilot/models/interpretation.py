"""Interpretation Engine models — structured interpretation output contracts."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ImpactDirection(str, Enum):
    """Direction of company impact."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ImpactMagnitude(str, Enum):
    """Magnitude of impact."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class TimeHorizon(str, Enum):
    """Time horizon for impact."""
    IMMEDIATE = "immediate"      # same day / intraday
    SHORT_TERM = "short_term"    # days to weeks
    MEDIUM_TERM = "medium_term"  # weeks to months
    LONG_TERM = "long_term"      # months to quarters
    UNKNOWN = "unknown"


class StockBias(str, Enum):
    """Directional stock bias."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    MIXED = "mixed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence level for interpretation."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScenarioType(str, Enum):
    """Scenario type."""
    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class EvidenceRef(BaseModel):
    """Reference to supporting evidence."""
    evidence_id: str
    source_type: str  # e.g., "sec_filing", "news", "earnings", "management_statement"
    description: str
    url: Optional[str] = None
    timestamp: Optional[datetime] = None


class CompanyImpact(BaseModel):
    """Company fundamental impact assessment."""
    direction: ImpactDirection
    magnitude: ImpactMagnitude
    horizon: TimeHorizon
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    def __hash__(self) -> int:
        return hash((self.direction, self.magnitude, self.horizon))


class StockImpact(BaseModel):
    """Stock price impact assessment."""
    bias: StockBias
    magnitude: ImpactMagnitude
    horizon: TimeHorizon
    reasons: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

    def __hash__(self) -> int:
        return hash((self.bias, self.magnitude, self.horizon))


class Scenario(BaseModel):
    """Scenario analysis (base/bull/bear)."""
    scenario_type: ScenarioType
    description: str
    required_conditions: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    probability_band: Optional[str] = None  # e.g., "40-60%"

    def __hash__(self) -> int:
        return hash((self.scenario_type, self.description))


class ViewChangeTrigger(BaseModel):
    """Specific evidence that would change the current view."""
    trigger: str
    description: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


class Interpretation(BaseModel):
    """Complete structured interpretation for a symbol/event."""

    interpretation_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Core interpretation
    headline: str
    what_happened: str
    what_it_means: str
    why_it_matters: str

    # Impact assessments
    company_impact: CompanyImpact
    stock_impact: StockImpact

    # Scenario analysis
    base_case: Scenario
    bull_case: Scenario
    bear_case: Scenario

    # View change triggers
    what_would_change_view: list[ViewChangeTrigger] = Field(default_factory=list)

    # Confidence and provenance
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence_reasons: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)

    # Evidence traceability
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)

    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_version: str = "1.0"

    def __hash__(self) -> int:
        return hash(self.interpretation_id)


class InterpretationRequest(BaseModel):
    """Request to generate an interpretation."""
    symbol: str
    as_of: Optional[datetime] = None
    force_refresh: bool = False
    focus_events: Optional[list[str]] = None  # event IDs to focus on
    include_quant_context: bool = True


class Answer(BaseModel):
    """Answer to a specific question."""
    question: str
    answer: str
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AnswerRequest(BaseModel):
    """Request for a specific answer."""
    symbol: str
    question: str
    context: Optional[dict[str, Any]] = None


if __name__ == "__main__":
    # Quick test
    impact = CompanyImpact(
        direction=ImpactDirection.POSITIVE,
        magnitude=ImpactMagnitude.MEDIUM,
        horizon=TimeHorizon.MEDIUM_TERM,
        reasons=["Guidance raised 5%", "Revenue growth accelerating"],
        confidence=0.8
    )
    print(f"CompanyImpact: {impact}")

    stock = StockImpact(
        bias=StockBias.BULLISH,
        magnitude=ImpactMagnitude.MEDIUM,
        horizon=TimeHorizon.SHORT_TERM,
        reasons=["Earnings beat", "Guidance raised"],
        confidence=0.7
    )
    print(f"StockImpact: {stock}")

    interpretation = Interpretation(
        symbol="AAPL",
        headline="AAPL beats Q3, raises guidance",
        what_happened="AAPL reported EPS of $1.55 vs $1.42 consensus, revenue $89.5B vs $89.2B consensus. Raised Q4 guidance.",
        what_it_means="Fundamental business accelerating with strong execution",
        why_it_matters="Demonstrates pricing power and demand resilience in challenging macro environment",
        company_impact=CompanyImpact(
            direction=ImpactDirection.POSITIVE,
            magnitude=ImpactMagnitude.MEDIUM,
            horizon=TimeHorizon.MEDIUM_TERM,
            reasons=["Revenue growth accelerating", "Margin expansion"],
            confidence=0.8
        ),
        stock_impact=StockImpact(
            bias=StockBias.BULLISH,
            magnitude=ImpactMagnitude.MEDIUM,
            horizon=TimeHorizon.SHORT_TERM,
            reasons=["Earnings beat", "Guidance raised", "Momentum positive"],
            confidence=0.7
        ),
        base_case=Scenario(scenario_type=ScenarioType.BASE, description="Steady growth continues"),
        bull_case=Scenario(scenario_type=ScenarioType.BULL, description="Guidance conservatism implies further upside"),
        bear_case=Scenario(scenario_type=ScenarioType.BEAR, description="Macro headwinds compress multiple"),
        confidence=0.75
    )
    print(f"Interpretation: {interpretation.headline}")
    print(f"Company Impact: {interpretation.company_impact.direction.value} ({interpretation.company_impact.magnitude.value})")
    print(f"Stock Impact: {interpretation.stock_impact.bias.value} ({interpretation.stock_impact.magnitude.value})")