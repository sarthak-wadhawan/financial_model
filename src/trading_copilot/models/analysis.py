"""AI analysis models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from trading_copilot.models.sources import EvidenceClaim


class CatalystAnalysis(BaseModel):
    """Structured catalyst analysis from LLM."""

    symbol: str

    catalyst_type: Literal[
        "earnings",
        "guidance",
        "product",
        "regulatory",
        "corporate_action",
        "analyst_revision",
        "macro_sensitive",
        "other",
        "none",
    ]

    catalyst_direction: Literal[
        "positive",
        "negative",
        "mixed",
        "neutral",
    ]

    catalyst_strength: Literal[
        "high",
        "medium",
        "low",
        "none",
    ]

    summary: str

    guidance_change: Literal[
        "raised",
        "lowered",
        "reaffirmed",
        "not_found",
    ]

    key_positive_claims: list[EvidenceClaim] = Field(default_factory=list)
    key_negative_claims: list[EvidenceClaim] = Field(default_factory=list)
    risks: list[EvidenceClaim] = Field(default_factory=list)
    upcoming_events: list[EvidenceClaim] = Field(default_factory=list)

    extraction_confidence: float = Field(ge=0.0, le=1.0)

    def all_claims(self) -> list[EvidenceClaim]:
        """Get all claims for validation."""
        return (
            self.key_positive_claims
            + self.key_negative_claims
            + self.risks
            + self.upcoming_events
        )