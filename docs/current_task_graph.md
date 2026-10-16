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

## 2026-10-15 Shepherd pause checkpoint

**User requested pause because credits expire; resume in approximately five hours. This is a checkpoint, NOT a completion claim. NO Phase 12.** Existing A–P DAG above remains the plan; do not recreate it or reread the entire repository.

### Current node classifications

| Node | Status | Current evidence |
|---|---|---|
| A reproduce | PASS | Original failures reproduced; eight current route/viewport screenshots retained |
| B Vite | PASS | Owned strict-port 3000 server; working normal API proxy |
| C CSS | PASS | Styled desktop/mobile; no document overflow |
| D API | PASS | Real paths, bounded inputs, date-only filtering, current observation wiring |
| E dashboard | PASS | Market-first ordering; provider coverage and scoped refresh |
| F scanner | PASS | Deterministic values, partial errors, genuine provenance; scan→status ordering and market date fixed |
| G stock | PASS | Real price, evidence/management views, honest unknown impacts and uncalibrated scenarios |
| H Phase11 | PASS | Persistence; genuine manual evaluation/history/ack; side-effect-free dry-run; valid date-only ICS |
| I accessibility | PASS | Mobile term taps, keyboard/modal focus, responsive layout independently checked |
| J providers | PASS | P7/P8 and reachable extraction/validation repaired; final timestamp boundary independently approved |
| K tests | NEEDS VERIFICATION | Final broad backend run required after last feed timestamp guard; frontend suites already current |
| L screenshots | PASS | Six desktop pages plus Dashboard/AAPL at 375px, independently visually reviewed |
| M provider audit | PASS | Final combined verdict, including actual feedparser timestamp matrix |
| N security | PASS | Loopback, bounds, URLs/ICS/CORS/secrets and harness DB isolation checked |
| O reviewer | PASS | All original material and subsequent minor findings resolved/rechecked |
| P docs/commit | NEEDS VERIFICATION | Only pause notes and dependency correction saved; final reconciliation/staging/commit/push pending |

### Resume in this order

1. Read this checkpoint; inspect `git status --short` selectively. HEAD/main remains `0dc30132`; no staging, commit or push performed. Remote main matched that hash when last checked; recheck before eventual push.
2. All application implementation is finished. **Do not launch more broad discovery or research.** Final changed source is on disk. Only repair an actual failing test/auditor finding.
3. Run exactly one final broad backend regression on the current source: `LLM_ENABLED=false python3 -m pytest -o addopts='' -q --durations=3 --junitxml=/tmp/opencode/repair-backend-final.xml`. Allow roughly 7–8 minutes; do not treat timeout/interruption as PASS. Latest successful earlier run was 474 passed / 35 skipped / 0 failed, 422.65s, before the last feed guard. New targeted cases are not included in that old total.
4. Preserve successful frontend results unless relevant source changes: final full unit **161 passed / 0 failed**, full desktop/mobile Chromium **112 passed / 0 failed**, build/TypeScript/lint **PASS**. Tests now reject accidental real XHR/fetch; unit suite passed with API base `http://127.0.0.1:9/api/v1`. Node used `/tmp/node-v20.17.0-linux-x64/bin`; declared supported engine is >=20.19, `.nvmrc` recommends 22. Record actual tested environment honestly.
5. Once regression passes, minimally reconcile START_HERE, PROJECT_STATUS, this graph and FULL_SYSTEM_AUDIT. Historical START_HERE sections still contain obsolete Phase 9/10 handoffs and false “no website yet” limitations: mark historical/correct, do not trust them. Explicitly hold Phase 12. Dependency advisory correction is already independently approved.
6. Review and stage **only explicit legitimate source/docs/tests**. Durable backup/allowlist is recorded below. Never stage generated churn, database, skills, old user screenshots/scripts, or the pre-existing legacy requirements snapshot. `git diff --cached --check`; inspect staged names/diff; normal commit and `git push origin main` only after gates. Never force push; stop if remote diverged. Do not create an empty verification commit.

### Final repairs / bounded limitations

- Alpaca: exact RFC3339 historical bounds/cache keys; pagination/repeated-token protection; errors do not silently become cached empty bars; scanner partial failures explicit; true original upstream retrieval timestamps retained. TTL and newest-evidenced leadership source URL/retrieval/filing date verified.
- Reachable `WebsiteSourceAdapter` now includes IR/exhibits plus deterministic management extraction and validated quote/attribution spans. The separate `WebsiteEvidenceAdapter` remains unused intentionally; do not wire its unsafe broad refresh paths wholesale.
- Wrong-speaker Alice/Bob quote verification fixed and independently replayed. Raw headlines do not inflate validated-claim confidence. Missing evidence no longer implies stable fundamentals or neutral/low stock impact. All Base/Bull/Bear probability bands are null and explicitly uncalibrated; no Phase 12 research undertaken.
- Feedparser aliases previously invented update timestamps. Actual supplied keys now govern timestamps. Final shared RSS/IR guard requires an actual clock AND timezone; date-only/timezone-unknown entries are conservatively omitted, not promoted to midnight/UTC. RSS update/create-only entries are not publication evidence; IR preserves known update/create concepts without claiming original release. Explicit source midnight remains valid. **Last implementation verification: 36 affected tests passed; independent auditor: 24 selected regressions plus 30 actual-feedparser matrix cases passed.** Do not add these overlapping counts to broad-suite totals.
- Real disposable runtime refresh populated SEC filings/insiders, Fed meeting dates and seven IR releases. Current-window earnings/exhibits were genuinely empty; macro partial/BLS failures and news provider_error remain explicit. BEA/Census parsers and future earnings calendar remain unsupported/unavailable in the website bridge. Leadership is ingested-filings-only, not a complete authoritative officer roster. No live management quotes were fabricated; populated extraction is proven by injected transport endpoint regressions.
- Live API proved future Fed dates survive filters/upcoming and export `DTSTART;VALUE=DATE:20261028` / `20261209`, no fabricated midnight. Actual AAPL price dry-run had zero history mutation; manual evaluation created a genuine trigger and persisted acknowledgment.
- Scanner status now follows scan completion/refetch, exposes a source-consistent market timestamp. E2E teardown waits pending route handlers.
- API entrypoint and Vite default to loopback. Old verified repository-owned wildcard PID was gracefully replaced, no unknown processes killed. Security PASS is local-only, not deployment approval.
- Required untracked `frontend/website_repair_capture.cjs` is now hardened to force its child DB path despite inherited `TRADING_COPILOT_DB_PATH`. Independent security replay verified a disposable inherited sentinel remained unchanged while a watchlist mutation landed only in the fresh harness DB. Include this harness in the eventual commit.
- `docs/DEPENDENCY_ADVISORIES.md` now correctly attributes old msgpack/urllib3 risk to unused legacy `alpaca-trade-api`, NOT feedparser, and distinguishes declared `web`/`full` extras from the incomplete untracked requirements snapshot. No dependency change required; cleanup/complete locking are nonblocking maintenance.

### Recovery locations / safe runtime

- Source/tests are saved in the current working tree. **No source reset/restore/clean was used.** Initial 1773 dirty entries included 1747 generated frontend entries plus legitimate tests/scripts and the pre-existing modified `data/events.db`. Preserve all unrelated work; no generated deletion/untracking authorized.
- Durable explicit staging manifest: `.git/repair-checkpoints/phase1-11-20261015-paths.txt`. Durable source/test/docs archive: `.git/repair-checkpoints/phase1-11-20261015.tar.gz`. Archive intentionally excludes generated dependencies/builds/reports, databases, credentials and unrelated user work. Archive is an additional backup, not permission to overwrite current files.
- Extra session notes/allowlist: `/tmp/opencode/repair-resume-findings.md`, `/tmp/opencode/repair-release-paths.txt`; these may expire, so this repository checkpoint is authoritative for resumption.
- Eight current screenshots/metrics: `/tmp/opencode/repair-browser/` (Dashboard, Scanner, AAPL, Watchlists, Calendar, Alerts desktop; Dashboard/AAPL mobile). Latest full E2E artifacts `/tmp/opencode/repair-e2e-release/`; backend JUnit may be overwritten by the final rerun.
- If still running: owned Vite `127.0.0.1:3000`; owned normal backend `127.0.0.1:8000` uses **disposable** `/tmp/opencode/repair-runtime.db`, not original data. That process predates the final RSS guard: restart the verified owned backend before final live ingestion checks. Original `data/events.db` was never mutated for screenshots.
- Disposable marker backend `18080` latest environment `/tmp/opencode/website-repair-zDilp8/environment.sh`; older agent-owned disposable `18081` may also remain. Tokens change on restart. Never reuse a stale token or mutate an unverified backend. Stop only verified owned processes; leave pre-existing 3001 Vite untouched. No processes are guaranteed to survive the pause.
- From root: `python3 -m pip install -e '.[web,dev]'` supplies runtime/test dependencies. Existing `.venv` lacks FastAPI; verified runs used system Python3.10.12. Backend `LLM_ENABLED=false python3 -m backend.main`; frontend Node22 / `npm run dev` on strict loopback3000. Never print credential values.

### Independent sessions (reuse if available; do not spawn many agents)

- Provider auditor: `ses_ebf2a3b17ffeTrldThrCFKDqeX` — final combined PASS after final feed precision recheck.
- Security reviewer: `ses_ebf2a1f7dffeEuB3odXZqXdfvj` — final PASS including dependency docs and harness isolation.
- Rendered-site reviewer: `ses_ebf133710ffefoP5TMVwhQYUig` — final PASS after scanner/harness recheck.
- API/calendar/alert BUILD: `ses_ebf25ea3bffeodKl0w6Za3otMg`.
- Provider/extraction BUILD: `ses_ebf23f138ffeD5aSV0MQPa8t7Y`.
- Frontend/harness BUILD: `ses_ebf209e8bffetAXKTb44WUHWGo`.
- All workers were available general agents assigned bounded BUILD/audit roles; exact routed model/durations were not reported. Maximum two concurrently; no research agents. All agents finished at pause. No automatic continuation is scheduled; resume on the user's next message.

## 2026-10-16 — Checkpoint Resumed / Final Verification

This section supersedes the dated pause classifications, without replacing the existing DAG. All 48 checkpoint files matched their archive on resumption; no implementation node was restarted and no source code changed. Prior Provider/Security/rendered Reviewer PASS evidence and frontend results remain valid.

| Existing nodes | Current status | Evidence |
|---|---|---|
| A, B, C, D, E, F, G, H, I, J | PASS | Completed implementation/runtime evidence preserved from checkpoint |
| K tests | PASS | Final full backend **492 passed / 35 skipped / 0 failed**, 386.02s, final source revision; frontend **161 unit / 112 Chromium passed**, TypeScript/build/lint PASS reused unchanged |
| L screenshots | PASS | Existing eight route/viewport captures and independent visual review reused |
| M provider audit | PASS | Final source timestamp/attribution/P7/P8 verdict unchanged |
| N security | PASS | Final local-only verdict, dependency correction and harness isolation unchanged |
| O reviewer | PASS | Final rendered-site verdict and bounded scanner/harness recheck unchanged |
| P docs/commit | PASS | Reconciled handoff independently approved; explicit-path staged checks completed; normal publication is the terminal Git step |

Final backend command: `LLM_ENABLED=false python3 -m pytest -o addopts='' -q --durations=3 --junitxml=/tmp/opencode/repair-backend-final-20261016.xml`. The earlier 474-pass snapshot and overlapping targeted counts are not added to this final result. Two dependency deprecation warnings remain nonblocking.

Only the verified 48-path source/test/config/docs manifest is eligible for staging. Original DB, generated dependencies/builds/reports, unrelated user scripts/screenshots/skills and the legacy requirements snapshot stay untouched/unstaged. Remote main matched `0dc30132` on final fetch. Independent handoff review returned PASS after inspecting current docs, the manifest and final JUnit; prior application/provider/security gates remain closed. Publication is recorded by Git history/remote, not a self-referential commit hash in this document. **NEXT ACTION: normal selective commit/push if not yet published; otherwise HOLD. No Phase 12.**

### Bounded leaf P1 — Staged whitespace gate: PASS

The staged check caught trailing spaces on 40 blank lines in the previously untracked `tests/test_website_evidence.py`. BUILD `ses_eba4f7da4ffe3rSOvygn3b7QDE` removed only those spaces; exact AST (including attributes), line count and newline style remained identical. Parent verifies the staged-to-working-file whitespace-only transformation and reruns the staged whitespace check. No functional test/audit evidence is invalidated and no broad test suite is repeated for this formatting-only leaf.

## R1 — Actual normal-startup frontend/backend integration repair (2026-10-16)

**Status: PASS — actual normal runtime, independent review and final regression verified.** Depends on existing B/D/H; does not restart A–P or authorize Phase12. User's actual website disproved the earlier functional-completion claim at `c9b77fbd`; that claim is not reused as R1 runtime evidence.

- Exact initial trace: Chromium origin `http://127.0.0.1:3000`, GET `/api/v1/watchlists`, response500/empty. Same GET directly at `127.0.0.1:8000` refused connection. `ss` showed Vite3000 but no FastAPI8000. Configured `/api` proxy destination is8000; this is system-wide startup failure, not demonstrated provider failure. Before evidence: `/tmp/opencode/runtime-integration-20261016/before-network.json` and `watchlists-before.png`.
- BUILD `ses_eba38f579ffev1MLrzb5QpaGhZ`: bounded canonical dev startup/readiness/process ownership and repository-root `.env` loading; small startup/config regressions. No source-provider rewrite or broad re-audit.
- Acceptance: clean documented normal startup must start and wait for the real backend on loopback; root `.env` presence/config and actual intended database verified without secret values. Direct FastAPI and Vite proxy calls must both work for search AAPL/MSFT, watchlists, alerts and remaining API paths. Prove local CRUD/reload persistence first, then provider/market/scanner/macro behavior.
- Final gate must be real Chromium → unmodified `/api/v1` requests → Vite → normal FastAPI → intended DB/providers → rendered UI, NOT route-forwarding to a disposable marker backend. Use unique API-created verification records and clean up only those records; never manually edit SQLite or fabricate events.
- After local connectivity is proven: independent bounded Provider Auditor, security check of launcher/environment boundary, and actual-runtime Reviewer. Reuse unaffected prior evidence; one final regression near the end. Previous 492/161/112 counts remain historical, not proof of current runtime connectivity.
- Final docs must supersede the withdrawn completion claim. Stage only legitimate R1 source/tests/docs, excluding generated churn and original DB. No force push; no Phase 12.

### R1 progress — actual normal stack, not disposable forwarding

- Canonical command is now **`npm --prefix frontend run dev`** from root (equivalently `npm run dev` in frontend), using Node22.23.3. It starts Python from repository root, waits for JSON `/api/v1/health/detailed`, then launches strict-loopback Vite3000; backend8000 is owned by the same coordinator. Do NOT start an additional backend first. Unknown occupied ports fail rather than being adopted/killed. Python alone loads root `.env`; explicit test dotenv overrides remain supported. No secret values printed or loaded into Vite by the launcher.
- Security found and BUILD repaired single-probe shutdown sensitivity: three consecutive failures are required, successful health resets the counter, real child exits/signals interrupt waits promptly. Independent SecurityReviewer `ses_eba2e119fffeWum00QLNBERFyq`: PASS; 15 Node lifecycle tests passed. Root dotenv tests: 2 passed.
- Clean restart was performed after gracefully stopping only verified target Vite2712701 and owned diagnostic API2732594. Pre-existing Vite3001 remains untouched. New stack is running via one normal command, log `/tmp/opencode/runtime-r1-normal-dev.log`; **leave this normal stack running for the user** unless explicitly asked to stop. No temporary database/mode overrides. Actual DB is `/home/bito/Desktop/financial_model/data/events.db`; a read-only pre-mutation backup is internally stored at `.git/repair-checkpoints/runtime-r1-before.db` and must never be staged.
- Provider-independent proof: direct8000 and Vite3000 search MSFT/AAPL, watchlists, alerts and coverage return200 JSON. API-created uniquely named watchlist/AAPL/notes and inactive alert survived the actual backend+frontend process restart; readonly SQLite queries confirmed IDs in the intended DB. Only those two verification records were then deleted through API and confirmed404. Existing user/default records were not deleted or reset.
- Post-clean-start matrix: all 22 direct/proxy calls returned200 across health, MSFT/AAPL search, watchlists, alerts, overview, scanner top/status, macro/upcoming and AAPL detail. Real scanner returned20 calculated candidates. SPY available; VIX/DXY/10Y explicitly unsupported with null values/source/time, not substituted. Evidence `/tmp/opencode/runtime-integration-20261016/clean-start-direct-vite.json`.
- New opt-in actual-runtime E2E: `RUN_NORMAL_RUNTIME_SMOKE=1 node frontend/scripts/verify-normal-runtime.mjs` — **5/5 passed after clean restart**, no interception/mocks/temporary API, real original DB; created resources cleaned through API. Network evidence redacts values and retains URL/method/status/body structure only. Without opt-in these tests clearly skip; skipped tests are not PASS evidence.
- Actual Macro UI refresh POST through Vite returned200, with official Fed/SEC/IR source outcomes. Concurrent watchlist, alert and health requests all returned200 during refresh, proving source failures do not take down local paths. Evidence `/tmp/opencode/runtime-integration-20261016/normal-macro-refresh.json`.
- Independent ProviderAuditor `ses_eba3473b3ffeJM1E2JUCuFXRqb`: PASS for real daily bars/pagination/scanner, SEC evidence/persistence, Fed ingestion/store/API. Two standalone helper defects were fixed and rechecked: historical quotes/trades iterate continuation tokens without caching partial ranges; data health uses a read-only data endpoint rather than `/v2/account` on the data host. Helper+existing Alpaca tests: 54 passed, with bounded live health/quote/trade reads. No account/trading action or paid service.
- Genuine nonblocking external/source limits: BLS anonymous daily quota exhausted; BLS/BEA/Census optional keys absent (presence-only check); news endpoints returned401/403/429. Fed8 successes coexist with BLS6 failures (`macro:partial`); SEC8 and IR7 succeed. Earnings/exhibits are empty in the bounded window. BEA/Census/future earnings calendar and VIX/DXY/10Y remain explicitly unsupported/unavailable. No fixtures replace live observations.
- Independent actual normal-runtime Reviewer `ses_eba247524ffedefT4ZekZ3gZWu`: PASS. It reran the real-origin five-case browser gate without interception/test backend, checked additional desktop/mobile pages, observed successful API responses and rendered data, and left the normal servers running. It did not certify old test records as official/live or assert a fixed upcoming-event count.

### R1 final regression / publication gate

| Gate | Result |
|---|---|
| Backend, final broad run | **532 passed / 35 skipped / 0 failed**, 401.85s |
| Frontend unit, Vitest | **163 passed / 0 failed** |
| Dev coordinator, Node | **15 passed / 0 failed** |
| TypeScript / build / lint | **PASS / PASS / PASS** |
| Chromium desktop/mobile | **122 passed / 0 failed**, including 10 actual normal-runtime cases |
| Provider / Security / actual-runtime Reviewer | **PASS / PASS / PASS**, explicit external/unsupported limits retained |

Final backend XML: `/tmp/opencode/runtime-r1-backend-final.xml`. E2E artifacts: `/tmp/opencode/runtime-r1-e2e-final/`; redacted normal-origin request evidence: `/tmp/opencode/runtime-integration-20261016/`. The total122 includes normal cases once per desktop/mobile project; separate five-case runs and auditor/targeted repeats are not added. Legacy isolated/degraded tests remain distinct from actual normal-stack evidence.

Commands used after the clean restart (Node22.23.3): backend `LLM_ENABLED=false python3 -m pytest -o addopts='' -q --durations=3 --junitxml=/tmp/opencode/runtime-r1-backend-final.xml`; frontend `npm run test:dev`, `npm test`, `npx tsc --noEmit`, `npm run build`, `npm run lint`; full browser `RUN_NORMAL_RUNTIME_SMOKE=1 PLAYWRIGHT_REUSE_SERVER=1 npm run test:e2e -- --project=chromium --project=mobile-chrome --workers=2` with a separately identified legacy marker fixture solely for old isolated cases. Normal cases never route-forwarded to that fixture.

Only the focused18-path manifest `.git/repair-checkpoints/runtime-r1-paths.txt` is eligible for publication. Never stage the original DB, private backup, provider caches, generated files or unrelated user scripts. Do not stop normal3000/8000 after publication; stop only the extra legacy fixture when finished. **NEXT ACTION: selective normal commit/push if outstanding, otherwise HOLD. No Phase12.**

## UX — approved Phase≤11 KISS website overhaul (2026-10-16)

User authorized this extension after R1 publication at `1f81b004`. Preserve all prior nodes/history; no Phase12. Work branch `work/trading-copilot-ux`; checkpoint `WORK_CHECKPOINT.md`. No main merge before final gates. Each node: bounded BUILD → targeted test → independent review → fix failed leaves → checkpoint/commit/push. Maximum two simultaneous agents; do not edit overlapping critical files. Audit only affected boundaries. Runtime truth overrides historical claims.

| Node / deps | Owner / skills | Acceptance and targeted verification |
|---|---|---|
| UX0 recovery/plan | Shepherd; plan-first-orchestrator, repository-audit | Existing git/history/checkpoint inspected, user changes preserved; initial DAG/checkpoint pushed BEFORE implementation. |
| UX1 shell, no deps | BUILD; frontend-ui-audit, accessibility-responsive-audit | Restrained coordinated dark/light palette, one collapsible sidebar, real global search, keyboard/mobile navigation. Own layout/App/styles only. Layout/theme tests + rendered Chromium review. |
| UX2 coverage/source contracts, no deps | BUILD then Provider Auditor; backend-api-audit, provenance-data-audit, timestamp-leakage-audit | Trace identity/history/earnings/management/insider sources to API for AAPL/MSFT/TMO/V/LLY; classify actual absence vs unsupported/auth/parser/refresh/mapping. Freeze truthful range, event, transaction and identity contracts; official free sources only. Offline fixtures and bounded gated live probes; no invented times/consensus/roles. Separate source audit before implementation. |
| UX3 core stock/chart, deps UX2 | BUILD; frontend-ui-audit, test-generation | Company/price/source/time, chart, next earnings and concise research first; watchlist/alert actions. Interactive responsive history with hover/tap and requested ranges only where supported; unsupported intraday explicit. Prefer compatible Lightweight Charts; API bars real, no fabricated history. Own StockPage + extracted stock components; targeted UI/range tests + actual browser. |
| UX4 research/events/insiders, deps UX2,UX3 | BUILD then Provider Auditor | Readable relevant deduplicated timeline and transaction tables; code/10b5-1/award/tax distinctions evidence-based; historical role not current claim. Management/filings/news accessible; raw details collapsed. Phase9 company≠stock and scenarios preserved without repeated filler. Fixture/classification tests + LLY real UI. |
| UX5 quant explanations, deps UX3 | BUILD; frontend-ui-audit, provenance-data-audit | Explanations match actual formulas and configured40/25/15/10/10 weights; hover/focus/tap accessible authoritative links, contributions/rank/freshness/nonprobability caveat. No scoring changes. Formula reconciliation tests + desktop/mobile interaction. |
| UX6 calendar/alerts, deps UX1,UX2 | BUILD; backend-api-audit, security-audit | One week/month/agenda calendar with filters + secondary safe ICS; date/session/time distinct. Plain alert above/below/change-up/down form, symbol-context links, honest manual-only capability. Existing persistence/evaluation/security preserved; CRUD/calendar tests + real browser. |
| UX7 dashboard/scanner/model boundary, deps UX1,UX3,UX5 | BUILD; frontend-ui-audit | Attention-first dashboard/scanner with sortable/filterable rows and explanations; ten-second primary-action check. Inspect requested separate ModelA artifacts read-only; inference only if saved artifact/feature/symbol/horizon/validation contract proven. Otherwise explicit unvalidated stock panel; no training or Phase12/13. |
| UX8 integrated gates, deps UX1–UX7 | Reviewer + Provider Auditor + Security Reviewer (max2 concurrently) | Actual normal browser→Vite→FastAPI→DB/providers; AAPL/MSFT/TMO/V/LLY desktop/mobile dark/light, all requested sections and interactions. Evidence/provenance/security checks, targeted failures fixed; ONE final backend/frontend/TS/build/lint/Chromium regression. No PASS with material findings. |
| UX9 publication, deps UX8 | Shepherd + independent handoff reviewer | Current START_HERE/PROJECT_STATUS/FULL_SYSTEM_AUDIT/checkpoint reconcile exact evidence/limits. Selective commit/push verified; only then normal main merge/push without force. No secrets/generated/private data. |

Initial plan published before implementation at `9d5cad96` on the working branch; remote SHA verified. UX1 BUILD and UX2 source audit dispatched with exclusive file ownership; neither is certified complete. Fresh baseline spot checks:4 backend settings/snapshot tests pass; real TMO browser/proxied health/search work with no uncaught errors. Existing skills are local untracked user content; do not blanket-add them. Portable task contracts above remain readable without those files. Routine work uses general BUILD/reviewer roles, not research agents. Parallelize UX1 and UX2 only initially; later stock-page nodes serialize to prevent shared-file conflicts.

### UX live checkpoint — source audit and first builds

- UX1 independent Reviewer `ses_eb9e44c41ffeXWVX11qb1KbF5I`: **PASS** on actual desktop1440/mobile390/320 light/dark, global search/history/stock navigation, one accessible collapsible nav, keyboard/focus/Escape, zero page errors/overflow.35 targeted tests and TypeScript passed. Source-owned files: App/layout/styles/new layout tests; no stock/provider edits. Nonblocking search-field/history polish was fixed and independently rechecked:10 shell tests and actual Back/Forward synchronization PASS, without overwriting typing on theme/stock navigation. **UX1 complete**, selective commit/push checkpoint follows; broader UX2–UX9 remain open.
- UX2 source audit complete, not provider acceptance: `UX_DATA_CONTRACT_AUDIT.md` preserves per-symbol observations, source URLs, precise proposed contracts, gaps and fixture/live-test plan. Official SEC identity is available for all5 symbols; current API gap is missing cache synchronization. V official feed verifies results2026-10-27 AMC; TMO official feed verifies a2026-10-21 call only. Keep source403s/stale feeds explicit, not absence claims.
- UX2 is split into bounded leaves: **UX2a identity** (active BUILD), **UX2b schedule/feed bridge**, **UX2c bars/range metadata**, **UX2d per-symbol category coverage**. Each requires targeted tests and provider review before acceptance. Stock/chart starts after its needed UX2c contract is frozen; no same-file parallel edits.
- No entire UX2 PASS until material coverage findings are resolved or documented as independently verified external/unsupported limits. Raw source audit/partial checkpoints can be safely published with accurate WIP labels; they are not completed product nodes.

### Interruption recovery — unfinished work preserved

Recovered from local/origin `e86624d6`; both interrupted BUILD sessions reported usage-limit errors. UX1 remains independently verified and published. UX2a has useful uncommitted identity implementation in main/website_data/sec_cik_map and a new focused identity test file; Python compilation and scoped whitespace checks pass, but interrupted test results and provider/reviewer acceptance are unconfirmed. UX3a added Lightweight Charts5.2.1 to package/lock only; **no chart component exists yet**. No3000/8000 listener survived at recovery. Preserve this exact source as a WIP checkpoint before continuing; never mark it PASS or rebuild existing identity work. See `WORK_CHECKPOINT.md` for next actions. Existing graph/dependencies unchanged; no Phase12/main merge.

Recovery WIP pushed/confirmed as `9855c4ba`. Normal stack restarted; all5 SEC names/exchanges render via real Vite/Chromium with prices preserved. Independent UX2a Provider Auditor `ses_eb90521aaffe4b3cjL2cs54B5R`: **FAIL** on malformed submissions cache isolation, explicit-refresh/read singleflight, arbitrary legacy cache source URL and inconsistent future retrieval provenance. Identity tests14pass/1timestamp-precision assertion failure;44 affected tests passed under network isolation. BUILD `ses_eb902b8f0ffeW04jb1XqViaZX7` fixes only failed leaves with regressions; UX3a component BUILD `ses_eb904fd10ffe86cKLJBrJVNbdB` runs independently. No node PASS until re-audit; max2 agents and original dependencies preserved.

UX3a BUILD component now complete locally: `components/stock/PriceHistoryChart.{tsx,test.tsx,css}`,11 focused tests/TS/scoped lint PASS. No StockPage integration or actual-canvas acceptance yet: publish portable **WIP**, then perform bounded UX3 integration and independent real-browser review. Disabled1D/ALL explain current daily-only/unknown-total-history limits; no fabricated ranges or live prices. Existing UX2c contract task remains required, not silently closed by component work.

UX3a component WIP published at `18e7390e`. UX3b then integrated it in StockPage with scoped CSS and improved company/price header, removing duplicate legacy history.34 targeted tests/TS/scoped lint PASS. Actual-canvas Reviewer `ses_eb8ff6435ffe0RH53KNvHUC0qe` is inspecting current real-origin desktop/mobile light/dark interactions; no final UX3 PASS yet. Integration is checkpointed as WIP while review and UX2 dependencies remain open.

UX3b integration WIP pushed at `0564696f`. UX2a failed-leaf BUILD completed malformed-cache isolation, singleflight refresh ownership, exact official provenance/schema/digest/timestamp checks and precision-safe test assertion;108 affected tests PASS with real HTTP/socket blocked. Source/regressions are checkpointed pending independent Provider Auditor recheck (`ses_eb90521aaffe4b3cjL2cs54B5R`) and dedicated security acceptance. PriorFAIL is not silently promoted toPASS; normal runtime restart remains required after source freeze.

UX2a fixes pushed `25d9ee13`; Provider+focusedReviewer recheck **PASS**:103 tests in its narrower scope and4 original reproductions. SecurityReviewer `ses_eb8fd976effedAPxYhwxPec5mr`: **PARTIAL**,88 tests PASS/source boundaries sound, inherited SEC transport `Retry-After` may request86400-second sleep. Bounded transport fix/regressions assigned to `ses_eb8fc41c3ffezxsOlCvvmgw0Dq`; security recheck and owned runtime restart still required. Counts are separate/overlapping evidence, not additive. UX2a and broaderUX2 remain unaccepted pending these gates.

UX3 actual-canvas Reviewer `ses_eb8ff6435ffe0RH53KNvHUC0qe`: **PARTIAL**. Verified all5 stocks and1W/1M/3M/1Y/5Y real requests/canvases; hover and mobile long-press/drag update date+close; keyboard/table access; independent headerprice; correct session labels across timezone; no overflow/pageerrors desktop/mobile light/dark.34 tests/TS/scoped lint PASS. Fix only acceptance gaps: technicalclutter/mobile hierarchy, coordinatedpalette, providerlink and touchguidance. BUILD `ses_eb8fb2b76ffe53k5ZJsP5zv7Qc` owns component/scopedCSS/tests; backend transport BUILD remains independent. No final UX3 PASS.

SEC transport retry-budget BUILD complete:30-second monotonic request/retry budget,5-second maximum permitted wait, excessiveRetryAfter rejected without premature retry, bounded lock acquisition/timeouts;84 focused offline tests PASS. Source/tests checkpointed pending SecurityReviewer recheck of its sole finding. No source/provider/UI acceptance is inferred from BUILD report alone; fresh normal backend restart remains required.

### UX2a identity — verified leaf PASS

Source through `e6371260` reviewed. Provider/focused Reviewer PASS:103 targeted tests +4 prior independent reproductions. Security recheck PASS:138 focused tests, including86400RetryAfter→one request/no sleep/sanitized rejection/unlocked transport. Separate overlapping scopes, not additive. Both previous failure nodes are resolved.

Owned canonical stack gracefully restarted after source freeze. Independent ProviderAuditor then verified20 direct/proxied detail/search GETs for all5 targets: officialSEC names/exchanges, consistent snapshot/retrieval/per-field evidence and independently sourced prices. Parent real Chromium verified all5 official company headings after restart with zero page errors. Evidence `/tmp/opencode/ux-identity-restarted-runtime.json`, `/tmp/opencode/ux-identity-final-browser.json`. **UX2a PASS only; full UX2 remains open** for schedules, bars metadata, category coverage and richer supported profile facts. Sector/description are not invented. Normal stack remains running.

Chart polish BUILD complete (38 targeted tests/TS/scoped lint PASS); actual-canvas Reviewer narrow recheck active. It is not yet an accepted chart leaf. Continue original graph; no main merge or Phase12.

### UX3 chart leaf — verified PASS (not full UX3)

Reviewer `ses_eb8ff6435ffe0RH53KNvHUC0qe` recheck PASS: technical/provider details collapsed with actual safeAlpaca link; coordinatedgreen/neutralpalette; touchguidance and keyboardfallback; horizontal mobiletabs/End reveal;320/390/1440 light/dark zero pageerrors/documentoverflow. Hover/touch update sessiondate+close, independent headerprice remains stable; prior5-symbol/all-range evidence retained.38 targeted chart/StockPage tests PASS, TS/scoped lint PASS. Mobilecanvas top improved to~807px320/~700px390; further overallstockinformation hierarchy remains part of broader UX work, not concealed by this leaf acceptance. E2E identity headings now assert actual returned companyname plus ticker, not stale ticker-onlyh1.

UX2a acceptance pushed/confirmed at `77393ab6`. Publish six chartpolish source/test paths plus checkpoint/docs, then continue existing UX2c and UX2b with disjoint file ownership. FullUX2 and fullUX3 remain open; no main merge/Phase12.

Chart acceptance source/checkpoint pushed and remote-confirmed at `21779ece`. Continuing existing leaves: UX2c BUILD `ses_eb8f6fd2dffepBMSrHyC4QoQ0R` owns bars/price metadata in website_data and main bars route/new tests. UX2b BUILD `ses_eb8f6ce9bffeK40m4zCDrcwgHl` owns website_sources/IR provider/new bounded parser/tests; it must not edit main.py until UX2c releases ownership. Scope: additive range facts/10-year span policy vs official explicit announcement ingestion. Both pending targeted verification/audits; neither PASS. Next-earnings projection/presentation is a serialized follow-up, not inferred from source ingestion alone.

UX2c BUILD finished:website_data additivebars/price metadata + main route doc +23 new offline tests.48 affected range/provenance tests and36 runtime-helper tests PASS (separate scopes). Ten-year span policy/returnedbounds/tailcap/truncation/unknown completeness preserve rawdaily/IEX/history freshness and originalretrieval. Provider/focused Reviewer `ses_eb8f4faceffeKewjY5twe6oja8` auditing source; not PASS yet. Publish source/tests as WIP pending review/security/runtime; main.py BUILD ownership released for later serialized projection task, not concurrent edits by current schedule BUILD.

UX2c source WIP pushed/confirmed `bf6d8b85`. Provider/focused review **PASS**:67 tests +4 independent providererror/pagination probes; Security **PASS**:23 tests +15 independent route/input probes. **Runtime gate pending**, not fullleafPASS: restart only after active website_sources startup edits stabilize. CurrentindependentBUILDs:UX2b schedule sources (`ses_eb8f6ce9bffeK40m4zCDrcwgHl`) and UX2d provider-only category quotas/per-symbol diagnostics (`ses_eb8f321abffeF0lRnEcaU5kltO`, filing_provider/newtests). No overlapping files; coveragewebsitewiring/projection remain later serialized integration. Existing graph retained.

UX2b source/ingestion BUILD finished:website_sources+IRprovider+newofficial_earnings_schedule parser/tests,71 targeted tests PASS. CorrectedV/TMOofficialfeeds,90dayschedulelookback separate7daynews, explicitAMC/callnotrelease semantics, evidence/revisions/idempotency and boundedlinkedbodyfetch. **Livegate SOURCE_FAILURE:both officialfeedGETs403**; no bypass or fixtures as live data. Provider/focused Reviewer `ses_eb8f20289ffewuaEvXaCTCPiBn` audits currentsource; dedicatedsecurityreview/APIprojection/liveacceptance still open. Checkpoint asWIP, notUX2bPASS. UX2dproviderBUILD remains independent; do not restart importedstartup sources mid-build.

UX2b WIP pushed/confirmed `a95c5428`. Independent Provider/focused audit **FAIL**:41 scoped tests pass but extra probes show obsolete schedules survive explicitcancellation/replacement, unrelateddividend/record dates and negated/conflicting text accepted, arbitrarycustom COMPANY_IRsources grantedofficialverification. BUILD `ses_eb8f0ea2affeUtcPtncLlKGKxD` fixes only failedleaves with evidence-preserving cancellation/revision/provenance regressions. Live403 is a separate source-limit gate; no implementationPASS or future-date claim. UX2dproviderBUILD remains disjoint.

UX2d provider-only BUILD done:filing_provider.py + newcategorycoverage tests,94 targeted tests PASS. Optionalcategory reservations prevent Form4crowding while preserving max_per_symbol/defaults/history; unused slots fall back to newest eligible, per-symbol/category coverage distinguishes checkedwindow/selection/success/errorstages. Provider/focused Reviewer `ses_eb8eff28effeqHIAo2T2APYb9j` auditing source. Publish asWIP, notfullUX2dPASS: website/APIwiring and independently verified runtime coverage remain futureintegration.

### UX2d provider-only leaf — PASS (not full UX2d)

Source `561cb62a` independently reviewed by `ses_eb8eff28effeqHIAo2T2APYb9j`:94 focused tests +209 in-memory quota/cap combinations, zeroquota fallback and parser-failure isolation probes PASS. Reservations/cap/defaults/history/amendments/revisions and window-scoped coverage truthful. Transport/parser share documentstage with exception types retained; no dedicatedauth stage. No currentleadership inference. **Website orchestration/per-symbol coverage API wiring remains open** and is not accepted by this provider verdict. Checkpoint/push this verified leaf; continue bounded UX2b projection after main.py bars ownership release, disjoint from parser fixes.

Provider-leaf acceptance pushed/confirmed `814c7e0c`. UX2b projection BUILD `ses_eb8ece09affeYNdxXdzmkO0w2w` now owns only new pure projection/tests + main.py stock-detail additions (bars edit ownership released). It must reject calls/cancelled/unverified/conflicting schedules and preserve raw date/session/time/provenance without GET-triggered network; per-symbol source coverage wiring/frontend remain later integration. Runs alongside parser/reconciliation fixes with no overlapping files; neither UX2b component is accepted yet.

UX2b failed-leaf BUILD finished84 targeted tests PASS: source cancellation/ambiguous revision nonactive, whole-document conflicts/dividend/record-date rejection, authenticated approvedfeed/response/entryorigins, explicitcrossdocreschedule+fiscalperiod/kind/order/noresurrection. Unprovable replacement relationships remain independent sourceclaims; projection must reject conflictingnextselection. Provider recheck `ses_eb8f20289ffewuaEvXaCTCPiBn` active; checkpoint asWIP, notsourcePASS/livePASS. **After projection releasesmain.py, freeze backend and perform owned restart + UX2c realruntime gate before any new website coverage edits.**

UX2b projection BUILD finished102 focused tests PASS (networkblocked), newpure earnings_projection/tests + additive stockdetail fields. NoGETrefresh, boundedrecordscan/capfailclosed, strictprovenance/conflict/cancellation/callfilters, rawcalendarprecision and duplicateevidence preserved. WIP pending independent audits; no livefuturedate claim. Both backend BUILDs released ownership; sourcefreeze for owned restart and UX2c realruntime gate. Providerrecheck and dedicatedfetch/projection SecurityReviewer read-only; do not launch more startup-source edits until runtimegate done.

### UX2c bars-range leaf — PASS

After sourcefreeze, ownedcanonicalstack restarted through `2635f936` (bars source `bf6d8b85`). ProviderReviewer independently verified16 direct8000/proxy3000 GETs: historical available/notwallclockstale, exacttail2+truncation/falsecompleteness, repeated originalretrieval, futureendclamp/current exclusion, oversized/inverted/intraday400, limit5001→422, header daily_session_label/is_livefalse independent. Parent actualChromium→Vite→normalFastAPI5Y query returned1254 bars/coverage_complete:null, unchangedheaderprice andzeroerrors. PriorProvider67tests+4errorprobes andSecurity23tests+15inputprobes remain valid separate/overlapping evidence. **UX2c PASS, notfullUX2.** Evidence `/tmp/opencode/ux-bars-frozen-{runtime,browser}.json`; currentnormal log `ux-bars-frozen-dev.log`.

### UX2b remaining failed nodes / current recovery

Financialrecheck105 scopedtests PASS but extra probes stillFAIL: contradictoryheadline/bodydates and supersededannouncement resurrection after unrelatedbody/hashchange. Security164tests PASS but twoextra probesFAIL: unsafecredentialURL retained by titlefallback/errorIDs and incompleteDNS/header/emptybody elapsed deadline. ConsolidatedBUILD `ses_eb8e7b0b8ffeen8zuv59Eav4J3` owns source/parser/IRfetch/tests only. Independentprojection Provider/focused Auditor `ses_eb8e7517fffeqSfIppKIMMV42n` owns readonlyprojection/main audit. Nofileoverlap, max2. Live403 remains separate; noearningsPASS. Finish/fix/re-audit only these nodes, checkpoint/push, then websitecoverage/frontendprojection integration. Preserve acceptedUX2a/UX2c/chart/providerquota leaves.

Projection audit `ses_eb8e7517fffeqSfIppKIMMV42n`: **FAIL**,101 focusedtests PASS,23 probes21PASS/2FAIL. Numeric fiscalquartermetadata treatedunknown causingfalseconflict acrossdistinctquarters; valid'after market closing'AMC sourcewording rejected. BUILD `ses_eb8e63302ffeh7cYZsd7NiQfyv` owns onlyprojection/helpertests to normalizequartervariants/preserveconflicts and alignsessionwordingwithoutclockinvention. Other source-boundary BUILD remainsdisjoint. Accept/checkpoint UX2c verifiedruntime leaf now; fullUX2b/UX2 stillopen, no mainmerge/Phase12.
