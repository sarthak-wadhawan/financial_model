"""Isolated HTTP runtime regressions; real adapter with injected daily-bar provider."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as backend
from backend.website_data import WebsiteDataAdapter
from trading_copilot.alerts.service import AlertService
from trading_copilot.alerts.store import AlertStore
from trading_copilot.calendar.service import CalendarService
from trading_copilot.config import load_config, load_settings
from trading_copilot.events.store import EventStore
from trading_copilot.models.events import MarketEvent, EventType


NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


class DailyProvider:
    def get_daily_bars(self, symbols, start, end):
        dates = [NOW - timedelta(days=i) for i in range(450, 0, -1)]
        dates = [d.replace(hour=4) for d in dates if d.weekday() < 5]
        return {s: [SimpleNamespace(timestamp=d, open=100+i, high=102+i,
                                   low=99+i, close=101+i, volume=2_000_000)
                    for i, d in enumerate(dates) if start <= d <= end] for s in symbols}


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    import backend.website_data as data
    monkeypatch.setattr(backend, "datetime", Clock)
    monkeypatch.setattr(data, "datetime", Clock)
    config = load_config(backend.Path("backend/config.yaml"))
    config.universe.symbols_file = None
    adapter = WebsiteDataAdapter(config, load_settings(), provider=DailyProvider())
    adapter.symbols = ["AAPL", "SPY"]
    store = EventStore(tmp_path / "runtime.db")
    monkeypatch.setattr(backend, "market_adapter", adapter)
    monkeypatch.setattr(backend, "event_store", store)
    monkeypatch.setattr(backend, "calendar_service", CalendarService(store))
    monkeypatch.setattr(backend, "alert_service", AlertService(AlertStore(tmp_path / "runtime.db")))
    yield TestClient(backend.app, raise_server_exceptions=False), adapter, store
    store.close()


def create(client, **changes):
    body = dict(name="Manual", alert_type="price", symbols=["AAPL"], condition="above", threshold=1)
    body.update(changes)
    response = client.post("/api/v1/alerts", json=body)
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize("kind", ["price", "price_change_pct", "volume", "quant_score"])
def test_dryrun_populated_provenance_without_state_mutation(runtime, kind):
    client, _, _ = runtime
    identifier = create(client, alert_type=kind, threshold=-1)
    root = "/api/v1/alerts/" + identifier
    before = client.get(root).json()
    response = client.post("/api/v1/alerts/test", json={"alert_id": identifier})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "evaluated"
    assert result["would_trigger"] is True
    observation = result["current_values"]["AAPL"]
    assert observation["source"] == "Alpaca IEX"
    assert observation["as_of"] < NOW.isoformat()
    assert client.get(root).json() == before
    assert client.get(root + "/triggers").json() == []


def test_manual_scoped_evaluation_history_ack_and_cooldown(runtime):
    client, _, _ = runtime
    identifier = create(client)
    other = create(client)
    root = "/api/v1/alerts/" + identifier
    result = client.post(root + "/evaluate").json()
    assert result["status"] == "evaluated"
    assert result["delivery"] == "in_app_history_only"
    assert len(result["triggers"]) == 1
    trigger = result["triggers"][0]
    assert trigger["metadata"]["observation"]["source"] == "Alpaca IEX"
    assert client.get(root).json()["trigger_count"] == 1
    assert client.get(f"/api/v1/alerts/{other}").json()["trigger_count"] == 0
    again = client.post(root + "/evaluate").json()
    assert again["status"] == "cooldown" and again["triggers"] == []
    assert client.get(root + "/triggers").json()[0]["id"] == trigger["id"]
    assert client.post(f"/api/v1/alerts/triggers/{trigger['id']}/acknowledge").status_code == 200
    assert client.get(root + "/triggers?unacknowledged_only=true").json() == []
    client.post(root + "/deactivate")
    assert client.post(root + "/evaluate").json()["status"] == "inactive"


def test_crossing_uses_prior_completed_daily_values_and_quant_prior_unavailable(runtime):
    client, _, _ = runtime
    price = backend.market_adapter.price("AAPL")["price"]
    identifier = create(client, condition="crosses_above", threshold=price - 0.5)
    result = client.post("/api/v1/alerts/test", json={"alert_id": identifier}).json()
    assert result["would_trigger"] is True
    data = result["current_values"]["AAPL"]
    assert data["previous_price"] == price - 1
    assert data["previous_as_of"] < data["as_of"]
    quant = create(client, alert_type="quant_score", condition="crosses_above")
    assert client.post("/api/v1/alerts/test", json={"alert_id": quant}).json()["status"] == "unavailable"


def test_missing_prior_and_unsupported_alert_are_unavailable(runtime):
    client, adapter, _ = runtime
    original = adapter.provider.get_daily_bars
    adapter.provider.get_daily_bars = lambda *args: {s: bars[-1:] for s, bars in original(*args).items()}
    for fields in ({"condition": "crosses_above"}, {"alert_type": "news"}):
        identifier = create(client, **fields)
        result = client.post(f"/api/v1/alerts/{identifier}/evaluate").json()
        assert result["status"] == "unavailable"
        assert result["would_trigger"] is None
        assert result["triggers"] == []


@pytest.mark.parametrize("failure", ["missing", "error", "stale"])
def test_provider_failures_never_fake_or_store_triggers(runtime, failure):
    client, adapter, _ = runtime
    if failure == "missing":
        adapter.provider = None
    elif failure == "error":
        adapter.provider.get_daily_bars = lambda *args: (_ for _ in ()).throw(RuntimeError("secret"))
    else:
        original = adapter.provider.get_daily_bars
        adapter.provider.get_daily_bars = lambda *args: {s: bars[:-10] for s, bars in original(*args).items()}
    identifier = create(client)
    result = client.post(f"/api/v1/alerts/{identifier}/evaluate")
    assert result.status_code == 200
    assert result.json()["status"] == "unavailable"
    assert result.json()["would_trigger"] is None
    assert result.json()["triggers"] == []
    assert "secret" not in result.text
    assert client.get(f"/api/v1/alerts/{identifier}").json()["trigger_count"] == 0


def test_date_only_fed_api_upcoming_and_ics_keep_unknown_time(runtime):
    client, _, store = runtime
    for day in ("2026-10-28", "2026-12-09"):
        store.upsert_event(MarketEvent(event_type=EventType.MACRO, title="FOMC", source="federal_reserve", source_id=day,
                                      metadata={"event_date": day, "time_precision": "date_only"}))
    store.upsert_event(MarketEvent(event_type=EventType.EARNINGS, symbol="AAPL", title="Results", source="IR",
                                  metadata={"event_date": "2026-10-29", "session": "AMC"}))
    macro = client.get("/api/v1/events/macro?from_date=2026-10-15&to_date=2026-12-31").json()
    assert {e["metadata"]["event_date"] for e in macro} == {"2026-10-28", "2026-12-09"}
    assert all(e["scheduled_at"] is None and e["released_at"] is None for e in macro)
    upcoming = client.get("/api/v1/events/upcoming?days=90").json()
    assert len(upcoming) == 3
    assert upcoming[1]["metadata"]["session"] == "AMC"
    company = client.get("/api/v1/events/company?symbol=AAPL&from_date=2026-10-29&to_date=2026-10-29").json()
    assert len(company) == 1 and company[0]["scheduled_at"] is None
    session_export = client.post("/api/v1/calendar/export", json={"symbols": ["AAPL"]}).json()
    assert session_export["event_count"] == 1
    assert "DTSTART;VALUE=DATE:20261029" in session_export["content"]
    assert "Session: AMC" in session_export["content"]
    for method in ("post", "get"):
        filters = dict(event_types=["macro"] if method == "post" else "macro", from_date="2026-10-15", to_date="2026-12-31")
        response = (client.post("/api/v1/calendar/export", json=filters) if method == "post"
                    else client.get("/api/v1/calendar/export", params=filters))
        assert response.status_code == 200
        result = response.json()
        assert result["event_count"] == 2
        assert "DTSTART;VALUE=DATE:20261028" in result["content"]
        assert "DTSTART;VALUE=DATE:20261209" in result["content"]
        assert "T000000" not in result["content"]
        assert "Event status: scheduled" in result["content"]
    assert all(e.scheduled_at is None for e in store.events_by_type(EventType.MACRO))


def test_errors_and_input_bounds(runtime):
    client, _, _ = runtime
    assert client.post("/api/v1/alerts/missing/evaluate").status_code == 404
    assert client.post("/api/v1/alerts/test", json={"alert_id": "missing"}).status_code == 404
    assert client.get("/api/v1/stocks/AAPL/answer", params={"question": "x" * 2001}).status_code == 422
    assert client.get("/api/v1/stocks/BAD!/answer", params={"question": "why"}).status_code == 400
    assert client.get("/api/v1/terms/search", params={"q": "x" * 201}).status_code == 422
    for key in ("symbols", "event_types", "importance"):
        assert client.post("/api/v1/calendar/export", json={key: ["x" * 100]}).status_code == 422
        assert client.get("/api/v1/calendar/export", params={key: "x" * 100}).status_code in (400, 422)
    identifier = create(client, symbols=[f"T{i}" for i in range(51)])
    assert client.post(f"/api/v1/alerts/{identifier}/evaluate").status_code == 400
