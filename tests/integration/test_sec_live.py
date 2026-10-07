"""Explicit live SEC smoke test; requires the user's genuine configured identity."""
import os
from datetime import date, timedelta

import pytest

from trading_copilot.config import load_settings
from trading_copilot.events.store import EventStore
from trading_copilot.providers.filing_provider import SECFilingProvider


@pytest.mark.skipif(os.getenv("RUN_LIVE_TESTS") != "1", reason="Set RUN_LIVE_TESTS=1 for live SEC")
def test_sec_live(tmp_path):
    if not load_settings().sec_user_agent:
        pytest.skip("Live SEC blocker: configure SEC_USER_AGENT with real organization/contact")
    store = EventStore(tmp_path / "events.db")
    provider = SECFilingProvider(store, tmp_path / "sec")
    try:
        docs = provider.get_filings(["AAPL"], lookback_days=90, max_per_symbol=2)
        assert not provider.errors, provider.errors
        assert docs["AAPL"]
        for doc in docs["AAPL"]:
            assert doc.provider == "sec_edgar" and doc.text and doc.metadata["raw_sha256"]
        counts = provider.refresh(["AAPL"], from_date=date.today() - timedelta(days=90), max_per_symbol=2)
        assert counts["NEW"] >= 1 and counts["ERROR"] == 0
        assert provider.refresh(["AAPL"], max_per_symbol=2)["UNCHANGED"] >= 1
    finally:
        provider.close()
        store.close()
