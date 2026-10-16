"""Scanner status exposes observation time, never calculation/retrieval time."""
from copy import deepcopy
from datetime import datetime, timezone

from backend.website_data import WebsiteDataAdapter


def adapter(candidates):
    value = WebsiteDataAdapter.__new__(WebsiteDataAdapter)
    value.source, value.mode = "Alpaca IEX", "real"
    value.symbols = ["AAPL", "MSFT"]
    value._scan_status, value._scan_reason = "available", None
    value._scanned_at = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
    value._candidates = candidates
    return value


def test_status_uses_newest_source_consistent_market_time_without_mutation():
    candidates = [
        {"symbol": "AAPL", "source": "Alpaca IEX", "mode": "real", "market_timestamp": "2026-10-13T04:00:00+00:00", "upstream_retrieved_at": "2026-10-15T10:00:00Z"},
        {"symbol": "MSFT", "source": "Alpaca IEX", "mode": "real", "market_timestamp": "2026-10-14T00:00:00-04:00", "upstream_retrieved_at": "2026-10-15T11:00:00Z"},
        {"symbol": "OTHER", "source": "Other provider", "mode": "real", "market_timestamp": "2026-10-15T04:00:00Z"},
        {"symbol": "DEMO", "source": "Alpaca IEX", "mode": "demo", "market_timestamp": "2026-10-16T04:00:00Z"},
    ]
    before = deepcopy(candidates)
    status = adapter(candidates).status()
    assert status["market_timestamp"] == "2026-10-14T00:00:00-04:00"
    assert status["calculated_at"] == "2026-10-15T12:00:00+00:00"
    assert candidates == before


def test_status_without_candidate_observation_does_not_substitute_calculation_time():
    for candidates in ([], [{"source": "Alpaca IEX", "mode": "real", "market_timestamp": None}]):
        status = adapter(candidates).status()
        assert status["market_timestamp"] is None
        assert status["calculated_at"] is not None
