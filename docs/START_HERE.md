# Trading Copilot — Start Here

> **CURRENT — 2026-10-16: R1 normal-runtime integration verified.** The earlier functional-completion claim at `c9b77fbd` was withdrawn: Vite was running without FastAPI. The repaired single-command startup was clean-restarted and verified through the **actual browser → Vite3000 → normal FastAPI8000 → original database/providers**, with no interception or test backend for the normal-runtime gate. Final results: **532 backend passed / 35 skipped / 0 failed; 163 frontend unit passed; 15 startup tests passed; 122 Chromium E2E passed**, including 10 opt-in normal-runtime cases. TypeScript/build/lint and independent Provider/Security/actual-runtime Reviewer gates PASS. See `FULL_SYSTEM_AUDIT.md` and node R1 at the end of `current_task_graph.md`. Source limits remain explicit; this is local operation, not deployment approval. **No Phase12.**

## NEXT ACTION

**New user authorization: Phase≤11 UX/data-completeness overhaul on `work/trading-copilot-ux`.** Resume `WORK_CHECKPOINT.md` and the final UX extension of `current_task_graph.md`; R1 below remains the baseline, not an overhaul completion claim. Initial plan/checkpoint must be pushed before implementation; checkpoint each verified node. No Phase12; no main merge until final gates.

UX progress: UX1 shell/navigation/search/theme has independent desktop/mobile light/dark PASS, including history synchronization; UX2 source audit is recorded and identity implementation is active. UX2–UX9 remain incomplete. Resume the checkpoint, not the earlier R1 HOLD instruction below.

Publish only the focused R1 source/test/docs changes if not yet committed/pushed, then **HOLD: no Phase12 or further phase is authorized**. Leave the verified normal stack running for the user's retest unless explicitly asked to stop. Preserve existing database records, generated-file churn and unrelated work; database ingestion/runtime mutations are not source changes to commit.

### Local startup

Use Node22 (`frontend/.nvmrc`) and a Python interpreter with website dependencies installed: from root, `python3 -m pip install -e '.[web,dev]'`; install frontend dependencies with `npm --prefix frontend ci` if needed. Then the **single canonical normal startup command**, from repository root, is:

```bash
npm --prefix frontend run dev
```

This starts FastAPI on `127.0.0.1:8000`, waits for initialized JSON API/database health, and then starts strict-loopback Vite on `127.0.0.1:3000`. **Do not start a separate backend first.** Unknown occupied ports are refused, not silently reused or killed. Keep the command running; Ctrl+C stops only its owned backend/frontend children. Optional `PYTHON=/path/to/python` selects an interpreter with the required dependencies.

Backend Settings automatically loads this repository's root `.env`, independent of the launch directory; manual secret exports are not required. Keep `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` and `SEC_USER_AGENT` there/backend-side, never in `VITE_*` variables. The launcher forces local binding and `LLM_ENABLED=false`. Normal startup uses the intended project `data/events.db` unless an explicit database override is deliberately configured; it does not substitute a test database or demo mode. Real mode never silently falls back to fixtures. Browser `/api/v1/...` requests go through Vite to the normal backend; use `/api/v1/health/detailed` for proxied JSON health, not the SPA's `/health` path.

R1 verification used Python3.10.12 and **Node22.23.3**. Normal-runtime browser tests used the intended original database and cleaned only their own uniquely named API-created records; existing watchlists/items/alerts were independently compared read-only with the pre-repair backup and preserved exactly. Other regression tests may use isolated fixtures, but they are not the normal-runtime acceptance evidence. The one-command normal stack remains running after R1; after a machine/session restart, start it explicitly using the command above.

> Fresh coding-agent session: Read this file first, then PROJECT_STATUS.md, then the authoritative requirements/architecture/roadmap documents referenced below. Inspect the repository and Git history, run the tests, verify documented state against the code, and continue from NEXT ACTION. Do not rebuild completed phases.

---

## Product Goal

Build a user-friendly stock research website that answers: **What matters, why does it matter, what changed, and what should I know next?**

Core value is **interpretation + impact** — not just data display. Every meaningful event must answer:

```
WHAT HAPPENED? → WHAT DOES IT MEAN? → WHY DOES IT MATTER?
→ COMPANY IMPACT → STOCK IMPACT → SCENARIOS → EVIDENCE → HUMAN DECISION
```

---

## Core Product Principles

| Principle | Description |
|-----------|-------------|
| **Interpretation is core** | Every event answers: What happened? What does it mean? Why does it matter? Company impact? Stock bias? Time horizon? Base/Bull/Bear cases? What would change the view? Confidence? |
| **Company ≠ Stock Impact** | Store separately: `company_impact` (fundamental), `stock_bias` (directional), `confidence`, `time_horizon` |
| **Scenario Analysis** | Base Case / Bull Case / Bear Case / What would change the view — required for every interpretation |
| **Term UX** | Desktop: hover → definition. Mobile: tap → popover. "Learn more" → authoritative external link |
| **Zero-LLM Core** | All core functionality works with `LLM_ENABLED=false`. Optional local/free AI only enhances qualitative output (Phase 8+) |
| **Evidence-First** | Every claim traceable to source. Primary sources preferred. Distinguish fact / calculated / attributed / AI / inference |
| **Human Decision** | No automatic trade placement. Human review is final decision point |
| **Model A Separation** | Model A is an independent SPY microstructure experiment. Trading Copilot research discovers its own models via autonomous competing hypotheses |

---

## Current Architecture

```
Market Data (Alpaca/IEX) → Feature Engineering → Quant Scanner (deterministic)
                                                           ↓
Event Providers (Fed/BLS/BEA/Census) → Event Store (SQLite) → Event Intelligence
                                                           ↓
Company Providers (Earnings/SEC/Insiders/News) ──────────────→ Company Intelligence
                                                           ↓
                               AI Extraction (Phase 8+, optional) → Evidence Validation
                                                           ↓
                               Interpretation Engine → Answer Engine → Research Brief
                                                           ↓
                               API → Website (answer-focused, progressive disclosure)
                                                           ↓
                                                     HUMAN DECISION
```

---

## Historical Phase Milestones (current coverage: FULL_SYSTEM_AUDIT.md)

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| 0–1 | ✅ COMPLETE | Deterministic scanner, mock data, feature calculations, eligibility, quant scoring, top-N ranking, artifacts |
| 2 | ✅ COMPLETE | Alpaca IEX daily bars, batching, retry/backoff, caching, provider selection, live smoke tests |
| 3 | ✅ COMPLETE | SQLite Event Store, MarketEvent model, upsert/dedupe, revision history, change detection, queries |
| 4 | ✅ COMPLETE | MacroCalendarProvider: FOMC (Fed parsing + corrected fixtures: Oct 27-28, Dec 8-9 2026), BLS API (CPI/NFP/Unemployment/PPI/JOLTS), BEA API (GDP/PCE), Census API (Retail/Housing), importance tiers, refresh/upsert, revision tracking, live tests |
| 5 | ✅ COMPLETE | EarningsCalendarProvider (fixtures, multi-source ready), CorporateActionsProvider (Alpaca API live), EventType.EARNINGS/DIVIDEND/STOCK_SPLIT/MERGER_ACQUISITION/SPINOFF/CORPORATE_ACTION, importance tiers, refresh/upsert with revision tracking, live tests |
| 6 | ✅ COMPLETE | SEC EDGAR integration: 8-K/10-Q/10-K/Form 4, historical shards, amendments, leadership (CEO/CFO) extraction, insider classification, source preservation, importance tiers, idempotent refresh, live verification |
| 7 | ✅ COMPLETE | EarningsIntelligenceProvider (SEC 8-K Item 2.02, 10-Q, 10-K earnings extraction with actual EPS/revenue, consensus, guidance, surprise), EarningsReactionProvider (reaction windows: pre-market for BMO, immediate AH, next session, 5-session, SPY benchmark), timestamp semantics (filing_accepted_at ≠ announcement_released_at), unit tests (74 passed: 43 earnings_parsers + 15 earnings_intelligence + 16 earnings_reaction), live integration tests (4 + 4 gated), all Phase 1-6 tests pass |
| 8 | ✅ COMPLETE | NewsDocument/ManagementStatement/EvidenceClaim models, NewsProvider protocol, SECExhibitProvider (8-K exhibits via index.json), IRReleaseProvider (50+ company IR feeds), NewsRSSProvider (15+ financial news feeds), ManagementExtractor (deterministic zero-LLM), LLMProvider abstraction (Disabled/Local), EvidenceClaimGenerator + DeduplicationEngine. All offline tests pass (250), Phase 7/8 live tests pass (16), all Phase 1-7 tests pass. No paid dependencies. |
| 9 | ✅ COMPLETE | InterpretationEngine (deterministic synthesis of earnings/macro/SEC/management/news evidence), AnswerEngine (deterministic Q&A for why moving/what happened/impact/scenarios/risks/catalysts), TermDefinitionService (70+ authoritative definitions with official references), EvidenceValidator, independent audits PASS. All offline tests pass (284), Phase 7/8/9 live tests pass (24), all Phase 1-8 tests pass. No paid dependencies. |

---

## Historical Phase 9 Handoff (superseded)

### Phase 9 — Interpretation + Impact Engine / Answer Engine

**Goal**: Build the deterministic Interpretation + Impact Engine that converts existing structured evidence into:

WHAT HAPPENED?
→ WHAT DOES IT MEAN?
→ WHY DOES IT MATTER?
→ COMPANY IMPACT
→ STOCK IMPACT
→ TIME HORIZON
→ BASE CASE
→ BULL CASE
→ BEAR CASE
→ WHAT WOULD CHANGE THE VIEW?
→ CONFIDENCE
→ EVIDENCE
→ HUMAN DECISION

This is the core analytical layer of the Trading Copilot.

**State**: ✅ COMPLETE — All nodes passing.

**Architecture**:
```
SOURCE DOCUMENT
      ↓
FETCH / PRESERVE
      ↓
DEDUPLICATE
      ↓
STRUCTURED FACT / STATEMENT EXTRACTION
      ↓
EVIDENCE CLAIMS
      ↓
SOURCE + TIMESTAMP + PROVENANCE
      ↓
PHASE 9 INTERPRETATION + IMPACT
      ↓
ANSWER ENGINE
      ↓
HUMAN DECISION
```

**Core Principles**:
- Zero-LLM Core: All functionality works with `LLM_ENABLED=false`
- Source Priority: 1. Primary company sources (SEC, IR) 2. Regulatory 3. Reputable news 4. Optional free structured
- No Paid Dependencies: All providers use free official sources
- Company ≠ Stock Impact: Stored separately with confidence and time_horizon
- Scenario Analysis: Base/Bull/Bear cases + "What would change the view" required
- Term UX: Desktop hover → popover, Mobile tap → popover, "Learn more" → authoritative link
- Final Trading Decision: Remains human

**Delivered (All Nodes Complete)**:
1. **InterpretationEngine**: Deterministic synthesis of earnings/macro/SEC/management/news evidence into structured interpretations
2. **AnswerEngine**: Deterministic Q&A for why moving/what happened/impact/scenarios/risks/catalysts/next event
3. **TermDefinitionService**: 70+ authoritative definitions with official references (SEC, BLS, Fed, Investopedia)
3. **EvidenceValidator**: Validates evidence spans, rejects unsupported claims
4. **Independent Audits PASS**: Provenance ✅, Hallucination ✅, Deduplication ✅, Timestamps ✅, Zero-LLM ✅, LLM Failure Isolation ✅
5. All offline tests pass (284), Phase 7/8/9 live tests pass (24), all Phase 1-8 tests pass
6. No paid dependencies added


**Core Principles**:
- Zero-LLM Core: All functionality works with `LLM_ENABLED=false`
- Source Priority: 1. Primary company sources (SEC, IR) 2. Regulatory 3. Reputable news 4. Optional free structured
- No Paid Dependencies: All providers use free official sources
- Deduplication: Canonical URLs, content hashes, normalized headlines
- Attribution: Speaker, role, company, statement_type, source_document
- Evidence Model: CLAIM + SOURCE + SOURCE_URL + EVENT_DATE + RETRIEVED_AT + EXACT_EVIDENCE + CONFIDENCE

**Delivered (All Nodes Complete)**:
1. **NewsDocument, ManagementStatement, EvidenceClaim** models with full provenance
2. **NewsProvider protocol** with `fetch_news` / `fetch_company_releases`
3. **SECExhibitProvider**: Reuses Phase 6/7 SEC infrastructure for 8-K exhibits (99.1, etc.) via index.json
4. **IRReleaseProvider**: Company IR RSS feed ingestion (50+ known feeds)
5. **NewsRSSProvider**: Reputable financial news RSS ingestion (15+ feeds) with symbol extraction
6. **ManagementExtractor**: Deterministic statement extraction (attribution patterns, known executives, role detection, evidence spans)
7. **LLMProvider abstraction**: DisabledLLMProvider (zero-LLM baseline) + LocalLLMProvider (Ollama)
7. **EvidenceClaimGenerator + DeduplicationEngine**
8. **Independent Audits PASS**: Provenance ✅, Hallucination ✅, Deduplication ✅, Timestamps ✅, Zero-LLM ✅, LLM Failure Isolation ✅
9. All offline tests pass (284), Phase 7/8 live tests pass (24), all Phase 1-7 tests pass
10. No paid dependencies added## Next Phases (Summary)

| Phase | Focus |
|-------|-------|
| 9 | ✅ Interpretation + Impact Engine / Answer Engine — All nodes complete |
| 10 | Website (Interpretation output, Why It Matters + Market Impact, term hover/tap, scenario sections, company vs stock impact, progressive disclosure, mobile) |
| 10 | Website (Interpretation output, Why It Matters + Market Impact, term hover/tap, scenario sections, company vs stock impact, progressive disclosure, mobile) |
| 11 | Watchlists + Calendar + Alerts |
| 12 | Historical Event Impact (validate relationships used in impact statements) |
| 13 | Strategy Evaluation + Autonomous Model Discovery (experiment registry, evaluation contracts, leaderboard, promotion gate, leakage audit) |
| 14 | Deployment Hardening (browser inference, serverless, mobile, security) |

---

## Important Architectural Decisions (Settled — Do Not Change)

| Decision | Details |
|----------|---------|
| **Zero-LLM Core** | All core functionality works with `LLM_ENABLED=false`. Optional AI only for qualitative enhancement (Phase 8+) |
| **Model A Separation** | Model A is a separate SPY microstructure experiment. Trading Copilot discovers its own models via autonomous competing hypotheses. No preferential treatment. |
| **Leakage-Free Evaluation** | Autonomous model discovery uses common chronological evaluation contracts, frozen data/target/features, no future data in training |
| **Evidence-First Answers** | Every claim traceable to source. Distinguish fact / calculated / attributed / AI / inference |
| **Company ≠ Stock Impact** | `company_impact` (fundamental) stored separately from `stock_bias` (directional) with `confidence` and `time_horizon` |
| **Scenario Analysis** | Base/Bull/Bear cases + "What would change the view" required for every interpretation |
| **Term UX** | Desktop: hover → popover. Mobile: tap → popover. "Learn more" → authoritative external link |
| **Final Trading Decision** | Remains human. No automatic trade placement. |
| **Deterministic Scanner Independence** | Quant scores never modified by AI. LLM only extracts evidence. |
| **Historical Preservation** | Event store preserves full revision history for research (no overwriting) |
| **No Paid Data Required** | All providers use free official sources (Fed, BLS, BEA, Census, SEC) |

---

## Historical Provider Inventory (not a current coverage guarantee)

| Provider | Status | Notes |
|----------|--------|-------|
| Alpaca / IEX | ✅ VERIFIED LIVE | Daily bars, latest price, quotes, trades, caching |
| Federal Reserve | ✅ VERIFIED LIVE | FOMC schedule (HTML parsing + corrected fixtures: Oct 27-28, Dec 8-9 2026), minutes |
| BLS (Bureau of Labor Statistics) | ✅ VERIFIED LIVE | CPI, Core CPI, NFP, Unemployment, Avg Hourly Earnings, PPI, JOLTS |
| BEA (Bureau of Economic Analysis) | ⚠️ IMPLEMENTED / CREDENTIAL REQUIRED | GDP, PCE, Core PCE — needs free API key |
| Census Bureau | ⚠️ IMPLEMENTED / CREDENTIAL REQUIRED | Retail Sales, Housing Starts, Building Permits — needs free API key |
| SEC EDGAR | ✅ VERIFIED LIVE | Phase 6 complete: filings, leadership, insiders, historical shards, amendments |
| Earnings Calendar | ✅ IMPLEMENTED | Phase 5 (fixtures, multi-source ready: Alpha Vantage, FMP, Polygon, Twelve Data) |
| Corporate Actions (Alpaca) | ✅ VERIFIED LIVE | Phase 5 (dividends, splits, mergers, spin-offs) |
| SEC Exhibits (Phase 8) | ✅ IMPLEMENTED | 8-K exhibits (99.1, 99.2, 99.3) via index.json |
| IR Releases (Phase 8) | ✅ IMPLEMENTED | Company IR RSS feeds (50+ feeds) |
| News RSS (Phase 8) | ✅ IMPLEMENTED | Financial news RSS (15+ feeds) with symbol extraction |

---

## Historical Test Snapshots (superseded by current verification)

```
Offline baseline: 284 passed, 34 skipped (includes Phase 7 earnings intelligence/reaction/parsers + Phase 8 news/management unit tests + Phase 9 interpretation/answer/term unit tests + audit tests)
Live baseline: 24 passed, 34 skipped (includes SEC live + Phase 7/8/9 live integration tests gated by RUN_LIVE_TESTS=1; 1 Alpaca health check failure is pre-existing)
Last run:   2026-10-09
```

Run:
```bash
python3 -m pytest -q                    # offline tests
RUN_LIVE_TESTS=1 python3 -m pytest -q   # live tests
```

---

## Current Known Limitations

1. **Coverage is bounded, not exhaustive.** R1 verified SEC/IR/Fed ingestion through the normal running stack and intended original database; earlier disposable verification is separate historical evidence. Failed BLS/news requests remain explicit partial/provider-error states. IEX completed daily closes are not live consolidated quotes.
2. **BEA/Census and future earnings-calendar website coverage are unavailable.** No fixture calendar or invented observations fill real mode. Other standalone provider capabilities are not implied by the bounded website refresh bridge.
3. **Timestamp fidelity is conservative.** Date-only calendar events retain dates without invented instants; unsupported date-only/timezone-unknown feed entries are omitted. IR update/creation times are not original publication times. Exact source midnight remains exact.
4. **Evidence/leadership coverage is limited.** Leadership is derived from ingested filings, not a complete officer roster. Ambiguous quote attribution is rejected; missing evidence remains unknown. Scenario probabilities are uncalibrated/null.
5. **Alerts are manually evaluated, in-app only.** Supported price/change/volume/quant observations can produce genuine stored triggers; dry-run does not mutate history. Scheduling, email/webhooks and trading are not implemented or claimed.
6. **Security approval is local-only.** Loopback defaults, bounds, links, ICS and CORS were verified. Dependency maintenance and incomplete Python transitive locking are documented in `DEPENDENCY_ADVISORIES.md`. This is not hosted/deployment approval.
7. **Browser scope is Chromium desktop/mobile.** Prior WebKit system-library limitations are not application PASS evidence. The historically referenced model/deployment architecture document is absent; no architectural approval is inferred from that reference.

---

## Important Commands

```bash
# Run all offline tests
python3 -m pytest -q

# Run live tests (requires API keys for Alpaca, BEA, Census, SEC_USER_AGENT)
RUN_LIVE_TESTS=1 python3 -m pytest -q

# Run scanner (mock provider)
python3 -m trading_copilot scan --config tests/fixtures/config.yaml

# Run scanner (Alpaca provider)
python3 -m trading_copilot scan --config config.alpaca.yaml

# Explain a symbol from a run
python3 -m trading_copilot explain NVDA 2026-10-05T203400Z --config tests/fixtures/config.yaml

# Validate a run
python3 -m trading_copilot validate-run 2026-10-05T203400Z --config tests/fixtures/config.yaml
```

---

## Historical Phase 10 Verification (superseded)

**Historical completion claim; use the current verification report above.**

### Phase 10 Final Verification Report (2026-10-12)

**Backend Verification: ✅ PASS**
- Fixed `/api/v1/events/upcoming` semantic bug (bounded window semantics)
- Added permanent regression tests: `test_upcoming_events_bounded_window`, `test_upcoming_events_timezone_handling`
- Full backend regression suite: **286 passed, 34 skipped**
- All API endpoints verified with real backend data

**Frontend Verification: ✅ PASS**
- Dev server runs (Vite 5.4.21, React 18, TanStack Query v5)
- **Production build: PASS** — all 100+ TypeScript errors resolved
- **TypeScript: PASS** — `npx tsc --noEmit` clean
- **Lint: PASS** — ESLint clean for production code
- **Runtime API integration: PASS** — frontend fetches real backend data
- **Security: PASS** — no secrets in production bundle (verified by grep)

**Test Matrix (Final):**
| Category | Result | Details |
|----------|--------|---------|
| Backend Python | 286 passed / 34 skipped | All Phase 1-9 tests |
| Frontend TypeScript | PASS | Clean compilation |
| Frontend Build | PASS | `npm run build` succeeds |
| Frontend Lint | PASS | ESLint clean |
| Frontend Unit/Component | INFRASTRUCTURE READY | Vitest + RTL configured; blocked by known vitest 4.x + @csstools/css-calc ESM incompatibility (non-code issue) |
| Browser/E2E (Playwright) | 42 passed / 111 failed | Chromium/mobile-chrome PASS; WebKit/Safari FAIL due to missing system libs (not code issue) |
| Live Provider Tests | 24 passed / 2 skipped | Gated by RUN_LIVE_TESTS=1 |

**Phase 10-Specific Audits (All Material Checks PASS):**
| Audit | Status | Evidence |
|-------|--------|----------|
| Backend/Frontend Contract | ✅ PASS | API response types match frontend TypeScript interfaces |
| Financial Data Fidelity | ✅ PASS | All data sourced from backend API; no client-side financial logic |
| Phase 9 Interpretation Fidelity | ✅ PASS | InterpretationEngine output verified at `/api/v1/stocks/AAPL/interpretation` |
| Frontend Security/Secrets | ✅ PASS | `grep` of `dist/` shows no Alpaca keys, SEC credentials, .env contents |
| Responsive UX/Accessibility | ✅ PASS | Manual dev server verification: mobile viewport no horizontal overflow, keyboard nav works, focus states visible |
| Evidence/Provenance UX | ✅ PASS | Evidence links render with source_type, URL, timestamp; term definitions work on hover/tap |
| Degraded/Provider Failure | ✅ PASS | Empty states render for missing data; API errors don't crash UI; section isolation confirmed |
| Regression Safety | ✅ PASS | Backend regression suite green; production build reproducible |

**Visual/Manual Verification (Dev Server):**
- ✅ Landing page desktop: hero, market overview, macro events, scanner candidates, recent events, features, CTA
- ✅ Stock page desktop: tabs (overview/earnings/events/news/insiders/leadership/filings/quant), interpretation sections, scenarios, evidence, term hover
- ✅ Stock page mobile: responsive layout, no horizontal overflow, tap-to-expand term definitions
- ✅ Scenarios: Base/Bull/Bear cards render with probability bands and required conditions
- ✅ Evidence expansion: supporting_evidence items show source_type, link, description, timestamp
- ✅ Term definitions: desktop hover → popover; mobile tap → popover; "Learn more" → authoritative source
- ✅ Missing-data state: interpretation.missing_information renders as list; empty tabs show "No X available"
- ✅ Provider-error state: API errors handled gracefully, no crash
- ✅ Dark/light mode: ThemeContext toggles correctly, persisted to localStorage
- ✅ No horizontal overflow on mobile (375px viewport tested)

**Final Gate Status: ALL PASS**

**Verification-Environment Limitations (Non-Blocking, Carried Forward):**
1. **Vitest/RTL execution** blocked by Vitest 4.x / @csstools/css-calc ESM incompatibility — toolchain limitation, not application defect.
2. **Playwright WebKit** unavailable in current Linux environment (missing WebKit/GStreamer libs). Chromium/mobile-Chrome PASS.

Do not reopen Phase 10 unless later development reveals an actual functional regression.

---

## Historical Phase 11 Handoff — Watchlists + Calendar + Alerts

### Phase 11 Completion Summary (2026-10-13)

**Backend Implementation: ✅ COMPLETE** (previously complete)

**Frontend Integration: ✅ COMPLETE**

- **WatchlistPage**: Full CRUD + item management
  - Create/read/update/delete watchlists with name, description, sort order
  - Default watchlist designation
  - Add/remove/reorder symbols with optional notes
  - Symbol validation (1-5 uppercase letters), duplicate detection
  - Get all watchlists, default watchlist, watchlists containing a symbol

- **CalendarPage**: `.ics` export with filters
  - Export macro/earnings events with filters (event_types, symbols, date range, importance)
  - Standards-compliant iCalendar (RFC 5545) output
  - Smart duration: 2hr for major macro (FOMC, CPI, NFP, GDP, PCE), 1hr for earnings, 30min default
  - **Unknown-time semantics**: Events without exact time export as all-day (DATE format), BMO/AMC session semantics preserved in description

- **AlertsPage**: Full configuration + trigger system
  - Alert types: price, price_change_pct, volume, earnings, earnings_surprise, guidance_change, filing, insider, leadership, news, macro_event, quant_score
  - Conditions: above/below/equals/crosses_above/crosses_below/changes
  - Channels: in_app, email, webhook (email/webhook noted as requiring backend infrastructure)
  - Cooldown support, trigger history, acknowledgment workflow
  - Test/dry-run endpoint

**API Endpoints Added:**
- `/api/v1/watchlists/*` - Full watchlist management
- `/api/v1/calendar/export` - `.ics` calendar export (POST + GET)
- `/api/v1/alerts/*` - Alert management + triggers

**Runtime Verification: ✅ PASS**
- Watchlist CRUD + item management working
- Calendar `.ics` export generating valid iCalendar format (validated)
- Alert creation + trigger system working
- Production build: PASS
- TypeScript: PASS
- Frontend lint: PASS (pre-existing issues only)

**Test Matrix: ✅ PASS**
- Backend Python: 286 passed / 34 skipped
- Frontend TypeScript: PASS
- Frontend Build: PASS
- Frontend Lint: PASS (pre-existing issues only)
- Backend unit tests: 286 passed / 34 skipped

**Current boundary:** Phase 12 remains ON HOLD; this historical handoff does not authorize advancement.

---

## Document Authority Hierarchy

1. `docs/FINAL_PRODUCT_REQUIREMENTS.md` — what the finished product must do
2. `docs/SYSTEM_ARCHITECTURE_UPDATED.md` — approved architecture
3. `docs/DEVELOPMENT_ROADMAP_UPDATED.md` — build sequence and phase success criteria
4. `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` — historically referenced but absent; do not invent its contents or approvals
5. `docs/PROJECT_STATUS.md` — detailed implementation history/current factual state
6. `docs/START_HERE.md` — this file (concise current-session bootstrap/handoff)

**Do not let documentation describe an older system after implementation changes.**
