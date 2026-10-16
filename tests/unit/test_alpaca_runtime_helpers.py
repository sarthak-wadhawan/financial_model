"""Offline regression checks for historical helpers and data-host health."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from tenacity import wait_none

from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider
from trading_copilot.storage.cache import MemoryCache


START = datetime(2024, 1, 2, 9, 30, 1, 123456, tzinfo=timezone(timedelta(hours=-5)))
END = START + timedelta(seconds=2)


@pytest.fixture
def provider():
    instance = AlpacaMarketDataProvider(
        api_key="offline-key", api_secret="offline-secret", cache=MemoryCache()
    )
    instance._client.close()
    yield instance
    instance.close()


def transport(provider, handler):
    provider._client = httpx.Client(
        base_url=provider.base_url,
        headers=provider._auth_headers(),
        transport=httpx.MockTransport(handler),
    )


def fetch(provider, kind, limit=10000):
    # Keep production retry count/types, but eliminate backoff in offline tests.
    method = getattr(provider, f"get_historical_{kind}")
    return method.retry_with(wait=wait_none())(provider, "SPY", START, END, limit=limit)


@pytest.mark.parametrize("kind", ["quotes", "trades"])
def test_all_pages_exact_bounds_and_complete_cache(provider, kind):
    requests = []
    records = [{"t": "2024-01-02T14:30:02Z", "i": i, "p": 100 + i} for i in range(3)]

    def handler(request):
        requests.append(request)
        assert request.url.path == f"/v2/stocks/SPY/{kind}"
        assert request.url.params["start"] == "2024-01-02T14:30:01.123456Z"
        assert request.url.params["end"] == "2024-01-02T14:30:03.123456Z"
        assert request.url.params["feed"] == "iex"
        assert request.url.params["limit"] == "1"
        index = len(requests) - 1
        assert request.url.params.get("page_token") == (None if index == 0 else f"page-{index}")
        return httpx.Response(200, json={
            kind: [records[index]],
            "next_page_token": f"page-{index + 1}" if index < 2 else None,
        })

    transport(provider, handler)
    assert fetch(provider, kind, limit=1) == records
    # Page size is not a total cap and does not alter range-cache identity.
    assert fetch(provider, kind) == records
    assert len(requests) == 3


@pytest.mark.parametrize("kind", ["quotes", "trades"])
@pytest.mark.parametrize("tokens", [("same", "same"), ("a", "b", "a")])
def test_repeated_token_fails_without_caching(provider, kind, tokens):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={kind: [{"i": len(requests)}], "next_page_token": tokens[len(requests) - 1]})

    transport(provider, handler)
    with pytest.raises(ValueError, match="Repeated Alpaca pagination token"):
        fetch(provider, kind)
    assert len(requests) == len(tokens)
    assert not provider.cache._store


@pytest.mark.parametrize("kind", ["quotes", "trades"])
@pytest.mark.parametrize("failure", [401, 403, 429, 500, "timeout", "connect"])
def test_later_page_error_never_caches_partial_and_preserves_retries(provider, kind, failure):
    requests = []

    def handler(request):
        requests.append(request)
        if "page_token" not in request.url.params:
            return httpx.Response(200, json={kind: [{"i": 1}], "next_page_token": "next"})
        if failure == "timeout":
            raise httpx.ReadTimeout("offline timeout", request=request)
        if failure == "connect":
            raise httpx.ConnectError("offline connect", request=request)
        return httpx.Response(failure, json={"message": "offline failure"})

    transport(provider, handler)
    error = ValueError if failure in (401, 403) else (
        httpx.ReadTimeout if failure == "timeout" else
        httpx.ConnectError if failure == "connect" else httpx.HTTPStatusError
    )
    with pytest.raises(error) as caught:
        fetch(provider, kind)
    if failure in (401, 403):
        assert ("authentication failed" if failure == 401 else "access forbidden") in str(caught.value)
    if isinstance(failure, int) and failure >= 429:
        assert caught.value.response.status_code == failure
    assert len(requests) == (2 if failure in (401, 403) else 6)
    assert not provider.cache._store


@pytest.mark.parametrize("kind", ["quotes", "trades"])
def test_legacy_partial_cache_is_ignored(provider, kind):
    old_key = provider._cache_key(["SPY"], START, END, data_type=kind)
    provider.cache.set(old_key, [{"i": "legacy-partial"}])
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={kind: [{"i": "complete"}], "next_page_token": None})

    transport(provider, handler)
    assert fetch(provider, kind) == [{"i": "complete"}]
    assert len(requests) == 1
    assert provider.cache.get(old_key) == [{"i": "legacy-partial"}]


@pytest.mark.parametrize("kind", ["quotes", "trades"])
@pytest.mark.parametrize("limit", [0, 10001, -1, 1.5, True])
def test_invalid_page_size_rejected_before_cache_or_request(provider, kind, limit):
    transport(provider, lambda request: pytest.fail("Invalid limit must not make a request"))
    with pytest.raises(ValueError, match="integer page size from 1 to 10000"):
        fetch(provider, kind, limit=limit)
    assert not provider.cache._store


@pytest.mark.parametrize("status", [200, 401, 403, 429, 404])
def test_health_uses_authenticated_free_stock_data_only(provider, status):
    requests = []
    provider.feed = "sip"  # Health must still probe the free feed.

    def handler(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url.host == "data.alpaca.markets"
        assert request.url.path == "/v2/stocks/SPY/quotes/latest"
        assert dict(request.url.params) == {"feed": "iex"}
        assert request.headers["APCA-API-KEY-ID"] == "offline-key"
        assert request.headers["APCA-API-SECRET-KEY"] == "offline-secret"
        return httpx.Response(status, json={})

    transport(provider, handler)
    assert provider.health_check() is (status == 200)
    assert len(requests) == 1


def test_health_network_failure_is_false(provider):
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    transport(provider, handler)
    assert provider.health_check() is False
