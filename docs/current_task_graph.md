# Phase 11 + Full System Re-Audit — Task Graph

## Phase 11 Frontend Integration (PART A)

### Node A1 — Watchlist Frontend
**Dependencies:** None (can start immediately)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** PENDING
**Tests:** Component tests, E2E tests
**Files to create/modify:**
- `frontend/src/pages/WatchlistPage.tsx` (new)
- `frontend/src/components/watchlist/WatchlistList.tsx` (new)
- `frontend/src/components/watchlist/WatchlistItem.tsx` (new)
- `frontend/src/components/watchlist/AddWatchlistModal.tsx` (new)
- `frontend/src/components/watchlist/AddSymbolModal.tsx` (new)
- `frontend/src/services/api.ts` (add watchlist/calendar/alert types and methods)
- `frontend/src/App.tsx` (add routes)
- `frontend/src/components/layout/Sidebar.tsx` (add watchlist/calendar/alert nav items)
- `frontend/src/pages/StockPage.tsx` (add "Add to Watchlist" button)

**Deliverables:**
- Watchlist page with list, create, edit, delete
- Add/remove/reorder symbols with notes
- Default watchlist designation
- "Add to Watchlist" button on stock page
- Show watchlists containing current stock

---

### Node A2 — Calendar Frontend
**Dependencies:** A1 (shared API types in api.ts)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** PENDING
**Files to create/modify:**
- `frontend/src/pages/CalendarPage.tsx` (new)
- `frontend/src/components/calendar/CalendarExportButton.tsx` (new)
- `frontend/src/components/calendar/CalendarExportModal.tsx` (new)
- `frontend/src/services/api.ts` (calendar export types/methods)
- `frontend/src/App.tsx` (add route)
- `frontend/src/components/layout/Sidebar.tsx` (add calendar nav)
- `frontend/src/pages/MacroCalendarPage.tsx` (add export button)
- `frontend/src/pages/StockPage.tsx` (add export for earnings/events)

**Deliverables:**
- Calendar page with export button
- Export modal with filters (event types, symbols, date range, importance)
- Valid .ics file download
- Export buttons on macro calendar, stock page earnings/events sections

---

### Node A3 — Alert Frontend
**Dependencies:** A1, A2 (shared API types)
**Role:** Frontend implementation
**Model:** Lightning/Big Pickle
**Status:** PENDING
**Files to create/modify:**
- `frontend/src/pages/AlertsPage.tsx` (new)
- `frontend/src/components/alert/AlertList.tsx` (new)
- `frontend/src/components/alert/AlertForm.tsx` (new)
- `frontend/src/components/alert/AlertTriggerHistory.tsx` (new)
- `frontend/src/services/api.ts` (alert types/methods)
- `frontend/src/App.tsx` (add route)
- `frontend/src/components/layout/Sidebar.tsx` (add alerts nav)
- `frontend/src/pages/StockPage.tsx` (add "Create Alert" button)

**Deliverables:**
- Alerts page with list, create, edit, delete
- Alert form with all types, conditions, channels
- Dry-run/test button
- Trigger history with acknowledgment
- Activate/deactivate toggle
- "Create Alert" button on stock page

---

### Node A4 — API/State Integration
**Dependencies:** A1, A2, A3
**Role:** Integration
**Model:** Lightning
**Status:** PENDING
**Files to create/modify:**
- `frontend/src/hooks/useWatchlists.ts` (new)
- `frontend/src/hooks/useAlerts.ts` (new)
- `frontend/src/hooks/useCalendar.ts` (new)
- `frontend/src/context/WatchlistContext.tsx` (new, optional)
- `frontend/src/context/AlertContext.tsx` (new, optional)

**Deliverables:**
- React Query hooks for all Phase 11 endpoints
- Optimistic updates for mutations
- Shared state management if needed

---

### Node A5 — Backend Phase 11 Tests
**Dependencies:** None (backend already complete)
**Role:** Backend testing
**Model:** Lightning
**Status:** PENDING
**Files to create/modify:**
- `tests/unit/test_watchlists.py` (new)
- `tests/unit/test_calendar.py` (new)
- `tests/unit/test_alerts.py` (new)

**Deliverables:**
- Unit tests for watchlist CRUD + items
- Unit tests for calendar .ics export
- Unit tests for alert configuration + triggers

---

### Node A6 — Frontend Tests
**Dependencies:** A1, A2, A3, A4
**Role:** Frontend testing
**Model:** Lightning
**Status:** PENDING
**Files to create/modify:**
- `frontend/src/pages/WatchlistPage.test.tsx` (new)
- `frontend/src/pages/CalendarPage.test.tsx` (new)
- `frontend/src/pages/AlertsPage.test.tsx` (new)
- `frontend/src/components/watchlist/*.test.tsx` (new)
- `frontend/src/components/alert/*.test.tsx` (new)

**Deliverables:**
- Component tests for watchlist/calendar/alert components
- Integration tests for user workflows

---

### Node A7 — Browser/E2E Verification
**Dependencies:** A1, A2, A3, A4, A6
**Role:** E2E testing
**Model:** Lightning
**Status:** PENDING
**Files to create/modify:**
- `frontend/src/test/e2e/watchlist.spec.ts` (new)
- `frontend/src/test/e2e/calendar.spec.ts` (new)
- `frontend/src/test/e2e/alert.spec.ts` (new)
- `frontend/playwright.config.ts` (verify config)

**Deliverables:**
- Playwright tests covering core user workflow
- Chromium desktop + mobile verification

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
**Status:** PENDING
**Tasks:**
- Verify complete user workflow: Watchlist → Stock → Alert → Calendar → Trigger History
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
**Status:** PENDING
**Files to update:**
- `docs/START_HERE.md`
- `docs/PROJECT_STATUS.md`
- `docs/DEVELOPMENT_ROADMAP_UPDATED.md` (if needed)

---

### Node A12 — Commit/Push
**Dependencies:** A11
**Role:** Release
**Model:** Ultra
**Status:** PENDING
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
**Status:** PENDING
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

### Phase 11 (PART A) — Parallelizable Groups:
**Group 1 (Independent):** A1, A5
**Group 2 (After A1):** A2, A3
**Group 3 (After A1, A2, A3):** A4
**Group 4 (After A1, A2, A3, A4):** A6
**Group 5 (After A1-A4, A6):** A7
**Group 6 (After A1-A7):** A8
**Group 7 (After A8):** A9
**Group 8 (After A9):** A10
**Group 9 (After A10):** A11
**Group 10 (After A11):** A12

### PART B — Sequential (mostly):
B1 → B2-B5 (parallel) → B6 → B7-B9 (parallel) → B10 → B11 → B12 → B13 → B14 → B15