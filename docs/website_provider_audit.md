# Website provider audit — preliminary, independent

**Observed:** 2026-10-14, approximately 18:59–19:02 UTC. **STATUS: PRELIMINARY / MATERIAL FAILURES FOUND. FINAL GATE NOT COMPLETED.** BUILD was still running. This is not a release approval or a completed implementation verdict.

## Scope and evidence discipline

Read `.opencode/agents/provider-auditor.md`, local provenance-data, timestamp-leakage and backend-api audit skills, bootstrap/status/roadmap, application/provider/store/frontend source independently. Queried the existing backend using GET only; inspected `data/events.db` using SQLite `mode=ro`; made free direct HTTP probes; ran six in-memory diagnostic assertions. No application edits, ingestion, refresh, database writes, server restarts, trading, paid services, or credential values printed. Only this report was written. Shared source was changing during BUILD: re-check line references and behavior at the final gate.

**Critical runtime/source mismatch:** existing port 8000 process reports `healthy`, providers `configured`, scanner `ready` and market `operational`; current `backend/main.py` instead defines different health/status responses and a new `WebsiteDataAdapter`. Thus the existing process is stale relative to the source under construction. Its responses must not be presented as current-build verification.

## Independent missing-data classification

| Website area | Actual observation | Cause classification / confidence |
|---|---|---|
| SPY snapshot/chart | Running overview has no prices, `symbols_tracked=0`; bars endpoint returns empty bars. Direct authenticated Alpaca IEX request returned HTTP 200 and nine daily SPY bars, Oct 1–13, no further page. | **Backend/API integration + stale running process**, not missing credentials or demonstrated Alpaca/network failure. New adapter still awaits restarted-runtime verification. |
| VIX, DXY, 10Y | New adapter overview only fetches configured benchmark (SPY); no registered index/rate provider or output for these series. Current landing component renders only returned indices. | **Unimplemented provider/API coverage**, not proven genuine empty or frontend-only fault. Do not substitute ETFs or stale constants as these indices/yield. |
| Scanner/stock quant | Existing scanner returns `[]` while advertised ready. New adapter computes deterministic features from live bars but is not running in that process. | **Backend integration/stale process** primarily; new eligibility/coverage outcomes unknown until final gate. Empty must not mean ready. |
| Macro calendar | GET returns four rows; DB has only four `event_type=macro, source=test, symbol=TEST` records. No actual official macro rows. | **Unrefreshed/test-contaminated DB + absent refresh integration**. Additional **provider implementation defects** below. Not real production evidence. |
| Company events/earnings | Company endpoint and AAPL earnings return `[]`; DB contains zero company/earnings events. | **No ingestion/refresh wiring**, not demonstrated absence of earnings. Earnings-calendar fixture fallback is a separate material risk. |
| SEC filings/insiders | AAPL endpoints return `[]`, DB contains no SEC/insider rows. Direct SEC AAPL submissions request returns HTTP 200 and 1,001 recent filing entries. | **Ingestion/API wiring missing**, not upstream genuine emptiness or demonstrated SEC outage. |
| Leadership | API returns empty leadership map; no leadership rows. Current endpoint derives roles from change events, not a verified complete current roster. | **No ingestion**, plus **incomplete current-roster semantics**. Lack of recent changes does not establish unknown company leadership globally. |
| News | AAPL news is empty; endpoint reads `EventType.NEWS` only; RSS/IR/exhibit providers return document models and are not instantiated/persisted by backend lifespan. | **Provider-to-store/API integration missing**, not proven no news. |
| Management statements | No website management endpoint/tab or backend registration; Phase 9 analyzer unconditionally returns `[]`. | **Unimplemented integration**, independent of upstream availability. |

No company tab is established as **real empty**: there is no successful scoped ingestion record against which emptiness can be judged. No observed evidence implicates a browser cache as the primary cause. Frontend React Query stale times (5 minutes / 1 hour) can delay changes after real ingestion but cannot account for zero database coverage.

## Config, registration and refresh

- Canonical Alpaca key/secret are **present** in local config/environment and running-process environment; direct IEX authentication succeeds. Legacy Alpaca key is present; legacy secret name checked is absent. No values disclosed.
- `SEC_USER_AGENT` is **present** in local configuration, passes existing real-contact validation, and succeeds for `data.sec.gov` submissions. It is absent from the old process environment; absence there alone does not prove unavailable because settings load `.env`.
- BLS/BEA/Census key names checked are **absent**. BLS works without a key in the direct probe. BEA's free key requirement is real, but adding a key cannot repair its empty parser. Census is not established as credential-blocked: public variable metadata is reachable without a key.
- `backend/config.yaml:10–13` still declares `market.provider: mock`, whereas the new adapter explicitly selects Alpaca unless `WEBSITE_DATA_MODE=demo`. This discrepancy needs clear documentation/config ownership; it is not proof the new real-mode adapter serves mocks. Zero-LLM remains the default.
- Current lifespan constructs `EventStore`, `EventService`, Phase 9 engines and market adapter, **not** macro/SEC/earnings/news providers. There is no refresh route/scheduler/provider orchestration in `backend/main.py`; no refresh commands found in `src/trading_copilot/cli.py`. Provider `refresh()` methods existing in modules do not constitute a working website refresh path.
- DB rows were created Oct 12, contain no releases, and have **zero revisions**. Upcoming GET returned one test row, recent GET zero. Data readiness cannot be inferred from `/health` success or DB connection.

## Material source defects independently confirmed

1. **Macro promises substantially exceed implementation.** `macro_calendar.py:540–591`: BEA and Census both fetch responses then return an unpopulated `results=[]`. `fetch_economic_calendar():631–650` is a placeholder returning `[]`; refresh cannot produce CPI/jobs/etc. scheduled releases. Census uses `get=value,date` and `series=...` against marts; official variables metadata lists none of those requested fields. Housing series cannot be presumed supported by this retail endpoint.
2. **Current-year Fed schedule is always fixture-backed.** `fetch_fomc_schedule():316–320` bypasses the official website for the current year. Fixture availability/dates are not fresh live verification; lookup is CWD-relative `tests/fixtures/fomc_{year}.json`. Calendar times are fixed 18:00 UTC, giving incorrect 2pm Eastern winter semantics. Do not label fixture freshness as current official retrieval.
3. **BLS reference periods become fake release times.** `fetch_bls_series():515` creates the first day of the observation month; `fetch_latest_bls_release():534` calls it `release_date`; `fetch_released_values():676–681` converts it to midnight UTC `released_at`. Reference month is not publication date. These values also lack a production schedule to update. M13 annual-average period is not excluded before constructing `date(year, month, 1)`.
4. **Earnings fixtures silently replace live failures.** `earnings_calendar.py:87–114` returns fixtures for missing keys, all failed sources, or even all legitimately empty responses. Live and demo outcomes are not segregated. FMP BMO/AMC becomes fixed 13:30/21:00 UTC and unknown time becomes midnight (`:219–228`); Alpha Vantage dates likewise become midnight (`:167`). These are fabricated exact timestamps and DST mistakes, not merely display formatting. Estimates need source/as-of provenance before use as consensus.
5. **Historical preservation is incomplete.** `MarketEvent.compute_content_hash():107–132` excludes all metadata. EPS/revenue/evidence/leadership/insider changes stored only in metadata therefore compare unchanged; `EventStore.upsert_event():225–234` then updates only `last_seen_at` and loses the new payload. When other fields change, revision tracking (`store.py:303–333`) omits metadata and source, despite overwriting them. Full revision reconstruction is not established.
6. **`as_of` is not point-in-time data.** `interpretation_engine.py:792–795` filters latest event state by release/scheduled date only, not `first_seen_at` or revisions. Revised values and subsequently retrieved evidence can leak backward. Management/news analyzers and quant context are hardcoded empty (`:73–81`, `:143–154`); preserving Phase 9 output is not evidence these provider inputs are connected.
7. **Alpaca pagination and ambiguous failures.** `_fetch_bars_batch():176–192` ignores `next_page_token`; large multi-symbol/historical requests may truncate coverage. `_get_daily_bars_simple():309–324` suppresses certain HTTP/network failures into empty arrays, potentially caching them. New adapter detects some thrown errors but explicitly classifies suppressed failures as `empty` with coverage/failure unknown (`website_data.py:80–83`). Scanner can incorrectly label insufficient/error-derived coverage as no eligible symbols. Never turn failure into verified real empty.
8. **Provenance/freshness surface needs completion.** New market bars have source/URL/market timestamp/retrieved time and completed-daily-close semantics, a useful improvement. However cached provider data must not acquire a false fresh upstream retrieval time. Scanner candidate rows omit source URL and upstream retrieval timestamp. Stock header/landing render numerical prices without exposing all backend status/source/time semantics; stale/unavailable status must remain visible for nonempty payloads too. Leadership output drops source URL/retrieval precision and iterates newest-first events while overwriting roles with older changes, potentially returning stale incumbents.

## Official/free HTTP probes

Direct probes were read-only and not persisted into provider stores:

| Probe | Result | Interpretation |
|---|---|---|
| Alpaca `/v2/stocks/bars`, SPY, IEX, Oct 1–14 | 200, 9 bars, last Oct 13 | Credentials/provider/connectivity work for tested scope. |
| SEC `data.sec.gov/submissions/CIK0000320193.json` with configured contact | 200, 1,001 recent entries | Submissions available; does not certify exhibit/archive coverage. |
| BLS public v2 POST, CPI series, 2026 | 200, REQUEST_SUCCEEDED, 1 series | Keyless BLS connectivity succeeds. |
| BEA official API user guide PDF | 200 | Official docs accessible; no authenticated BEA live-data claim. |
| Census marts `variables.json` | 200; value/date/series absent | Existing request fields require correction against official schema. |
| Fed calendar; SEC/BLS/Census documentation pages; Alpaca reference page | 403 | Environment/access-specific blocking; do not claim verified current schedules/docs, removed endpoints, or global outages from these responses. |

References: <https://data.alpaca.markets/v2/stocks/bars>, <https://docs.alpaca.markets/reference/stockbars>, <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>, <https://www.bls.gov/developers/api_signature_v2.htm>, <https://apps.bea.gov/api/_pdf/bea_web_service_api_user_guide.pdf>, <https://api.census.gov/data/timeseries/eits/marts/variables.json>, <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>.

## Tests performed and limits

- Existing-runtime GET checks: health/detailed health, overview, scanner, SPY bars, macro/company/upcoming/recent, AAPL earnings/news/insiders/leadership/filings. Responses independently compared against read-only DB counts. HTTP 200 did **not** establish readiness.
- SQLite read-only aggregate/schema/revision queries: four test macro rows, zero company rows, zero revisions.
- **6/6 in-memory diagnostic assertions passed**, confirming defects (not product correctness): metadata hash exclusion, fake AMC time, BEA empty parser, BLS reference-month release label, ignored Alpaca pagination, hardcoded management/news analysis. Used mock clients and `__new__`; no provider constructor/cache writes/database creation.
- No full regression/live-ingestion suite executed during this preliminary read-only pass; no browser/E2E verdict; no code corrections or permanent tests added because implementer owns those changes.

## Required fixes / release gates

1. Restart against completed source and record build/process identity; re-run current-code API/provider/offline regression/browser checks. **Final current-code provider audit remains explicitly uncompleted.**
2. Either implement safe bounded provider refresh/persistence with per-provider attempts, outcomes, provenance and freshness, or visibly label every affected section as **not integrated/not refreshed**. Never call connected DB/provider class existence production readiness.
3. Isolate test/demo rows from real-mode website results non-destructively; do not delete existing DB rows without authorization. Reject or flag synthetic provenance rather than displaying as official evidence.
4. Correct macro/earnings schedule/parser/timestamp behavior; absent keys are not the sole blocker. Remove silent production fixture substitution. Register proper VIX/DXY/10Y sources or explicitly state not supported.
5. Preserve metadata changes and complete revision/as-of reconstruction before historical research claims. Add permanent regressions for these defects and time precision/DST/missing values.
6. Preserve provider error vs unknown coverage vs true empty; implement pagination and safe cache/freshness semantics. Complete source/timestamp/status display, leadership role selection and Phase 8→9 data interfaces.

**Shepherd handoff:** resume this independent auditor after BUILD completes. Do not promote this report to PASS based on implementer statements, compilation success, mocked data, or stale-process HTTP 200 responses.
