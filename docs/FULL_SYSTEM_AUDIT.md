# R1 — Actual Normal-Runtime Integration Verification

**2026-10-16: bounded R1 verified in the actual running application. No Phase12 or deployment approval.**

The earlier functional-completion claim at `c9b77fbd` was withdrawn. Its test results did not establish that the normal backend was running for the user's website. R1 resumes the existing DAG; it does not restart the project or reinterpret isolated test success as normal operation.

## Reproduced Failure / Root Cause

- Actual Chromium origin `http://127.0.0.1:3000`: GET `/api/v1/watchlists` returned500, empty response, and a browser console resource error.
- The same GET directly at `127.0.0.1:8000` refused connections. Listener inspection showed Vite3000 but **no FastAPI8000**.
- Vite's `/api` proxy and the client's relative `/api/v1` base matched. This was frontend-only startup, not an Alpaca/BLS/SEC outage or CORS failure.
- Direct API `/health` is JSON; `/` is intentionally404. Frontend `/health` is SPA HTML, not proxied API health. The startup gate and smoke tests therefore require JSON `/api/v1/health/detailed`.

## Focused Repairs

- **One normal command:** `npm --prefix frontend run dev`. It starts FastAPI at root/loopback8000, waits for initialized persistence/API health, then launches strict-loopback Vite3000. Unknown occupied ports fail explicitly. Shutdown targets only owned children.
- Three consecutive runtime health-probe failures are required before shutdown; recovery resets the counter. Real child exits/signals interrupt waits promptly. Missing interpreter/dependencies and startup timeout are actionable failures, not a frontend silently served without an API.
- Python Settings resolves repository-root `.env` independently of working directory; explicit test overrides remain supported. The launcher does not load that file into Node/Vite. No provider-secret values were printed or placed in browser configuration.
- Normal startup preserves the intended `data/events.db`; no test-database or demo substitution. SPY retains real daily-close data while VIX/DXY/10Y explicitly report unsupported/null, independently of SPY success.
- Two standalone Alpaca findings were repaired: quotes/trades continuation-token iteration with complete-only caching/legacy partial-cache bypass, and read-only data-host health probing instead of `/v2/account` on the data host. Daily-bar/scoring algorithms and ModelA experiments were not changed.

## Actual Runtime Acceptance Evidence

The owned old servers were stopped and the new normal stack started with the single command above, using **Python3.10.12 / Node22.23.3**. Backend cwd was the repository root; frontend cwd was `frontend/`; no database/demo override was present. Backend-only root dotenv credential presence was verified without exposing values.

After restart, all22 representative direct/proxy requests returned200 JSON: health, MSFT/AAPL search, watchlists, alerts, market overview, scanner top/status, macro/upcoming and AAPL detail. Useful data was rendered: real SPY,20 calculated scanner results, macro/Fed data and AAPL price/bars. Counts/windows are observations, not fixed API invariants.

Watchlist/AAPL notes and an inactive alert created through the real Vite API survived the actual backend+frontend process restart. Read-only SQLite inspection confirmed their IDs in the intended original database. Only the verification-created records were API-deleted. Read-only comparison preserved all8 pre-existing watchlists,4 items,2 alerts and0 triggers exactly; no verification records remained. Official ingestion legitimately updated event data and is not a source change to commit.

The actual Macro UI refresh POST traversed Vite→normal FastAPI→providers/store and returned200. During source failures, concurrent watchlist, alert and health requests still returned200. This is runtime failure-isolation evidence, not just an injected-provider unit test.

New opt-in `normal-runtime.spec.ts` sends unmodified browser requests to3000: JSON health, MSFT/AAPL search, watchlist persistence, alert save/reload/side-effect-free dry-run, Dashboard/Scanner/Macro/AAPL rendering and valid calendar download. No interception, financial mocks, marker backend or temporary database is used for that gate. The independent reviewer repeated it and inspected desktop/mobile pages, with no global API-error alerts or uncaught browser errors.

## Final Regression (Separate Totals)

| Gate | Result |
|---|---|
| Backend Python | **532 passed / 35 skipped / 0 failed** |
| Frontend unit | **163 passed / 0 failed** |
| Startup coordinator tests | **15 passed / 0 failed** |
| TypeScript | **PASS** |
| Production build | **PASS** |
| Lint | **PASS** |
| Chromium desktop/mobile E2E | **122 passed / 0 failed** |
| Provider Auditor | **PASS**, source/unsupported limits below |
| Security Reviewer | **PASS**, bounded startup/local scope |
| Actual-runtime Reviewer | **PASS** |

The122 E2E cases include10 normal-runtime cases (five per project); legacy isolated/degraded cases are not claimed as real normal-database flows. Separate five-case runs and overlapping targeted/auditor tests are not added to totals. Skips are not passes. The full backend run took401.85s, with two dependency deprecation warnings and no failures/errors.

Independent R1 sessions: Provider `ses_eba3473b3ffeJM1E2JUCuFXRqb`; Security `ses_eba2e119fffeWum00QLNBERFyq`; actual-runtime Reviewer `ses_eba247524ffedefT4ZekZ3gZWu`.

Evidence (local artifacts may expire): `/tmp/opencode/runtime-integration-20261016/` contains the before failure,22-call direct/proxy matrix, process identity and redacted browser requests; `normal-macro-refresh.json` records concurrent local success during provider refresh. Normal logs: `/tmp/opencode/runtime-r1-normal-dev.log`. Backend XML: `/tmp/opencode/runtime-r1-backend-final.xml`; full browser artifacts: `/tmp/opencode/runtime-r1-e2e-final/`. Source regression tests are permanent; normal-browser capture omits existing user-data values, screenshots and traces.

## Explicit Provider / Product Boundaries

- **PASS:** real Alpaca auth, uncached AAPL/MSFT/SPY daily bars and pagination, deterministic scanner, SEC identity/documents/provenance/persistence, official Fed ingestion→store→API, and primary IR releases. Health/historical quote/trade helpers were independently rechecked with bounded live reads. No account/trading action or paid service.
- **SOURCE_FAILURE, not a global API outage:** BLS anonymous daily quota exhausted; optional BLS/BEA/Census keys absent. News endpoints returned upstream401/403/429. Macro correctly reports partial: official Fed successes coexist with BLS failures; SEC/IR/local features continue working.
- **UNSUPPORTED:** VIX/DXY/10Y, incomplete BEA/Census live pathways and verified future earnings calendar. No substitute instruments, invented numeric observations or fixture fallback. Earnings/exhibits may be genuinely empty in the bounded lookback.
- Retained historical/test records are not certified official/live. Leadership remains ingested-filings-only; unknown/ambiguous evidence remains unknown. IEX completed closes are not live consolidated quotes; scenario probability bands remain uncalibrated/null.
- Manual alerts/in-app history are supported; scheduling, external notifications, automatic trading, deployment hardening and Phase12 research are not included. Dependency maintenance risks remain in `DEPENDENCY_ADVISORIES.md`.

Leave the verified normal3000/8000 stack running for the user's retest. Closing its command stops both; restart using the canonical command in `START_HERE.md`. Only focused R1 source/tests/docs are published; never stage databases, private backups, caches, generated churn or unrelated user files. Git history/remote records publication; no force push.
