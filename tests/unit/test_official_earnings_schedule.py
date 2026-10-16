"""Offline contract/security regressions for the bounded official schedule leaf."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from contextlib import contextmanager
import hashlib

import feedparser
import httpx
import pytest

from backend.website_sources import DatedIRProvider, WebsiteSourceAdapter
from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.models.news import NewsDocument, NewsSourceType
from trading_copilot.providers.ir_release_provider import IRReleaseProvider, IR_RSS_FEEDS
from trading_copilot.providers.official_earnings_schedule import extract_official_schedule


TODAY = date(2026, 10, 16)
VISA = ("Visa will announce its fiscal fourth quarter and full-year 2026 financial results "
        "on Tuesday, October 27, 2026, after market close. "
        "The webcast will begin at 5:00 p.m. Eastern Time.")
TMO = "Thermo Fisher Scientific to Hold Earnings Conference Call on Wednesday, October 21, 2026"


def doc(body=VISA, title="Official results announcement", symbol="V"):
    return NewsDocument(document_id=f"ir_release:{symbol}:stable", symbol=symbol,
                        headline=title, body=body, publisher=symbol,
                        published_at=datetime(2026, 9, 28, 12, tzinfo=timezone.utc),
                        retrieved_at=datetime.now(timezone.utc),
                        source_url=f"https://{('investor.visa.com' if symbol == 'V' else 'ir.thermofisher.com')}/release",
                        source_type=NewsSourceType.COMPANY_IR, provider_id="company_ir_rss",
                        metadata={"feed_url": IR_RSS_FEEDS[symbol], "feed_response_url": IR_RSS_FEEDS[symbol]},
                        content_hash=hashlib.sha256(body.encode()).hexdigest())


def authenticate_parsed(document):
    # Isolated parser tests explicitly inject the observed feed response origin;
    # production sets this only after a real HTTP response in _fetch_feed.
    document.metadata["feed_response_url"] = IR_RSS_FEEDS[document.symbol]
    return document


def test_visa_session_is_not_webcast_clock():
    document = doc()
    event = extract_official_schedule(document, TODAY)
    assert event.event_type == EventType.EARNINGS
    assert event.status.value == "scheduled"
    assert event.scheduled_at is None and event.released_at is None
    assert event.metadata["event_date"] == "2026-10-27"
    assert event.metadata["session"] == "amc"
    assert event.metadata["scheduled_time_precision"] == "session"
    assert event.metadata["event_kind"] == "results_release"
    assert event.metadata["event_timezone"] is None
    span = event.metadata["evidence_span"]
    assert document.body[span["start"]:span["end"]] == span["text"]
    assert "webcast" not in span["text"]


@pytest.mark.parametrize("body", [
    "Microsoft will announce financial results on April 30, 2025.",
    "Results may be available on October 27, 2026.",
    "Visa will announce financial results on October 27.",
    "Visa will announce financial results on October 27, 2026 or October 28, 2026.",
    "Visa will announce financial results on October 27, 2026. Visa will announce financial results on October 28, 2026.",
    "Visa will announce financial results on February 30, 2027.",
    "Visa will announce financial results on October 27, 2026 (tentative).",
    "The earnings conference call on October 21, 2026 was cancelled.",
])
def test_stale_ambiguous_or_unsourced_dates_rejected(body):
    assert extract_official_schedule(doc(body), TODAY) is None


@pytest.mark.parametrize("suffix", ["", " at 5:00 pm", " at 5:00 p.m. Eastern Time"])
def test_date_only_or_unknown_clock_has_no_fabricated_instant(suffix):
    event = extract_official_schedule(doc("Visa will announce financial results on October 27, 2026" + suffix + "."), TODAY)
    assert event.metadata["session"] == "unknown"
    assert event.metadata["scheduled_time_precision"] == "date"
    assert event.scheduled_at is None


def test_tmo_call_never_becomes_results_or_bmo():
    event = extract_official_schedule(doc(TMO, TMO, "TMO"), TODAY)
    assert event.metadata["event_kind"] == "earnings_call"
    assert event.metadata["event_date"] == "2026-10-21"
    assert event.metadata["session"] == "unknown"
    assert event.scheduled_at is None


def entry(title=TMO, body="", timestamp="Mon, 28 Sep 2026 12:00:00 GMT"):
    return feedparser.parse(f'''<rss version="2.0"><channel><item><guid>stable</guid>
        <title>{title}</title><link>https://ir.thermofisher.com/release</link>
        <pubDate>{timestamp}</pubDate><description>{body}</description>
        </item></channel></rss>''').entries[0]


@pytest.mark.parametrize("status", [403, 404])
def test_title_only_denied_body_preserves_cited_call(monkeypatch, status):
    def denied(*args):
        raise httpx.HTTPStatusError("official denial", request=httpx.Request("GET", "https://ir.thermofisher.com/release"),
                                    response=httpx.Response(status))
    provider = DatedIRProvider()
    provider.schedule_mode = True
    monkeypatch.setattr(provider, "fetch_linked_body", denied)
    document = provider._parse_entry("TMO", entry(), date(2026, 7, 18), TODAY)
    assert document.body == TMO
    assert document.metadata["body_basis"] == "feed_title_only"
    assert provider.errors[0]["stage"] == "linked_body"
    assert extract_official_schedule(authenticate_parsed(document), TODAY).metadata["event_kind"] == "earnings_call"
    # Legacy news-only parser does not start fetching linked bodies.
    provider.schedule_mode = False
    assert provider._parse_entry("TMO", entry(), date(2026, 7, 18), TODAY) is None


def test_atom_timestamp_and_missing_zone():
    atom = feedparser.parse('''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>stable</id>
      <title>Official results announcement</title><link href="https://investor.visa.com/release"/>
      <published>2026-09-28T12:00:00Z</published><content>''' + VISA + '''</content></entry></feed>''').entries[0]
    provider = DatedIRProvider()
    document = provider._parse_entry("V", atom, date(2026, 7, 18), TODAY)
    assert document.published_at == datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    assert provider._parse_entry("TMO", entry(body=VISA, timestamp="2026-09-28"), date(2026, 7, 18), TODAY) is None


def test_mapping_and_partial_coverage():
    assert IR_RSS_FEEDS["V"].endswith("PressRelease.aspx?LanguageId=1&CategoryWorkflowId=00000000-0000-0000-0000-000000000000&tags=")
    assert IR_RSS_FEEDS["TMO"] == "https://ir.thermofisher.com/rss/pressrelease.aspx"
    assert "LLY" not in IR_RSS_FEEDS
    reason = WebsiteSourceAdapter(None, SimpleNamespace()).state["earnings_calendar"]["reason"]
    assert "Partial" in reason and "fixtures" not in reason


def test_ambiguous_body_cannot_be_repaired_by_old_headline():
    document = doc("Visa will announce financial results on October 27, 2026 or October 28, 2026.",
                   "Visa to announce financial results on October 27, 2026")
    assert extract_official_schedule(document, TODAY) is None


def test_successful_linked_body_and_bounded_requests(monkeypatch):
    provider = DatedIRProvider()
    provider.schedule_mode = True
    calls = []
    def body(*args):
        calls.append(args)
        return "<p>Thermo Fisher will announce financial results on October 21, 2026, before market open.</p>"
    monkeypatch.setattr(provider, "fetch_linked_body", body)
    for _ in range(5):
        document = provider._parse_entry("TMO", entry(), date(2026, 7, 18), TODAY)
    assert len(calls) == 4
    assert document.metadata["body_basis"] == "feed_title_only"
    assert extract_official_schedule(authenticate_parsed(document), TODAY).metadata["event_kind"] == "earnings_call"
    provider.linked_body_budget = 1
    document = provider._parse_entry("TMO", entry(), date(2026, 7, 18), TODAY)
    assert document.metadata["raw_content"].startswith("<p>")
    schedule = extract_official_schedule(authenticate_parsed(document), TODAY)
    assert schedule.metadata["event_kind"] == "results_release"
    assert schedule.metadata["session"] == "bmo"


@pytest.mark.parametrize("url", [
    "http://ir.thermofisher.com/release", "https://127.0.0.1/release",
    "https://evil.test/release", "https://ir.thermofisher.com.evil.test/release",
    "https://user:password@ir.thermofisher.com/release", "https://ir.thermofisher.com:444/release",
])
def test_body_ssrf_rejected_before_network(monkeypatch, url):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: pytest.fail("must reject before DNS"))
    with pytest.raises(ValueError):
        IRReleaseProvider().fetch_linked_body("TMO", url)


def test_body_private_dns_refused(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(ValueError):
        IRReleaseProvider().fetch_linked_body("TMO", "https://ir.thermofisher.com/release")


def test_linked_body_elapsed_limit(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))])
    ticks = iter([0, 11])
    monkeypatch.setattr("trading_copilot.providers.ir_release_provider.time.monotonic", lambda: next(ticks))
    @contextmanager
    def stream(*args, **kwargs):
        yield httpx.Response(200, content=b"body", headers={"content-type": "text/html"},
                             request=httpx.Request("GET", "https://ir.thermofisher.com/release"))
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises(ValueError, match="limit"):
        IRReleaseProvider().fetch_linked_body("TMO", "https://ir.thermofisher.com/release")


@pytest.mark.parametrize("status", [403, 404])
def test_feed_denials_are_explicit_not_fixture_fallback(monkeypatch, status):
    def denied(url, **kwargs):
        return httpx.Response(status, request=httpx.Request("GET", url))
    monkeypatch.setattr(httpx, "get", denied)
    provider = DatedIRProvider()
    assert provider.fetch_company_releases(["V"], date(2026, 7, 18), TODAY) == []
    assert provider.errors[0]["stage"] == "fetch_feed"


@pytest.mark.parametrize("status,content,headers", [
    (302, b"", {"location": "http://127.0.0.1/"}),
    (403, b"denied", {}), (404, b"missing", {}),
    (200, b"x" * 512_001, {"content-type": "text/html"}),
    (200, b"{}", {"content-type": "application/json"}),
])
def test_body_redirect_denial_and_size_limits(monkeypatch, status, content, headers):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))])
    @contextmanager
    def stream(*args, **kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["timeout"] <= 10 and kwargs["trust_env"] is False
        yield httpx.Response(status, content=content, headers=headers,
                             request=httpx.Request("GET", "https://ir.thermofisher.com/release"))
    monkeypatch.setattr(httpx, "stream", stream)
    with pytest.raises((ValueError, httpx.HTTPStatusError)):
        IRReleaseProvider().fetch_linked_body("TMO", "https://ir.thermofisher.com/release")


def test_refresh_90_day_schedule_discovery_idempotency_and_amendment(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date()
    future = today + timedelta(days=11)
    amended = future + timedelta(days=1)
    document = doc(f"Visa will announce financial results on {future.strftime('%B %d, %Y')}, after market close.")
    document.published_at = datetime.now(timezone.utc) - timedelta(days=18)
    seen = []
    def fetch(self, symbols, from_date, to_date):
        seen.append((to_date - from_date).days)
        return [document]
    monkeypatch.setattr(DatedIRProvider, "fetch_company_releases", fetch)
    store = EventStore(str(tmp_path / "events.db"))
    adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
    try:
        assert adapter._releases(["V"], "ir_releases")["NEW"] == 2
        document.retrieved_at += timedelta(seconds=1)
        assert adapter._releases(["V"], "ir_releases")["UNCHANGED"] == 2
        schedule_id = document.document_id + ":schedule:results_release"
        prior = store.get_event_by_source_id(schedule_id, EventType.EARNINGS)
        document.body = f"Visa will announce financial results on {amended.strftime('%B %d, %Y')}, after market close."
        assert adapter._releases(["V"], "ir_releases")["CHANGED"] == 2
        current = store.get_event_by_source_id(schedule_id, EventType.EARNINGS)
        assert current.event_id == prior.event_id
        assert current.metadata["event_date"] == amended.isoformat()
        news = store.get_event_by_source_id(document.document_id, EventType.NEWS)
        assert datetime.fromisoformat(news.metadata["document"]["retrieved_at"].replace("Z", "+00:00")) == document.retrieved_at
        revisions = store.get_revisions(prior.event_id)
        assert len(revisions) == 1
        assert revisions[0].old_snapshot["metadata"]["event_date"] == future.isoformat()
        assert seen == [90, 90, 90]
    finally:
        store.close()


@pytest.mark.parametrize("body", [
    "Visa will announce earnings dividend on October 27, 2026.",
    "Visa will announce financial results for shareholders of record on October 27, 2026.",
    "On October 27, 2026 the dividend is payable; Visa will announce financial results soon.",
    "October 27, 2026 is the investor day; Visa will announce financial results soon.",
    VISA + " The previously announced financial results release has been cancelled.",
    VISA + " We will not release these results as announced.",
    "Visa will announce financial results on October 27, 2026 or October 28, 2026. "
    "Visa will announce financial results on October 29, 2026.",
])
def test_targeted_whole_claim_false_positive_repros(body):
    assert extract_official_schedule(doc(body), TODAY) is None


@pytest.mark.parametrize("changes", [
    {"feed_url": "https://evil.test/rss"},
    {"feed_response_url": "https://evil.test/rss"},
    {"feed_response_url": "http://investor.visa.com/rss"},
    {"feed_response_url": "https://investor.visa.com:444/rss"},
    {"feed_response_url": "https://user:secret@investor.visa.com/rss"},
])
def test_classification_or_guessed_link_cannot_authenticate(changes):
    document = doc()
    document.metadata.update(changes)
    assert extract_official_schedule(document, TODAY) is None
    document.metadata.clear()
    assert extract_official_schedule(document, TODAY) is None


@pytest.mark.parametrize("response_url,link,custom,verified", [
    (IR_RSS_FEEDS["TMO"], "https://ir.thermofisher.com/release", None, True),
    ("https://evil.test/rss", "https://ir.thermofisher.com/release", None, False),
    (IR_RSS_FEEDS["TMO"], "https://evil.test/release", None, False),
    ("https://evil.test/rss", "https://ir.thermofisher.com/release", "https://evil.test/rss", False),
    (IR_RSS_FEEDS["TMO"], "https://ir.thermofisher.com/release", "https://ir.thermofisher.com/other", False),
])
def test_injected_ir_response_requires_approved_feed_and_actual_origin(monkeypatch, response_url, link, custom, verified):
    xml = (f'<rss version="2.0"><channel><item><guid>stable</guid><title>{TMO}</title>'
           f'<link>{link}</link><pubDate>Mon, 28 Sep 2026 12:00:00 GMT</pubDate>'
           f'<description>{TMO}</description></item></channel></rss>')
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(
        200, content=xml.encode(), request=httpx.Request("GET", response_url)))
    provider = DatedIRProvider(custom_feeds={"TMO": custom} if custom else None)
    documents = provider.fetch_company_releases(["TMO"], date(2026, 7, 18), TODAY)
    assert len(documents) == 1  # Custom feeds remain usable as raw, unverified news.
    assert (extract_official_schedule(documents[0], TODAY) is not None) == verified


@pytest.mark.parametrize("revision,expected", [
    ("Visa's fiscal fourth quarter 2026 financial results release on {old} has been cancelled.", "cancelled"),
    ("The timing of Visa's fiscal fourth quarter 2026 financial results is under review.", "unknown"),
    ("Visa will announce fiscal fourth quarter 2026 financial results on {old} or {new}. "
     "Visa will announce fiscal fourth quarter 2026 financial results on {later}.", "unknown"),
])
def test_same_document_revision_retires_support_without_deleting_history(monkeypatch, tmp_path, revision, expected):
    today = datetime.now(timezone.utc).date()
    old, new, later = [(today + timedelta(days=n)).strftime("%B %d, %Y") for n in (11, 12, 13)]
    document = doc(f"Visa will announce fiscal fourth quarter 2026 financial results on {old}.")
    monkeypatch.setattr(DatedIRProvider, "fetch_company_releases", lambda *a, **k: [document])
    store = EventStore(str(tmp_path / "events.db"))
    adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
    assert adapter._releases(["V"], "ir_releases")["NEW"] == 2
    source_id = document.document_id + ":schedule:results_release"
    original = store.get_event_by_source_id(source_id, EventType.EARNINGS)
    document.body = revision.format(old=old, new=new, later=later)
    assert adapter._releases(["V"], "ir_releases")["CHANGED"] == 2
    current = store.get_event_by_source_id(source_id, EventType.EARNINGS)
    assert current.event_id == original.event_id
    assert current.status.value == expected
    assert current.metadata["verification_status"] == "stale_unverified"
    assert current.metadata["projection_eligible"] is False
    assert current.metadata["revision_evidence"]["text"] == document.body
    assert store.get_revisions(original.event_id)[0].old_snapshot["status"] == "scheduled"
    assert store.count_events() == 2
    assert adapter._releases(["V"], "ir_releases")["UNCHANGED"] == 2
    assert len(store.get_revisions(original.event_id)) == 1


def test_new_document_explicit_replacement_is_scoped_and_preserves_raw_history(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date()
    old, new = [(today + timedelta(days=n)).strftime("%B %d, %Y") for n in (11, 12)]
    document = doc(f"Visa will announce fiscal fourth quarter 2026 financial results on {old}.")
    documents = [document]
    monkeypatch.setattr(DatedIRProvider, "fetch_company_releases", lambda *a, **k: documents)
    store = EventStore(str(tmp_path / "events.db"))
    adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
    adapter._releases(["V"], "ir_releases")
    original = store.get_event_by_source_id(document.document_id + ":schedule:results_release", EventType.EARNINGS)
    replacement = doc(f"Visa will announce fiscal fourth quarter 2026 financial results, rescheduled from {old} to {new}.")
    replacement.document_id += ":replacement"
    documents[:] = [replacement]
    counts = adapter._releases(["V"], "ir_releases")
    assert counts["NEW"] == 2 and counts["CHANGED"] == 1
    assert store.get_event(original.event_id).status.value == "cancelled"
    active = store.get_event_by_source_id(replacement.document_id + ":schedule:results_release", EventType.EARNINGS)
    assert active.status.value == "scheduled"
    assert active.metadata["event_date"] == (today + timedelta(days=12)).isoformat()
    assert store.count_events() == 4
    assert store.get_event_by_source_id(document.document_id, EventType.NEWS).metadata["document"]["body"] == document.body
    assert len(store.get_revisions(original.event_id)) == 1
    assert adapter._releases(["V"], "ir_releases")["UNCHANGED"] == 3


@pytest.mark.parametrize("period,language", [
    ("fiscal third quarter 2026", "rescheduled from"),
    ("fiscal fourth quarter 2026", "on"),
    ("", "rescheduled from"),
])
def test_cross_document_never_retires_by_company_or_date_alone(period, language):
    from trading_copilot.providers.official_earnings_schedule import reconcile_schedule_revision
    original = extract_official_schedule(doc("Visa will announce fiscal fourth quarter 2026 financial results on October 27, 2026."), TODAY)
    replacement = doc(f"Visa will announce {period} financial results {language} October 27, 2026 to October 28, 2026.")
    replacement.document_id += ":new"
    schedule = extract_official_schedule(replacement, TODAY)
    revisions = reconcile_schedule_revision(replacement, schedule, [original])
    if period == "fiscal fourth quarter 2026":
        assert revisions[0].status.value == "unknown"
        assert revisions[0].metadata["verification_status"] == "stale_unverified"
    else:
        assert revisions == []


@pytest.mark.parametrize("reverse", [False, True])
def test_same_batch_replacement_order_and_repeated_old_feed_entry_cannot_resurrect(monkeypatch, tmp_path, reverse):
    today = datetime.now(timezone.utc).date()
    old, new = [(today + timedelta(days=n)).strftime("%B %d, %Y") for n in (11, 12)]
    original = doc(f"Visa will announce fiscal fourth quarter 2026 financial results on {old}.")
    replacement = doc(f"Visa will announce fiscal fourth quarter 2026 financial results, rescheduled from {old} to {new}.")
    replacement.document_id += ":replacement"
    documents = [original, replacement]
    if reverse:
        documents.reverse()
    monkeypatch.setattr(DatedIRProvider, "fetch_company_releases", lambda *a, **k: documents)
    store = EventStore(str(tmp_path / "events.db"))
    adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
    assert adapter._releases(["V"], "ir_releases")["NEW"] == 4
    prior = store.get_event_by_source_id(original.document_id + ":schedule:results_release", EventType.EARNINGS)
    assert prior.status.value == "cancelled"
    counts = adapter._releases(["V"], "ir_releases")
    assert counts["CHANGED"] == 0 and counts["NEW"] == 0
    assert store.get_event(prior.event_id).status.value == "cancelled"
    assert not store.get_revisions(prior.event_id)


def test_unrelated_call_cancellation_never_cancels_results():
    from trading_copilot.providers.official_earnings_schedule import reconcile_schedule_revision
    original = extract_official_schedule(doc(), TODAY)
    revision = doc(VISA + " The conference call was cancelled.")
    assert extract_official_schedule(revision, TODAY) is None
    revised = reconcile_schedule_revision(revision, None, [original])[0]
    assert revised.status.value == "unknown"
    assert revised.metadata["projection_eligible"] is False


def test_new_document_cancellation_is_scoped_to_verified_kind_period_and_old_date(monkeypatch, tmp_path):
    today = datetime.now(timezone.utc).date()
    old = (today + timedelta(days=11)).strftime("%B %d, %Y")
    original = doc(f"Visa will announce fiscal fourth quarter 2026 financial results on {old}.")
    documents = [original]
    monkeypatch.setattr(DatedIRProvider, "fetch_company_releases", lambda *a, **k: documents)
    store = EventStore(str(tmp_path / "events.db"))
    adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
    adapter._releases(["V"], "ir_releases")
    call = extract_official_schedule(doc(f"Visa to hold earnings conference call on {old}."), today)
    store.upsert_event(call)
    cancellation = doc(f"Visa's fiscal fourth quarter 2026 financial results release on {old} has been cancelled.")
    cancellation.document_id += ":cancellation"
    documents[:] = [cancellation]
    counts = adapter._releases(["V"], "ir_releases")
    assert counts["NEW"] == 1 and counts["CHANGED"] == 1
    prior = store.get_event_by_source_id(original.document_id + ":schedule:results_release", EventType.EARNINGS)
    assert prior.status.value == "cancelled"
    assert store.get_event_by_source_id(call.source_id, EventType.EARNINGS).status.value == "scheduled"
    assert len(store.get_revisions(prior.event_id)) == 1
    assert store.count_events() == 4
