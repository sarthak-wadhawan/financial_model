"""Offline snapshot projection: unsupported instruments never borrow SPY values."""
from datetime import datetime, timedelta, timezone

from backend.website_data import WebsiteDataAdapter
from trading_copilot.config import Config, Settings
from trading_copilot.models.market import DailyBar


class SpyProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.requests = []
        self.last_retrieval_metadata = {"SPY": {
            "retrieved_at": "2026-10-16T12:00:00+00:00",
            "source_url": "https://data.alpaca.markets/v2/stocks/bars",
        }}

    def get_daily_bars(self, symbols, start, end):
        self.requests.append(symbols)
        if self.fail:
            raise RuntimeError("SECRET upstream request")
        return {"SPY": [DailyBar(
            symbol="SPY", timestamp=datetime.now(timezone.utc) - timedelta(days=days),
            open=value, high=value, low=value, close=value, volume=1000,
        ) for days, value in [(2, 600.0), (1, 606.0)]]}


def assert_unsupported(indices):
    assert [item["symbol"] for item in indices] == ["VIX", "DXY", "10Y"]
    for item in indices:
        assert item["status"] == "unsupported"
        assert "no proxy instrument" in item["reason"]
        for key in ["price", "change", "change_pct", "source", "source_url", "market_timestamp", "retrieved_at"]:
            assert item[key] is None


def test_spy_available_independently_of_three_unsupported_instruments():
    provider = SpyProvider()
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=provider)
    result = adapter.overview()
    spy = result["indices"][0]
    assert spy["symbol"] == "SPY"
    assert spy["price"] == 606.0
    assert spy["status"] == result["market_data_status"] == "available"
    assert spy["source"] == "Alpaca IEX"
    assert spy["retrieved_at"] == provider.last_retrieval_metadata["SPY"]["retrieved_at"]
    assert spy["market_timestamp"] is not None
    assert provider.requests == [["SPY"]]
    assert_unsupported(result["indices"][1:])


def test_spy_provider_failure_preserves_snapshot_and_unsupported_distinction():
    provider = SpyProvider(fail=True)
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=provider)
    result = adapter.overview()
    spy = result["indices"][0]
    assert spy["status"] == result["market_data_status"] == "provider_error"
    assert spy["price"] is None
    assert spy["market_timestamp"] is None
    assert spy["reason"] == "Market provider request failed"
    assert "SECRET" not in str(result)
    assert provider.requests == [["SPY"]]
    assert_unsupported(result["indices"][1:])
