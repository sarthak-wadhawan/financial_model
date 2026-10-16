"""Gated external reads only; never imports API lifespan or writes production DB."""
import os
from datetime import datetime, timedelta, timezone
import pytest
from trading_copilot.config import Config, load_settings, get_alpaca_config
from backend.website_data import WebsiteDataAdapter

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_TESTS") != "1", reason="Read-only provider test requires RUN_LIVE_TESTS=1")


def test_live_iex_completed_daily_bars():
    settings = load_settings()
    if not all(get_alpaca_config(settings).values()):
        pytest.skip("Alpaca credentials missing")
    adapter = WebsiteDataAdapter(Config(), settings)
    try:
        result = adapter.bars("AAPL", start=(datetime.now(timezone.utc)-timedelta(days=30)).date())
        assert result["mode"] == "real"
        assert result["source"] == "Alpaca IEX"
        assert result["status"] in {"available", "stale"}, f"Live market unavailable: {result['status']} ({result['reason']})"
        assert result["bars"]
        assert all(datetime.fromisoformat(b["t"]).date() < datetime.now(timezone.utc).date() for b in result["bars"])
    finally:
        adapter.close()
