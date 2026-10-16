"""Offline regressions for bounded SEC retries and fair-access pacing."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import threading

import httpx
import pytest

from trading_copilot.providers import sec_http


URL = "https://data.sec.gov/submissions/CIK0000123456.json"
IDENTITY = "Offline tests sec@synthetic.invalid"


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        now = 100.0

        def __init__(self):
            self.sleeps = []

        def sleep(self, amount):
            assert 0 <= amount <= sec_http.SECTransport.MAX_RETRY_WAIT
            self.sleeps.append(amount)
            self.now += amount

    clock = Clock()
    monkeypatch.setattr(sec_http.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(sec_http.time, "sleep", clock.sleep)
    monkeypatch.setattr(sec_http, "_LAST_REQUEST", 0.0)
    monkeypatch.setattr(sec_http, "_LOCK", threading.Lock())
    return clock


def transport(handler):
    return sec_http.SECTransport(
        IDENTITY, httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    )


@pytest.mark.parametrize("retry", [
    "86400", "6", "1e309", "9" * 1000, "NaN", "inf", "-inf", "-1",
    "garbage https://secret.invalid/?token=private", "", "Mon, 99 Foo 99999 00:00:00 GMT",
    "Fri, 31 Dec 9999 23:59:59 GMT", "Fri, 01 Jan 1999 00:00:00 GMT",
])
@pytest.mark.parametrize("status", [429, 503])
def test_rejects_unsafe_retry_without_sleeping_or_resending(clock, retry, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Retry-After": retry})

    sec = transport(handler)
    try:
        with pytest.raises(httpx.TransportError, match="SEC unavailable") as error:
            sec.get(URL)
        assert len(calls) == 1
        assert clock.sleeps == [0]
        assert "private" not in str(error.value)
        assert "https://" not in str(error.value)
        assert sec_http._LOCK.acquire(blocking=False)
        sec_http._LOCK.release()
    finally:
        sec.close()


@pytest.mark.parametrize("retry", ["0", "0.01", "1", "5", "date", None])
def test_ordinary_retry_succeeds_with_minimum_spacing(clock, monkeypatch, retry):
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)

    class FixedDateTime:
        @staticmethod
        def now(tz):
            return now

    monkeypatch.setattr(sec_http, "datetime", FixedDateTime)
    header = format_datetime(now + timedelta(seconds=2)) if retry == "date" else retry
    calls = []

    def handler(request):
        calls.append(clock.now)
        return httpx.Response(429 if len(calls) == 1 else 200, json={"ok": True},
                              headers={} if header is None else {"Retry-After": header})

    sec = transport(handler)
    try:
        assert sec.get(URL).json() == {"ok": True}
        expected = 2 if retry == "date" else float(retry) if retry is not None else 1
        assert calls[1] - calls[0] >= max(0.125, expected)
    finally:
        sec.close()


@pytest.mark.parametrize("failure", [500, 502, 503, 504, "transport"])
def test_transient_errors_still_retry_then_succeed(clock, failure):
    calls = []

    def handler(request):
        calls.append(clock.now)
        if len(calls) < 3:
            if failure == "transport":
                raise httpx.ConnectError("secret URL?token=private", request=request)
            return httpx.Response(failure)
        return httpx.Response(200, content=b"ok")

    sec = transport(handler)
    try:
        assert sec.get(URL).content == b"ok"
        assert calls == [100, 101, 103]
    finally:
        sec.close()


@pytest.mark.parametrize("failure", [429, 503, "transport"])
def test_three_attempt_limit_and_sanitized_errors(clock, failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "transport":
            raise httpx.ConnectError("secret URL?token=private", request=request)
        return httpx.Response(failure, text="token=private")

    sec = transport(handler)
    try:
        with pytest.raises(httpx.HTTPError) as error:
            sec.get(URL)
        assert len(calls) == 3
        assert "private" not in str(error.value)
        assert "https://" not in str(error.value)
    finally:
        sec.close()


def test_overall_budget_includes_requests_and_rejects_wait_not_caps(clock):
    calls = []

    def handler(request):
        calls.append(request)
        remaining = 30 if len(calls) == 1 else 1
        assert all(0 < value <= remaining / 4 for value in request.extensions["timeout"].values())
        clock.now += 28 if len(calls) == 1 else 0.5
        return httpx.Response(503)

    sec = transport(handler)
    try:
        with pytest.raises(httpx.TransportError, match="time budget"):
            sec.get(URL)
        assert len(calls) == 2
        assert clock.now == 129.5
        assert max(clock.sleeps) == 1
    finally:
        sec.close()


def test_elapsed_request_budget_stops_before_retry(clock):
    calls = []

    def handler(request):
        calls.append(request)
        clock.now += 31
        return httpx.Response(200, content=b"late")

    sec = transport(handler)
    try:
        with pytest.raises(httpx.TimeoutException, match="time budget"):
            sec.get(URL)
        assert len(calls) == 1
        assert clock.sleeps == [0]
    finally:
        sec.close()


def test_http_date_wait_cannot_exceed_remaining_budget(clock, monkeypatch):
    now = datetime(2026, 10, 16, tzinfo=timezone.utc)

    class FixedDateTime:
        @staticmethod
        def now(tz):
            return now

    monkeypatch.setattr(sec_http, "datetime", FixedDateTime)
    calls = []

    def handler(request):
        calls.append(request)
        clock.now += 29
        return httpx.Response(429, headers={"Retry-After": format_datetime(now + timedelta(seconds=2))})

    sec = transport(handler)
    try:
        with pytest.raises(httpx.TransportError, match="time budget"):
            sec.get(URL)
        assert len(calls) == 1
        assert clock.sleeps == [0]
    finally:
        sec.close()


def test_retry_sleep_holds_neither_lock_nor_response(clock, monkeypatch):
    responses = []
    sleep = clock.sleep

    def checked_sleep(amount):
        if amount == 1:
            assert responses[0].is_closed
            assert sec_http._LOCK.acquire(blocking=False)
            sec_http._LOCK.release()
        sleep(amount)

    monkeypatch.setattr(sec_http.time, "sleep", checked_sleep)

    def handler(request):
        response = httpx.Response(503 if not responses else 200, content=b"ok")
        responses.append(response)
        return response

    sec = transport(handler)
    try:
        assert sec.get(URL).status_code == 200
    finally:
        sec.close()


def test_throttle_lock_wait_is_bounded(clock, monkeypatch):
    class BusyLock:
        def acquire(self, *, timeout):
            assert timeout == 30
            return False

    monkeypatch.setattr(sec_http, "_LOCK", BusyLock())
    sec = transport(lambda request: pytest.fail("Must not send while lock is busy"))
    try:
        with pytest.raises(httpx.TimeoutException, match="time budget"):
            sec.get(URL)
    finally:
        sec.close()


@pytest.mark.parametrize("status", [403, 302])
def test_403_and_redirects_are_not_retried_or_followed(clock, status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Location": "https://evil.invalid/?token=private"})

    sec = transport(handler)
    try:
        with pytest.raises(httpx.HTTPStatusError) as error:
            sec.get(URL)
        assert error.value.response.status_code == status
        assert len(calls) == 1
        assert "private" not in str(error.value)
    finally:
        sec.close()


@pytest.mark.parametrize("url", [
    "https://evil.invalid/a", URL + "?token=private", "http://data.sec.gov/a",
])
def test_url_restrictions_still_precede_network(clock, url):
    sec = transport(lambda request: pytest.fail("Unsafe URL must not reach transport"))
    try:
        with pytest.raises(ValueError, match="Unsafe SEC URL") as error:
            sec.get(url)
        assert "private" not in str(error.value)
    finally:
        sec.close()
