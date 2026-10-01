"""Alpaca market data provider for real-time and historical data."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from trading_copilot.config import get_alpaca_config, load_settings
from trading_copilot.models import DailyBar
from trading_copilot.providers.base import MarketDataProvider
from trading_copilot.storage.cache import FileCache


logger = logging.getLogger(__name__)

# Alpaca API base URLs
ALPACA_BASE_URL = "https://data.alpaca.markets"
ALPACA_PAPER_BASE_URL = "https://paper-api.alpaca.markets"


class AlpacaMarketDataProvider:
    """Alpaca market data provider with caching and retry logic."""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = ALPACA_BASE_URL,
        cache: FileCache | None = None,
        max_symbols_per_request: int = 100,
        timeout_seconds: int = 30,
    ):
        """
        Initialize Alpaca market data provider.

        Args:
            api_key: Alpaca API key (defaults to ALPACA_API_KEY env var)
            api_secret: Alpaca API secret (defaults to ALPACA_API_SECRET env var)
            base_url: Alpaca data API base URL
            cache: Optional FileCache instance for caching responses
            max_symbols_per_request: Maximum symbols per API request (Alpaca limit)
            timeout_seconds: HTTP timeout in seconds
        """
        settings = load_settings()
        alpaca_config = get_alpaca_config(settings)

        self.api_key = api_key or alpaca_config["api_key"]
        self.api_secret = api_secret or alpaca_config["api_secret"]
        self.base_url = base_url
        self.cache = cache
        self.max_symbols_per_request = max_symbols_per_request
        self.timeout = timeout_seconds

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials not provided. "
                "Set ALPACA_API_KEY and ALPACA_API_SECRET environment variables."
            )

        # HTTP client with retry logic
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._auth_headers(),
            timeout=timeout_seconds,
        )

    def _auth_headers(self) -> dict[str, str]:
        """Return authentication headers for Alpaca API."""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def _cache_key(self, symbols: list[str], start: datetime, end: datetime, timeframe: str = "1Day") -> str:
        """Generate cache key for a bar request."""
        # Sort symbols for consistent key
        sorted_symbols = sorted(symbols)
        key_parts = [
            "alpaca",
            "bars",
            timeframe,
            ",".join(sorted_symbols),
            start.date().isoformat(),
            end.date().isoformat(),
        ]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def _parse_alpaca_bar(self, bar: dict[str, Any], symbol: str) -> DailyBar:
        """Convert Alpaca bar format to DailyBar model."""
        # Alpaca returns timestamps in RFC3339 format (e.g., "2024-01-15T00:00:00Z")
        timestamp = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))
        
        return DailyBar(
            symbol=symbol,
            timestamp=timestamp,
            open=float(bar["o"]),
            high=float(bar["h"]),
            low=float(bar["l"]),
            close=float(bar["c"]),
            volume=float(bar["v"]),
        )

    @retry(
        wait=wait_exponential_jitter(initial=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    def _fetch_bars_batch(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Day",
        limit: int = 10000,
    ) -> dict[str, list[dict]]:
        """
        Fetch bars for a batch of symbols from Alpaca.

        Returns dict mapping symbol to list of bar dicts.
        """
        # Format dates for Alpaca API (RFC3339)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start_str,
            "end": end_str,
            "limit": limit,
            "adjustment": "raw",  # No split/dividend adjustment
            "feed": "sip",  # Use SIP feed for best coverage
        }

        logger.debug("Fetching bars for %d symbols from %s to %s", len(symbols), start_str, end_str)

        response = self._client.get("/v2/stocks/bars", params=params)

        # Handle specific error codes
        if response.status_code == 401:
            raise ValueError("Alpaca authentication failed: check API credentials")
        elif response.status_code == 403:
            raise ValueError("Alpaca access forbidden: check subscription/permissions")
        elif response.status_code == 429:
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)

        response.raise_for_status()
        data = response.json()

        # Parse response: {"bars": {"SYMBOL": [...bars...]}}
        bars_by_symbol = data.get("bars", {})
        
        # Convert to list of dicts for each symbol
        result = {}
        for symbol, bars in bars_by_symbol.items():
            result[symbol] = bars
            
        # Ensure all requested symbols have entries (even if empty)
        for symbol in symbols:
            if symbol not in result:
                result[symbol] = []

        return result

    def get_daily_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[DailyBar]]:
        """
        Get daily OHLCV bars for multiple symbols.

        Handles batching for large symbol lists and uses cache when available.
        """
        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Check cache first
        cache_key = self._cache_key(symbols, start, end)
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Cache hit for %d symbols", len(symbols))
                return cached

        # Batch symbols to respect API limits
        all_results: dict[str, list[DailyBar]] = {}
        
        for i in range(0, len(symbols), self.max_symbols_per_request):
            batch = symbols[i:i + self.max_symbols_per_request]
            try:
                batch_results = self._fetch_bars_batch(batch, start, end)
                
                # Convert to DailyBar objects
                for symbol, bars in batch_results.items():
                    daily_bars = []
                    for bar in bars:
                        try:
                            daily_bars.append(self._parse_alpaca_bar(bar, symbol))
                        except (KeyError, ValueError) as e:
                            logger.warning("Failed to parse bar for %s: %s", symbol, e)
                            continue
                    all_results[symbol] = daily_bars
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    # Server error - re-raise for retry
                    raise
                elif e.response.status_code == 429:
                    # Rate limited - re-raise for retry
                    raise
                else:
                    # Client error - log and continue with other batches
                    logger.error("Failed to fetch bars for batch: %s", e)
                    for symbol in batch:
                        all_results[symbol] = []
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.error("Network error fetching bars for batch: %s", e)
                for symbol in batch:
                    all_results[symbol] = []

        # Cache the results
        if self.cache:
            self.cache.set(cache_key, all_results)

        return all_results

    def get_benchmark_bars(
        self,
        benchmark: str,
        start: datetime,
        end: datetime,
    ) -> list[DailyBar]:
        """Get benchmark (e.g., SPY) daily bars."""
        result = self.get_daily_bars([benchmark], start, end)
        return result.get(benchmark, [])

    def health_check(self) -> bool:
        """Check if Alpaca API is accessible."""
        try:
            # Simple endpoint to verify credentials
            response = self._client.get("/v2/account")
            return response.status_code == 200
        except Exception:
            return False

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "AlpacaMarketDataProvider":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_market_data_provider(
    provider_name: str,
    config: dict | None = None,
    cache: FileCache | None = None,
) -> MarketDataProvider:
    """
    Factory function to create market data provider by name.

    Args:
        provider_name: "mock" or "alpaca"
        config: Optional provider configuration
        cache: Optional FileCache instance

    Returns:
        MarketDataProvider instance
    """
    if provider_name == "mock":
        from trading_copilot.providers.mock import MockMarketDataProvider
        return MockMarketDataProvider()
    elif provider_name == "alpaca":
        return AlpacaMarketDataProvider(cache=cache, **(config or {}))
    else:
        raise ValueError(f"Unknown market data provider: {provider_name}")