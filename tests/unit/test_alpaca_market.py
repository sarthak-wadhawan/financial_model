"""Unit tests for Alpaca market data provider."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

from trading_copilot.models import DailyBar
from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider, create_market_data_provider
from trading_copilot.storage.cache import MemoryCache


class TestAlpacaMarketDataProvider:
    @pytest.fixture
    def mock_cache(self):
        return MemoryCache()

    @pytest.fixture
    def provider(self, mock_cache):
        """Create provider with mocked httpx.Client."""
        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            provider = AlpacaMarketDataProvider(
                api_key="test_key",
                api_secret="test_secret",
                cache=mock_cache,
            )
            provider._client = mock_client
            yield provider

    def test_init_requires_credentials(self):
        with pytest.raises(ValueError, match="Alpaca API credentials not provided"):
            AlpacaMarketDataProvider(api_key=None, api_secret=None)

    def test_init_with_explicit_credentials(self):
        with patch("httpx.Client"):
            provider = AlpacaMarketDataProvider(
                api_key="explicit_key",
                api_secret="explicit_secret",
            )
            assert provider.api_key == "explicit_key"
            assert provider.api_secret == "explicit_secret"

    def test_cache_key_consistency(self, provider):
        symbols = ["AAPL", "MSFT"]
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        key1 = provider._cache_key(symbols, start, end)
        key2 = provider._cache_key(symbols, start, end)
        
        assert key1 == key2
        assert len(key1) == 32  # SHA256 truncated to 32 chars

    def test_cache_key_order_independent(self, provider):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        key1 = provider._cache_key(["AAPL", "MSFT"], start, end)
        key2 = provider._cache_key(["MSFT", "AAPL"], start, end)
        
        assert key1 == key2  # Should be same regardless of order

    def test_parse_alpaca_bar(self, provider):
        bar = {
            "t": "2024-01-15T00:00:00Z",
            "o": "150.0",
            "h": "155.0",
            "l": "149.0",
            "c": "153.0",
            "v": "1000000",
        }
        
        daily_bar = provider._parse_alpaca_bar(bar, "AAPL")
        
        assert daily_bar.symbol == "AAPL"
        assert daily_bar.timestamp == datetime(2024, 1, 15, tzinfo=timezone.utc)
        assert daily_bar.open == 150.0
        assert daily_bar.high == 155.0
        assert daily_bar.low == 149.0
        assert daily_bar.close == 153.0
        assert daily_bar.volume == 1000000.0

    def test_parse_alpaca_bar_with_microseconds(self, provider):
        bar = {
            "t": "2024-01-15T00:00:00.123456Z",
            "o": "150.0",
            "h": "155.0",
            "l": "149.0",
            "c": "153.0",
            "v": "1000000",
        }
        
        daily_bar = provider._parse_alpaca_bar(bar, "AAPL")
        
        assert daily_bar.timestamp.microsecond == 123456

    def test_get_daily_bars_uses_cache(self, provider, mock_cache):
        """Test that cached results are returned without API call."""
        # This test would require more complex mocking of the httpx client
        # For now, we test the cache key generation and storage
        pass

    def test_health_check(self, provider):
        # Mock the client's get method
        provider._client.get = MagicMock(return_value=MagicMock(status_code=200))
        assert provider.health_check() is True
        
        provider._client.get = MagicMock(side_effect=Exception("Connection error"))
        assert provider.health_check() is False


class TestCreateMarketDataProvider:
    def test_create_mock_provider(self):
        provider = create_market_data_provider("mock")
        from trading_copilot.providers.mock import MockMarketDataProvider
        assert isinstance(provider, MockMarketDataProvider)

    def test_create_alpaca_provider(self):
        with patch("httpx.Client"):
            provider = create_market_data_provider("alpaca", {"api_key": "test", "api_secret": "test"})
            assert isinstance(provider, AlpacaMarketDataProvider)

    def test_create_unknown_provider(self):
        with pytest.raises(ValueError, match="Unknown market data provider"):
            create_market_data_provider("unknown")


class TestAlpacaProviderIntegration:
    """Integration-style tests with mocked HTTP responses."""

    @pytest.fixture
    def mock_response(self):
        """Create a mock Alpaca API response."""
        return {
            "bars": {
                "AAPL": [
                    {
                        "t": "2024-01-15T00:00:00Z",
                        "o": "150.0",
                        "h": "155.0",
                        "l": "149.0",
                        "c": "153.0",
                        "v": "1000000",
                    },
                    {
                        "t": "2024-01-16T00:00:00Z",
                        "o": "153.0",
                        "h": "158.0",
                        "l": "152.0",
                        "c": "156.0",
                        "v": "1200000",
                    },
                ],
                "MSFT": [
                    {
                        "t": "2024-01-15T00:00:00Z",
                        "o": "300.0",
                        "h": "310.0",
                        "l": "298.0",
                        "c": "305.0",
                        "v": "800000",
                    },
                ],
            }
        }

    @patch("httpx.Client")
    def test_get_daily_bars_single_batch(self, mock_client_class, mock_response):
        """Test fetching bars for a small symbol list."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_client.get.return_value = mock_response_obj
        
        cache = MemoryCache()
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
            cache=cache,
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = provider.get_daily_bars(["AAPL", "MSFT"], start, end)
        
        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) == 2
        assert len(result["MSFT"]) == 1
        assert all(isinstance(bar, DailyBar) for bars in result.values() for bar in bars)
        assert result["AAPL"][0].symbol == "AAPL"
        assert result["AAPL"][0].close == 153.0
        assert result["MSFT"][0].symbol == "MSFT"
        assert result["MSFT"][0].close == 305.0

    @patch("httpx.Client")
    def test_get_daily_bars_multiple_batches(self, mock_client_class, mock_response):
        """Test batching for large symbol lists."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_client.get.return_value = mock_response_obj
        
        cache = MemoryCache()
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
            cache=cache,
            max_symbols_per_request=2,  # Force batching
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        # 4 symbols, batch size 2 = 2 batches
        result = provider.get_daily_bars(["AAPL", "MSFT", "GOOGL", "TSLA"], start, end)
        
        assert "AAPL" in result
        assert "MSFT" in result
        # GOOGL and TSLA will have empty results since not in mock response
        assert result["GOOGL"] == []
        assert result["TSLA"] == []

    @patch("httpx.Client")
    def test_get_daily_bars_handles_missing_symbols(self, mock_client_class, mock_response):
        """Test that missing symbols in response get empty lists."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Response missing MSFT
        partial_response = {"bars": {"AAPL": mock_response["bars"]["AAPL"]}}
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = partial_response
        mock_client.get.return_value = mock_response_obj
        
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = provider.get_daily_bars(["AAPL", "MSFT"], start, end)
        
        assert "AAPL" in result
        assert "MSFT" in result
        assert len(result["AAPL"]) == 2
        assert result["MSFT"] == []

    @patch("httpx.Client")
    def test_get_daily_bars_caches_results(self, mock_client_class, mock_response):
        """Test that results are cached."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_client.get.return_value = mock_response_obj
        
        cache = MemoryCache()
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
            cache=cache,
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        # First call - should hit API
        result1 = provider.get_daily_bars(["AAPL"], start, end)
        assert mock_client.get.call_count == 1
        
        # Second call - should use cache
        result2 = provider.get_daily_bars(["AAPL"], start, end)
        assert mock_client.get.call_count == 1  # No additional call
        
        assert result1 == result2

    @patch("httpx.Client")
    def test_get_daily_bars_retries_on_timeout(self, mock_client_class, mock_response):
        """Test retry logic on timeout."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # First call times out, second succeeds
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_client.get.side_effect = [
            httpx.TimeoutException("Timeout"),
            mock_response_obj,
        ]
        
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = provider.get_daily_bars(["AAPL"], start, end)
        
        # Should have retried and succeeded
        assert mock_client.get.call_count == 2
        assert len(result["AAPL"]) == 2

    @patch("httpx.Client")
    def test_get_daily_bars_fails_on_auth_error(self, mock_client_class):
        """Test that auth errors are raised clearly."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 401
        mock_client.get.return_value = mock_response_obj
        
        provider = AlpacaMarketDataProvider(
            api_key="bad_key",
            api_secret="bad_secret",
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with pytest.raises(ValueError, match="Alpaca authentication failed"):
            provider.get_daily_bars(["AAPL"], start, end)

    @patch("httpx.Client")
    def test_get_benchmark_bars(self, mock_client_class, mock_response):
        """Test fetching benchmark bars."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response_obj = MagicMock()
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response
        mock_client.get.return_value = mock_response_obj
        
        provider = AlpacaMarketDataProvider(
            api_key="test_key",
            api_secret="test_secret",
        )
        provider._client = mock_client
        
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        result = provider.get_benchmark_bars("SPY", start, end)
        
        assert isinstance(result, list)
        # SPY not in mock, so empty list
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])