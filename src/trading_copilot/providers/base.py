"""Provider base interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Protocol

from trading_copilot.models.market import DailyBar, SymbolInfo
from trading_copilot.models.sources import SourceDocument
from trading_copilot.models.news import NewsDocument


class UniverseProvider(Protocol):
    """Protocol for universe providers."""

    def get_symbols(self) -> list[SymbolInfo]:
        ...


class MarketDataProvider(Protocol):
    """Protocol for market data providers."""

    def get_daily_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[DailyBar]]:
        ...

    def get_benchmark_bars(
        self,
        benchmark: str,
        start: datetime,
        end: datetime,
    ) -> list[DailyBar]:
        ...


class NewsProvider(Protocol):
    """Protocol for news/document providers.

    Phase 8: structured evidence layer for news, company releases, management statements.
    """

    def fetch_news(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]:
        """Fetch news articles for symbols within date range."""
        ...

    def fetch_company_releases(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]:
        """Fetch company press releases (IR, SEC exhibits)."""
        ...


class FilingProvider(Protocol):
    """Protocol for SEC filing providers."""

    def get_filings(
        self,
        symbols: list[str],
        lookback_days: int,
        max_per_symbol: int,
    ) -> dict[str, list[SourceDocument]]:
        ...


class OptionsProvider(Protocol):
    """Protocol for options data providers."""

    def get_options_metrics(
        self,
        symbols: list[str],
    ) -> dict[str, dict]:
        ...


class BaseProvider(ABC):
    """Base class with common provider functionality."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available."""
        ...