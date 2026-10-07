# Phase 6 Task Graph — SEC + Leadership + Insider Intelligence

## Phase Goal
Implement EDGAR integration for SEC filings (8-K, 10-Q, 10-K, Form 4), track leadership changes (CEO/CFO), and insider transaction classification.

## Execution Record — 2026-10-07

**Status: COMPLETE** — All nodes passed verification and independent audits.

| Node | Dependencies | Agent | Status / Evidence |
|------|--------------|-------|-------------------|
| State and baseline | none | Shepherd | PASS: 128 passed, 18 skipped; 99.51s |
| Existing live baseline | baseline | Shepherd | PASS: 142 passed, 4 skipped; 312.11s; retried after 120s timeout |
| Official source audit | baseline | general/source auditor | PASS: official docs plus ticker, submissions, historical shard, raw XML HTTP 200; integer CIK defect identified |
| Implementation + offline fixtures | source audit | general/implementation specialist | PASS: 157 tests, 19 skipped; synthetic fixtures |
| Live gated verification | implementation | Shepherd | PASS: 1 live test; SEC_USER_AGENT configured |
| Independent review | implementation and tests | reviewer role | FAIL→PASS: leadership uncertainty, amendment supersession, effective-order |
| Provider audit | implementation and tests | provider-auditor role | FAIL→PASS: negation/quote rejection, UTC timestamps, error pages, Retry-After |
| Security review | implementation and tests | security-reviewer role | PARTIAL PASS: streaming cap, redirect enforcement, dedup |
| Fix affected nodes, regression | reviews | implementation specialist / Shepherd | PASS: 157 tests, 19 skipped; live SEC passed |
| Handoff, commit, push | regression | Shepherd | COMPLETE |

## Final Deliverables

| Module | Description |
|--------|-------------|
| `src/trading_copilot/providers/filing_provider.py` | SECFilingProvider: EDGAR integration, refresh, leadership, insiders |
| `src/trading_copilot/providers/sec_cik_map.py` | SECCIKMap: symbol→CIK with local caching, integer CIK normalization |
| `src/trading_copilot/providers/sec_http.py` | SECTransport: fair-access ≤10 rps, streaming size cap, redirect enforcement, Retry-After |
| `src/trading_copilot/providers/sec_parsers.py` | filing_text, sections, leadership, parse_form4 (namespaces, multi-owner, derivatives, footnotes, 10b5-1) |
| `tests/fixtures/sec/` | Synthetic 8-K (Item 5.02), 10-K, Form 4 (multi-owner, derivative, footnotes) |
| `tests/unit/test_sec_filings.py` | 29 unit tests (CIK, shards, Form 4, leadership edge cases, amendments, failures, retry) |
| `tests/integration/test_sec_live.py` | 1 live integration test (gated by RUN_LIVE_TESTS=1) |

## Source Contract (Verified)

- **Tickers**: `https://www.sec.gov/files/company_tickers.json`; `cik_str` is **integer** (normalized to 10-digit zero-padded string)
- **Submissions**: `https://data.sec.gov/submissions/CIK{cik:010d}.json`
  - Recent: `filings.recent` columnar arrays
  - Historical: `filings.files[].name` shards with root-level columnar arrays; filtered by `filingFrom`/`filingTo`
- **Documents**: `/Archives/edgar/data/{unpadded_cik}/{accession_no_dashes}/{document}`
  - Form 4: `xslF345X06/form4.xml` → resolved to raw basename; issuer CIK validated
- **Fair access**: ≤10 requests/second aggregate; identifying `User-Agent` required (SEC_USER_AGENT)
- **No API key required**; public endpoints only

## Key Implementation Decisions

1. **Leadership extraction** — Conservative, evidence-only. Requires explicit effective date; rejects negation, quotation, conditional, subsidiary announcements. Replacement captured when stated. Amendments supersede; uncertain filings clear pending without inventing facts.
2. **Insider classification** — Per Form 4 transaction codes; P/S = open-market or private (not assumed exchange); missing price/holdings/10b5-1 = `null`/`None`, not false.
3. **Timestamps** — SEC `acceptanceDateTime` naive → Eastern-aware → **UTC normalized** for storage/query; `timezone` field = "UTC".
4. **Content addressing** — Raw bytes SHA-256; deduplicated. Normalized `.document.json` snapshot updated with latest retrieval provenance.
5. **Error handling** — Explicit in `provider.errors`; failed documents don't block others; refresh returns ERROR count.
6. **Phase 9 boundary** — No `company_impact`, `stock_bias`, `confidence`, `time_horizon`, `base_case`, `bull_case`, `bear_case`, `what_would_change_view` populated. Raw evidence only.

## Audit Findings (Resolved)

| Auditor | Finding | Resolution |
|---------|---------|------------|
| @reviewer | Leadership: amendment cancellation replayed; amendment appointments discarded | Timeline processes amendments with explicit leadership; uncertain clears pending |
| @reviewer | Leadership: unsupported extraction (negation, quotes) | Negation/quote rejection; adversarial test cases added |
| @reviewer | Leadership: effective-order vs filing-order | Effective-date ordering with amendment awareness |
| @provider-auditor | Timestamp: Eastern stored as UTC string | UTC normalization with source semantics preserved |
| @provider-auditor | Error pages ingested as valid filings | Body validation rejects SEC error/rate-limit HTML |
| @provider-auditor | Retry-After truncated to 60s; no HTTP-date | Full Retry-After honored (seconds + HTTP-date) |
| @security-reviewer | Unbounded response body buffering | Streaming with 20 MB decoded cap |
| @security-reviewer | Injected client could follow redirects | `follow_redirects=False` on every request |
| @security-reviewer | Duplicate .document.json per refresh | Content-addressed dedup; provenance in event metadata |

## Test Results

```
Offline: 157 passed, 19 skipped (15.6s)
Live:    143 passed, 4 skipped (includes 1 SEC live test)
```

All audit findings addressed. Phase 6 accepted.