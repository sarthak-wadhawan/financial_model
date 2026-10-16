"""Synthetic public-filing shapes only; HTTP is always MockTransport."""
from datetime import date
from pathlib import Path

import httpx
import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.sec_cik_map import SEC_TICKERS_URL
from trading_copilot.providers.sec_http import SECTransport

CIK = "0000123456"
SUBMISSIONS = f"https://data.sec.gov/submissions/CIK{CIK}.json"
QUOTAS = {"ownership": 2, "reports": 1, "companyevents": 1}


def row(number, form, day):
    return {"accessionNumber": f"0000123456-26-{number:06}", "form": form,
            "filingDate": day, "primaryDocument": "filing.xml" if form.startswith("4") else "filing.htm"}


def columns(rows):
    return {key: [r[key] for r in rows] for key in row(1, "8-K", "2026-01-01")}


@pytest.fixture
def sec(tmp_path, monkeypatch):
    import trading_copilot.providers.sec_http as module
    monkeypatch.setattr(module, "_LAST_REQUEST", 0)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    rows = [row(i, "4", f"2026-01-{30-i:02}") for i in range(1, 7)]
    rows += [row(7, "8-K", "2026-01-10"), row(8, "10-Q", "2026-01-09")]
    responses = {
        SEC_TICKERS_URL: {"0": {"cik_str": 123456, "ticker": "SYN", "title": "Synthetic"}},
        SUBMISSIONS: {"filings": {"recent": columns(rows), "files": []}},
    }
    urls = {}
    for r in rows:
        url = ("https://www.sec.gov/Archives/edgar/data/123456/"
               + r["accessionNumber"].replace("-", "") + "/" + r["primaryDocument"])
        urls[r["accessionNumber"]] = url
        responses[url] = ((Path(__file__).parents[1] / "fixtures/sec/synthetic_form4.xml").read_bytes()
                          if r["form"] == "4" else b"<p>Synthetic filing evidence.</p>")
    calls = []

    def handler(request):
        url = str(request.url)
        calls.append(url)
        value = responses[url]
        if isinstance(value, int):
            return httpx.Response(value)
        return httpx.Response(200, content=value) if isinstance(value, bytes) else httpx.Response(200, json=value)

    transport = SECTransport("Synthetic offline sec@synthetic.invalid",
                             httpx.Client(transport=httpx.MockTransport(handler)))
    store = EventStore(tmp_path / "events.db")
    provider = SECFilingProvider(store, tmp_path / "sec", transport=transport)
    yield provider, responses, calls, rows, urls
    store.close()
    provider.close()


def fetch(provider, **kwargs):
    return provider.get_filings(["syn"], max_per_symbol=4, from_date=date(2026, 1, 1),
                               to_date=date(2026, 1, 31), **kwargs)["SYN"]


def test_reservations_prevent_crowding_without_extra_requests(sec):
    provider, _, calls, _, _ = sec
    assert provider.coverage == {}  # Never checked is not checked-empty.
    default = fetch(provider)
    assert [d.metadata["form"] for d in default] == ["4"] * 4
    calls.clear()
    selected = fetch(provider, category_quotas=QUOTAS)
    assert [d.metadata["form"] for d in selected] == ["4", "4", "8-K", "10-Q"]
    assert len([url for url in calls if "/Archives/" in url]) == 4
    assert len(calls) == 5  # Cached mapping, one submissions call, four documents.
    coverage = provider.coverage["SYN"]
    assert (coverage["discovered_eligible"], coverage["selected"], coverage["successful_documents"]) == (8, 4, 4)
    assert coverage["status"] == "partial"
    assert coverage["categories"]["reports"]["status"] == "available"


@pytest.mark.parametrize("quotas", [{"unknown": 1}, {"reports": -1}, {"reports": True},
                                   {"reports": 1.5}, {"reports": 5}, [], "reports"])
def test_invalid_quota_rejected_before_transport(sec, quotas):
    provider, _, calls, _, _ = sec
    with pytest.raises(ValueError, match="category quotas"):
        fetch(provider, category_quotas=quotas)
    assert calls == [] and provider.coverage == {}


def test_empty_reservations_and_unused_slots_preserve_default(sec):
    provider, _, _, _, _ = sec
    default = [d.source_id for d in fetch(provider)]
    assert [d.source_id for d in fetch(provider, category_quotas={})] == default
    assert len(fetch(provider, category_quotas={"reports": 4})) == 4


def test_amendments_boundary_and_idempotent_revision(sec):
    provider, responses, _, rows, urls = sec
    rows[0]["form"] = "4/A"
    rows[6]["form"] = "8-K/A"
    rows[7]["form"] = "10-K/A"
    rows[7]["filingDate"] = "2026-01-01"  # Inclusive boundary.
    responses[SUBMISSIONS]["filings"]["recent"] = columns(rows + [row(9, "10-K", "2025-12-31")])
    kwargs = dict(max_per_symbol=4, from_date=date(2026, 1, 1), to_date=date(2026, 1, 31),
                  category_quotas=QUOTAS)
    first = provider.refresh(["SYN"], **kwargs)
    assert first["NEW"] == 6 and first["ERROR"] == 0
    assert provider.refresh(["SYN"], **kwargs)["UNCHANGED"] == 6
    for r in (rows[0], rows[6], rows[7]):
        event = provider.event_store.get_event_by_source_id(r["accessionNumber"], EventType.SEC_FILING)
        assert event.metadata["is_amendment"] and event.metadata["amends_accession"] is None
    responses[urls[rows[7]["accessionNumber"]]] = b"<p>Revised synthetic report.</p>"
    assert provider.refresh(["SYN"], **kwargs)["CHANGED"] == 1
    event = provider.event_store.get_event_by_source_id(rows[7]["accessionNumber"], EventType.SEC_FILING)
    assert len(provider.event_store.get_revisions(event.event_id)) == 1
    assert provider.get_current_leadership("SYN")["CEO"] is None


def test_document_failures_are_category_local_and_symbols_isolated(sec):
    provider, responses, _, rows, urls = sec
    responses[urls[rows[0]["accessionNumber"]]] = b"<html>Access denied</html>"
    docs = provider.get_filings(["missing", "syn"], max_per_symbol=4,
                                from_date=date(2026, 1, 1), to_date=date(2026, 1, 31),
                                category_quotas=QUOTAS)
    assert len(docs["SYN"]) == 3 and docs["MISSING"] == []
    coverage = provider.coverage["SYN"]
    assert coverage["categories"]["ownership"]["status"] == "partial"
    assert coverage["categories"]["reports"]["status"] == "available"
    assert coverage["categories"]["companyevents"]["status"] == "available"
    assert coverage["error_stage_counts"] == {"document": 1}
    assert provider.coverage["MISSING"]["status"] == "provider_error"
    assert not provider.coverage["MISSING"]["source_checked"]


def test_checked_empty_vs_failed_submissions(sec):
    provider, responses, _, _, _ = sec
    responses[SUBMISSIONS] = 403
    assert fetch(provider) == []
    assert provider.coverage["SYN"]["status"] == "provider_error"
    assert provider.coverage["SYN"]["checked_at"] is None
    responses[SUBMISSIONS] = {"filings": {"recent": columns([]), "files": []}}
    assert fetch(provider) == []
    coverage = provider.coverage["SYN"]
    assert coverage["status"] == "empty" and coverage["source_checked"]
    assert coverage["checked_at"] and coverage["from_date"] == "2026-01-01"
    assert all(c["status"] == "empty" for c in coverage["categories"].values())


def test_failed_shard_never_claims_empty_categories(sec):
    provider, responses, calls, _, _ = sec
    shard = f"CIK{CIK}-submissions-001.json"
    responses[SUBMISSIONS]["filings"] = {"recent": columns([]), "files": [
        {"name": shard, "filingFrom": "2026-01-01", "filingTo": "2026-01-31"},
        {"name": f"CIK{CIK}-submissions-002.json", "filingTo": "2025-12-31"}]}
    responses["https://data.sec.gov/submissions/" + shard] = 403
    assert fetch(provider, category_quotas=QUOTAS) == []
    coverage = provider.coverage["SYN"]
    assert coverage["status"] == "provider_error"
    assert coverage["error_stage_counts"] == {"historical_shard": 1}
    assert all(c["status"] == "provider_error" for c in coverage["categories"].values())
    assert not any("002.json" in url for url in calls)


def test_missing_auth_is_not_a_source_check(sec, monkeypatch):
    provider, _, calls, _, _ = sec
    provider.transport.user_agent = None
    monkeypatch.setattr("trading_copilot.providers.sec_http.load_settings",
                        lambda: type("Settings", (), {"sec_user_agent": None})())
    assert fetch(provider) == []
    assert calls == []
    assert provider.coverage["SYN"]["status"] == "provider_error"
    assert not provider.coverage["SYN"]["source_checked"]


def test_unselected_category_is_partial_not_empty(sec):
    provider, _, _, _, _ = sec
    fetch(provider)
    for name in ("reports", "companyevents"):
        entry = provider.coverage["SYN"]["categories"][name]
        assert entry["discovered_eligible"] == 1
        assert entry["selected"] == entry["successful_documents"] == 0
        assert entry["status"] == "partial"
