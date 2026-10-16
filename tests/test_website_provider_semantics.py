"""Permanent regressions for provider audit findings 38–41.

All requests are mocked. Fixture mode is opt-in and timestamps are never
promoted from date/session/reference-period evidence into exact release times.
"""

from datetime import date, datetime, timedelta, timezone
import json
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import httpx
import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.providers.earnings_calendar import EarningsCalendarProvider
from trading_copilot.providers.macro_calendar import MacroCalendarProvider


@pytest.fixture
def store(tmp_path):
    value = EventStore(tmp_path / "events.db")
    yield value
    value.close()


@pytest.fixture
def macro(store, tmp_path):
    value = MacroCalendarProvider(store, cache_dir=tmp_path / "macro")
    yield value
    value.close()


@pytest.fixture
def earnings(store, tmp_path):
    value = EarningsCalendarProvider(store, cache_dir=tmp_path / "earnings")
    yield value
    value.close()


def response(payload=None, text=None, url="https://example.test/calendar"):
    return httpx.Response(200, json=payload if text is None else None,
                          text=text, request=httpx.Request("GET", url))


def panel(year, month, days):
    return f'''<div class="panel panel-default"><div class="panel-heading">
    <h4>{year} FOMC Meetings</h4></div><div class="panel-body">
    <div class="row fomc-meeting"><div class="fomc-meeting__month"><strong>{month}</strong></div>
    <div class="fomc-meeting__date">{days}</div></div></div></div>'''


def test_fed_current_year_official_first_no_fixture_merge(macro, monkeypatch):
    year = datetime.now().year
    get = Mock(return_value=response(text=panel(year, "January", "27-28"), url=macro.FED_FOMC_CALENDAR_URL))
    monkeypatch.setattr(macro.client, "get", get)
    fixture = Mock(side_effect=AssertionError("live must not read fixtures"))
    monkeypatch.setattr(macro, "_load_fomc_fixture", fixture)
    events = macro.fetch_fomc_schedule(year)
    assert len(events) == 1
    get.assert_called_once_with(macro.FED_FOMC_CALENDAR_URL)
    fixture.assert_not_called()
    assert events[0]["source"] == "federal_reserve"
    assert events[0]["metadata"]["retrieved_at"]
    assert events[0]["metadata"]["evidence"]
    assert macro.health_check()


@pytest.mark.parametrize("failure", ["network", "403", "parse"])
def test_fed_failures_are_errors_never_fixture_success(macro, monkeypatch, failure):
    if failure == "network":
        get = Mock(side_effect=httpx.ConnectError("offline"))
    elif failure == "403":
        get = Mock(return_value=httpx.Response(403, request=httpx.Request("GET", macro.FED_FOMC_CALENDAR_URL)))
    else:
        get = Mock(return_value=response(text="unrecognized calendar layout"))
    monkeypatch.setattr(macro.client, "get", get)
    fixture = Mock(side_effect=AssertionError("no fallback"))
    monkeypatch.setattr(macro, "_load_fomc_fixture", fixture)
    with pytest.raises((httpx.HTTPError, ValueError)):
        macro.fetch_fomc_schedule()
    assert macro.last_fetch_status["fomc"]["status"] == "error"
    assert not macro.health_check()
    assert macro.refresh(years=[datetime.now().year])["ERROR"] == 2
    fixture.assert_not_called()


def test_fed_panels_year_scope_cross_month_and_no_prose_dates(macro):
    html = panel(2026, "January", "27-28") + panel(2027, "January", "26-27")
    html += panel(2026, "April/May", "30-1*")
    html += "<p>Minutes published March 17-18, 2026</p>"
    events = macro._parse_fomc_html(html, 2026)
    assert [e["metadata"]["meeting_end"] for e in events] == ["2026-01-28", "2026-05-01"]
    assert all(e["released_at"] is None and e["scheduled_at"] is None for e in events)
    assert all(e["metadata"]["minutes_date"] is None for e in events)


def test_fed_official_abbreviated_cross_month_and_notation_vote(macro):
    html = panel(2024, "Apr/May", "30-1") + panel(2024, "August", "22 (notation vote)")
    event = macro._parse_fomc_html(html, 2024)[0]
    assert event["metadata"]["meeting_start"] == "2024-04-30"
    assert event["metadata"]["meeting_end"] == "2024-05-01"
    assert len(macro._parse_fomc_html(html, 2024)) == 1


def test_fed_unsupported_date_shape_does_not_guess(macro):
    with pytest.raises(ValueError, match="Unsupported"):
        macro._parse_fomc_html(panel(2026, "January", "date pending"), 2026)


@pytest.mark.parametrize("month,days,expected_hour", [("January", "27-28", 19), ("March", "17-18", 18), ("December", "8-9", 19)])
def test_fed_derived_customary_time_uses_dst_not_exact_schedule(macro, month, days, expected_hour):
    event = macro._parse_fomc_html(panel(2026, month, days), 2026)[0]
    metadata = event["metadata"]
    expected = datetime.fromisoformat(metadata["expected_statement_at"])
    assert expected.hour == expected_hour
    assert expected.astimezone(ZoneInfo("America/New_York")).hour == 14
    assert metadata["scheduled_time_precision"] == "date"
    assert "not_verified" in metadata["expected_statement_time_source"]
    assert event["scheduled_at"] is None


def test_fed_demo_fixture_is_marked_and_cwd_independent(macro, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    macro.mode = "demo"
    monkeypatch.setattr(macro.client, "get", Mock(side_effect=AssertionError("demo offline")))
    events = macro.fetch_fomc_schedule(2026)
    assert len(events) == 8
    assert all(e["source"] == "fixture" for e in events)
    assert all(e["event_key"].startswith("fixture_") for e in events)
    assert all(e["metadata"]["verification_state"] == "demo_fixture" for e in events)
    assert not macro.health_check()


def bls_payload():
    return {"status": "REQUEST_SUCCEEDED", "Results": {"series": [{"seriesID": "CUSR0000SA0", "data": [
        {"year": "2026", "period": "M13", "value": "310"},
        {"year": "2026", "period": "M09", "value": "315.301", "footnotes": [{"code": "P", "text": "Preliminary"}]},
        {"year": "2026", "period": "M08", "value": "."},
    ]}]}}


def test_bls_reference_month_not_release_and_m13_excluded(macro, monkeypatch):
    monkeypatch.setattr(macro.client, "post", Mock(return_value=response(bls_payload())))
    rows = macro.fetch_bls_series("CUSR0000SA0", 2026, 2026)
    assert len(rows) == 1
    assert rows[0]["date"] == date(2026, 9, 1)  # compatibility: observation date only
    assert rows[0]["observation_period"] == "2026-09"
    assert rows[0]["release_date"] is None and rows[0]["released_at"] is None
    release = macro.fetch_latest_bls_release("CUSR0000SA0")
    assert release["actual"] == "315.301"
    assert release["release_date"] is None and release["released_at"] is None
    assert release["observation_date"] == date(2026, 9, 1)
    assert release["source_url"] == macro.BLS_API_URL
    assert datetime.fromisoformat(release["retrieved_at"]).tzinfo is not None
    assert release["footnotes"][0]["code"] == "P"


def test_bls_observations_do_not_publish_or_mutate_schedule(macro, monkeypatch):
    observation = {"actual": "315.301", "release_date": None, "released_at": None,
                   "observation_period": "2026-09", "retrieved_at": "2026-10-14T19:00:00+00:00"}
    monkeypatch.setattr(macro, "fetch_latest_bls_release", Mock(return_value=observation))
    update = Mock(side_effect=AssertionError("no invented release"))
    monkeypatch.setattr(macro, "update_event_values", update)
    counts = macro.fetch_released_values(since=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert counts == {"UPDATED": 0, "ERROR": 0, "UNMATCHED": 7}
    update.assert_not_called()


@pytest.mark.parametrize("method,series,status_key", [("fetch_bea_series", "GDP", "bea"), ("fetch_census_series", "RSXFS", "census")])
def test_unimplemented_official_parsers_explicit_unavailable(macro, monkeypatch, method, series, status_key):
    get = Mock(side_effect=AssertionError("no invalid HTTP query"))
    monkeypatch.setattr(macro.client, "get", get)
    with pytest.raises(NotImplementedError):
        getattr(macro, method)(series)
    assert macro.last_fetch_status[status_key]["status"] == "unavailable"
    get.assert_not_called()
    assert macro.get_provider_status()["gdp" if status_key == "bea" else "retail_sales"] == "provider_pending"


def test_economic_schedule_not_successful_empty(macro):
    with pytest.raises(NotImplementedError):
        macro.fetch_economic_calendar(2026)
    assert macro.last_fetch_status["economic_calendar"]["status"] == "unavailable"


def test_earnings_live_missing_keys_no_demo_fallback(earnings, monkeypatch):
    load = Mock(side_effect=AssertionError("no live fixture"))
    monkeypatch.setattr(earnings, "_load_fixtures", load)
    with pytest.raises(RuntimeError, match="No live"):
        earnings.fetch_earnings_calendar()
    assert earnings.last_fetch_status["status"] == "unavailable"
    assert earnings.refresh()["ERROR"] == 1
    assert not earnings.health_check()
    load.assert_not_called()


def test_earnings_live_failed_sources_not_demo_and_no_key_logging(earnings, monkeypatch, caplog):
    earnings.fmp_api_key = "fake-secret-test-only"
    monkeypatch.setattr(earnings, "_fetch_fmp", Mock(side_effect=RuntimeError("https://example.test?apikey=fake-secret-test-only")))
    load = Mock(side_effect=AssertionError("no live fixture"))
    monkeypatch.setattr(earnings, "_load_fixtures", load)
    with pytest.raises(RuntimeError, match="sources failed"):
        earnings.fetch_earnings_calendar()
    assert earnings.last_fetch_status["status"] == "error"
    assert "fake-secret-test-only" not in caplog.text
    load.assert_not_called()


def test_earnings_scoped_successful_empty_does_not_fall_through(earnings, monkeypatch):
    earnings.alpha_vantage_api_key = "dummy"
    earnings.fmp_api_key = "dummy"
    monkeypatch.setattr(earnings, "_fetch_alpha_vantage", Mock(return_value=[]))
    fmp = Mock(side_effect=AssertionError("empty is success"))
    monkeypatch.setattr(earnings, "_fetch_fmp", fmp)
    assert earnings.fetch_earnings_calendar(["AAPL"]) == []
    assert earnings.last_fetch_status["status"] == "empty"
    assert earnings.health_check()
    fmp.assert_not_called()


@pytest.mark.parametrize("session", ["bmo", "amc", "dmc", "unknown"])
@pytest.mark.parametrize("report_date", ["2026-01-28", "2026-07-28"])
def test_fmp_session_date_never_fake_exact(earnings, monkeypatch, session, report_date):
    monkeypatch.setattr(earnings.client, "get", Mock(return_value=response([
        {"symbol": "AAPL", "date": report_date, "time": session, "epsEstimated": 1.5}]
    )))
    events = earnings._fetch_fmp(["AAPL"], None, None)
    event = events[0]
    assert event["scheduled_at"] is None and event["released_at"] is None
    metadata = event["metadata"]
    assert metadata["event_date"] == report_date and metadata["session"] == session
    assert metadata["scheduled_time_precision"] == ("date" if session == "unknown" else "session")
    assert metadata["consensus_as_of"] is None
    assert metadata["estimate_source"] == "fmp"
    assert metadata["estimate_source_url"] == event["source_url"]
    assert datetime.fromisoformat(metadata["retrieved_at"]).tzinfo is not None
    stored = earnings._create_market_event(event)
    assert stored.scheduled_at is None and stored.metadata["event_date"] == report_date


def test_alpha_vantage_date_only(earnings, monkeypatch):
    csv = "symbol,reportDate,estimate,currency\nAAPL,2026-10-28,1.55,USD\n"
    monkeypatch.setattr(earnings.client, "get", Mock(return_value=response(text=csv)))
    event = earnings._fetch_alpha_vantage(["AAPL"], None, None)[0]
    assert event["scheduled_at"] is None
    assert event["metadata"]["scheduled_time_precision"] == "date"
    assert event["metadata"]["event_date"] == "2026-10-28"


@pytest.mark.parametrize("method,payload", [("_fetch_alpha_vantage", None), ("_fetch_fmp", {"Error Message": "quota"}), ("_fetch_polygon", {"status": "ERROR"}), ("_fetch_twelve_data", {"status": "error"})])
def test_earnings_error_payload_not_verified_empty(earnings, monkeypatch, method, payload):
    resp = response(text='{"Note":"quota"}') if payload is None else response(payload)
    monkeypatch.setattr(earnings.client, "get", Mock(return_value=resp))
    with pytest.raises(ValueError):
        getattr(earnings, method)(None, None, None)


@pytest.mark.parametrize("method,payload", [
    ("_fetch_fmp", [{"symbol": "AAPL", "date": "invalid"}]),
    ("_fetch_polygon", {"results": [{"ticker": "AAPL", "report_date": "invalid"}]}),
    ("_fetch_twelve_data", {"data": [{"symbol": "AAPL", "report_date": "invalid"}]}),
])
def test_malformed_earnings_rows_not_scoped_empty(earnings, monkeypatch, method, payload):
    monkeypatch.setattr(earnings.client, "get", Mock(return_value=response(payload)))
    with pytest.raises(ValueError, match="report date"):
        getattr(earnings, method)(None, None, None)


def test_explicit_earnings_exact_time_distinct_from_session(earnings):
    exact = datetime(2026, 10, 28, 16, 35, tzinfo=ZoneInfo("America/New_York"))
    timing = earnings._calendar_timing(date(2026, 10, 28), "amc", exact)
    assert timing["scheduled_time_precision"] == "exact"
    assert timing["scheduled_at"] == datetime(2026, 10, 28, 20, 35, tzinfo=timezone.utc)
    assert timing["session"] == "amc"
    with pytest.raises(ValueError, match="timezone"):
        earnings._calendar_timing(date(2026, 10, 28), "amc", exact.replace(tzinfo=None))


def test_demo_earnings_persists_date_only_and_upcoming(earnings, store, tmp_path, monkeypatch):
    tomorrow = date.today() + timedelta(days=1)
    fixture = [{"symbol": "AAPL", "date": tomorrow.isoformat(), "time": "amc"}]
    (tmp_path / "earnings_calendar.json").write_text(json.dumps(fixture))
    earnings.fixture_dir = tmp_path
    earnings.mode = "demo"
    monkeypatch.setattr(earnings.client, "get", Mock(side_effect=AssertionError("demo offline")))
    first = earnings.refresh(["AAPL"], date.today(), tomorrow)
    second = earnings.refresh(["AAPL"], date.today(), tomorrow)
    assert first["NEW"] == 1 and first["ERROR"] == 0
    assert second["UNCHANGED"] == 1
    upcoming = earnings.get_upcoming_earnings("AAPL", 2)
    assert len(upcoming) == 1
    event = upcoming[0]
    assert event.scheduled_at is None and event.released_at is None
    assert event.source == "fixture" and event.metadata["verification_state"] == "demo_fixture"
    assert event.metadata["event_date"] == tomorrow.isoformat()
    assert len(store.events_by_type(EventType.EARNINGS)) == 1
    assert not earnings.health_check()
