"""Mock market data provider for offline testing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import sqrt
from typing import Protocol

import numpy as np

from trading_copilot.models import DailyBar
from trading_copilot.providers.base import MarketDataProvider


class MockMarketDataProvider:
    """Generate deterministic synthetic market data for testing."""

    # Seed for reproducibility
    SEED = 42

    def __init__(self, seed: int | None = None):
        self.seed = seed or self.SEED
        self._rng = np.random.default_rng(self.seed)

    def get_daily_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[DailyBar]]:
        """Generate synthetic daily bars for each symbol."""
        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Generate business days
        dates = self._business_days(start, end)
        
        result = {}
        for i, symbol in enumerate(symbols):
            # Use symbol-specific seed for deterministic per-symbol data
            symbol_seed = hash((symbol, self.seed)) % (2**32)
            rng = np.random.default_rng(symbol_seed)
            
            bars = self._generate_bars_for_symbol(symbol, dates, rng)
            result[symbol] = bars
        
        return result

    def get_benchmark_bars(
        self,
        benchmark: str,
        start: datetime,
        end: datetime,
    ) -> list[DailyBar]:
        """Generate synthetic benchmark bars (SPY-like)."""
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        dates = self._business_days(start, end)
        
        # SPY-like parameters: ~10% annual return, ~15% annual vol
        return self._generate_bars_for_symbol(benchmark, dates, self._rng, 
                                               drift=0.10/252, vol=0.15/sqrt(252),
                                               start_price=450.0)

    def _business_days(self, start: datetime, end: datetime) -> list[datetime]:
        """Generate list of business days between start and end."""
        dates = []
        current = start
        while current <= end:
            if current.weekday() < 5:  # Mon-Fri
                dates.append(current)
            current += timedelta(days=1)
        return dates

    def _generate_bars_for_symbol(
        self,
        symbol: str,
        dates: list[datetime],
        rng: np.random.Generator,
        drift: float = 0.10/252,
        vol: float = 0.20/sqrt(252),
        start_price: float = 100.0,
    ) -> list[DailyBar]:
        """Generate OHLCV bars using geometric Brownian motion."""
        n = len(dates)
        
        # Generate returns
        returns = rng.normal(drift, vol, n)
        
        # Generate prices
        prices = [start_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        bars = []
        for i, (date, close) in enumerate(zip(dates, prices)):
            # Generate intraday noise
            daily_vol = vol * close
            high = close * (1 + abs(rng.normal(0, daily_vol/close)))
            low = close * (1 - abs(rng.normal(0, daily_vol/close)))
            open_ = close * (1 + rng.normal(0, daily_vol/close * 0.5))
            
            # Ensure high >= low and high >= open,close and low <= open,close
            high = max(high, open_, close)
            low = min(low, open_, close)
            
            # Volume: log-normal around a symbol-specific mean
            # Use symbol hash for consistent volume profile
            volume_base = 1_000_000 + (hash(symbol) % 50) * 1_000_000
            volume = max(1000, int(rng.lognormal(np.log(volume_base), 0.5)))
            
            bars.append(DailyBar(
                symbol=symbol,
                timestamp=date,
                open=round(open_, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=float(volume),
            ))
        
        return bars