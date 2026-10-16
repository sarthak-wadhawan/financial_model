"""Alpaca market data provider for real-time and historical data."""

from __future__ import annotations

import hashlib
import logging
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

# Default feed for historical data (IEX as specified)
DEFAULT_FEED = "iex"


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
        feed: str = DEFAULT_FEED,
    ):
        """
        Initialize Alpaca market data provider.

        Args:
            api_key: Alpaca API key (defaults to APCA_API_KEY_ID env var)
            api_secret: Alpaca API secret (defaults to APCA_API_SECRET_KEY env var)
            base_url: Alpaca data API base URL
            cache: Optional FileCache instance for caching responses
            max_symbols_per_request: Maximum symbols per API request (Alpaca limit)
            timeout_seconds: HTTP timeout in seconds
            feed: Data feed to use ("iex" or "sip")
        """
        settings = load_settings()
        alpaca_config = get_alpaca_config(settings)

        self.api_key = api_key or alpaca_config["api_key"]
        self.api_secret = api_secret or alpaca_config["api_secret"]
        self.base_url = base_url
        self.cache = cache
        self.max_symbols_per_request = max_symbols_per_request
        self.timeout = timeout_seconds
        self.feed = feed
        self.last_retrieval_metadata: dict[str, dict] = {}

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials not provided. "
                "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables "
                "(or legacy ALPACA_API_KEY and ALPACA_API_SECRET)."
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

    def _cache_key(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Day",
        data_type: str = "bars",
    ) -> str:
        """Generate cache key for a request."""
        # Sort symbols for consistent key
        sorted_symbols = sorted(symbols)
        key_parts = [
            "alpaca-v2-exact-bounds",
            self.base_url,
            data_type,
            self.feed,
            timeframe,
            ",".join(sorted_symbols),
            self._rfc3339(start),
            self._rfc3339(end),
        ]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

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
        Fetch bars for a batch of symbols from Alpaca, handling pagination via next_page_token.

        Returns dict mapping symbol to list of bar dicts.
        """
        # Format dates for Alpaca API (RFC3339)
        start_str = self._rfc3339(start)
        end_str = self._rfc3339(end)

        params = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start_str,
            "end": end_str,
            "limit": limit,
            "adjustment": "raw",  # No split/dividend adjustment
            "feed": self.feed,
        }

        logger.debug("Fetching bars for %d symbols from %s to %s (feed=%s)", len(symbols), start_str, end_str, self.feed)

        all_bars_by_symbol: dict[str, list[dict]] = {symbol: [] for symbol in symbols}
        page_token = None
        seen_tokens = set()

        while True:
            if page_token:
                params["page_token"] = page_token

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

            # Accumulate bars for each symbol
            for symbol, bars in bars_by_symbol.items():
                if symbol in all_bars_by_symbol:
                    all_bars_by_symbol[symbol].extend(bars)

            # Check for pagination
            page_token = data.get("next_page_token")
            if not page_token:
                break
            if page_token in seen_tokens:
                raise ValueError("Repeated Alpaca pagination token")
            seen_tokens.add(page_token)

            logger.debug("Fetching next page of bars (token present)")

        return all_bars_by_symbol

    def get_daily_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        min_trading_sessions: int | None = None,
    ) -> dict[str, list[DailyBar]]:
        """
        Get daily OHLCV bars for multiple symbols.

        Handles batching for large symbol lists and uses cache when available.
        If min_trading_sessions is provided, expands the lookback window until
        at least that many trading sessions are retrieved for each symbol
        (up to a maximum of 5 expansion attempts).
        """
        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # If no minimum sessions required, use simple fetch
        if min_trading_sessions is None:
            results, statuses = self._get_daily_bars_simple(symbols, start, end)
            if "provider_error" in statuses.values():
                raise RuntimeError("Alpaca market data request failed; use status API for partial results")
            return results

        # Otherwise, iteratively expand lookback until we have enough sessions
        current_start = start
        max_attempts = 5
        # Approximate trading days per calendar day (252/365 ≈ 0.69)
        # Use conservative 0.65 to account for holidays
        trading_day_ratio = 0.65

        for attempt in range(max_attempts):
            logger.debug("Fetching bars (attempt %d/%d) for %d symbols from %s to %s",
                         attempt + 1, max_attempts, len(symbols), current_start.date(), end.date())
            
            results, statuses = self._get_daily_bars_simple(symbols, current_start, end)
            if "provider_error" in statuses.values():
                raise RuntimeError("Alpaca market data request failed; use status API for partial results")

            # Check if all symbols have enough sessions
            all_sufficient = True
            min_sessions_found = float('inf')
            for symbol, bars in results.items():
                session_count = len(bars)
                min_sessions_found = min(min_sessions_found, session_count)
                if session_count < min_trading_sessions:
                    all_sufficient = False
                    logger.debug("Symbol %s has %d sessions, need %d", symbol, session_count, min_trading_sessions)

            if all_sufficient:
                logger.info("All %d symbols have ≥%d trading sessions (min found: %d)",
                            len(symbols), min_trading_sessions, min_sessions_found)
                return results

            # If any batch had provider errors, don't keep expanding - return what we have
            if any(s == "provider_error" for s in statuses.values()):
                logger.warning("Provider errors encountered; stopping lookback expansion")
                return results

            if attempt < max_attempts - 1:
                # Calculate how many more calendar days we need
                # If we got X sessions in Y calendar days, we need (target/X) * Y calendar days
                calendar_days_so_far = (end - current_start).days
                if min_sessions_found > 0:
                    required_calendar_days = int(calendar_days_so_far * min_trading_sessions / min_sessions_found)
                else:
                    required_calendar_days = calendar_days_so_far * 2
                # Add 10% buffer
                required_calendar_days = int(required_calendar_days * 1.1)
                # Cap at 1000 calendar days (approx 3 years)
                required_calendar_days = min(required_calendar_days, 1000)
                
                new_start = end - timedelta(days=required_calendar_days)
                if new_start >= current_start:
                    # Can't expand further
                    logger.warning("Cannot expand lookback further (at %s)", current_start.date())
                    break
                current_start = new_start
                logger.info("Expanding lookback to %s (%d calendar days) to reach %d sessions",
                            current_start.date(), required_calendar_days, min_trading_sessions)
            else:
                logger.warning("Max attempts reached. Min sessions found: %d, required: %d",
                               min_sessions_found, min_trading_sessions)

        # Return best effort results
        return results

    def _get_daily_bars_simple(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> tuple[dict[str, list[DailyBar]], dict[str, str]]:
        """Internal method to fetch bars without session count validation.

        Returns a tuple of (results_dict, status_dict) where status_dict maps symbols
        to their fetch status: "available", "empty", or "provider_error".
        """
        # Check cache first
        cache_key = self._cache_key(symbols, start, end, data_type="bars")
        self.last_retrieval_metadata = {}
        if self.cache:
            cached = self.cache.get(cache_key)
            if isinstance(cached, dict) and cached.get("schema") == 2 and cached.get("provenance"):
                logger.info("Cache hit for %d symbols (bars)", len(symbols))
                self.last_retrieval_metadata = cached["provenance"]
                return cached["results"], cached["statuses"]
            # Legacy entries have no upstream retrieval provenance: refetch.

        # Batch symbols to respect API limits
        all_results: dict[str, list[DailyBar]] = {}
        all_statuses: dict[str, str] = {}

        for i in range(0, len(symbols), self.max_symbols_per_request):
            batch = symbols[i:i + self.max_symbols_per_request]
            try:
                batch_results = self._fetch_bars_batch(batch, start, end)
                retrieved_at = datetime.now(timezone.utc).isoformat()

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
                    all_statuses[symbol] = "empty" if not daily_bars else "available"
                    self.last_retrieval_metadata[symbol] = {
                        "retrieved_at": retrieved_at,
                        "source_url": self.base_url.rstrip("/") + "/v2/stocks/bars",
                    }

            except httpx.HTTPStatusError as e:
                # Retries are exhausted inside _fetch_bars_batch.
                logger.error("Market bars request failed (status=%d)", e.response.status_code)
                for symbol in batch:
                    all_results[symbol] = []
                    all_statuses[symbol] = "provider_error"
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                # Network error - classify as provider_error (do not re-raise for retry on network)
                logger.error("Network error fetching bars for batch: %s", e)
                for symbol in batch:
                    all_results[symbol] = []
                    all_statuses[symbol] = "provider_error"

        # Only cache if no provider errors occurred
        if self.cache and all(s != "provider_error" for s in all_statuses.values()):
            self.cache.set(cache_key, {"schema": 2, "results": all_results, "statuses": all_statuses,
                                       "provenance": self.last_retrieval_metadata})

        return all_results, all_statuses

    def get_benchmark_bars(
        self,
        benchmark: str,
        start: datetime,
        end: datetime,
        min_trading_sessions: int | None = None,
    ) -> list[DailyBar]:
        """Get benchmark (e.g., SPY) daily bars."""
        result = self.get_daily_bars([benchmark], start, end, min_trading_sessions=min_trading_sessions)
        return result.get(benchmark, [])

    def get_daily_bars_with_status(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
        min_trading_sessions: int | None = None,
    ) -> tuple[dict[str, list[DailyBar]], dict[str, str]]:
        """
        Get daily OHLCV bars for multiple symbols along with per-symbol fetch status.

        Returns a tuple of (results_dict, status_dict) where status_dict maps symbols
        to their fetch status: "available", "empty", or "provider_error".
        """
        # Ensure timezone-aware
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if min_trading_sessions is None:
            return self._get_daily_bars_simple(symbols, start, end)

        # For min_trading_sessions, we need to expand lookback; use the simple method
        # and return statuses from the final attempt
        current_start = start
        max_attempts = 5
        trading_day_ratio = 0.65

        for attempt in range(max_attempts):
            logger.debug("Fetching bars (attempt %d/%d) for %d symbols from %s to %s",
                         attempt + 1, max_attempts, len(symbols), current_start.date(), end.date())

            results, statuses = self._get_daily_bars_simple(symbols, current_start, end)

            # Check if all symbols have enough sessions
            all_sufficient = True
            min_sessions_found = float('inf')
            for symbol, bars in results.items():
                session_count = len(bars)
                min_sessions_found = min(min_sessions_found, session_count)
                if session_count < min_trading_sessions:
                    all_sufficient = False
                    logger.debug("Symbol %s has %d sessions, need %d", symbol, session_count, min_trading_sessions)

            if all_sufficient:
                logger.info("All %d symbols have ≥%d trading sessions (min found: %d)",
                            len(symbols), min_trading_sessions, min_sessions_found)
                return results, statuses

            # If any batch had provider errors, don't keep expanding
            if any(s == "provider_error" for s in statuses.values()):
                logger.warning("Provider errors encountered; stopping lookback expansion")
                return results, statuses

            if attempt < max_attempts - 1:
                calendar_days_so_far = (end - current_start).days
                if min_sessions_found > 0:
                    required_calendar_days = int(calendar_days_so_far * min_trading_sessions / min_sessions_found)
                else:
                    required_calendar_days = calendar_days_so_far * 2
                required_calendar_days = int(required_calendar_days * 1.1)
                required_calendar_days = min(required_calendar_days, 1000)

                new_start = end - timedelta(days=required_calendar_days)
                if new_start >= current_start:
                    logger.warning("Cannot expand lookback further (at %s)", current_start.date())
                    break
                current_start = new_start
                logger.info("Expanding lookback to %s (%d calendar days) to reach %d sessions",
                            current_start.date(), required_calendar_days, min_trading_sessions)
            else:
                logger.warning("Max attempts reached. Min sessions found: %d, required: %d",
                               min_sessions_found, min_trading_sessions)

        return results, statuses

    # ---------------------------------------------------------------------
    # Latest price
    # ---------------------------------------------------------------------

    def get_latest_price(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get latest price information for symbols.

        Returns dict mapping symbol to dict with:
            - symbol
            - latest_price
            - daily_change
            - daily_change_pct
            - timestamp
        """
        # Use the latest trade endpoint for real-time price
        # For simplicity, fetch the most recent daily bar which gives us close price
        # and compute change from previous close
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=5)  # Get last 5 days to compute daily change

        bars = self.get_daily_bars(symbols, start, end)

        result = {}
        for symbol in symbols:
            symbol_bars = bars.get(symbol, [])
            if not symbol_bars:
                result[symbol] = {
                    "symbol": symbol,
                    "latest_price": None,
                    "daily_change": None,
                    "daily_change_pct": None,
                    "timestamp": None,
                }
                continue

            # Sort by timestamp
            symbol_bars.sort(key=lambda b: b.timestamp)
            latest_bar = symbol_bars[-1]
            latest_price = latest_bar.close
            latest_timestamp = latest_bar.timestamp

            # Compute daily change from previous day's close
            daily_change = None
            daily_change_pct = None
            if len(symbol_bars) >= 2:
                prev_close = symbol_bars[-2].close
                daily_change = latest_price - prev_close
                daily_change_pct = (daily_change / prev_close) * 100 if prev_close != 0 else None

            result[symbol] = {
                "symbol": symbol,
                "latest_price": latest_price,
                "daily_change": daily_change,
                "daily_change_pct": daily_change_pct,
                "timestamp": latest_timestamp,
            }

        return result

    # ---------------------------------------------------------------------
    # Historical IEX quotes
    # ---------------------------------------------------------------------

    @retry(
        wait=wait_exponential_jitter(initial=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    def get_historical_quotes(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """
        Get historical IEX quotes for a symbol.

        Returns list of quote dicts with fields:
            - ap: ask price
            - as: ask size
            - ax: ask exchange
            - bp: bid price
            - bs: bid size
            - bx: bid exchange
            - c: conditions
            - t: timestamp
            - z: tape
        """
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Check cache
        cache_key = self._cache_key([symbol], start, end, data_type="quotes")
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Cache hit for %s (quotes)", symbol)
                return cached

        start_str = start.isoformat().replace("+00:00", "Z")
        end_str = end.isoformat().replace("+00:00", "Z")

        params = {
            "feed": self.feed,
            "start": start_str,
            "end": end_str,
            "limit": limit,
        }

        logger.debug("Fetching quotes for %s from %s to %s", symbol, start_str, end_str)

        response = self._client.get(f"/v2/stocks/{symbol}/quotes", params=params)

        if response.status_code == 401:
            raise ValueError("Alpaca authentication failed: check API credentials")
        elif response.status_code == 403:
            raise ValueError("Alpaca access forbidden: check subscription/permissions")
        elif response.status_code == 429:
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)

        response.raise_for_status()
        data = response.json()

        quotes = data.get("quotes", [])

        # Cache the results
        if self.cache:
            self.cache.set(cache_key, quotes)

        return quotes

    # ---------------------------------------------------------------------
    # Historical IEX trades
    # ---------------------------------------------------------------------

    @retry(
        wait=wait_exponential_jitter(initial=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError)
        ),
        reraise=True,
    )
    def get_historical_trades(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """
        Get historical IEX trades for a symbol.

        Returns list of trade dicts with fields:
            - c: conditions
            - i: trade ID
            - p: price
            - s: size
            - t: timestamp
            - x: exchange
            - z: tape
        """
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Check cache
        cache_key = self._cache_key([symbol], start, end, data_type="trades")
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.info("Cache hit for %s (trades)", symbol)
                return cached

        start_str = start.isoformat().replace("+00:00", "Z")
        end_str = end.isoformat().replace("+00:00", "Z")

        params = {
            "feed": self.feed,
            "start": start_str,
            "end": end_str,
            "limit": limit,
        }

        logger.debug("Fetching trades for %s from %s to %s", symbol, start_str, end_str)

        response = self._client.get(f"/v2/stocks/{symbol}/trades", params=params)

        if response.status_code == 401:
            raise ValueError("Alpaca authentication failed: check API credentials")
        elif response.status_code == 403:
            raise ValueError("Alpaca access forbidden: check subscription/permissions")
        elif response.status_code == 429:
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)

        response.raise_for_status()
        data = response.json()

        trades = data.get("trades", [])

        # Cache the results
        if self.cache:
            self.cache.set(cache_key, trades)

        return trades

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
