"""UX2a identity contract. All HTTP is injected/offline; no operator DB changes."""
from datetime import datetime, timezone
from threading import Event
import json
import time

import pytest

from backend.website_data import OfficialIdentitySnapshot, WebsiteDataAdapter
from trading_copilot.config import Config, Settings
from trading_copilot.providers.sec_cik_map import (
    SECCIKMap, DEFAULT_CACHE_DIR, SEC_EXCHANGE_TICKERS_URL, SEC_TICKERS_URL,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network is not permitted in identity unit tests")
    monkeypatch.setattr("trading_copilot.providers.sec_http.SECTransport.get", denied)


@pytest.fixture
def exchange_map():
    # Official exchange-file shape; fixture evidence, not production profiles.
    return {"fields": ["cik", "name", "ticker", "exchange"], "data": [
        [320193, "Apple Inc.", "AAPL", "Nasdaq"],
        [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
        [97745, "THERMO FISHER SCIENTIFIC INC.", "TMO", "NYSE"],
        [1403161, "VISA INC.", "V", "NYSE"],
        [59478, "ELI LILLY & Co", "LLY", "NYSE"],
    ]}


class Transport:
    def __init__(self, raw):
        self.raw, self.calls = raw, []

    def get(self, url):
        self.calls.append(url)
        if isinstance(self.raw, Exception):
            raise self.raw
        return self

    def json(self):
        return self.raw


class EmptyPrices:
    def get_daily_bars(self, symbols, start, end):
        return {s: [] for s in symbols}


def test_cold_missing_cache_resolves_all_five_once(tmp_path, exchange_map):
    transport = Transport(exchange_map)
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=transport)
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=EmptyPrices(),
        identity_service=service)
    for row in exchange_map["data"]:
        identity = adapter.identity(row[2])
        assert (identity["name"], identity["exchange"]) == (row[1], row[3])
        assert identity["status"] == "available"
        assert identity["cik"] == str(row[0]).zfill(10)
        assert identity["verified_as_of"] == identity["retrieved_at"]
        assert identity["source_url"] == SEC_EXCHANGE_TICKERS_URL
        assert identity["sector"] is identity["description"] is identity["industry"] is None
        assert identity["fields"]["name"]["source_effective_at"] is None
    assert transport.calls == [SEC_EXCHANGE_TICKERS_URL]
    assert adapter.search("thermo")[0]["symbol"] == "TMO"
    assert adapter.price("AAPL")["status"] == "empty"
    assert adapter.identity("NOTVERIFIED")["verified_as_of"] is None


def test_legacy_official_schema_still_supports_provider_consumers(tmp_path):
    raw = {"0": {"cik_str": 320193, "ticker": "aapl", "title": "Apple Inc."}}
    transport = Transport(raw)
    mapping = SECCIKMap(tmp_path, transport=transport)
    assert mapping.get_cik("AAPL") == "0000320193"
    assert mapping.get_title("aapl") == "Apple Inc."
    assert mapping.get_symbol(320193) == "AAPL"
    assert mapping.resolve_symbols(["aapl", "missing"]) == {"AAPL": "0000320193"}
    assert transport.calls == [SEC_TICKERS_URL]
    assert mapping._mapping["AAPL"]["exchange"] is None


def test_legacy_normalized_cache_is_not_current_exchange_verification(tmp_path):
    observed = time.time() - 172800
    (tmp_path / "company_tickers.json").write_text(json.dumps({
        "mapping": {"AAPL": {"cik": "0000320193", "title": "Old observed name"}},
        "fetched_at": observed,
    }))
    service = OfficialIdentitySnapshot(cache_dir=tmp_path)
    identity = service.identity("AAPL")
    assert identity["status"] == "stale"
    assert identity["exchange"] is None
    assert datetime.fromisoformat(identity["retrieved_at"]).timestamp() == observed
    assert identity["snapshot_id"] is None


def test_cache_path_anchored_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert DEFAULT_CACHE_DIR.is_absolute()
    assert DEFAULT_CACHE_DIR.name == "sec_cik"
    assert tmp_path not in DEFAULT_CACHE_DIR.parents


@pytest.mark.parametrize("content", ["not json", "[]", '{"mapping": {"AAPL": {"cik": "bad"}}}'])
def test_corrupt_cache_isolated_and_preserved_on_repair(tmp_path, exchange_map, content):
    cache = tmp_path / "company_tickers.json"
    cache.write_text(content)
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=Transport(exchange_map))
    assert service.identity("MSFT")["status"] == "available"
    assert any(p.read_text() == content for p in (tmp_path / "snapshots").glob("*.json"))


def test_error_is_sanitized_cooled_down_and_does_not_verify_price_symbols(tmp_path):
    transport = Transport(RuntimeError("PRIVATE_REQUEST_ID_AND_CREDENTIAL"))
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=transport)
    adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=EmptyPrices(), identity_service=service)
    for symbol in ("AAPL", "MSFT", "TMO", "V", "LLY"):
        identity = adapter.identity(symbol)
        assert identity["status"] == "provider_error"
        assert identity["verified_as_of"] is identity["name"] is None
        assert "PRIVATE" not in str(identity)
    assert len(transport.calls) == 1
    assert adapter.search("AAPL")[0]["symbol"] == "AAPL"
    assert adapter.price("AAPL")["status"] == "empty"


def test_external_refresh_visible_after_missing_startup_cache(tmp_path, exchange_map):
    service = OfficialIdentitySnapshot(cache_dir=tmp_path)
    assert service.identity("AAPL")["status"] == "not_refreshed"
    writer = SECCIKMap(tmp_path, transport=Transport(exchange_map), source_url=SEC_EXCHANGE_TICKERS_URL)
    writer.refresh()
    first = service.identity("AAPL")
    assert first["name"] == "Apple Inc."
    exchange_map["data"][0][1] = "Revised official fixture name"
    writer.refresh()
    second = service.identity("AAPL")
    assert second["name"] == "Revised official fixture name"
    assert second["snapshot_id"] != first["snapshot_id"]
    assert second["retrieved_at"] != first["retrieved_at"]
    old = json.loads((tmp_path / "snapshots" / (first["snapshot_id"] + ".json")).read_text())
    assert old["raw"]["data"][0][1] == "Apple Inc."


def test_slow_map_job_has_bounded_wait_and_is_shared(tmp_path, exchange_map):
    entered, release = Event(), Event()

    class Slow(Transport):
        def get(self, url):
            entered.set()
            release.wait(5)
            return super().get(url)

    transport = Slow(exchange_map)
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=transport)
    service.WAIT_SECONDS = 0.01
    try:
        started = time.monotonic()
        result = service.identity("AAPL")
        assert time.monotonic() - started < 0.5
        assert entered.is_set() and result["refresh_pending"]
        assert result["verified_as_of"] is None
        assert service.identity("MSFT")["refresh_pending"]
    finally:
        release.set()
        assert service._done.wait(3)
    assert service.identity("V")["status"] == "available"
    assert len(transport.calls) == 1


def test_stale_snapshot_survives_refresh_error(tmp_path, exchange_map, monkeypatch):
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=Transport(exchange_map))
    service.refresh()
    original = service.identity("AAPL")
    service.cik_map.max_age_seconds = -1
    service._next_attempt = 0
    service.cik_map.transport.raw = RuntimeError("private failure")
    service.read()
    assert service._done.wait(3)
    stale = service.identity("AAPL")
    assert stale["status"] == "stale"
    assert stale["refresh_status"] == "provider_error"
    assert stale["verified_as_of"] == original["verified_as_of"]
    assert stale["snapshot_id"] == original["snapshot_id"]


def test_integrity_failure_not_exposed_as_verified(tmp_path, exchange_map):
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=Transport(exchange_map))
    service.refresh()
    path = tmp_path / "company_tickers.json"
    data = json.loads(path.read_text())
    data["mapping"]["AAPL"]["title"] = "Unsourced edit"
    path.write_text(json.dumps(data))
    other = OfficialIdentitySnapshot(cache_dir=tmp_path)
    identity = other.identity("AAPL")
    assert identity["status"] == "provider_error"
    assert identity["name"] is None


def test_sic_from_observed_submissions_is_not_sector_or_profile(tmp_path, exchange_map):
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=Transport(exchange_map))
    service.refresh()
    raw = {"cik": "0000320193", "name": "Apple Inc.",
        "tickers": ["UNRELATED", "AAPL"], "exchanges": ["NYSE", "Nasdaq"],
        "sic": "3571", "sicDescription": "Electronic Computers", "description": ""}
    observed = "2026-10-01T12:30:00+00:00"
    service.record_submissions(raw, observed)
    identity = service.identity("AAPL")
    assert identity["industry"] == {"scheme": "SEC_SIC", "code": "3571", "label": "Electronic Computers"}
    assert identity["fields"]["industry"]["retrieved_at"] == observed
    assert identity["retrieved_at"] != observed
    assert identity["sector"] is identity["description"] is None
    assert "CEO" not in str(identity)
    assert identity["exchange"] == "Nasdaq"
    assert service.identity("MSFT")["industry"] is None
    raw["tickers"] = ["UNRELATED"]
    service.record_submissions(raw, observed)
    assert service.identity("AAPL")["industry"] is None


def test_missing_exchange_is_unknown_not_guessed(tmp_path, exchange_map):
    exchange_map["data"][0][3] = None
    service = OfficialIdentitySnapshot(cache_dir=tmp_path, transport=Transport(exchange_map))
    identity = service.identity("AAPL")
    assert identity["exchange"] is None
    assert identity["status"] == "partial"
    assert "exchange" not in identity["fields"]


def test_additive_stock_detail_contract(tmp_path, monkeypatch, exchange_map):
    from fastapi.testclient import TestClient
    import backend.main as api
    monkeypatch.setenv("TRADING_COPILOT_DB_PATH", str(tmp_path / "isolated.db"))
    monkeypatch.delenv("WEBSITE_REFRESH_PROVIDERS", raising=False)
    with TestClient(api.app) as client:
        service = OfficialIdentitySnapshot(cache_dir=tmp_path / "identity", transport=Transport(exchange_map))
        adapter = WebsiteDataAdapter(Config(), Settings(_env_file=None), provider=EmptyPrices(), identity_service=service)
        monkeypatch.setattr(api, "market_adapter", adapter)
        response = client.get("/api/v1/stocks/LLY")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == data["identity"]["name"] == "ELI LILLY & Co"
        assert data["exchange"] == data["identity"]["exchange"] == "NYSE"
        assert data["price"] is None
        assert isinstance(data["events"], list)
        assert data["price_data"]["status"] == "empty"
