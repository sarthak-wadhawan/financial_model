"""Feature models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class FeatureRow(BaseModel):
    """Computed features for a single symbol."""

    symbol: str
    as_of: datetime
    price: float

    # Returns
    ret_21d: float
    ret_63d: float
    ret_126d: float

    # Relative returns vs benchmark
    rel_ret_21d: float
    rel_ret_63d: float
    rel_ret_126d: float

    # Moving averages
    sma_20: float
    sma_50: float
    sma_200: float

    # Distance from MAs
    dist_sma_20_pct: float
    dist_sma_50_pct: float
    dist_sma_200_pct: float

    # Volatility and volume
    realized_vol_20d: float
    avg_dollar_volume_20d: float
    relative_volume_1d: float
    drawdown_from_63d_high: float

    @field_validator("price", "sma_20", "sma_50", "sma_200", "avg_dollar_volume_20d", "realized_vol_20d")
    @classmethod
    def positive_values(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    @field_validator("relative_volume_1d")
    @classmethod
    def relative_volume_nonnegative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Relative volume must be non-negative")
        return v

    @field_validator("drawdown_from_63d_high")
    @classmethod
    def drawdown_nonpositive(cls, v: float) -> float:
        if v > 0:
            raise ValueError("Drawdown must be non-positive")
        return v


class QuantScore(BaseModel):
    """Quant score with components."""

    symbol: str
    momentum_score: float = Field(ge=0, le=100)
    trend_score: float = Field(ge=0, le=100)
    liquidity_score: float = Field(ge=0, le=100)
    volume_score: float = Field(ge=0, le=100)
    volatility_score: float = Field(ge=0, le=100)
    quant_score: float = Field(ge=0, le=100)
    components: dict[str, float]

    @field_validator("components")
    @classmethod
    def validate_components(cls, v: dict[str, float]) -> dict[str, float]:
        expected = {"momentum", "trend", "liquidity", "volume", "volatility_quality"}
        if set(v.keys()) != expected:
            raise ValueError(f"Components must contain exactly: {expected}")
        for val in v.values():
            if not (0 <= val <= 100):
                raise ValueError("Component scores must be in [0, 100]")
        return v


class EligibilityResult(BaseModel):
    """Result of eligibility check."""

    symbol: str
    eligible: bool
    reasons: list[str] = Field(default_factory=list)