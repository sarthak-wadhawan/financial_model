"""Independent-audit regressions: exact bounds, retrieval provenance, reachable evidence.

All writes are to tmp_path stores; all provider transports are injected offline.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.website_data import WebsiteDataAdapter
from backend.website_sources import WebsiteSourceAdapter, WebsiteSECExhibitProvider
from trading_copilot.config import Config, Settings
from trading_copilot.events.store import EventStore
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine
from trading_copilot.models.events import MarketEvent, EventType
from trading_copilot.models.interpretation import InterpretationRequest
from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider
from trading_copilot.providers.mock import MockMarketDataProvider
from trading_copilot.storage.cache import MemoryCache
from trading_copilot.models.news import NewsDocument, NewsSourceType
from trading_copilot.providers.management_extractor import ManagementExtractor

UTC = timezone.utc


@pytest.mark.parametrize("feed_format", ["rss", "atom"])
@pytest.mark.parametrize("kind", ["news", "ir"])
@pytest.mark.parametrize("publication", ["2026-10-14", "2026-10-14T12:00:00", "2026-10-14T00:00:00Z"])
def test_feed_normalization_requires_source_clock_and_zone(feed_format, kind, publication):
    import feedparser
    from backend.website_sources import DatedRSSProvider, DatedIRProvider
    body = "Tim Cook said we expect revenue growth to accelerate with strong customer demand."
    link = "https://www.apple.com/newsroom/precision"
    if feed_format == "atom":
        xml = f'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Apple</title><entry>
        <title>$AAPL outlook</title><id>{link}</id><link href="{link}"/>
        <published>{publication}</published><content type="text">{body}</content></entry></feed>'''
    else:
        xml = f'''<rss version="2.0"><channel><title>Apple</title><item><title>$AAPL outlook</title>
        <link>{link}</link><pubDate>{publication}</pubDate><description>{body}</description></item></channel></rss>'''
    entry = feedparser.parse(xml).entries[0]
    assert dict(entry.items())["published_parsed"]  # Parser fabricates clock/UTC for incomplete source dates.
    provider = DatedRSSProvider() if kind == "news" else DatedIRProvider()
    provider.feeds = {"AAPL": link}
    document = provider._parse_entry("AAPL", entry, datetime(2026, 10, 14).date(), datetime(2026, 10, 15).date())
    if publication.endswith("Z"):
        assert document is not None  # Explicit source midnight is legitimate.
        assert document.published_at == datetime(2026, 10, 14, tzinfo=UTC)
        assert document.metadata["timestamp_basis"] == "published_at"
    else:
        assert document is None


@pytest.mark.parametrize("feed_format", ["rss", "atom"])
@pytest.mark.parametrize("timestamp_kind", ["published", "updated", "created"])
def test_news_requires_actual_publication_in_real_parsed_feeds(tmp_path, monkeypatch, feed_format, timestamp_kind):
    import feedparser
    from backend.website_sources import DatedRSSProvider
    body = "Tim Cook said we expect revenue growth to accelerate with strong customer demand."
    url = "https://news.example.test/aapl"
    namespaces = 'xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dcterms="http://purl.org/dc/terms/"'
    if feed_format == "rss":
        tag = {"published":"pubDate", "updated":"atom:updated", "created":"dcterms:created"}[timestamp_kind]
        value = "Wed, 14 Oct 2026 12:00:00 GMT" if timestamp_kind == "published" else "2026-10-14T12:00:00Z"
        xml = f'''<rss version="2.0" {namespaces}><channel><title>News</title><item>
        <title>$AAPL outlook</title><link>{url}</link><{tag}>{value}</{tag}>
        <description>{body}</description></item></channel></rss>'''
    else:
        tag = "dcterms:created" if timestamp_kind == "created" else timestamp_kind
        xml = f'''<feed xmlns="http://www.w3.org/2005/Atom" {namespaces}><title>News</title>
        <entry><id>{url}</id><title>$AAPL outlook</title><link href="{url}"/>
        <{tag}>2026-10-14T12:00:00Z</{tag}><content type="text">{body}</content></entry></feed>'''
    supplied = dict(feedparser.parse(xml).entries[0].items())
    assert f"{timestamp_kind}_parsed" in supplied
    assert ("published_parsed" in supplied) == (timestamp_kind == "published")
    provider = DatedRSSProvider()
    provider.feeds = {"publisher": "https://news.example.test/feed"}
    monkeypatch.setattr("trading_copilot.providers.news_rss_provider.httpx.get",
        lambda request_url, **kwargs: httpx.Response(200, text=xml, request=httpx.Request("GET", request_url)))
    documents = provider.fetch_news(["AAPL"], datetime(2026, 10, 14).date(), datetime(2026, 10, 15).date())
    assert provider.errors == []
    if timestamp_kind != "published":
        assert documents == []  # Deliberate coverage limitation, not a made-up publication.
        return
    assert len(documents) == 1
    document = documents[0]
    assert document.metadata["timestamp_basis"] == "published_at"
    assert "source_updated_at" not in document.metadata
    assert "source_created_at" not in document.metadata
    store = EventStore(tmp_path / "news-publication.db")
    try:
        WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))._documents(documents, "news_rss")
        event = store.get_event_by_source_id(document.document_id)
        assert event.released_at == datetime(2026, 10, 14, 12, tzinfo=UTC)
        assert event.source_url == url
        assert event.metadata["document"]["metadata"]["timestamp_basis"] == "published_at"
    finally:
        store.close()


@pytest.mark.parametrize("timestamp_tag", ["published", "updated"])
def test_actual_atom_timestamp_presence_ignores_feedparser_aliases(tmp_path, timestamp_tag):
    import feedparser
    from backend.website_sources import DatedIRProvider
    timestamp = "2026-10-14T12:00:00Z"
    atom = f'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Apple IR</title>
    <id>https://www.apple.com/newsroom/</id><entry><id>atom-timestamp</id>
    <title>Company outlook</title><{timestamp_tag}>{timestamp}</{timestamp_tag}>
    <link href="https://www.apple.com/newsroom/atom-timestamp"/>
    <content type="text">Tim Cook said we expect revenue growth to accelerate with strong customer demand.</content>
    </entry></feed>'''
    entry = feedparser.parse(atom).entries[0]
    supplied = dict(entry.items())
    assert f"{timestamp_tag}_parsed" in supplied
    other = "updated" if timestamp_tag == "published" else "published"
    assert f"{other}_parsed" not in supplied
    document = DatedIRProvider()._parse_entry("AAPL", entry,
        datetime(2026, 10, 14).date(), datetime(2026, 10, 15).date())
    assert document is not None
    assert "source_created_at" not in document.metadata
    store = EventStore(tmp_path / "atom.db")
    try:
        WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))._documents([document], "ir_releases")
        event = store.get_event_by_source_id(document.document_id)
        if timestamp_tag == "published":
            assert "source_updated_at" not in document.metadata
            assert document.metadata["timestamp_basis"] == "published_at"
            assert event.released_at == datetime(2026, 10, 14, 12, tzinfo=UTC)
            assert event.metadata["evidence_claims"]
        else:
            assert document.metadata["source_updated_at"] == "2026-10-14T12:00:00+00:00"
            assert document.metadata["timestamp_basis"] == "source_updated_at"
            assert event.released_at is None
            assert event.metadata["document"]["published_at"] is None
            assert event.metadata["evidence_claims"] == []
    finally:
        store.close()


@pytest.fixture
def alpaca():
    provider = AlpacaMarketDataProvider(api_key="offline", api_secret="offline", cache=MemoryCache())
    yield provider
    provider.close()


def bar(timestamp):
    return dict(t=timestamp, o=100, h=102, l=99, c=101, v=1000000)


def test_pagination_exact_rfc3339_and_cache_identity(alpaca):
    start = datetime(2026, 10, 1, 14, 30, 1, 123456, tzinfo=UTC)
    end = start + timedelta(hours=4)
    requests = []

    def transport(request):
        requests.append(request)
        assert request.url.params["start"] == "2026-10-01T14:30:01.123456Z"
        assert request.url.params["end"] == "2026-10-01T18:30:01.123456Z"
        second = "page_token" in request.url.params
        return httpx.Response(200, json={"bars": {"AAPL": [bar("2026-10-01T16:00:00Z" if second else "2026-10-01T15:00:00Z")]},
                                         "next_page_token": None if second else "second"})

    alpaca._client.close()
    alpaca._client = httpx.Client(base_url=alpaca.base_url, transport=httpx.MockTransport(transport))
    assert len(alpaca.get_daily_bars(["AAPL"], start, end)["AAPL"]) == 2
    assert len(requests) == 2
    assert alpaca._cache_key(["AAPL"], start, end) != alpaca._cache_key(["AAPL"], start, end + timedelta(microseconds=1))
    assert alpaca._cache_key(["AAPL"], start, end) != alpaca._cache_key(["AAPL"], start + timedelta(seconds=1), end)
    original = alpaca.last_retrieval_metadata.copy()
    alpaca.get_daily_bars(["AAPL"], start, end)
    assert alpaca.last_retrieval_metadata == original
    assert len(requests) == 2


def test_legacy_cache_without_retrieval_provenance_is_refetched(alpaca, monkeypatch):
    start = datetime(2026, 10, 1, tzinfo=UTC)
    alpaca.cache.set(alpaca._cache_key(["AAPL"], start, start), ({"AAPL": []}, {"AAPL": "available"}))
    fetch = Mock(return_value={"AAPL": []})
    monkeypatch.setattr(alpaca, "_fetch_bars_batch", fetch)
    _, statuses = alpaca.get_daily_bars_with_status(["AAPL"], start, start)
    assert statuses == {"AAPL": "empty"}
    fetch.assert_called_once()
    assert alpaca.last_retrieval_metadata["AAPL"]["retrieved_at"]


@pytest.mark.parametrize("minimum", [None, 250])
def test_public_api_does_not_hide_provider_failure(alpaca, monkeypatch, minimum):
    monkeypatch.setattr(alpaca, "_fetch_bars_batch", Mock(side_effect=httpx.ConnectError("offline")))
    now = datetime.now(UTC)
    with pytest.raises(RuntimeError, match="request failed"):
        alpaca.get_daily_bars(["AAPL"], now-timedelta(days=400), now, minimum)


def test_scanner_partial_failure_and_original_upstream_provenance():
    class Partial:
        def get_daily_bars_with_status(self, symbols, start, end):
            data = MockMarketDataProvider().get_daily_bars(symbols, start, end)
            data["BAD"] = []
            self.last_retrieval_metadata = {s: {"retrieved_at": "2026-01-01T12:00:00+00:00",
                "source_url": "https://data.alpaca.markets/v2/stocks/bars"} for s in symbols}
            return data, {s: "provider_error" if s == "BAD" else "available" for s in symbols}

    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=Partial())
    adapter.symbols = ["AAPL", "BAD"]
    results = adapter.scan()
    assert results
    assert adapter.status()["status"] == "partial"
    assert all(r["upstream_retrieved_at"] == "2026-01-01T12:00:00+00:00" for r in results)
    assert adapter.scan() == results


def test_scanner_failed_benchmark_is_not_empty_or_available():
    class Failed:
        def get_daily_bars_with_status(self, symbols, start, end):
            return {s: [] for s in symbols}, {s: "provider_error" for s in symbols}
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=Failed())
    adapter.symbols = ["AAPL"]
    assert adapter.scan() == []
    assert adapter.status()["status"] == "provider_error"


def test_empty_and_raw_headline_do_not_invent_confidence(tmp_path):
    store = EventStore(tmp_path / "empty.db")
    try:
        engine = InterpretationEngine(store)
        before = engine.generate_interpretation(InterpretationRequest(symbol="AAPL"))
        store.upsert_event(MarketEvent(symbol="AAPL", event_type=EventType.NEWS, title="An unverified headline",
            source="publisher", source_url="https://publisher.test/story", source_id="raw"))
        after = engine.generate_interpretation(InterpretationRequest(symbol="AAPL"))
        assert after.confidence == before.confidence
        assert before.stock_impact.bias.value == "unknown"
        assert before.stock_impact.magnitude.value == "unknown"
        assert before.stock_impact.horizon.value == "unknown"
        assert "stable" not in before.what_it_means.lower()
        assert "No material catalyst" not in before.why_it_matters
        for scenario in [before.base_case, before.bull_case, before.bear_case]:
            assert scenario.probability_band is None
            assert "uncalibrated conditional" in scenario.description.lower()
        evidence = {"earnings": {"has_earnings": True, "eps_surprise": 1.2, "guidance_direction": "raised"}}
        for scenario in engine._generate_scenarios("AAPL", evidence, before.company_impact, before.stock_impact):
            assert scenario.probability_band is None
    finally:
        store.close()


def test_daily_response_retains_original_cache_retrieval_time(alpaca, monkeypatch):
    original = "2026-01-01T12:00:00+00:00"
    def fetch(symbols, start, end):
        alpaca.last_retrieval_metadata = {"AAPL": {"retrieved_at": original,
            "source_url": "https://data.alpaca.markets/v2/stocks/bars"}}
        return {"AAPL": []}, {"AAPL": "empty"}
    monkeypatch.setattr(alpaca, "get_daily_bars_with_status", fetch)
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=alpaca)
    assert adapter.bars("AAPL")["retrieved_at"] == original
    assert adapter.bars("AAPL")["retrieved_at"] == original


def test_unknown_exhibit_publication_never_promoted_to_midnight_claims(tmp_path):
    store = EventStore(tmp_path / "unknown.db")
    try:
        adapter = WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))
        document = NewsDocument(document_id="sec:unknown", symbol="AAPL", headline="Exhibit",
            body="Tim Cook said we expect revenue growth to accelerate with strong demand.", publisher="AAPL",
            published_at=datetime(2026, 10, 1, tzinfo=UTC), retrieved_at=datetime.now(UTC),
            source_url="https://www.sec.gov/Archives/exhibit", source_type=NewsSourceType.SEC_EXHIBIT,
            provider_id="sec_edgar_exhibit", content_hash="raw-hash")
        adapter._documents([document], "sec_exhibits")
        event = store.get_event_by_source_id("sec:unknown")
        assert event.released_at is None
        assert event.metadata["event_date"] == "2026-10-01"
        assert event.metadata["document"]["published_at"] is None
        assert event.metadata["management_statements"] == []
        assert event.metadata["evidence_claims"] == []
        adapter._run("ir_releases", lambda: {"NEW": 0, "UNAVAILABLE": 1})
        assert adapter.state["ir_releases"]["status"] == "unavailable"
    finally:
        store.close()


@pytest.mark.parametrize("body", [
    'Alice Smith said demand remains robust and revenue is growing. "We expect massive losses next quarter due to collapsing demand," Bob Jones said.',
    'Alice Smith said demand remains robust; "We expect massive losses next quarter due to collapsing demand," Bob Jones said.',
    'Alice Smith said "We expect massive losses next quarter due to collapsing demand," Bob Jones said.',
])
def test_two_speaker_quote_cannot_become_verified_alice_claim(tmp_path, body):
    from backend.website_sources import EvidenceValidator
    from trading_copilot.models.news import EvidenceSpan
    now = datetime.now(UTC)
    document = NewsDocument(document_id="ir:two-speakers", symbol="AAPL", headline="Outlook",
        body=body, publisher="AAPL", published_at=now, retrieved_at=now,
        source_url="https://www.apple.com/newsroom/outlook", source_type=NewsSourceType.COMPANY_IR,
        provider_id="company_ir_rss", content_hash="two-speakers")
    statements = ManagementExtractor().extract_statements(document)
    assert not any(s.speaker == "Alice Smith" and "massive losses" in s.statement for s in statements)
    assert all(s.speaker == "Bob Jones" for s in statements if "massive losses" in s.statement)
    # Recreate the OLD broad Alice span, which contained Bob's quote but not
    # Bob's attribution, and prove validator independently refuses that payload.
    template = statements[0] if statements else None
    if template is None:
        from trading_copilot.models.news import ManagementStatement, StatementType
        template = ManagementStatement(statement_id="stmt:old", symbol="AAPL", speaker="Alice Smith",
            statement=body, statement_type=StatementType.GUIDANCE, source_document_id=document.document_id,
            source_url=document.source_url, published_at=now, retrieved_at=now,
            source_type=document.source_type, provider_id=document.provider_id)
    bad_end = body.index("Bob Jones")
    broad = body[:bad_end].rstrip()
    bad = template.model_copy(update={"statement_id": "stmt:old", "speaker": "Alice Smith",
        "statement": broad, "evidence_span": EvidenceSpan(start=0, end=len(broad), text=broad)})
    assert not EvidenceValidator.supports(bad, document)
    store = EventStore(tmp_path / "speakers.db")
    try:
        WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))._documents([document], "ir_releases")
        event = store.get_event_by_source_id(document.document_id)
        for payload in event.metadata["evidence_claims"]:
            if "massive losses" in payload["claim"]:
                assert payload["speaker"] == "Bob Jones"
    finally:
        store.close()


@pytest.mark.parametrize("basis", ["updated", "created", "published"])
def test_ir_timestamp_concepts_never_promote_update_or_creation(tmp_path, basis):
    from backend.website_sources import DatedIRProvider
    now = datetime.now(UTC).replace(microsecond=0)
    updated = now - timedelta(hours=1)
    created = now - timedelta(hours=2)
    published = now - timedelta(hours=3)
    entry = {"id": "timestamp-entry", "link": "https://www.apple.com/newsroom/timestamps",
        "title": "Company outlook", "summary": "Tim Cook said we expect revenue growth to accelerate with strong customer demand."}
    # Always retain creation; updated and original publication are distinct.
    entry["created_parsed"] = created.timetuple()
    entry["created"] = created.isoformat()
    if basis in {"updated", "published"}:
        entry["updated_parsed"] = updated.timetuple()
        entry["updated"] = updated.isoformat()
    if basis == "published":
        entry["published_parsed"] = published.timetuple()
        entry["published"] = published.isoformat()
    document = DatedIRProvider()._parse_entry("AAPL", entry, (now-timedelta(days=1)).date(), now.date())
    assert document.metadata["source_created_at"] == created.isoformat()
    if basis != "created":
        assert document.metadata["source_updated_at"] == updated.isoformat()
    expected_basis = "published_at" if basis == "published" else f"source_{basis}_at"
    assert document.metadata["timestamp_basis"] == expected_basis
    store = EventStore(tmp_path / "timestamps.db")
    try:
        WebsiteSourceAdapter(store, SimpleNamespace(sec_user_agent=None))._documents([document], "ir_releases")
        event = store.get_event_by_source_id(document.document_id)
        if basis == "published":
            assert event.released_at == published
            assert event.metadata["management_statements"]
            assert event.metadata["evidence_claims"]
        else:
            assert event.released_at is None
            assert event.status.value == "unknown"
            assert event.metadata["document"]["published_at"] is None
            assert event.metadata["timestamp_basis"] == expected_basis
            assert event.metadata["management_statements"] == []
            assert event.metadata["evidence_claims"] == []
    finally:
        store.close()


def test_real_refresh_endpoint_reaches_ir_exhibits_management_claims(tmp_path, monkeypatch):
    import backend.main as api
    import backend.website_sources as sources
    now = datetime.now(UTC)
    accession = "0000320193-26-000001"
    body = 'Tim Cook said we expect revenue growth to accelerate with strong customer demand.'
    revised = [False]

    def sec_get(url):
        if "submissions/" in url:
            payload = {"filings": {"recent": {"accessionNumber": [accession], "filingDate": [now.date().isoformat()],
                "form": ["8-K"], "primaryDocument": ["report.htm"], "items": ["2.02"],
                "acceptanceDateTime": [(now-timedelta(hours=2)).isoformat()]}, "files": []}}
            return httpx.Response(200, json=payload, request=httpx.Request("GET", url))
        if url.endswith("index.json"):
            return httpx.Response(200, json={"directory": {"item": [{"name": "ex991.htm", "type": "EX-99.1"}]}}, request=httpx.Request("GET", url))
        return httpx.Response(200, text=body + (" We anticipate continued growth." if revised[0] else ""),
                              headers={"Content-Type": "text/html"}, request=httpx.Request("GET", url))

    class InjectedExhibits(WebsiteSECExhibitProvider):
        def __init__(self, **kwargs):
            super().__init__(cache_dir=tmp_path / "exhibits", transport=SimpleNamespace(get=sec_get, close=lambda: None),
                cik_map=SimpleNamespace(get_cik=lambda symbol: "0000320193"), **kwargs)

    class EmptySEC:
        def __init__(self, *args, **kwargs): pass
        def refresh(self, *args, **kwargs): return {"NEW": 0}
        def close(self): pass

    def ir_get(url, **kwargs):
        rss = f'''<rss version="2.0"><channel><title>Apple</title><item><title>Company outlook</title>
        <link>https://www.apple.com/newsroom/verified-release</link><guid>ir-one</guid>
        <pubDate>{(now-timedelta(hours=3)).strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
        <description>{body}</description></item></channel></rss>'''
        return httpx.Response(200, text=rss, request=httpx.Request("GET", url))

    monkeypatch.setenv("TRADING_COPILOT_DB_PATH", str(tmp_path / "endpoint.db"))
    monkeypatch.delenv("WEBSITE_REFRESH_PROVIDERS", raising=False)
    monkeypatch.setattr(sources, "SECFilingProvider", EmptySEC)
    monkeypatch.setattr(sources, "EarningsIntelligenceProvider", EmptySEC)
    monkeypatch.setattr(sources, "WebsiteSECExhibitProvider", InjectedExhibits)
    monkeypatch.setattr(sources.WebsiteSourceAdapter, "_macro", lambda self: {"NEW": 0})
    monkeypatch.setattr(sources.WebsiteSourceAdapter, "_news", lambda self, symbols: {"NEW": 0})
    monkeypatch.setattr("trading_copilot.providers.ir_release_provider.httpx.get", ir_get)
    with TestClient(api.app) as client:
        api.source_adapter.settings = SimpleNamespace(sec_user_agent="Offline Test test@example.test")
        response = client.post("/api/v1/market/refresh", json={"symbols": ["AAPL"]})
        assert response.status_code == 200
        assert api.source_adapter.state["sec_exhibits"]["status"] == "available"
        assert api.source_adapter.state["ir_releases"]["status"] == "available"
        events = api.event_store.events_as_of(datetime.now(UTC))
        assert len(events) == 2
        for event in events:
            assert event.metadata["management_statements"]
            assert event.metadata["evidence_claims"]
            claim = event.metadata["evidence_claims"][0]
            span = claim["evidence_span"]
            assert event.description[span["start"]:span["end"]] == span["text"]
            assert claim["speaker"] == "Tim Cook"
            assert claim["verification_status"] == "verified"
            assert claim["retrieved_at"]
        exhibit = next(e for e in events if e.metadata["source_type"] == "sec_exhibits")
        assert exhibit.released_at is None
        assert exhibit.metadata["document"]["published_at"] is None
        assert exhibit.metadata["filing_accepted_at"]
        assert api.interpretation_engine._analyze_news_claims("AAPL", events)
        interpretation = api.interpretation_engine.generate_interpretation(InterpretationRequest(symbol="AAPL"))
        assert "Tim Cook stated" in interpretation.what_happened
        assert interpretation.base_case.probability_band is None
        revised[0] = True
        assert client.post("/api/v1/market/refresh", json={"symbols": ["AAPL"]}).status_code == 200
        changed = api.event_store.get_event(exhibit.event_id)
        assert changed.description != exhibit.description
        assert api.event_store.get_revisions(exhibit.event_id)
