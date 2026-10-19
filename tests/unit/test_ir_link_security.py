"""No live requests: unsafe fallback URLs and whole-operation deadlines."""
from contextlib import contextmanager
from datetime import date
import json
import threading

import httpx
import pytest

from backend.website_sources import DatedIRProvider, WebsiteSourceAdapter
from trading_copilot.events.store import EventStore
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from tests.unit.test_official_earnings_schedule import entry, TODAY


@pytest.mark.parametrize("location", ["entry", "feed", "id"])
@pytest.mark.parametrize("unsafe", [
    "https://USER_SENTINEL:PASS_SENTINEL@ir.thermofisher.com/release",
    "https://ir.thermofisher.com/release?api_key=SECRET_SENTINEL",
])
def test_unsafe_source_never_emitted_or_diagnosed_verbatim(monkeypatch, tmp_path, location, unsafe):
    provider = DatedIRProvider()
    provider.schedule_mode = True
    item = entry()
    if location == "entry":
        item["link"] = unsafe
    elif location == "id":
        item["id"] = unsafe
    else:
        provider.feeds["TMO"] = unsafe
    monkeypatch.setattr(provider, "fetch_linked_body", lambda *a: pytest.fail("unsafe fetch"))
    documents = [d for d in [provider._parse_entry("TMO", item, date(2026, 7, 18), TODAY)] if d]
    assert documents == []
    provider._error("TMO", "fetch_feed", unsafe, ValueError("failed " + unsafe))
    store = EventStore(str(tmp_path / "events.db"))
    try:
        adapter = WebsiteSourceAdapter(store, None)
        assert adapter._documents(documents, "ir_releases", len(provider.errors))["NEW"] == 0
        serialized = json.dumps({"documents": documents, "errors": provider.errors,
                                 "events": [e.model_dump(mode="json") for e in store.events_for_symbol("TMO")]})
        for secret in ("USER_SENTINEL", "PASS_SENTINEL", "SECRET_SENTINEL", unsafe):
            assert secret not in serialized
    finally:
        store.close()


@pytest.mark.parametrize("slow_stage", ["dns", "headers", "empty_return"])
def test_entire_operation_deadline_including_empty_body(monkeypatch, slow_stage):
    clock = [0]
    monkeypatch.setattr("trading_copilot.providers.ir_release_provider.time.monotonic", lambda: clock[0])
    def dns(*a, **k):
        if slow_stage == "dns":
            clock[0] = 45
        return [(2, 1, 6, "", ("8.8.8.8", 443))]
    monkeypatch.setattr("socket.getaddrinfo", dns)
    @contextmanager
    def stream(*a, **k):
        if slow_stage == "headers":
            clock[0] = 45
        yield httpx.Response(200, content=b"", headers={"content-type": "text/html"},
                             request=httpx.Request("GET", a[1]))
        if slow_stage == "empty_return":
            clock[0] = 45
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises(ValueError, match="elapsed limit"):
        IRReleaseProvider().fetch_linked_body("TMO", "https://ir.thermofisher.com/release")


@pytest.mark.parametrize("stage", ["dns", "headers"])
def test_uncooperative_operation_has_bounded_workers_and_no_late_result(monkeypatch, stage):
    import trading_copilot.providers.ir_release_provider as module
    slots = threading.BoundedSemaphore(2)
    monkeypatch.setattr(module, "_LINKED_SLOTS", slots)
    release = threading.Event()
    entered = []
    def dns(*a, **k):
        if stage == "dns":
            entered.append(1)
            release.wait()
        return [(2, 1, 6, "", ("8.8.8.8", 443))]
    @contextmanager
    def stream(*a, **k):
        entered.append(1)
        release.wait()
        yield httpx.Response(200, content=b"late", headers={"content-type": "text/html"},
                             request=httpx.Request("GET", a[1]))
    monkeypatch.setattr(module.socket, "getaddrinfo", dns)
    monkeypatch.setattr(httpx, "stream", stream)
    try:
        provider = IRReleaseProvider(timeout=0.01)
        for _ in range(2):
            with pytest.raises(ValueError, match="elapsed limit"):
                provider.fetch_linked_body("TMO", "https://ir.thermofisher.com/release")
        for _ in range(8):
            with pytest.raises(ValueError, match="inflight limit"):
                provider.fetch_linked_body("TMO", "https://ir.thermofisher.com/release")
        assert len(entered) == 2
    finally:
        release.set()
    # Workers release their slots only after leaving the blocked operation.
    assert slots.acquire(timeout=1)
    assert slots.acquire(timeout=1)
    slots.release()
    slots.release()
