"""Watchlist models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class WatchlistSortOrder(str, Enum):
    """Watchlist sort order options."""
    MANUAL = "manual"
    SYMBOL = "symbol"
    QUANT_SCORE = "quant_score"
    PRICE_CHANGE = "price_change"
    MARKET_CAP = "market_cap"


class WatchlistBase(BaseModel):
    """Base watchlist model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: WatchlistSortOrder = WatchlistSortOrder.MANUAL
    is_default: bool = False


class WatchlistCreate(WatchlistBase):
    """Watchlist creation model."""
    pass


class WatchlistUpdate(BaseModel):
    """Watchlist update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    sort_order: Optional[WatchlistSortOrder] = None
    is_default: Optional[bool] = None


class WatchlistItem(BaseModel):
    """Watchlist item (symbol in a watchlist)."""
    symbol: str = Field(..., min_length=1, max_length=10)
    added_at: datetime = Field(default_factory=lambda: datetime.now())
    notes: Optional[str] = Field(None, max_length=500)
    sort_index: int = 0


class WatchlistItemCreate(BaseModel):
    """Watchlist item creation model."""
    symbol: str = Field(..., min_length=1, max_length=10)
    notes: Optional[str] = Field(None, max_length=500)


class WatchlistItemUpdate(BaseModel):
    """Watchlist item update model."""
    notes: Optional[str] = Field(None, max_length=500)
    sort_index: Optional[int] = None


class Watchlist(WatchlistBase):
    """Complete watchlist model."""
    id: str
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    symbols: list[str] = Field(default_factory=list)


class WatchlistWithItems(Watchlist):
    """Watchlist with full items."""
    items: list[WatchlistItem] = Field(default_factory=list)