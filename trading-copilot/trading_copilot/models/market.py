"""Market data models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SymbolInfo(BaseModel):
    """Symbol metadata."""

    symbol: str
    name: str | None = None
    exchange: str | None = None
    asset_type: str = "equity"
    active: bool = True


class DailyBar(BaseModel):
    """Daily OHLCV bar."""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    @field_validator("open", "high", "low", "close")
    @classmethod
    def prices_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Prices must be positive")
        return v

    @field_validator("high")
    @classmethod
    def high_ge_low(cls, v: float, info: Any) -> float:
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("High must be >= low")
        return v

    @field_validator("volume")
    @classmethod
    def volume_nonnegative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Volume must be non-negative")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware")
        return v


class MarketSnapshot(BaseModel):
    """Complete market data for a symbol."""

    symbol: str
    bars: list[DailyBar]
    benchmark_bars: list[DailyBar] | None = None


# Need to import Any for the validator
from typing import Any