# Phase 1–11 Website Repair — Final Verification

**2026-10-16: local website verification PASS; no Phase 12 or deployment approval.**

The completion claim at base commit `0dc30132` was not accepted. The existing repair DAG was resumed, material findings were repaired and independently rechecked, and the final backend regression was completed after the last source change. At resumption all 48 checkpoint files matched the durable archive; unchanged frontend/audit evidence was reused rather than repeated. The current repair commit is identified by Git history, not by rewriting the base commit. See the final section of `current_task_graph.md` for publication status and independent session IDs. **Phase 12 must not start.**

| Gate | Latest completed result |
|---|---|
| Backend Python, final broad regression | **492 passed / 35 skipped / 0 failed** |
| Final feed guard | Included in final broad regression; independent real-library matrix PASS |
| Frontend unit | 161 passed / 0 failed |
| TypeScript | PASS |
| Production build | PASS |
| Lint | PASS |
| Chromium desktop/mobile E2E | 112 passed / 0 failed |
| Provider Auditor | PASS, including final feed precision boundary |
| Security Reviewer | PASS, local-only; includes hardened harness DB isolation |
| Independent rendered-site Reviewer | PASS |

These are separate suites; overlapping targeted runs are not combined into broad totals. The backend result includes the final RSS/IR guard. The 35 skips remain skips, not passes; live-gated checks are distinct from the broad run. Chromium totals include real marker-isolated workflows and deliberately synthetic/degraded-state tests, not 112 live-provider checks. A superseded interrupted run was never counted as PASS.

## Reproducible Evidence

- Final command: `LLM_ENABLED=false python3 -m pytest -o addopts='' -q --durations=3 --junitxml=/tmp/opencode/repair-backend-final-20261016.xml` — 386.02 seconds; two dependency deprecation warnings, no failures.
- Unchanged frontend: unit suite used an unreachable API base and network guards; `npm test`, `npm run build`, `npx tsc --noEmit`, `npm run lint` passed. Full Chromium command selected `chromium` and `mobile-chrome`, 112 passed. Tests require the disposable marker backend from `frontend/website_repair_capture.cjs`; never direct mutations at an unverified database.
- Runtime/browser evidence: six desktop pages plus Dashboard/AAPL at 375px, current screenshots in `/tmp/opencode/repair-browser/`; Chromium artifacts in `/tmp/opencode/repair-e2e-release/`. Temporary artifacts may expire; permanent regression tests are included in the repair.
- Actual live disposable refresh ingested SEC filings/insiders, Fed meeting dates and seven IR releases. Earnings/exhibits were empty in the requested window, macro partial and news provider-error states were explicit. Populated management extraction was proven with injected source transport, not invented live quotes.
- Actual Fed dates exported as `DTSTART;VALUE=DATE:20261028` and `20261209`. Actual AAPL dry-run left history unchanged; manual evaluation created a genuine stored trigger and persisted acknowledgment.
- Independent sessions: Provider `ses_ebf2a3b17ffeTrldThrCFKDqeX`; Security `ses_ebf2a1f7dffeEuB3odXZqXdfvj`; rendered Reviewer `ses_ebf133710ffefoP5TMVwhQYUig`. All final verdicts PASS; final raw feedparser matrix distinguished date-only, missing timezone, updates/creation and genuinely supplied midnight.
- Environment: system Python 3.10.12; frontend evidence used temporary Node 20.17.0, below the declared >=20.19 engine. Node 22 (`.nvmrc`) is recommended, not claimed as a separately tested runtime.

Verified repairs include real API/provider wiring, Alpaca pagination/exact bounds/error classification/cache provenance, reachable IR/exhibit ingestion and exact attributed evidence, date-only API/calendar handling, genuine manual alert evaluation/history/acknowledgment, responsive styling, mobile term interactions, market-first dashboard, scanner status freshness, input bounds and loopback defaults. Unsupported/failed sources remain explicit, never synthetic live fallbacks. Scenario probabilities remain uncalibrated/null; missing evidence stays unknown.

Coverage limitations: IEX completed daily closes are not live consolidated quotes; bounded filing/feed windows are not exhaustive history; leadership is evidence-derived, not a complete roster. BEA/Census and future earnings-calendar website coverage remain unavailable. Date-only/timezone-unknown feed entries and unsupported publication formats are omitted rather than assigned fabricated instants. Scheduled monitoring, email/webhook delivery, deployment approval and Phase 12 research are not included.

All production-database preservation and selective-staging rules remain mandatory. Generated tracked-file churn, unrelated scripts/screenshots/skills and the pre-existing requirements snapshot must remain outside the repair commit. Dependency maintenance risks are documented in `DEPENDENCY_ADVISORIES.md`.
