"""Optional live smoke tests for Alpaca provider.

These tests only run when RUN_LIVE_TESTS=1 and Alpaca credentials are available.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider
from trading_copilot.storage.cache import FileCache


# Skip all tests in this module unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Live tests require RUN_LIVE_TESTS=1 and valid Alpaca credentials",
)


def _has_alpaca_credentials() -> bool:
    """Check if Alpaca credentials are available."""
    return bool(os.environ.get("ALPACA_API_KEY") and os.environ.get("ALPACA_API_SECRET"))


@pytest.fixture
def alpaca_provider():
    """Create Alpaca provider for live testing."""
    if not _has_alpaca_credentials():
        pytest.skip("Alpaca credentials not available")
    
    cache_dir = Path("artifacts/cache/market_data")
    cache = FileCache(cache_dir, ttl_days=1)
    
    provider = AlpacaMarketDataProvider(cache=cache)
    yield provider
    provider.close()


def test_live_get_daily_bars(alpaca_provider: AlpacaMarketDataProvider):
    """Test fetching daily bars for a few symbols."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    
    result = alpaca_provider.get_daily_bars(["SPY", "AAPL", "MSFT"], start, end)
    
    assert "SPY" in result
    assert "AAPL" in result
    assert "MSFT" in result
    
    # Each should have some bars
    for symbol, bars in result.items():
        assert len(bars) > 0, f"No bars returned for {symbol}"
        for bar in bars:
            assert bar.symbol == symbol
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.volume >= 0
            assert bar.timestamp.tzinfo is not None


def test_live_get_benchmark_bars(alpaca_provider: AlpacaMarketDataProvider):
    """Test fetching benchmark bars."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    
    bars = alpaca_provider.get_benchmark_bars("SPY", start, end)
    
    assert len(bars) > 0
    for bar in bars:
        assert bar.symbol == "SPY"
        assert bar.open > 0
        assert bar.high >= bar.low
        assert bar.volume >= 0


def test_live_health_check(alpaca_provider: AlpacaMarketDataProvider):
    """Test health check endpoint."""
    assert alpaca_provider.health_check() is True


def test_live_cache_persistence(alpaca_provider: AlpacaMarketDataProvider):
    """Test that cache persists across provider instances."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=10)
    
    # First request
    result1 = alpaca_provider.get_daily_bars(["AAPL"], start, end)
    
    # Create new provider with same cache
    cache_dir = Path("artifacts/cache/market_data")
    cache = FileCache(cache_dir, ttl_days=1)
    provider2 = AlpacaMarketDataProvider(cache=cache)
    
    try:
        # Second request should use cache
        result2 = provider2.get_daily_bars(["AAPL"], start, end)
        assert result1 == result2
    finally:
        provider2.close()


if __name__ == "__main__":
    # Allow running directly with RUN_LIVE_TESTS=1
    if os.environ.get("RUN_LIVE_TESTS") == "1":
        pytest.main([__file__, "-v", "-s"])
    else:
        print("Set RUN_LIVE_TESTS=1 to run live tests")
        print("Also requires ALPACA_API_KEY and ALPACA_API_SECRET environment variables")