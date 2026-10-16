"""Network-free serialized official results projection contract."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import socket
from types import SimpleNamespace

import pytest

from backend.earnings_projection import project_next_earnings, EARNINGS_QUERY_LIMIT
from trading_copilot.models.events import MarketEvent, EventType, EventStatus


NOW = datetime(2026, 10, 16, 23, 59, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Projection must not use the network")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


def announcement(day="2026-10-27", session="amc", period="fourth:2026", event_id="official-1"):
    d = datetime.fromisoformat(day)
    text = f"Visa will announce financial results on {d.strftime('%B')} {d.day}, {d.year}"
    text += {"amc": ", after market close.", "bmo": ", before market open.", "unknown": "."}[session]
    return MarketEvent(
        event_id=event_id, event_type=EventType.EARNINGS, symbol="V", title="Official results announcement",
        description=text, source="company_ir_rss", source_url="https://investor.visa.com/release",
        metadata={"event_date": day, "session": session,
                  "scheduled_time_precision": "date" if session == "unknown" else "session",
                  "event_kind": "results_release", "verification_status": "verified",
                  "verification_scope": "explicit_official_announcement", "event_timezone": None,
                  "fiscal_period": period, "source_document_id": "ir_release:V:stable",
                  "source_content_hash": hashlib.sha256(text.encode()).hexdigest(),
                  "retrieved_at": "2026-10-15T12:00:00+00:00",
                  "evidence_span": {"field": "body", "start": 0, "end": len(text), "text": text}},
    )


def project(events, **kwargs):
    return project_next_earnings("V", events, now=NOW, **kwargs)


def test_amc_calendar_only_and_retained_not_fresh():
    e = announcement()
    before = deepcopy(e.model_dump())
    result = project([e])
    data, coverage = result["next_earnings"], result["earnings_coverage"]
    assert data["event_date"] == "2026-10-27" and data["days_until"] == 11
    assert data["countdown_basis"] == "calendar_days"
    assert data["scheduled_at"] is None and data["event_timezone"] is None
    assert data["session"] == "amc" and data["scheduled_time_precision"] == "session"
    assert coverage["status"] == "not_refreshed" and coverage["checked_at"] is None
    assert coverage["confirmation_status"] == "retained_official_announcement"
    assert "did not refresh" in coverage["reason"]
    assert json.loads(json.dumps(result)) == result
    assert e.model_dump() == before
    assert not {"consensus", "eps_estimate", "price_reaction", "forecast"} & data.keys()


@pytest.mark.parametrize("session", ["unknown", "bmo", "amc"])
def test_today_is_not_past_even_late_utc(session):
    data = project([announcement("2026-10-16", session)])["next_earnings"]
    assert data["days_until"] == 0 and data["scheduled_at"] is None
    assert data["session"] == session


@pytest.mark.parametrize("field,value", [
    ("event_type", EventType.MACRO), ("event_type", EventType.EARNINGS_RESULT),
    ("symbol", "TMO"), ("symbol", None), ("status", EventStatus.CANCELLED),
    ("status", EventStatus.UNKNOWN), ("status", EventStatus.RELEASED),
    ("source", "company_ir"), ("source", "official"), ("source", "fixture"),
    ("source_url", "http://investor.visa.com/release"),
    ("source_url", "https://investor.visa.com.evil.com/release"),
    ("source_url", "https://investor.visa.com@evil.com/release"),
    ("source_url", "https://u:p@investor.visa.com/release"),
    ("source_url", "https://127.0.0.1/release"),
    ("source_url", "https://[::1]/release"), ("source_url", "https://localhost/release"),
    ("source_url", "file:///private/secret"), ("source_url", "https://investor.visa.com:444/release"),
    ("source_url", "https://investor.visa.com/release#fragment"),
    ("source_url", "https://investor.visa.com\\@evil.com/release"),
    ("scheduled_at", NOW), ("released_at", NOW),
])
def test_event_filters(field, value):
    e = announcement()
    setattr(e, field, value)
    assert project([e])["next_earnings"] is None


@pytest.mark.parametrize("field,value", [
    ("event_kind", "earnings_call"), ("verification_status", "estimated"),
    ("verification_status", "unverified"), ("verification_status", "stale_unverified"),
    ("verification_scope", None), ("verification_scope", "company_ir"),
    ("source_document_id", ""), ("source_document_id", None),
    ("source_content_hash", "abc"), ("source_content_hash", None),
    ("retrieved_at", "2026-10-17T00:00:00Z"), ("retrieved_at", "2026-10-15T12:00:00"),
    ("retrieved_at", "not-time"), ("retrieved_at", None),
    ("event_date", "2026-10-27T00:00:00Z"), ("event_date", "2026-02-30"),
    ("event_date", None), ("event_date", "2026-10-28"),
    ("session", "bmo"), ("session", "unknown"), ("session", "AMC"),
    ("scheduled_time_precision", "exact"), ("scheduled_time_precision", "date"),
    ("event_timezone", "America/New_York"), ("evidence_span", None),
    ("evidence_span", {"field": "body", "start": 0, "end": 4, "text": "fake"}),
])
def test_metadata_filters(field, value):
    e = announcement()
    e.metadata[field] = value
    assert project([e])["next_earnings"] is None


@pytest.mark.parametrize("change", [
    {"start": -1}, {"start": True}, {"end": 9999}, {"field": "url"}, {"text": ""},
])
def test_invalid_evidence_offsets(change):
    e = announcement()
    e.metadata["evidence_span"].update(change)
    assert project([e])["next_earnings"] is None


@pytest.mark.parametrize("text", [
    "Visa will announce an earnings conference call on October 27, 2026, after market close.",
    "Visa will announce a conference call to discuss financial results on October 27, 2026, after market close.",
    "Visa may announce financial results on October 27, 2026, after market close.",
    "Visa will announce financial results on October 27, 2026, after market close (estimated).",
])
def test_quote_must_support_confirmed_results_not_just_metadata(text):
    e = announcement()
    e.description = text
    e.metadata["evidence_span"].update(text=text, end=len(text))
    assert project([e])["next_earnings"] is None


@pytest.mark.parametrize("field", ["event_date", "session", "scheduled_time_precision", "retrieved_at", "source_content_hash", "verification_status"])
@pytest.mark.parametrize("value", [[], {}, False, 42])
def test_malformed_metadata_fails_closed(field, value):
    e = announcement()
    e.metadata[field] = value
    assert project([e])["next_earnings"] is None


def test_results_not_call_or_canceled_prior():
    past = announcement("2026-10-15")
    canceled = announcement("2026-10-20", event_id="canceled")
    canceled.status = EventStatus.CANCELLED
    unknown = announcement("2026-10-21", event_id="unknown")
    unknown.status = EventStatus.UNKNOWN
    call = announcement("2026-10-22", event_id="call")
    call.metadata["event_kind"] = "earnings_call"
    assert project([past, canceled, unknown, call])["next_earnings"] is None
    data = project([canceled, unknown, call, announcement()])["next_earnings"]
    assert data["event_ids"] == ["official-1"]


@pytest.mark.parametrize("period", ["fourth:2026", None, "unknown"])
def test_different_active_dates_same_or_unknown_period_conflict(period):
    a, b = announcement(), announcement("2026-10-28", period=period, event_id="other")
    for events in ([a, b], [b, a]):
        result = project(events)
        assert result["next_earnings"] is None
        assert result["earnings_coverage"]["confirmation_status"] == "conflicting_announcements"


def test_past_active_contradiction_not_arbitrarily_discarded():
    assert project([announcement("2026-10-15"), announcement()])["next_earnings"] is None


def test_known_distinct_future_periods_select_earliest():
    next_quarter = announcement("2027-01-27", period="first:2027", event_id="later")
    assert project([next_quarter, announcement()])["next_earnings"]["event_ids"] == ["official-1"]


def test_equivalent_duplicates_preserve_all_ids_and_evidence():
    a, b = announcement(event_id="b"), announcement(event_id="a")
    b.metadata["source_document_id"] = "ir_release:V:second"
    data = project([a, b])["next_earnings"]
    assert data["event_ids"] == ["a", "b"]
    assert len(data["evidence"]) == 2
    assert project([a, b]) == project([b, a])


def test_date_only_and_session_equivalent_merge_without_inventing_clock():
    data = project([announcement(session="unknown"), announcement(event_id="second")])["next_earnings"]
    assert data["session"] == "amc" and data["scheduled_at"] is None
    assert len(data["evidence"]) == 2


@pytest.mark.parametrize("other", [
    announcement(session="bmo", event_id="other"),
    announcement(period="third:2026", event_id="other"),
])
def test_non_equivalent_ties_fail_closed(other):
    assert project([announcement(), other])["next_earnings"] is None


def test_query_cap_is_not_global_next_completeness():
    result = project([announcement()] * EARNINGS_QUERY_LIMIT)
    assert result["next_earnings"] is None
    assert result["earnings_coverage"]["query_truncated"] is True


def test_coverage_empty_default_and_explicit_symbol_check():
    default = project([])["earnings_coverage"]
    assert default["status"] == "not_refreshed" and default["confirmation_status"] == "not_confirmed"
    state = {"symbol": "V", "status": "empty", "checked_at": "2026-10-15T12:00:00Z"}
    assert project([], checked_state=state)["earnings_coverage"]["status"] == "empty"
    state["symbol"] = "TMO"
    assert project([], checked_state=state)["earnings_coverage"]["status"] == "not_refreshed"
    state.update(symbol="V", checked_at="2099-01-01T00:00:00Z")
    assert project([], checked_state=state)["earnings_coverage"]["status"] == "not_refreshed"


def test_configured_feed_origin_required_even_for_official_enum():
    assert project([announcement()], trusted_feeds={})["next_earnings"] is None
    assert project([announcement()], trusted_feeds={"V": "https://127.0.0.1/feed"})["next_earnings"] is None


def test_zero_eps_not_replaced_or_projected_as_consensus():
    e = announcement()
    e.forecast = "0"
    e.metadata["eps_estimate"] = 0
    result = project([e])
    assert result["next_earnings"] is not None
    assert "eps_estimate" not in result["next_earnings"] and "forecast" not in result["next_earnings"]
    assert e.forecast == "0" and e.metadata["eps_estimate"] == 0


def test_stock_detail_additions_query_and_serialization_preserve_aliases(monkeypatch):
    # No lifespan/startup: fake adapters and store only, never an actual DB.
    import backend.main as api
    from fastapi.encoders import jsonable_encoder
    calls = []
    e = announcement()
    def events_for_symbol(symbol, **kwargs):
        calls.append((symbol, kwargs))
        return [e]
    price = {"price": None, "change": None, "change_pct": None, "volume": None, "status": "empty"}
    quant = {"components": []}
    monkeypatch.setattr(api, "event_store", SimpleNamespace(events_for_symbol=events_for_symbol))
    monkeypatch.setattr(api, "interpretation_engine", SimpleNamespace(generate_interpretation=lambda _: None))
    monkeypatch.setattr(api, "market_adapter", SimpleNamespace(
        price=lambda _: price, quant=lambda _: quant,
        identity=lambda _: {"name": "Visa", "exchange": "NYSE"}))
    monkeypatch.setattr(api, "project_next_earnings", lambda symbol, events: project_next_earnings(symbol, events, now=NOW))
    response = json.loads(json.dumps(jsonable_encoder(api.get_stock_detail("v"))))
    assert calls == [("V", {"limit": 50}), ("V", {"event_types": [EventType.EARNINGS], "limit": 1000})]
    assert response["name"] == response["identity"]["name"] == "Visa"
    assert response["price"] is None and response["price_data"] == price
    assert response["quant_signals"] == quant
    assert response["quant_signals_components"] == quant["components"]
    assert response["events"] == jsonable_encoder([e.model_dump()])
    assert response["next_earnings"]["event_date"] == "2026-10-27"
    assert response["earnings_coverage"]["status"] == "not_refreshed"
