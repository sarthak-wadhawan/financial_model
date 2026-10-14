# Phase 11 + Full System Re-Audit — Task Graph

## Phase 11 Frontend Integration (PART A) — COMPLETED ✅

### Node A1 — Watchlist Frontend
**Dependencies:** None (can start immediately)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** COMPLETED ✅
**Tests:** Component tests, E2E tests
**Files created/modified:**
- `frontend/src/pages/WatchlistPage.tsx` (new)
- `frontend/src/services/api.ts` (add watchlist/calendar/alert types and methods)
- `frontend/src/App.tsx` (add routes)
- `frontend/src/components/layout/Sidebar.tsx` (add watchlist/calendar/alert nav items)

**Deliverables:**
- Watchlist page with list, create, edit, delete
- Add/remove/reorder symbols with notes
- Default watchlist designation
- "Add Symbol" modal with validation (1-5 uppercase letters), duplicate detection, optional notes

---

### Node A2 — Calendar Frontend
**Dependencies:** A1 (shared API types in api.ts)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** COMPLETED ✅
**Files created/modified:**
- `frontend/src/pages/CalendarPage.tsx` (new)
- `frontend/src/services/api.ts` (calendar export types/methods)
- `frontend/src/App.tsx` (add route)
- `frontend/src/components/layout/Sidebar.tsx` (add calendar nav)

**Deliverables:**
- Calendar page with export modal with filters (event types, symbols, date range, importance)
- Valid .ics file download with proper unknown-time semantics
- All-day (DATE format) events for unknown exact time
- BMO/AMC session semantics preserved in description

---

### Node A3 — Alert Frontend
**Dependencies:** A1, A2 (shared API types)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** COMPLETED ✅
**Files created/modified:**
- `frontend/src/pages/AlertsPage.tsx` (new)
- `frontend/src/services/api.ts` (alert types/methods)
- `frontend/src/App.tsx` (add route)
- `frontend/src/components/layout/Sidebar.tsx` (add alerts nav)

**Deliverables:**
- Alerts page with list, create, edit, delete
- Alert form with all types, conditions, channels
- Dry-run/test button
- Trigger history with acknowledgment
- Activate/deactivate toggle

---

### Node A4 — API/State Integration
**Dependencies:** A1, A2, A3
**Role:** Integration
**Model:** Lightning
**Status:** COMPLETED ✅
**Files created/modified:**
- `frontend/src/services/api.ts` (all Phase 11 types and methods)

**Deliverables:**
- React Query hooks for all Phase 11 endpoints
- Optimistic updates for mutations

---

### Node A5 — Backend Phase 11 Tests
**Dependencies:** None (backend already complete)
**Role:** Backend testing
**Model:** Lightning
**Status:** PARTIAL - Tests exist for existing functionality but Phase 11-specific test files not yet created
**Status Note:** Core backend tests pass (286/34), but dedicated Phase 11 test files not yet created
**Files to create:**
- `tests/unit/test_watchlists.py` (new)
- `tests/unit/test_calendar.py` (new)
- `tests/unit/test_alerts.py` (new)

---

### Node A6 — Frontend Tests
**Dependencies:** A1, A2, A3, A4
**Role:** Frontend testing
**Model:** Lightning
**Status:** BLOCKED by toolchain (Vitest 4.x + @csstools/css-calc ESM incompatibility)
**Note:** Non-code issue, test infrastructure ready

---

### Node A7 — Browser/E2E Verification
**Dependencies:** A1, A2, A3, A4, A6
**Role:** E2E testing
**Model:** Lightning
**Status:** PARTIAL - Chromium desktop/mobile PASS, WebKit FAIL due to missing system libraries
**Files:**
- `frontend/playwright.config.ts` (configured)

**Deliverables:**
- Playwright tests covering core user workflow
- Chromium desktop + mobile verification PASS
- WebKit unavailable due to missing system libraries (not a code issue)

---

### Node A8 — Accessibility/Security/Degraded-State Review
**Dependencies:** A1, A2, A3, A4
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Tasks:**
- Keyboard navigation verification
- Focus states verification
- Color contrast verification
- Screen reader compatibility
- API error handling (section isolation)
- Empty state rendering
- Provider failure graceful degradation
- No secrets in bundle verification
- Alert channel honesty (no fake external delivery claims)

---

### Node A9 — Integration
**Dependencies:** A1-A8
**Role:** Integration
**Model:** Ultra
**Status:** COMPLETED ✅
**Verified:**
- Complete user workflow: Watchlist → Stock → Alert → Calendar → Trigger History
- Reload behavior verification
- Backend/frontend state consistency
- Alert conditions evaluation
- Calendar .ics semantics

---

### Node A10 — Independent Phase 11 Audits
**Dependencies:** A9
**Role:** Independent audit
**Model:** Ultra (independent)
**Status:** PENDING
**Auditors:** @reviewer, @provider-auditor, @security-reviewer
**Audits:**
- Watchlist persistence + reorder + notes
- Calendar .ics validity (RFC 5545) + filters + duration semantics
- Alert conditions + cooldown + acknowledgment + no fake delivery claims
- Frontend/backend contract
- Security/secrets
- Accessibility

---

### Node A11 — Documentation
**Dependencies:** A10
**Role:** Documentation
**Model:** Ultra
**Status:** COMPLETED ✅
**Files updated:**
- `docs/START_HERE.md`
- `docs/PROJECT_STATUS.md`

---

### Node A12 — Commit/Push
**Dependencies:** A11
**Role:** Release
**Model:** Ultra
**Status:** COMPLETED ✅
**Tasks:**
- Run final tests
- Update documentation
- Commit verified work
- Push to origin/main (no force push)

---

## PART B — Full System Re-Audit (Phases 1-11)

### Node B1 — Documentation Consistency Audit
**Dependencies:** A12 (Phase 11 complete)
**Role:** Audit
**Model:** Ultra
**Status:** IN PROGRESS
**Scope:** Reconcile all authoritative docs with code reality

---

### Node B2 — Quant + Market Data Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Phases 1-2 verification

---

### Node B3 — Event Store + Macro + Company Events Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Phases 3-5 verification

---

### Node B4 — SEC + Earnings + News Provenance Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Phases 6-8 verification

---

### Node B5 — Interpretation + AnswerEngine Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Phase 9 verification

---

### Node B6 — Frontend/API Integration Audit
**Dependencies:** B1, A12
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Phase 10 + Phase 11 frontend/backend contract

---

### Node B7 — Security Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Bundle inspection, API errors, validation, CORS, etc.

---

### Node B8 — Timestamp/Leakage Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** All phases timestamp semantics + future leakage prevention

---

### Node B9 — Zero-LLM Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Verify LLM_ENABLED=false works for all core functionality

---

### Node B10 — Phase 11 Workflow Audit
**Dependencies:** B1, A12
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Watchlist → Stock → Alert → Calendar → Trigger History workflow

---

### Node B11 — End-to-End Real-Symbol Workflow
**Dependencies:** B10
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Real symbol (AAPL) full workflow test

---

### Node B12 — Deployment-Readiness Architecture Audit
**Dependencies:** B1
**Role:** Audit
**Model:** Ultra
**Status:** PENDING
**Scope:** Architecture readiness for Phase 14

---

### Node B13 — Full Regression
**Dependencies:** B1-B12
**Role:** Regression
**Model:** Lightning
**Status:** PENDING
**Tasks:** Run all backend + frontend + E2E tests

---

### Node B14 — Final System Report
**Dependencies:** B13
**Role:** Documentation
**Model:** Ultra
**Status:** PENDING
**Output:** `docs/FULL_SYSTEM_AUDIT.md`

---

### Node B15 — Final Git Handoff
**Dependencies:** B14
**Role:** Release
**Model:** Ultra
**Status:** PENDING
**Tasks:**
- Final tests
- Documentation updates
- Clean git status
- Commit + push (no force push)
- Record commit SHA

---

## Execution Order

### Phase 11 (PART A) — Completed:
- A1, A2, A3, A4, A9, A11, A12: ✅ COMPLETED
- A5: PARTIAL (backend tests exist but Phase 11-specific test files not created)
- A6: BLOCKED (toolchain issue)
- A7: PARTIAL (Chromium PASS, WebKit unavailable)
- A8: PENDING
- A10: PENDING

### PART B — Sequential (mostly):
B1 (IN PROGRESS) → B2-B5 (parallel) → B6 → B7-B9 (parallel) → B10 → B11 → B12 → B13 → B14 → B15

---

# Active repair DAG — Phases 1–11 website (2026-10-14, PLAN handoff)

This section supersedes the execution order above for the requested repair only. Prior graph/history and existing uncommitted edits are preserved, not accepted as proof. **NO Phase 12, deployment, paid services, trades, commit or push by PLAN.** Shepherd must keep the repair bounded to existing Phase 1–11 requirements.

## Scope and invariants

- Repair the reported raw-looking website and missing data at `http://localhost:3000` using real runtime/browser evidence; a build or HTTP 200 is not a success gate.
- `LLM_ENABLED=false`; config defaults must agree. Deterministic scanner weights/ranking stay unchanged, Model A remains separate.
- Provider phases ingest raw facts/evidence only; Phase 9 owns interpretation. Preserve separate company impact/stock impact, evidence, confidence, time horizon and Base/Bull/Bear/change-view sections.
- Preserve source/source URL/id, market/publication/retrieval/calculation times, revisions and conflicts. Date-only and BMO/AMC do not imply exact timestamps. Unknown values stay unknown; zeros are valid values.
- Never silently serve synthetic fixture data as live. Explicit demo mode may use existing deterministic fixtures; real mode must expose unavailable/stale/provider-error states honestly.
- Do not mutate or delete existing production DB records to make screenshots look good. Tests use isolated temporary databases and injected providers.

## Discovery / verified baseline

- HEAD: `ddd7f6dc` (Phase 11 frontend integration); last 15 commits inspected. Prior claims of full PASS conflict with pending audit nodes, missing tests and current runtime failures.
- Pre-existing dirty work: `data/events.db`, `docs/PROJECT_STATUS.md`, `docs/current_task_graph.md`; untracked `skills/`, `frontend/audit_screenshots.cjs`, `frontend/screenshots/`. PLAN modifies only this graph. Preserve and review those items individually; no blanket staging/reset.
- Read first `docs/START_HERE.md`, then requirements, updated architecture/roadmap, PROJECT_STATUS and AGENTS. `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` is referenced but **absent**; no matching copy found. Reconcile this reference at P; do not invent architectural approvals or start Phase 14.
- Relevant audit evidence: existing graph has A5 PARTIAL (no dedicated Phase 11 tests), A6 BLOCKED, A8/A10 PENDING despite completion claims. PROJECT_STATUS lines 825–977 and START_HERE contain unverified CSS/data/accessibility/contract PASS assertions. No standalone FULL_SYSTEM_AUDIT report discovered.
- Runtime architecture: React 18 + Vite 5 + TanStack Query/axios → relative `/api/v1` → Vite proxy localhost:8000 → FastAPI `backend/main.py` → existing `src/trading_copilot` services and SQLite `data/events.db`. Provider refresh/scanner integration is not initialized in API lifespan; backend/config.yaml selects `mock` and disables LLM. This is not a static HTML app or deployed/serverless service.
- Port mismatch: configured Vite 3000, Playwright baseURL/webServer 3001, existing audit script 5173. At inspection 3000 refused connection; 3001, 3002, 5173 were occupied by this repository's Vite processes; API 8000 running from repository root. Do not kill unknown/pre-existing processes. B must own startup/restart and settle explicit ports.
- Browser reproduction on existing 5173: stylesheet loads (1 sheet, 38 rules) but `.app-layout`, `.app-header`, `.metrics-grid` compute `display:block`, `.hero` has zero padding. CSS file has only base/reset/tokens (292 lines), no application/component layout selectors. No Tailwind dependency/config/PostCSS pipeline discovered. Thus missing rules, not a proven stylesheet fetch failure. Shared components also contain utility-style classes without a utility compiler.
- Real HTTP checks: market overview 200 reports `symbols_tracked:0`, `ready/operational`; scanner 200 `[]`; AAPL detail 500; macro endpoint 200. These do not constitute data-integrated success. Browser shows stored `Test Event in 5 days` source `test`; existing data may include audit fixtures. J/M must classify provenance without deleting records.
- Code placeholders: backend market overview/search/scanner/bars/quant/detail price/name; landing hard-coded em dashes for SPY/VIX/DXY/yield; stock hard-coded `$-` and no chart wiring. Duplicate API registrations; term search registered after dynamic term route; company filters ignored; broad credentialed wildcard CORS; health returns hard-coded provider status.
- Contract risks: watchlist reorder client posts `{symbols}` while backend expects bare list; event arrays/metadata are typed as flattened earnings/news/insider objects in places; evidence references need comparison to actual Phase 9 model; macro subtypes vs generic MACRO selection/filtering; date filters act on released_at rather than scheduled date. Validate, do not blindly rename.
- Phase 11 semantics risks: alert dry-run explicitly returns mock response; crossing/change condition behavior requires audit; calendar infers exact time from non-midnight and falls back to `datetime.now()` for undated events. These violate honest missing/time semantics unless repaired.
- Zero-LLM risk: `LLMConfig.enabled` Python default is true even though backend YAML is false. J owns alignment and regression coverage.
- Baseline `LLM_ENABLED=false python3 -m pytest -q`: successful exit after rerun with 360s timeout (320 collected, progress shows 34 skips; 286 passing inferred). First 120s run timed out, not FAIL/PASS. Existing collection has no API/Phase 11-specific/Phase 9 engine test modules; green legacy suite alone proves little about website.
- Frontend with discovered Node PATH: production build PASS; lint FAIL **31 errors**; Vitest FAIL **5 ERR_REQUIRE_ESM startup errors, zero tests executed**. Also `frontend/src/test/setup.tsx` is referenced but only `setup.tsx.bak` exists. Do not label these non-blocking when verification cannot run.
- Actual Chromium headless launch works through installed Playwright. WebKit executable path available but launch/system-library capability not yet checked. No dedicated browser MCP tool exposed to PLAN; use existing Playwright. Screenshot script is untracked user/audit work with hard-coded paths/port and weak text heuristics, not acceptance evidence.
- Follow-up browser evidence: before screenshots `/tmp/opencode/phase1-11-plan-before/dashboard-desktop.png` (1440×900) and `dashboard-mobile.png` (375×812), both real current 5173 runtime. Mobile document scrollWidth **648** at viewport **375**, contradicting prior no-overflow claims. WebKit launch now verified FAIL due to missing GStreamer/flite/AVIF/x264 system libraries; Chromium launch PASS. No privileged installs performed.
- AAPL detail code calls `EventService.get_recent_company_events`, which does not exist (`events_for_symbol`/`recent_events` are available). Empty isolated-DB Phase9 interpretation generates successfully; D should repair the service call rather than replace the interpretation engine. Actual market frontend type demands market_status/snapshot_time/indices but backend returns timestamp/scanner/provider status; search expects `type` versus backend `asset_type`; answer POST omits required symbol and its frontend response type differs from Answer model. These are material contract defects for D/G tests.

## Skills and exact configured agent definitions

PLAN read all discovered skills under `skills/*/SKILL.md`: `plan-first-orchestrator`, `repository-audit`, `frontend-ui-audit`, `backend-api-audit`, `provenance-data-audit`, `timestamp-leakage-audit`, `test-generation`, `accessibility-responsive-audit`, `security-audit`, `documentation-reconciliation`, `deployment-readiness-audit`. Each worker must read relevant files directly; these local skill files are not assumed registered with the harness skill tool.

Configured orchestration/audit roles (discovered via opencode.json and actual files):
- Shepherd: `.opencode/agents/shepherd.md` (orchestrator, NOT primary coder).
- Independent reviewer: `.opencode/agents/reviewer.md`.
- Independent provider auditor: `.opencode/agents/provider-auditor.md`.
- Independent security reviewer: `.opencode/agents/security-reviewer.md`.
- Research auditor: `.opencode/agents/research-auditor.md`; research specialists `.opencode/agents/research/{baseline,tree,neural,features}.md` exist but are **not appropriate BUILD roles** for this website repair.
- Commands: `.opencode/commands/continue-project.md`, `.opencode/commands/audit-current.md`; explicit user NO Phase12/no commit overrides automatic phase-advance instructions here.
- No configured PLAN/BUILD/frontend/backend specialist definitions were found. BUILD labels below are bounded task assignments, not invented configured agent IDs. Shepherd must dispatch via an available general implementation mechanism; reviewer/auditors remain independent of implementation. PLAN cannot spawn from the exposed tools.

## DAG node contracts

Statuses: `PARTIAL` = some inspection complete, `READY` = can be dispatched, `WAITING` = unmet dependency. Owners are task labels unless prefixed with configured `@role`.

| Node | Objective / bounded scope | Dependencies | Owner / required skills | Acceptance / tests | Status |
|---|---|---|---|---|---|
| A reproduce | Capture true baseline at 3000 and current fallback port; identify owning processes, stylesheet/computed styles, console/network and API semantics; before screenshots desktop/mobile. | none | PLAN discovery + BUILD-REPRO; repository-audit, frontend-ui-audit, backend-api-audit | Repro artifacts with URL/viewport/runtime date; failures categorized CSS/contract/provider/empty. Chromium checks, API read-only probes; no production mutation. | PARTIAL: baseline dashboard desktop/mobile screenshots, port/CSS/API repro complete; remaining route matrix belongs L |
| B Vite | Reproducible startup/strict port 3000, proxy/API base consistency, preview/E2E port alignment; no silent alternate-port PASS. Own Vite/package/toolchain config/lockfile. | A | BUILD-TOOLCHAIN; repository-audit, test-generation | Root-start API and explicit Vite 3000 reachable; dev/proxy/production assets work; no stale-server testing. `npm run build`, `tsc --noEmit`, proxy smoke, Playwright startup. | READY after A evidence handoff |
| C CSS | Restore coherent responsive shell/page/shared styles with deliberate existing-class strategy (plain CSS preferred; no accidental Tailwind assumptions), themes, focus/loading/error/table/dialog styles. Own styles only. | A | BUILD-CSS; frontend-ui-audit, accessibility-responsive-audit | Actual grid/flex/padding/card/table/modal computed styles desktop/mobile, explicit dark/light classes work, no global overflow. Browser computed-style regressions and before/after screenshots; build. | READY after A evidence handoff |
| D API | Freeze/version existing API response contracts; fix API lifecycle/route conflicts/validation/filtering/projections and truthful health; wire market/scanner adapter from J, Phase 9 existing engines; own backend/main.py and frontend/services/api.ts/types. | A; J interface contract before adapter wiring | BUILD-API; backend-api-audit, provenance-data-audit, timestamp-leakage-audit, test-generation | All existing endpoint clients agree with serialized data; no placeholder operational claims, 500s or swallowed filters; search/detail outside candidates works. FastAPI TestClient with isolated DB/injected adapter; schema/filter/bounds/errors/terms route tests. | READY for audit/contract freeze; implementation adapter integration waits J |
| E dashboard | Home search/snapshot/today/just released/upcoming/candidates/watchlist/recent company events; typed API calls and section-specific loading/error/empty/stale/source/as-of. Own LandingPage only. | D frozen contract; C shared class contract | BUILD-DASHBOARD; frontend-ui-audit, provenance-data-audit, test-generation | Genuine API values or specific unavailable state; zero preserved; no static market placeholders posing as data; macro/company distinction. Component/network-error tests, browser backend-value comparison. | WAITING |
| F scanner | Scanner rankings/filter/navigation with deterministic scores/components/run freshness/provider provenance; no frontend recalculation. Own ScannerPage only. | D frozen contract; J scanner contract; C shared class contract | BUILD-SCANNER; frontend-ui-audit, provenance-data-audit, test-generation | UI agrees with existing scorer output and artifacts; ranks/ties/zero/empty/failure handled; direct stock links. Component + deterministic API/browser comparison tests. | WAITING |
| G stock | Detail price/chart/company/quant plus evidence-backed Phase 6–9 tabs, answers/scenarios/separate impacts and term UX; truthful missing/error states. Own StockPage/SearchPage only. | D frozen contract; C shared class contract | BUILD-STOCK; frontend-ui-audit, provenance-data-audit, timestamp-leakage-audit, test-generation | AAPL and noncandidate direct search usable; no NaN/fake zero/probability/evidence fields; bar timestamps/source; Phase 9 output faithfully rendered. Component schema-fixture, browser real API, term hover/tap/focus tests. | WAITING |
| H Phase11 | Watchlist persistence/reorder/notes/default/CRUD; truthful alerts dry-run/conditions/cooldown/ack/delivery; valid filtered ICS with date/session precision. Own Phase11 pages + watchlists/calendar/alerts package files; API changes requested from D. | A; D frozen contract before frontend work | BUILD-PHASE11; backend-api-audit, timestamp-leakage-audit, provenance-data-audit, test-generation | Reload-persist workflow verified with isolated DB; reorder exact symbols contract; no fabricated dates/dry-run data/external delivery. New Phase11 unit tests and integrated CRUD/ICS/alert workflows. | READY for service audit/tests; frontend waits D |
| I accessibility | Accessible shared primitives/layout, modal focus trap/restore/Escape, labelled forms/popovers, semantics/mobile nav; hooks/theme lint repair; semantic review of page work. Own ui/layout components, hooks, context, App/main only; do not edit CSS or pages concurrently. | C class contract; E/F/G/H for final cross-page audit | BUILD-A11Y; accessibility-responsive-audit, frontend-ui-audit, test-generation | One main landmark, keyboard-only tasks, visible focus, dialogue labeling, mobile tap/no overflow, theme persistence; no duplicate toaster. Chromium viewport/keyboard tests; lint/components. | WAITING for C class contract; read-only audit READY |
| J providers | Audit actual Phase1–8 reuse and missing integration, implement narrow market/scanner/refresh adapter (new separate module), align zero-LLM default; no provider rewrite or synthetic live fallback. Freeze adapter interface with D first. | A | BUILD-DATA; repository-audit, backend-api-audit, provenance-data-audit, timestamp-leakage-audit, test-generation | Existing Alpaca/mock/feature/eligibility/scorer/event provider services reused; isolated refresh preserving revision data; explicit real/demo/unavailable/stale mode. Offline provider/adapter/zero-LLM tests then gated read-only live smoke, record missing credential skips. | READY |
| K tests | Repair executable Vitest/RTL setup and deterministic browser test isolation; add permanent regressions for observed defects, integrate API/Phase11 coverage; own test files/config only, coordinate package/lock edits with B. | A for scaffold; B/D/E/F/G/H/I/J for full run | BUILD-TESTS; test-generation, repository-audit | Unit/component/API/E2E actually execute and assert semantics/rendering; no weaker assertions or xfails hiding app defects. Full pytest, build/tsc/lint/Vitest, desktop/mobile Chromium; WebKit separately classified. | READY for scaffold; full regression WAITING |
| L screenshots | After fixes capture route/viewport/theme/workflow screenshot matrix plus console/network/computed styles and backend-value comparison; compare A before artifacts. | B/C/D/E/F/G/H/I/J/K | BUILD-BROWSER (independent of UI implementation); frontend-ui-audit, accessibility-responsive-audit, provenance-data-audit | Desktop 1440/mobile 375, dashboard/scanner/stock/search/macro/watchlists/calendar/alerts; expanded evidence/term/modal, provider error/empty/stale; no fake data or unhandled browser errors. Screenshot paths + reproducible script/runtime metadata, no heuristics-only PASS. | WAITING |
| M provider audit | Independent source/schema/time/provenance/refresh/live-vs-fixture/zero-LLM review; enforce source audit→adapter→fixtures→gated live→audit→integration. | D/J/H/K; L for rendered provenance | @provider-auditor; provenance-data-audit, timestamp-leakage-audit, backend-api-audit | Direct inspection plus isolated regressions, current official source contracts where changed, rate limits and failure isolation; PASS/PARTIAL/FAIL with precise findings. | WAITING |
| N security | Independently inspect source/bundle/errors/routes/CORS/SQL/URL/SSRF/webhooks/input handling; no secrets printed, no live-order integration. | B/D/H/J/K; L for UI exposure | @security-reviewer; security-audit | Source/bundle review including sourcemaps, secret type/location-only report; invalid input/URL/error/CORS tests; no dangerous webhook execution. PASS/PARTIAL/FAIL findings. | WAITING |
| O reviewer | Skeptical independent review of Phase1–11 repair vs requirements/runtime; reproduce key workflows and compare all evidence, not implementer reports. | I/K/L/M/N | @reviewer; repository-audit, frontend-ui-audit, backend-api-audit, documentation-reconciliation | No material outstanding failure; executable regressions and real rendered behavior agree; every unmet requirement or external limitation explicitly classified. Return failed node IDs for targeted repair/retest. | WAITING |
| P docs/commit | Reconcile START_HERE/PROJECT_STATUS/graph with verified state, audit/test counts/commands/limitations; commit gate only for Shepherd if authorized, NO Phase12 advancement. | O; all failed nodes repaired/retested | @shepherd documentation handoff; documentation-reconciliation | Docs describe actual CSS/API/data/test state and next action within repair; inspect dirty changes and stage only owned verified files. PLAN never commits; no commit/push until successful gates and explicit parent authorization. | WAITING |

## Safe BUILD dispatch and conflict rules

1. Wave 0: finish A screenshot baseline (read-only), then in parallel B toolchain, C styles, D API contract audit/freeze, J data adapter/source audit, H Phase11 service audit/tests, K test scaffold. A/K/browser probes must not use production mutations. D and J publish the adapter contract before implementing integration.
2. **Single owners:** B owns package.json/lock/Vite/Playwright startup configuration; K requests dependency/config changes through B. D owns backend/main.py and api.ts/types; all other agents propose endpoint/client changes rather than editing those files. J owns new adapter module + zero-LLM default in config.py, not backend/main.py. H owns Phase11 package services/models/stores/pages, not API/client files. C owns CSS only; I owns shared TSX primitives/layout/context/hooks/App/main. Do not dispatch two agents on the same critical file.
3. Wave 1 after D/J contract freeze: E/F/G frontend pages and H Phase11 page repairs are independent of each other; run alongside I shared component repair using C's published class contract. C can extend styles only after class names agreed; component/page agents must not introduce unstyled new classes silently.
4. Every implementation owner adds targeted regression tests under agreed unique filenames, or returns cases to K. K owns consolidated suite config, not all feature code. Merge → K full regression → L rendered evidence → M/N independent audits → O independent review → P docs/release gate. M/N preliminary read-only audits can start earlier, final judgments wait dependencies.
5. Failed node only → repair → affected regression/browser checks → auditor recheck; do not reopen successful unrelated nodes or build Phase12. Record per-node agent/model, start/end/duration, files, commands/results, retries, findings and blockers in this section as work executes. PLAN actual model: GPT-6.1 Sol; other models unset until dispatched (configured routing says auto, not exact model IDs).

## Startup, tools and baseline commands

Run backend from repository root to avoid a second relative `data/events.db`. Existing Python 3.10 imports FastAPI/uvicorn successfully (server already running), but pyproject dependencies do not declare FastAPI/uvicorn; B/D should make backend installation reproducible. No backend requirements.txt exists.

```bash
# backend, repository root; only after B coordinates existing port 8000 owner
LLM_ENABLED=false python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# frontend, frontend/ cwd; current npm is not on shell PATH
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npm run dev -- --host 127.0.0.1 --port 3000 --strictPort
# regression, root; allow at least 360 seconds
LLM_ENABLED=false python3 -m pytest -q
# explicit summary instead of duplicated -q suppression
LLM_ENABLED=false python3 -m pytest -o addopts='' -q
# frontend/ cwd (same PATH prefix for each npm/npx command)
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npm run build
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npx tsc --noEmit
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npm run lint
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npm test
PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH npm run test:e2e -- --project=chromium --project=mobile-chrome
# gated read-only provider checks only after source/credential-presence audit
LLM_ENABLED=false RUN_LIVE_TESTS=1 python3 -m pytest tests/integration -q
```

Node binary discovered from active Vite process: `/tmp/node-v20.17.0-linux-x64/bin/node` v20.17.0; don't assume this temporary installation is durable. Chromium works at `/home/bito/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome`; WebKit path `/home/bito/.cache/ms-playwright/webkit-2370/pw_run.sh` launch fails with missing system libraries (see follow-up evidence above). Prefer new temporary artifacts under `/tmp/opencode/`; do not overwrite pre-existing frontend/screenshots. E2E command above is a baseline command, **not valid final evidence until B aligns its 3001 config with 3000**. No new dependencies/tools installed by PLAN, no live tests requested by PLAN, no application code implemented. `git diff --check` passes after graph edit.

## Current blockers / next dispatch

### Shepherd dispatch ledger (active repair, 2026-10-14)

PLAN completed repository/runtime/skill discovery before application edits. Its baseline invalidates historical visual PASS claims. Phase 12 is explicitly out of scope.

| Assignment | Session | Ownership | State |
|---|---|---|---|
| PLAN | `ses_ec447df0effeB0WqafAwpXtTPB` | DAG and baseline discovery | COMPLETE (planning only) |
| BUILD A/B/C | `ses_ec43d1c19ffe4zbSCesPSo3IlY` | Reproduction, frontend configuration/toolchain and CSS | RUNNING |
| BUILD D/J | `ses_ec43ce11fffel3RFqo5Adgz2sM` | API/client contracts and market/provider integration | RUNNING |
| BUILD E/F/G/I | `ses_ec43ca60bffeatJnp9wWccl0Uq` | Core pages and shared accessibility/layout components | RUNNING |
| BUILD H | `ses_ec43c6b7fffeOLIdcZKL6knFLB` | Phase 11 pages/services and isolated tests | RUNNING |
| BUILD K/L scaffold | `ses_ec43b4e24ffep71nDjbDVEyFOu` | New browser regression/capture harness only | RUNNING (final capture waits implementation) |

Workers use available general subagents under explicit roles, applying local skill files and configured independent reviewer instructions. No research agents assigned. Critical files have a single owner; API/CSS contracts are exchanged through repository reports. Independent provider/security/final review and final regression remain mandatory and pending. No implementation is self-certified and no commit/push is authorized before all gates pass.

#### Preliminary independent findings and targeted recovery

Shepherd baseline: **286 Python passed / 34 skipped / 0 failed**, 184.55 seconds. This existing suite does not establish website correctness.

Provider preliminary source/runtime audit (`ses_ec4381350ffeBFb3YtAqOJ3IoD`, `docs/website_provider_audit.md`) found upstream Alpaca SPY and SEC accessible, stale backend process, test-only database contents, absent ingestion integration, unsupported indices, and timestamp/revision/parser defects. Its final gate remains pending.

- Provider semantics recovery: `ses_ec4340ed8ffe6EI5AxI40j6DPy`, owns macro/earnings calendar providers and new targeted tests only. RUNNING.
- History/provenance recovery: `ses_ec433eb94ffe4hCDaxLSmzDH5T`, owns event models/store/service and InterpretationEngine with new targeted tests only. RUNNING; no Phase 12 implementation.
- D/J follow-up after its current implementation: refresh/persistence integration, safe real/demo separation, Alpaca pagination/failure/cache freshness, explicit unsupported VIX/DXY/10Y, and newest leadership selection. Pending bounded handoff; findings are not excused by an empty UI state.
- Independent security preliminary audit: `ses_ec437b081ffetdKaTH7t3N4qEY`, READ-ONLY RUNNING; final current-build audit still pending.

Security preliminary report (`docs/website_security_audit.md`) is PARTIAL, not release approval. Required follow-ups: ICS non-text CRLF injection (H), loopback API default and missing-record/input handling (D), safe evidence links (E/G/shared components), and applicable dependency advisory review (B). Safe-link helper/tests assigned independently to `ses_ec4318939ffe4UUxRSUtyQ0zIp`; it owns new utility files only.

K/L harness (`ses_ec43b4e24ffep71nDjbDVEyFOu`) PREPARED: new browser test at the actual configured testDir and capture script; preliminary run 8 passed/4 failed, later alert rerun 2 passed. These overlapping preliminary counts are not final totals. Remaining observed app 404 at watchlist detail route belongs to I/H repair; genuine trigger acknowledgment setup must use supported API rather than DB manipulation. Final browser matrix awaits merged implementation.

Safe-link helper node is IMPLEMENTED (not independently approved): `safeExternalUrl(input: unknown): string | undefined`, 68 focused unit tests reported passing. Page/shared-component integration and security-reviewer recheck still required; see `docs/website_safe_links.md`.

Second bounded repair wave:
- H resumed for ICS injection and real-observation evaluation checks; initial H service 19/component 4 passed, API missing-record failure remains D-owned.
- E/F/G/I resumed for safe-link integration (including MacroCalendarPage) and watchlist detail route; initial scoped tests/build/tsc passed, stale runtime integration did not.
- B/C resumed for applicable dependency advisories, isolated package-lock reproduction, ignore policy (no untracking), and compact visual refinements. Initial build/tsc/3000/proxy/CSS checks passed; full Vitest 85 passed/43 failed and lint 19 errors are failures, not acceptance.
- K resumed for existing frontend test contract/mocking repairs only, no weakened assertions; final browser capture still awaits current backend implementation.

No genuine user-authorization blocker to bounded repairs. Engineering failures: CSS absent for app classes, API placeholders/500s, port inconsistency, broken unit-test runtime/missing setup, lint errors, missing Phase9/API/Phase11 regression coverage, false operational health, timestamp/dry-run risks, missing architecture document. Credentials may gate live validation (BEA/Census/Alpaca/SEC identity); do not expose values or treat missing live access as license to fabricate. Dispatch BUILD owners above, keep Phase12 explicitly deferred, and replace historical PASS claims only when P has verified evidence.

### Independent Auditor Results (2026-10-14, post-BUILD)

| Auditor | Status | Key Unfixed Findings |
|---|---|---|
| Provider Auditor | PARTIAL PASS | 7. Alpaca pagination + failure suppression; 8. Scanner/leadership provenance, cache TTL |
| Security Reviewer | PARTIAL PASS | S2. API binds 0.0.0.0; S4. Export/reorder list limits; S5. Dependency advisories/docs |
| Reviewer | PARTIAL PASS | E2E selectors outdated; test env docs; alert evaluate endpoint (future) |

All three auditors completed read-only verification against current repaired code. No final PASS until targeted fixes and re-verification.

### Shepherd dispatch ledger (updated, 2026-10-15)

| Assignment | Session | Ownership | State |
|---|---|---|---|
| PLAN | `ses_ec447df0effeB0WqafAwpXtTPB` | DAG and baseline discovery | COMPLETE (planning only) |
| BUILD A/B/C | `ses_ec43d1c19ffe4zbSCesPSo3IlY` | Reproduction, frontend configuration/toolchain and CSS | COMPLETE |
| BUILD D/J | `ses_ec415790effeVO5Gdj3EwMxcD5` | API/client contracts and market/provider integration | COMPLETE |
| BUILD J2 | `ses_ec3f9f01dffeIHrX4jZjZ8MqFS` | Evidence ingestion bridge + tests/docs | COMPLETE |
| BUILD provider timestamp | `ses_ec4168b8dffe5QiMdP8WAch34n` | macro/earnings calendar + semantics tests | COMPLETE |
| BUILD history/provenance | `ses_ec4162e5affeit10KwSD5bjfzF` | events models/store/interpretation + tests | COMPLETE |
| BUILD K frontend regression | `ses_ec43b4e24ffep71nDjbDVEyFOu` | frontend TEST files, Vitest fixes | COMPLETE |
| BUILD E compact dashboard | `ses_ec43ca60bffeatJnp9wWccl0Uq` | LandingPage, compact layout, tests | COMPLETE |
| BUILD B/C toolchain advisory | `ses_ec43d1c19ffe4zbSCesPSo3IlY` | package-lock, advisories, ignore rules | PARTIAL (lint 11 errors remain) |
| BUILD H Phase11 | `ses_ec43c6b7fffeOLIdcZKL6knFLB` | Phase11 pages/services/isolated tests | COMPLETE |
| BUILD I accessibility | `ses_ec43ca60bffeatJnp9wWccl0Uq` | shared TSX primitives/layout/hooks/App | COMPLETE |
| M provider audit | `ses_ec3c9bba8ffepf8S0nZ1rHn0kV` | FINAL PARTIAL PASS | COMPLETE |
| N security | `ses_ec3c9dfe3ffeVtLvJmm1NfC1ei` | FINAL PARTIAL PASS | COMPLETE |
| O reviewer | `ses_ec3b4e9dcffeGXj4LWJzMaN9NK` | FINAL PARTIAL PASS | COMPLETE |

#### Remaining Unfixed Findings — Targeted BUILD Repairs Required

| ID | Source | Finding | Owner | Acceptance |
|---|---|---|---|---|
| P7a | Provider | Alpaca `_fetch_bars_batch` ignores `next_page_token` | D/J (backend) | Implement pagination loop; respect Alpaca contract |
| P7b | Provider | Alpaca `_get_daily_bars_simple` suppresses HTTP/network failures to empty arrays | D/J (backend) | Classify failures as `provider_error`; do not cache empty-on-error; surface error type |
| P8a | Provider | Scanner candidates lack `source_url` and upstream `retrieved_at` | D/J (backend) | Add fields to candidate dict in `scan()` |
| P8b | Provider | Leadership endpoint drops `source_url`/`retrieved_at` | D/J (backend) | Preserve full provenance in `/api/v1/stocks/{symbol}/leadership` |
| P8c | Provider | `FileCache` TTL not enforced | D/J (backend) | Add TTL param and expiry check |
| S2 | Security | `backend/main.py` launches on `0.0.0.0:8000` | D (backend) | Default to `127.0.0.1`; allow `WEB_API_HOST` override |
| S4 | Security | `CalendarExportRequest` and `ReorderBody.symbols` lack `max_items` | D (backend) | Add bounded list constraints (e.g., 50) |
| S5a | Security | React Router advisories non-exploitability undocumented | B (toolchain) | Add `docs/DEPENDENCY_ADVISORIES.md` with justification |
| S5b | Security | Python env not reproducible; no `pip-audit` | B (toolchain) | Create `requirements.txt` or `pyproject.toml` extras; run `pip-audit` |
| R1 | Reviewer | E2E test selectors outdated | K (frontend tests) | Update Playwright selectors to match current page content |
| R2 | Reviewer | Test env limitations undocumented | P (docs) | Update `START_HERE.md` and `PROJECT_STATUS.md` with test env notes |

Next dispatch wave: D/J for P7/P8/S2/S4; B for S5a/S5b; K for R1; P for R2. Then full regression → auditors re-check → docs/commit.
