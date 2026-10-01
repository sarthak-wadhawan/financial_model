"""Final result models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from trading_copilot.models.analysis import CatalystAnalysis


class FinalCandidate(BaseModel):
    """Final ranked candidate after all scoring stages."""

    symbol: str
    quant_score: float = Field(ge=0, le=100)
    catalyst_score: float = Field(ge=0, le=100)
    final_score: float = Field(ge=0, le=100)
    status: Literal["candidate", "review_required", "excluded"]
    exclusion_reasons: list[str] = Field(default_factory=list)
    analysis: CatalystAnalysis | None = None


class ResearchBrief(BaseModel):
    """Research brief for human review."""

    symbol: str
    as_of: datetime
    price: float
    quant_score: float
    catalyst_score: float
    final_score: float

    thesis_facts: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    upcoming_events: list[str] = Field(default_factory=list)
    invalidation_conditions: list[str] = Field(default_factory=list)

    sources: list[dict] = Field(default_factory=list)


class RunManifest(BaseModel):
    """Run metadata for reproducibility."""

    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    config_hash: str
    git_commit: str | None = None
    universe_size: int
    eligible_count: int
    top_n: int
    failures: int = 0