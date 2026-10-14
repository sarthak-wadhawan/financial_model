# Website Provider Audit — FINAL (Read-Only, Post-Build)

**Observed:** 2026-10-14, post-BUILD completion. **STATUS: MATERIAL FAILURES REMAIN. NO RELEASE APPROVAL.**  
This audit re-verifies the 8 findings from the preliminary audit (docs/website_provider_audit.md) against the current repaired source tree. No code/data changes were made. Only read-only inspection of source, fixtures, tests, and in-memory assertions.

---

## Scope and Evidence Discipline

- Read `.opencode/agents/provider-auditor.md` checklist, provenance/timestamp skills, bootstrap/status/roadmap, and all provider/store/frontend source independently.
- Queried no live endpoints; inspected source only. No ingestion, refresh, database writes, server restarts, trading, paid services, or credential values printed.
- Re-checked line references against current source (post-BUILD). The preliminary audit's line numbers were from a prior snapshot; this report uses current line numbers.

---

## Re-Verification of Preliminary Findings 1–8

| # | Preliminary Finding | Current Code Status | Verdict |
|---|---------------------|---------------------|---------|
| 1 | **Macro promises substantially exceed implementation.** BEA/Census return empty `results=[]`; `fetch_economic_calendar` placeholder returns `[]`. | `macro_calendar.py:590–608` — `fetch_bea_series` and `fetch_census_series` raise `NotImplementedError` with status `"unavailable"` and reason `"unsupported_official_parser"`. `fetch_economic_calendar:657–664` raises `NotImplementedError` with reason `"official_release_calendar_not_implemented"`. No empty arrays returned. | **FIXED** — Explicitly unavailable, not silently empty. |
| 2 | **Current-year Fed schedule is always fixture-backed.** `fetch_fomc_schedule` bypasses official website for current year; fixture dates not fresh; fixed 18:00 UTC = incorrect 2pm Eastern winter. | `macro_calendar.py:346–360` — Live mode (`self.mode == "live"`) calls `_fetch_fomc_from_fed` which parses the live Fed HTML calendar. Demo mode loads fixture. Fixture used **only** in demo mode. `_fomc_date_event:439–463` derives `expected_statement_at` at 14:00 America/New_York (not fixed UTC) and marks `expected_statement_time_source: "derived_customary_14_ET_not_verified"`. | **FIXED** — Official-first in live mode; fixture only in demo; customary time marked derived/not verified. |
| 3 | **BLS reference periods become fake release times.** `fetch_bls_series` creates first day of observation month; `fetch_latest_bls_release` calls it `release_date`; `fetch_released_values` converts to midnight UTC `released_at`. M13 annual-average not excluded. | `macro_calendar.py:502–563` — `fetch_bls_series` creates `date(year, month, 1)` as observation date, sets `release_date: None`, `released_at: None`. M13 excluded at line 546–547. `fetch_latest_bls_release:565–586` returns `release_date: None`, `released_at: None`. `fetch_released_values:666–699` explicitly does **not** match observations to events; increments `UNMATCHED` with reason `"release_time_and_schedule_identity_unknown"`. No fabricated timestamps. | **FIXED** — No fabricated release times; reference month preserved; M13 excluded; unmatched tracked explicitly. |
| 4 | **Earnings fixtures silently replace live failures.** `earnings_calendar.py` returns fixtures for missing keys, failed sources, or empty responses. Live/demo not segregated. BMO/AMC → fixed 13:30/21:00 UTC; unknown → midnight. | `earnings_calendar.py:82–124` — Demo mode (`self.mode == "demo"`) loads fixtures. Live mode with **no API keys** raises `RuntimeError("No live earnings calendar source configured")` (line 98–99). Live mode with keys tries each source; returns empty list with status `"empty"` on scoped empty response (line 116); raises only if **all** configured sources fail (line 123–124). `_calendar_timing:127–144` returns `scheduled_at: None` when no exact time; precision `"session"` or `"date"`. Alpha Vantage (line 220) sets `"time": "unknown"`. FMP/Polygon/Twelve Data use source-provided time or `"unknown"`. No midnight fabrication. | **FIXED** — Fixtures **only** in demo; live mode fails explicitly on missing keys; empty response ≠ failure; no fabricated exact timestamps. |
| 5 | **Historical preservation incomplete.** `MarketEvent.compute_content_hash` excludes all metadata. `EventStore.upsert_event` updates only `last_seen_at`, loses new payload. Revision tracking omits metadata/source. | `models/events.py:107–149` — `compute_content_hash` **includes** metadata minus bookkeeping keys (`retrieved_at`, `first_seen_at`, `last_seen_at`, `updated_at`, `created_at`, `calculated_at`, etc.). `store.py:199–309` — `upsert_event` detects content change via hash; on change, `_detect_changes:311–345` checks `metadata` field. `_record_revision:347–373` stores **full** `old_event.model_dump_json()` as `old_snapshot` including metadata and source. | **FIXED** — Content hash includes metadata (excl. bookkeeping); revisions preserve full snapshots. |
| 6 | **`as_of` is not point-in-time data.** `interpretation_engine.py` filters by release/scheduled date only, not `first_seen_at` or revisions. Revised values leak backward. | `store.py:397–428` — `events_as_of` filters by `first_seen_at` (line 409), rolls back revisions (lines 411–422), validates evidence provenance timestamps (line 424). `interpretation_engine.py:798–810` — `generate_interpretation` calls `event_store.events_as_of(as_of)` (line 807). Point-in-time reconstruction is used. | **FIXED** — Interpretation uses `events_as_of` with `first_seen_at` and revision rollback. |
| 7 | **Alpaca pagination and ambiguous failures.** `_fetch_bars_batch` ignores `next_page_token`; `_get_daily_bars_simple` suppresses HTTP/network failures into empty arrays, potentially caching them. New adapter classifies suppressed failures as `empty` with coverage/failure unknown. | `alpaca_market.py:137–192` — `_fetch_bars_batch` parses `bars` dict but **does not handle `next_page_token`** (Alpaca pagination). `alpaca_market.py:275–330` — `_get_daily_bars_simple` catches `HTTPStatusError` (4xx/5xx), `TimeoutException`, `ConnectError` and assigns `[]` per symbol (lines 309–324). `website_data.py:80–83` — cache hit returns stale data; on empty bars, status `"empty"` with reason `"No bars returned; symbol coverage or provider failure unknown"`. **Pagination unhandled; failures suppressed to empty arrays; cache freshness not validated.** | **CONFIRMED — UNFIXED** |
| 8 | **Provenance/freshness surface needs completion.** Cached provider data acquires false fresh upstream retrieval time. Scanner candidates omit source URL and upstream retrieval timestamp. Leadership drops source URL/retrieval precision; iterates newest-first while overwriting roles with older changes. | `website_data.py:59–88` — `bars` returns `retrieved_at` (adapter call time) and `market_timestamp` (last bar time). Cache TTL 300s; cached response carries **original** `retrieved_at`/`market_timestamp` (not refreshed). `website_data.py:112–147` — `scan` candidates include `source`, `mode`, `market_timestamp`, `calculated_at` but **no `source_url` or upstream `retrieved_at`**. `backend/main.py:500–529` + `filing_provider.py:247–319` — `get_current_leadership` builds timeline sorted by `(effective_date, filing_date, source_id)` **oldest-first** (line 303), so newer changes overwrite older (correct). However, leadership response drops `source_url` and `retrieved_at` precision (only `filing_date` retained). | **PARTIALLY FIXED** — Cache preserves original timestamps; scanner candidates lack source URL/upstream retrieval; leadership timeline logic correct but output drops provenance fields. |

---

## Additional Inspections

### SEC Filings / Insiders / Leadership
- `filing_provider.py` preserves raw content (SHA-256), normalized documents, and full metadata including `retrieved_at`, `raw_sha256`, `source_url`, `source_id`. `get_current_leadership` returns `"coverage": "ingested_filings_only"` and per-role `source`, `source_id`, `source_url`, `retrieved_at`, `filing_date` — **but** the website endpoint (`main.py:516–522`) wraps this and drops `source_url`/`retrieved_at` from the final response.
- No leadership ingestion path in `lifespan` (no provider refresh orchestration). `source_adapter.refresh` calls `SECFilingProvider` and `EarningsIntelligenceProvider` only when `WEBSITE_REFRESH_PROVIDERS=1` and `WEBSITE_REFRESH_SYMBOLS` set.

### News / IR Feeds
- `news_rss_provider.py`, `ir_release_provider.py`, `sec_exhibit_provider.py` produce `NewsDocument` with `content_hash`, `source_url`, `published_at`, `retrieved_at`, `provider_id`, `dedup_key`. `WebsiteSourceAdapter._news` (lines 92–101) upserts as `EventType.NEWS` with metadata including full document dump and `retrieved_at`. **No live refresh wiring in lifespan** unless env flags set.

### Earnings Intelligence (SEC-based)
- `earnings_intelligence.py` extracts EPS/revenue/guidance from 8-K/10-Q/10-K with `filing_accepted_at` (SEC acceptance) and `announcement_released_at` (set to `None` — correctly not conflated). Surprise computed only when both actual and consensus present. Events upserted with full provenance.

### Cache/Database Behavior
- `storage/cache.py` — `FileCache` uses content-addressed keys (SHA-256 of key parts). No TTL enforcement (manual invalidation only). `AlpacaMarketDataProvider` caches with 300s TTL in `website_data.py` but cache key includes date range only, not `retrieved_at`.
- `EventStore` schema includes `first_seen_at`, `last_seen_at`, `updated_at`, `content_hash`, `metadata` (JSON). Revisions table stores `changed_fields` and `old_snapshot` (full event JSON). `events_as_of` correctly reconstructs point-in-time state.

### Timestamp Semantics
- All providers use UTC internally. `published_at` = source publication/acceptance time. `retrieved_at` = fetch time. `filing_accepted_at` (SEC) ≠ `announcement_released_at` (earnings release) — kept separate. No midnight fabrication observed in current code.

### Failure Isolation
- Each provider has independent `errors` list. `WebsiteSourceAdapter._run` captures per-provider status. `MacroCalendarProvider.refresh` continues on per-event errors. `AlpacaMarketDataProvider` continues on batch failures (assigns `[]` per symbol). **One provider failure does not kill others.**

### Credential Leakage
- `SECTransport.get` validates `SEC_USER_AGENT` format but does not log it. `AlpacaMarketDataProvider` headers constructed from env vars; exceptions caught and logged without serializing request/response bodies. **No credentials in logs/error messages observed.**

---

## Test Coverage Status

| Test Module | Status | Notes |
|-------------|--------|-------|
| `tests/audit/test_timestamps.py` | Passes (in-memory) | Verifies timestamp semantics for SEC/IR/News/Management |
| `tests/audit/test_provenance.py` | Passes (in-memory) | Verifies source_url, content_hash, dedup_key, cross-source links |
| `tests/audit/test_deduplication.py` | Passes (in-memory) | Verifies URL, content_hash, headline+date+symbol dedup |
| `tests/integration/test_macro_calendar_live.py` | Gated (`RUN_LIVE_TESTS=1`) | Tests live Fed/BLS; fixture fallback for 2024 |
| `tests/integration/test_earnings_calendar_live.py` | Gated (`RUN_LIVE_TESTS=1`) | Tests fixture refresh only (no live API keys in CI) |
| `tests/integration/test_alpaca_live.py` | Gated | Live Alpaca bars |
| `tests/integration/test_website_readonly_live.py` | Gated | End-to-end website API |
| `tests/test_website_provider_semantics.py` | Unit | Provider behavior assertions |
| `tests/test_website_evidence.py` | Unit | Evidence/claim models |
| `tests/test_website_history_provenance.py` | Unit | Revision/as_of reconstruction |

**Gap:** No automated test for Alpaca pagination, cache freshness validation, or scanner candidate provenance fields.

---

## Material Findings Summary

| Severity | Finding | Files | Required Fix |
|----------|---------|-------|--------------|
| **HIGH** | Alpaca pagination unhandled — multi-page historical requests truncate silently | `alpaca_market.py:137–192` | Implement `next_page_token` loop in `_fetch_bars_batch`; respect Alpaca pagination contract |
| **HIGH** | Alpaca failures suppressed to empty arrays — cannot distinguish real empty from error | `alpaca_market.py:309–324`, `website_data.py:80–83` | Classify failures as `provider_error`; do not cache empty-on-error; surface error type in status |
| **MEDIUM** | Scanner candidates lack `source_url` and upstream `retrieved_at` | `website_data.py:135–140` | Add `source_url`, `upstream_retrieved_at` to candidate dict |
| **MEDIUM** | Leadership endpoint drops `source_url` and `retrieved_at` precision | `backend/main.py:516–522`, `filing_provider.py:314–318` | Preserve full provenance in leadership response |
| **LOW** | Cache TTL not enforced in `FileCache`; stale cached data may be served | `storage/cache.py` | Add TTL parameter and expiry check |

---

## Required Fixes Before Release

1. **Alpaca Pagination** — Implement `next_page_token` handling in `_fetch_bars_batch`. Verify against Alpaca docs for multi-symbol/historical requests.
2. **Failure Classification** — In `_get_daily_bars_simple`, distinguish client errors (4xx) from server/network errors. Do not cache empty arrays from errors. Return `provider_error` status with error class.
3. **Scanner Provenance** — Add `source_url` (Alpaca bars endpoint) and `upstream_retrieved_at` (provider `retrieved_at`) to each candidate in `scan()`.
4. **Leadership Provenance** — Include `source_url`, `retrieved_at`, `filing_date` per role in `/api/v1/stocks/{symbol}/leadership` response.
5. **Cache TTL** — Add TTL support to `FileCache`; enforce in `AlpacaMarketDataProvider` and `WebsiteDataAdapter`.
6. **Live Refresh Wiring** — Document `WEBSITE_REFRESH_PROVIDERS=1` + `WEBSITE_REFRESH_SYMBOLS` as the **only** supported refresh path. No scheduler; manual/bounded only.

---

## Final Classification

**CLASSIFICATION: PARTIAL PASS**

- Findings 1–6: **FIXED** — Source defects corrected in current code.
- Finding 7: **UNFIXED** — Alpaca pagination and failure suppression remain.
- Finding 8: **PARTIALLY FIXED** — Cache preserves timestamps; scanner/leadership provenance incomplete.

---

## Next Steps

1. Implement fixes for Findings 7 and 8 (Alpaca pagination, failure classification, scanner/leadership provenance).
2. Add regression tests for pagination, failure classification, and provenance fields.
3. Re-run this audit against merged state after fixes.
4. Only then consider release gate.

**Shepherd Note:** Resume this independent auditor after fixes are merged. Do not promote to PASS based on implementer statements, compilation success, or stale-process HTTP 200 responses.