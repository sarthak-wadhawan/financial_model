"""Website regressions, always isolated from the operator's persistent database."""
from datetime import datetime, timedelta, timezone
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from trading_copilot.config import Config, Settings
from trading_copilot.models.events import MarketEvent, EventType
from trading_copilot.models.market import DailyBar
from backend.website_data import WebsiteDataAdapter


class EmptyProvider:
    def get_daily_bars(self, symbols, start, end):
        return {s: [] for s in symbols}


class FailingProvider:
    def get_daily_bars(self, symbols, start, end):
        raise RuntimeError("SECRET must not escape")


@pytest.fixture
def client(tmp_path, monkeypatch):
    import backend.main as api
    monkeypatch.setenv("TRADING_COPILOT_DB_PATH", str(tmp_path / "events.db"))
    monkeypatch.delenv("WEBSITE_REFRESH_PROVIDERS", raising=False)
    with TestClient(api.app) as client:
        monkeypatch.setattr(api, "market_adapter", WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=EmptyProvider()))
        yield client


def test_detail_empty_db_does_not_500(client):
    result = client.get("/api/v1/stocks/AAPL")
    assert result.status_code == 200
    body = result.json()
    assert body["price"] is None
    assert body["events"] == []
    assert body["interpretation"]["missing_information"]
    assert body["price_data"]["status"] == "empty"


def test_search_independent_of_scanner(client):
    results = client.get("/api/v1/symbols/search?q=AAPL").json()
    assert results[0]["symbol"] == "AAPL"
    assert results[0]["name"] is None or isinstance(results[0]["name"], str)
    assert results[0]["type"] == "equity"


def test_terms_search_not_shadowed(client):
    result = client.get("/api/v1/terms/search?q=earn")
    assert result.status_code == 200
    assert isinstance(result.json(), list)
    assert client.get("/api/v1/terms/EPS").json()["short_definition"]


def test_answer_path_symbol_body(client):
    result = client.post("/api/v1/stocks/AAPL/answer", json={"question": "What happened?"})
    assert result.status_code == 200
    assert isinstance(result.json()["evidence_refs"], list)
    assert "generated_at" in result.json()


def test_no_duplicate_routes(client):
    counts = Counter((r.path, tuple(sorted(r.methods or []))) for r in client.app.routes)
    assert all(n == 1 for n in counts.values())


def test_event_filter_and_provenance(client):
    import backend.main as api
    for et in [EventType.NEWS, EventType.EARNINGS]:
        api.event_store.upsert_event(MarketEvent(event_type=et, symbol="AAPL", title=et.value, source="isolated_fixture", source_id=et.value, source_url="https://example.org/evidence", scheduled_at=datetime.now(timezone.utc)))
    result = client.get("/api/v1/stocks/AAPL/events?event_types=news").json()
    assert len(result) == 1
    assert result[0]["event_type"] == "news"
    assert result[0]["source_id"] == "news"
    assert "first_seen_at" in result[0]
    assert client.get("/api/v1/stocks/AAPL/events?event_types=invalid").status_code == 400


def test_scheduled_macro_date_filter(client):
    import backend.main as api
    tomorrow = datetime.now(timezone.utc)+timedelta(days=1)
    api.event_store.upsert_event(MarketEvent(event_type=EventType.MACRO, title="scheduled", source="isolated_fixture", scheduled_at=tomorrow))
    result = client.get(f"/api/v1/events/macro?from_date={tomorrow.date()}&to_date={tomorrow.date()}")
    assert result.status_code == 200
    assert len(result.json()) == 1
    assert result.json()[0]["released_at"] is None


def test_invalid_daily_chart_requests(client):
    assert client.get("/api/v1/market/bars/AAPL?timeframe=1Hour").status_code == 400
    assert client.get("/api/v1/market/bars/AAPL?start=2026-10-10&end=2026-10-01").status_code == 400
    assert client.get("/api/v1/market/bars/INVALID%24").status_code == 400


def test_missing_credentials_never_mock(monkeypatch):
    for key in ["APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "ALPACA_API_KEY", "ALPACA_API_SECRET"]:
        monkeypatch.delenv(key, raising=False)
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None))
    assert adapter.provider is None
    assert adapter.bars("AAPL")["status"] == "unavailable"
    assert adapter.overview()["mode"] == "real"
    assert adapter.scan() == []


def test_provider_failure_safe():
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=FailingProvider())
    result = adapter.bars("AAPL")
    assert result["status"] == "provider_error"
    assert "SECRET" not in str(result)
    assert adapter.scan() == []
    assert adapter.status()["status"] == "provider_error"


def test_completed_daily_bars_no_future_and_zero_volume():
    now = datetime.now(timezone.utc)
    class Provider:
        def get_daily_bars(self, symbols, start, end):
            return {"AAPL": [DailyBar(symbol="AAPL", timestamp=now+timedelta(days=i), open=10, high=10, low=10, close=10, volume=0) for i in [-2,-1,0,1]]}
    result = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=Provider()).bars("AAPL")
    assert len(result["bars"]) == 2
    assert result["bars"][-1]["v"] == 0
    assert result["market_timestamp"] != result["retrieved_at"]


def test_zero_llm_default():
    assert Config().llm.enabled is False


def test_explicit_demo_scanner_reuses_scorer():
    from trading_copilot.providers.mock import MockMarketDataProvider
    from trading_copilot.pipeline.features import FeatureEngine
    from trading_copilot.pipeline.eligibility import EligibilityFilter
    from trading_copilot.pipeline.quant_score import QuantScorer
    class RecordingProvider(MockMarketDataProvider):
        def get_daily_bars(self, symbols, start, end):
            self.market = super().get_daily_bars(symbols, start, end)
            return self.market
        def get_benchmark_bars(self, symbol, start, end):
            self.benchmark = super().get_benchmark_bars(symbol, start, end)
            return self.benchmark
    config = Config()
    provider = RecordingProvider()
    adapter = WebsiteDataAdapter(config, Settings(_env_file=None), provider=provider, mode="demo")
    candidates = adapter.scan(100)
    now = datetime.now(timezone.utc)
    data = {s:[b for b in bars if b.timestamp.date()<now.date()] for s,bars in provider.market.items()}
    benchmark = [b for b in provider.benchmark if b.timestamp.date()<now.date()]
    features = EligibilityFilter(config.eligibility).apply(FeatureEngine().compute(data, benchmark))
    expected = QuantScorer(config.scoring.quant).score(features)
    assert candidates
    assert [(s["symbol"],s["quant_score"]) for s in candidates] == [(s.symbol,s.quant_score) for s in expected]
    assert all(s["mode"] == "demo" for s in candidates)


def test_rss_unknown_publication_not_retrieval_time():
    from backend.website_sources import DatedRSSProvider
    from datetime import date
    assert DatedRSSProvider()._parse_entry("source", {"title":"undated"}, date(2020,1,1), date.today()) is None


def test_reorder_object_contract(client):
    created = client.post("/api/v1/watchlists", json={"name":"isolated"}).json()
    wid = created["id"]
    for symbol in ["AAPL", "MSFT"]:
        assert client.post(f"/api/v1/watchlists/{wid}/items", json={"symbol":symbol}).status_code == 201
    assert client.post(f"/api/v1/watchlists/{wid}/reorder", json={"symbols":["MSFT","AAPL"]}).status_code == 200
    assert client.get(f"/api/v1/watchlists/{wid}/symbols").json() == ["MSFT", "AAPL"]
