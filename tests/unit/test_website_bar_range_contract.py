"""Offline daily-range contract; no lifespan, event store, network or runtime changes."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import website_data
from backend.website_data import WebsiteDataAdapter
from trading_copilot.config import Config, Settings
from trading_copilot.models.market import DailyBar

UTC = timezone.utc
NOW = datetime(2026, 10, 16, 12, tzinfo=UTC)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


def bar(day, hour=4, close=100):
    return DailyBar(symbol="AAPL", timestamp=datetime.combine(day, datetime.min.time(), UTC)
                    + timedelta(hours=hour), open=close, high=close+1, low=close-1,
                    close=close, volume=0)


class Provider:
    def __init__(self, rows=(), status="available", fail=False):
        self.rows, self.status, self.fail = list(rows), status, fail
        self.calls = []
        self.last_retrieval_metadata = {"AAPL": {
            "retrieved_at": "2026-10-16T10:00:00+00:00",
            "source_url": "https://data.alpaca.markets/v2/stocks/bars"}}

    def get_daily_bars_with_status(self, symbols, start, end):
        self.calls.append((symbols, start, end))
        if self.fail:
            raise RuntimeError("SECRET credentials in upstream URL")
        return {"AAPL": self.rows}, {"AAPL": self.status}


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setattr(website_data, "datetime", Clock)

    def make(rows=(), **kwargs):
        provider = Provider(rows, **kwargs)
        value = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=provider,
                                   identity_service=SimpleNamespace())
        return value, provider
    return make


def test_response_bounds_tail_and_cached_provenance(adapter):
    rows = [bar(date(2020, 1, d)) for d in (2, 3, 6)]
    value, provider = adapter(rows)
    first = value.bars("AAPL", date(2020, 1, 1), date(2020, 1, 7), 2)
    assert first["requested_start"] == "2020-01-01"
    assert first["requested_end"] == first["effective_end"] == "2020-01-07"
    assert (first["available_start"], first["available_end"], first["returned_count"]) == ("2020-01-03", "2020-01-06", 2)
    assert first["truncated"] is True and first["coverage_complete"] is False
    provider.last_retrieval_metadata["AAPL"]["retrieved_at"] = "must not replace cache provenance"
    second = value.bars("AAPL", date(2020, 1, 1), date(2020, 1, 7), 5000)
    assert len(provider.calls) == 1
    assert second["available_start"] == "2020-01-02"
    assert second["returned_count"] == 3 and second["truncated"] is False
    assert second["coverage_complete"] is None
    assert second["retrieved_at"] == first["retrieved_at"] == "2026-10-16T10:00:00+00:00"
    assert second["market_timestamp"] == rows[-1].timestamp.isoformat()


def test_limit_5000_is_tail_cap_not_provider_page_count(adapter):
    # Deliberately oversized synthetic upstream payload (not 5001 unique sessions).
    # The adapter's cap is independent of upstream pagination and completeness.
    rows = [bar(date(2020, 1, 2), close=100+i) for i in range(5001)]
    value, provider = adapter(rows)
    result = value.bars("AAPL", date(2020, 1, 1), date(2020, 1, 3), 5000)
    assert result["returned_count"] == 5000
    assert result["bars"][0]["c"] == 101
    assert result["truncated"] is True and result["coverage_complete"] is False
    assert len(provider.calls) == 1
    tail = value.bars("AAPL", date(2020, 1, 1), date(2020, 1, 3), 1)
    assert tail["bars"][0]["c"] == 5100 and len(provider.calls) == 1


def test_default_bounds_and_raw_discontinuity_unchanged(adapter):
    value, _ = adapter([bar(date(2026, 10, 14), close=200),
                        bar(date(2026, 10, 15), close=50)])
    result = value.bars("AAPL")
    assert result["requested_start"] == (NOW-timedelta(days=max(400, value.config.market.history_days))).date().isoformat()
    assert result["requested_end"] == "2026-10-16"
    assert result["effective_end"] == "2026-10-15"
    assert [row["c"] for row in result["bars"]] == [200, 50]
    assert result["coverage_complete"] is None  # No inferred split adjustment or completeness.


def test_unavailable_metadata_without_fabricated_price(adapter):
    value, _ = adapter()
    value.provider = None
    value.reason = "Alpaca credentials missing; real market data unavailable"
    result = value.bars("AAPL")
    assert result["status"] == "unavailable"
    assert result["available_start"] is result["available_end"] is None
    assert result["coverage_complete"] is None and result["returned_count"] == 0
    price = value.price("AAPL")
    assert price["price"] is price["session_date"] is price["market_timestamp"] is None
    assert price["is_live"] is False


@pytest.mark.parametrize("start,end", [(date(2016, 10, 16), date(2026, 10, 16)),
                                        (date(2014, 2, 28), date(2024, 2, 29)),
                                        (date(2020, 3, 9), date(2020, 3, 9))])
def test_ten_calendar_year_boundary_and_same_day_accepted(adapter, start, end):
    value, _ = adapter()
    result = value.bars("AAPL", start, end)
    assert result["requested_start"] == start.isoformat()
    assert result["max_request_span_calendar_years"] == 10


@pytest.mark.parametrize("start,end", [(date(2016, 10, 15), date(2026, 10, 16)),
                                        (date(2014, 2, 27), date(2024, 2, 29)),
                                        (date(2026, 10, 17), date(2026, 10, 16)),
                                        (date(2016, 10, 16), date(2027, 10, 16))])
def test_invalid_span_rejected_before_provider_not_silently_clipped(adapter, start, end):
    value, provider = adapter()
    with pytest.raises(ValueError):
        value.bars("AAPL", start, end)
    assert provider.calls == []


@pytest.mark.parametrize("limit", [0, -1, 5001])
def test_invalid_tail_cap(adapter, limit):
    value, provider = adapter()
    with pytest.raises(ValueError, match="limit"):
        value.bars("AAPL", limit=limit)
    assert provider.calls == []


def test_current_future_exclusion_and_exact_requested_cache_identity(adapter):
    value, provider = adapter([bar(date(2026, 10, d)) for d in (14, 15, 16, 17)])
    for end in (date(2026, 10, 16), date(2026, 10, 20)):
        result = value.bars("AAPL", date(2026, 10, 14), end)
        assert result["requested_end"] == end.isoformat()
        assert result["effective_end"] == "2026-10-15"
        assert result["available_end"] == "2026-10-15"
        assert result["returned_count"] == 2
    assert len(provider.calls) == 2
    assert provider.calls[0][2] == datetime(2026, 10, 16, tzinfo=UTC)
    value.bars("AAPL", date(2026, 10, 15), date(2026, 10, 20))
    assert len(provider.calls) == 3


def test_future_only_window_is_explicit_empty_without_fetch(adapter):
    value, provider = adapter()
    result = value.bars("AAPL", date(2026, 10, 17), date(2026, 10, 20))
    assert result["status"] == "empty"
    assert result["effective_end"] == "2026-10-15"
    assert result["requested_start"] == "2026-10-17"
    assert result["available_start"] is result["available_end"] is None
    assert result["returned_count"] == 0 and result["coverage_complete"] is None
    assert provider.calls == []


def test_missing_middle_sessions_unknown_and_historical_not_wall_clock_stale(adapter):
    value, _ = adapter([bar(date(2020, 3, 6), 5), bar(date(2020, 3, 11), 4)])
    result = value.bars("AAPL", date(2020, 3, 6), date(2020, 3, 11))
    assert result["status"] == "available"
    assert result["coverage_complete"] is None
    assert result["timestamp_basis"] == "daily_session_label"
    assert result["feed"] == "iex" and result["adjustment"] == "raw"
    assert result["supported_timeframes"] == ["1Day"]
    assert [row["t"] for row in result["bars"]] == ["2020-03-06T05:00:00+00:00", "2020-03-11T04:00:00+00:00"]


def test_header_price_independent_of_historical_window_and_no_invented_close_time(adapter):
    value, provider = adapter([bar(date(2020, 1, 2), close=200),
                               bar(date(2026, 10, 14), close=50),
                               bar(date(2026, 10, 15), close=55)])
    historic = value.bars("AAPL", date(2020, 1, 2), date(2020, 1, 2))
    price = value.price("AAPL")
    assert historic["bars"][-1]["c"] == 200
    assert price["price"] == 55 and price["change"] == 5
    assert price["volume"] == 0 and price["session_date"] == "2026-10-15"
    assert price["market_timestamp"] == "2026-10-15T04:00:00+00:00"
    assert price["price_kind"] == "completed_daily_close" and price["is_live"] is False
    assert (price["feed"], price["adjustment"], price["timestamp_basis"]) == ("iex", "raw", "daily_session_label")
    assert len(provider.calls) == 2


def test_latest_header_stale_but_historical_window_not_stale(adapter):
    value, _ = adapter([bar(date(2020, 1, 2))])
    assert value.bars("AAPL", date(2020, 1, 1), date(2020, 1, 3))["status"] == "available"
    assert value.price("AAPL")["price"] is None  # Latest window cannot reuse historical cache.
    value, _ = adapter([bar(date(2026, 10, 1))])
    assert value.price("AAPL")["status"] == "stale"


@pytest.mark.parametrize("failure", ["raise", "status", "empty"])
def test_failure_empty_sanitization_and_unknown_coverage(adapter, failure):
    value, _ = adapter(status="provider_error" if failure == "status" else "empty", fail=failure == "raise")
    result = value.bars("AAPL")
    assert result["status"] == ("empty" if failure == "empty" else "provider_error")
    assert "SECRET" not in str(result)
    assert result["coverage_complete"] is None and result["available_end"] is None
    assert result["returned_count"] == 0
    assert value.price("AAPL")["session_date"] is None


def test_route_validation_without_lifespan_or_database(adapter, monkeypatch):
    import backend.main as api
    value, provider = adapter()
    monkeypatch.setattr(api, "market_adapter", value)
    app = FastAPI()
    app.add_api_route("/bars/{symbol}", api.get_bars)
    app.add_exception_handler(ValueError, api.app.exception_handlers[ValueError])
    with TestClient(app) as client:
        assert client.get("/bars/AAPL?start=2010-01-01&end=2020-01-02").status_code == 400
        assert client.get("/bars/AAPL?start=2020-01-02&end=2020-01-01").status_code == 400
        assert client.get("/bars/AAPL?timeframe=1Hour").status_code == 400
        for limit in (0, 5001):
            assert client.get(f"/bars/AAPL?limit={limit}").status_code == 422
        assert provider.calls == []
        result = client.get("/bars/AAPL?start=2020-01-01&end=2020-01-01&limit=1")
        assert result.status_code == 200 and result.json()["returned_count"] == 0
