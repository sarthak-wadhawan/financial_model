"""All SEC response fixtures here are SYNTHETIC; no live issuer facts."""
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.sec_cik_map import SEC_TICKERS_URL
from trading_copilot.providers.sec_http import SECTransport, safe_sec_url
from trading_copilot.providers.sec_parsers import leadership, parse_form4

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sec"
CIK = "0000123456"
SUBMISSIONS = f"https://data.sec.gov/submissions/CIK{CIK}.json"
HISTORY = f"https://data.sec.gov/submissions/CIK{CIK}-submissions-001.json"
ACCESSION = "0000123456-26-000001"
BASE = "https://www.sec.gov/Archives/edgar/data/123456/"


def row(accession=ACCESSION, form="8-K", day="2026-01-10", primary="report.htm", items="5.02,9.01"):
    return dict(accessionNumber=accession, filingDate=day, form=form, primaryDocument=primary,
                items=items, reportDate=day, acceptanceDateTime=day + "T16:00:00Z")


def columns(rows):
    return {key: [r[key] for r in rows] for key in row()}


class SyntheticTransport:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url):
        safe_sec_url(url)
        self.calls.append(url)
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return httpx.Response(200, request=httpx.Request("GET", url),
                              content=value if isinstance(value, bytes) else json.dumps(value).encode())

    def close(self):
        pass


@pytest.fixture
def setup(tmp_path):
    recent = [row(), row("0000123456-26-000002", "4", "2026-01-22", "xslF345X06/form4.xml", "")]
    older = row("0000123456-25-000003", "10-K", "2025-12-01", "annual.htm", "")
    responses = {
        SEC_TICKERS_URL: {"0": {"cik_str": 123456, "ticker": "SYN", "title": "Synthetic issuer"}},
        SUBMISSIONS: {"filings": {"recent": columns(recent), "files": [
            {"name": f"CIK{CIK}-submissions-001.json", "filingFrom": "2025-01-01", "filingTo": "2025-12-31"}]}},
        HISTORY: columns([older]),
        BASE + ACCESSION.replace("-", "") + "/report.htm": (FIXTURES / "synthetic_8k.html").read_bytes(),
        BASE + "000012345626000002/form4.xml": (FIXTURES / "synthetic_form4.xml").read_bytes(),
        BASE + "000012345625000003/annual.htm": b"<!-- SYNTHETIC --><p>PART I</p><p>Item 1. Business</p><p>Item 1A. Risk Factors</p>",
    }
    transport = SyntheticTransport(responses)
    store = EventStore(tmp_path / "events.db")
    provider = SECFilingProvider(store, tmp_path / "sec", transport=transport)
    yield provider, store, transport
    store.close()


def fetch(provider, **kwargs):
    return provider.get_filings(["syn"], from_date=date(2025, 1, 1), to_date=date(2026, 2, 1), **kwargs)["SYN"]


def refresh(provider):
    return provider.refresh(["SYN"], from_date=date(2025, 1, 1), to_date=date(2026, 2, 1))


def test_integer_cik_historical_columns_raw_form4_and_preservation(setup):
    provider, _, transport = setup
    docs = fetch(provider)
    assert len(docs) == 3 and not provider.errors
    assert provider.cik_map.get_cik("syn") == CIK
    assert HISTORY in transport.calls
    ownership = docs[0]
    assert ownership.url.endswith("/form4.xml") and "xslF345X06" not in ownership.url
    assert "xslF345X06" in ownership.metadata["listed_url"]
    assert Path(ownership.metadata["raw_path"]).read_bytes() == (FIXTURES / "synthetic_form4.xml").read_bytes()
    assert docs[1].metadata["items"] == ["5.02", "9.01"]
    assert docs[2].metadata["sections"][2]["heading"] == "Item 1A"
    assert docs[1].metadata["leadership"][0]["name"] == "Alice Example"


def test_form4_multiple_owners_derivatives_and_unknowns():
    raw = (FIXTURES / "synthetic_form4.xml").read_bytes()
    data = parse_form4(raw)
    assert len(data["owners"]) == 2 and len(data["transactions"]) == 3
    assert data["ten_b5_one"] is True
    purchase, tax, derivative = data["transactions"]
    assert purchase["classification"] == "purchase_open_market_or_private"
    assert purchase["transaction_value"] == "1250.00"
    assert purchase["holdings_after"] == "200"
    assert purchase["footnote_ids"] == ["F1"]
    assert purchase["footnote_references"] == [{"field": "transactionPricePerShare", "id": "F1"}]
    assert tax["price"] is None and tax["transaction_value"] is None
    assert tax["buy_sell_other"] == "other"
    assert derivative["derivative"] is True and derivative["underlying_shares"] == "5"
    assert parse_form4(raw.replace(b"<aff10b5One>1</aff10b5One>", b""))["ten_b5_one"] is None
    assert parse_form4(raw.replace(b"<aff10b5One>1", b"<aff10b5One>0"))["ten_b5_one"] is False


def test_refresh_idempotency_and_full_evidence_revision(setup):
    provider, store, transport = setup
    first = refresh(provider)
    assert first == {"NEW": 5, "CHANGED": 0, "UNCHANGED": 0, "ERROR": 0}
    assert refresh(provider)["UNCHANGED"] == 5
    old = store.get_event_by_source_id(ACCESSION, EventType.SEC_FILING)
    old_raw = Path(old.metadata["raw_path"])
    url = BASE + ACCESSION.replace("-", "") + "/report.htm"
    transport.responses[url] = transport.responses[url].replace(b"Alice Example", b"Carol Example")
    changed = refresh(provider)
    assert changed["CHANGED"] == 2 and changed["NEW"] == 0
    current = store.get_event_by_source_id(ACCESSION, EventType.SEC_FILING)
    assert current.event_id == old.event_id
    revisions = store.get_revisions(current.event_id)
    assert len(revisions) == 1
    assert "Alice Example" in revisions[0].changed_fields["description"]
    assert b"Alice Example" in old_raw.read_bytes()
    assert "Carol Example" in current.description
    assert refresh(provider)["UNCHANGED"] == 5
    assert not {"company_impact", "stock_bias", "confidence", "base_case"} & current.metadata.keys()


def test_amendments_are_distinct_and_unknown_original(setup):
    provider, store, transport = setup
    amendment = row("0000123456-26-000004", "8-K/A", "2026-01-25", "amend.htm")
    transport.responses[SUBMISSIONS]["filings"]["recent"] = columns([row(), amendment])
    transport.responses[BASE + "000012345626000004/amend.htm"] = b"<p>Item 5.02 Clarification of compensation.</p>"
    assert refresh(provider)["NEW"] == 5
    event = store.get_event_by_source_id(amendment["accessionNumber"], EventType.SEC_FILING)
    assert event.metadata["is_amendment"] and event.metadata["amends_accession"] is None
    assert store.get_event_by_source_id(ACCESSION, EventType.SEC_FILING)
    assert provider.get_current_leadership("SYN", date(2026, 1, 26))["CEO"] is None


def test_leadership_effective_dates_and_source_evidence(setup):
    provider, _, _ = setup
    refresh(provider)
    assert provider.get_current_leadership("SYN", date(2026, 1, 9))["CEO"] is None
    assert provider.get_current_leadership("SYN", date(2026, 1, 14))["CEO"] is None
    state = provider.get_current_leadership("SYN", date(2026, 1, 15))
    assert state["CEO"]["name"] == "Alice Example"
    assert state["CEO"]["source_id"] == ACCESSION
    assert state["CFO"] is None


def test_failures_isolated_and_not_synthetic_fallback(setup):
    provider, _, transport = setup
    transport.responses[BASE + "000012345626000002/form4.xml"] = b"<html>Access denied</html>"
    transport.responses[HISTORY] = ValueError("bad historical shard")
    docs = fetch(provider)
    assert len(docs) == 1
    assert {e["stage"] for e in provider.errors} == {"document", "historical_shard"}
    assert refresh(provider)["ERROR"] == 2
    assert provider.get_filings(["MISSING"])["MISSING"] == []
    assert provider.errors[0]["stage"] == "submissions"


def test_date_limit_and_empty_recent(setup):
    provider, _, transport = setup
    assert len(fetch(provider, max_per_symbol=1)) == 1
    transport.responses[SUBMISSIONS]["filings"]["recent"] = columns([])
    assert len(fetch(provider)) == 1
    with pytest.raises(ValueError):
        fetch(provider, max_per_symbol=0)


@pytest.mark.parametrize("url", ["http://www.sec.gov/a", "https://evil.test/a", "https://www.sec.gov/../a",
                                  "https://www.sec.gov/%2e%2e/a", "https://www.sec.gov@evil.test/a",
                                  "https://www.sec.gov/a?redirect=evil", "https://www.sec.gov:4430/a"])
def test_safe_urls(url):
    with pytest.raises(ValueError):
        safe_sec_url(url)


@pytest.mark.parametrize("raw", [b'<!DOCTYPE a [<!ENTITY e "boom">]><ownershipDocument>&e;</ownershipDocument>',
                                  '<!DOCTYPE a><ownershipDocument/>'.encode("utf-16")])
def test_xml_dtd_rejected(raw):
    with pytest.raises(ValueError, match="Unsafe"):
        parse_form4(raw)


def test_missing_identity_fails_before_network(monkeypatch):
    monkeypatch.setattr("trading_copilot.providers.sec_http.load_settings", lambda: type("S", (), {"sec_user_agent": None})())
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request)))
    transport = SECTransport(client=client)
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        transport.get(SEC_TICKERS_URL)
    assert calls == []
    transport.close()


@pytest.mark.parametrize("code,classification,direction", [
    ("S", "sale_open_market_or_private", "sell"), ("M", "option_exercise_or_conversion", "other"),
    ("A", "grant_award_or_acquisition", "other"), ("G", "gift", "other"),
    ("F", "tax_or_exercise_price_disposition", "other"), ("Z", "other", "other"),
])
def test_transaction_code_classification(code, classification, direction):
    raw = (FIXTURES / "synthetic_form4.xml").read_bytes().replace(
        b"<transactionCode>P</transactionCode>", f"<transactionCode>{code}</transactionCode>".encode())
    transaction = parse_form4(raw)["transactions"][0]
    assert transaction["classification"] == classification
    assert transaction["buy_sell_other"] == direction


def test_natural_dates_negation_and_unsupported_leadership():
    changes = leadership("The Board appointed Alice Example to serve as chief executive officer, "
                         "effective January 15, 2026. Bob Sample resigned as CFO, effective February 1, 2026.")
    assert [(c["role"], c["effective_date"]) for c in changes] == [("CEO", "2026-01-15"), ("CFO", "2026-02-01")]
    assert leadership("The Board has not appointed Alice Example as CEO, effective January 15, 2026.") == []
    assert leadership("Alice Example may be appointed CEO next quarter. Alice Example, CEO, signed this report.") == []
    assert leadership("Alice Example was appointed CEO, effective 2026-02-30.") == []


def test_form4_amendment_does_not_reset_leadership(setup):
    provider, _, transport = setup
    rows = transport.responses[SUBMISSIONS]["filings"]["recent"]
    rows["form"][1] = "4/A"
    refresh(provider)
    assert provider.get_current_leadership("SYN", date(2026, 1, 30))["CEO"]["name"] == "Alice Example"


def test_leadership_uses_effective_order_not_filing_order(setup):
    provider, _, transport = setup
    early = row("0000123456-26-000005", "8-K", "2026-01-01", "early.htm")
    transport.responses[SUBMISSIONS]["filings"]["recent"] = columns([row(), early])
    transport.responses[BASE + "000012345626000005/early.htm"] = (
        b"<p>Item 5.02</p><p>Carol Example was appointed CEO, effective 2026-01-20.</p>")
    refresh(provider)
    assert provider.get_current_leadership("SYN", date(2026, 1, 18))["CEO"]["name"] == "Alice Example"
    assert provider.get_current_leadership("SYN", date(2026, 1, 21))["CEO"]["name"] == "Carol Example"


def test_retry_and_shared_throttle_with_mock_http(monkeypatch):
    import trading_copilot.providers.sec_http as module
    clock = [100.0]
    requests = []
    monkeypatch.setattr(module, "_LAST_REQUEST", 0)
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.time, "sleep", lambda amount: clock.__setitem__(0, clock[0] + amount))

    def handler(request):
        requests.append(clock[0])
        return httpx.Response(429 if len(requests) == 1 else 200, json={}, headers={"Retry-After": "1"})

    # Synthetic identity only for MockTransport; never sent on a real network.
    first = SECTransport("Synthetic offline sec@synthetic.invalid", httpx.Client(transport=httpx.MockTransport(handler)))
    second = SECTransport("Synthetic offline sec@synthetic.invalid", httpx.Client(transport=httpx.MockTransport(handler)))
    assert first.get(SEC_TICKERS_URL).status_code == 200
    assert second.get(SUBMISSIONS).status_code == 200
    assert len(requests) == 3 and requests[1] - requests[0] >= 1
    assert requests[2] - requests[1] >= 0.125
    first.close()
    second.close()


def test_bad_shard_and_mismatched_columns_are_explicit(setup):
    provider, _, transport = setup
    data = transport.responses[SUBMISSIONS]["filings"]
    data["files"][0]["name"] = "../../not-sec.json"
    assert len(fetch(provider)) == 2
    assert provider.errors[0]["stage"] == "historical_shard"
    assert not any("not-sec" in url for url in transport.calls)
    data["recent"]["form"] = []
    assert fetch(provider) == []
    assert provider.errors[0]["stage"] == "submissions"


def test_xml_namespace_and_issuer_mismatch(setup):
    provider, _, transport = setup
    url = BASE + "000012345626000002/form4.xml"
    raw = transport.responses[url]
    transport.responses[url] = raw.replace(b"<ownershipDocument>", b'<ownershipDocument xmlns="urn:synthetic">')
    assert len(fetch(provider)) == 3
    transport.responses[url] = raw.replace(b"<issuerCik>123456", b"<issuerCik>654321")
    assert len(fetch(provider)) == 2
    assert provider.errors[0]["stage"] == "document"
