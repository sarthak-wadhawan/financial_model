# Trading Copilot — Start Here

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

## Completed Phases

| Phase | Status | Key Deliverables |
|-------|--------|------------------|
| 0–1 | ✅ COMPLETE | Deterministic scanner, mock data, feature calculations, eligibility, quant scoring, top-N ranking, artifacts |
| 2 | ✅ COMPLETE | Alpaca IEX daily bars, batching, retry/backoff, caching, provider selection, live smoke tests |
| 3 | ✅ COMPLETE | SQLite Event Store, MarketEvent model, upsert/dedupe, revision history, change detection, queries |
| 4 | ✅ COMPLETE | MacroCalendarProvider: FOMC (Fed parsing + corrected fixtures: Oct 27-28, Dec 8-9 2026), BLS API (CPI/NFP/Unemployment/PPI/JOLTS), BEA API (GDP/PCE), Census API (Retail/Housing), importance tiers, refresh/upsert, revision tracking, live tests |
| 5 | ✅ COMPLETE | EarningsCalendarProvider (fixtures, multi-source ready), CorporateActionsProvider (Alpaca API live), EventType.EARNINGS/DIVIDEND/STOCK_SPLIT/MERGER_ACQUISITION/SPINOFF/CORPORATE_ACTION, importance tiers, refresh/upsert with revision tracking, live tests |
| 6 | ✅ COMPLETE | SEC EDGAR integration: 8-K/10-Q/10-K/Form 4, historical shards, amendments, leadership (CEO/CFO) extraction, insider classification, source preservation, importance tiers, idempotent refresh, live verification |
| 7 | ✅ COMPLETE | EarningsIntelligenceProvider (SEC 8-K Item 2.02, 10-Q, 10-K earnings extraction with actual EPS/revenue, consensus, guidance, surprise), EarningsReactionProvider (reaction windows: pre-market for BMO, immediate AH, next session, 5-session, SPY benchmark), timestamp semantics (filing_accepted_at ≠ announcement_released_at), unit tests (74 passed: 43 earnings_parsers + 15 earnings_intelligence + 16 earnings_reaction), live integration tests (4 + 4 gated), all Phase 1-6 tests pass |

---

## Current Phase

### Phase 7 — Earnings Intelligence + Reaction History

**Goal**: Extract, normalize, and store historical earnings results (actual EPS/revenue, consensus estimates, guidance) with full provenance. Measure and preserve raw market behavior around earnings events across multiple time windows without interpretation.

**State**: ✅ COMPLETE. EarningsIntelligenceProvider extracts EPS/revenue actuals, consensus, guidance from SEC 8-K Item 2.02, 10-Q, 10-K filings. EarningsReactionProvider computes reaction windows (pre-market for BMO, immediate AH for AMC, next session, 5-session, SPY benchmark) using Alpaca IEX market data, anchored to released_at (actual earnings release timestamp). Timestamp semantics corrected: filing_accepted_at (SEC acceptance) tracked separately from announcement_released_at (actual earnings release) with release_time_source and release_time_precision fields. All unit tests pass (74), live integration tests created (8), all existing Phase 1-6 tests pass (231 total).

**Architecture**:
- Phase 7 = RAW EARNINGS RESULTS/GUIDANCE/REACTION EVENT INGESTION ONLY
- Phase 9 = INTERPRETATION ENGINE (computes company_impact, stock_bias, scenarios, confidence, time_horizon)
- Do NOT populate `company_impact`, `stock_bias`, `base_case`, `bull_case`, `bear_case`, `confidence`, `time_horizon` in Phase 7

**Must Preserve for Phase 9**:
- Earnings Results: fiscal quarter/year, EPS/revenue actual/consensus, surprise, report date/time, source document
- Guidance: type, period, EPS/revenue ranges, change classification (raised/lowered/maintained/new)
- Reactions: symbol, report_time, windows (pre_market, immediate_ah, next_session, session_5) with open/close/change_pct/volume, SPY benchmark
- All with provenance: source, source_url, source_id, retrieved_at, market_data_retrieved_at, calculated_at

**Delivered**:
1. EarningsIntelligenceProvider (SEC EDGAR earnings extraction with full provenance)
2. EarningsReactionProvider (market data reaction windows, lookahead-safe)
3. Earnings parsers (deterministic extraction, no invented values)
4. Three new event types: EARNINGS_RESULT, EARNINGS_GUIDANCE, EARNINGS_REACTION
5. Timestamp semantics: filing_accepted_at ≠ announcement_released_at ≠ scheduled_at
6. Unit tests: 43 earnings_parsers + 15 earnings_intelligence + 16 earnings_reaction = 74
7. Live integration tests: 4 earnings_intelligence + 4 earnings_reaction (gated by RUN_LIVE_TESTS=1)
8. Full regression: 231 passed, 19 skipped

---

## Next Phases (Summary)

| Phase | Focus |
|-------|-------|
| 7 | ✅ Earnings Intelligence + Reaction History (EPS/revenue, guidance, reaction windows, surprise, scenario inputs) |
| 8 | News + Management Analysis (structured AI extraction, source-backed catalyst/risk claims, evidence for interpretation engine) |
| 9 | **Interpretation + Impact Engine / Answer Engine** (What happened? What does it mean? Why does it matter? Company impact? Stock bias? Time horizon? Scenarios? Term definitions. Zero-LLM Core) |
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

## Data Providers

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
| News/Management | 🔄 PROVIDER PENDING | Phase 8 |

---

## Tests

```
Offline baseline: 231 passed, 27 skipped (includes Phase 7 earnings intelligence/reaction/parsers unit tests)
Live baseline: 257 passed, 27 skipped (includes SEC live + Phase 7 live integration tests gated by RUN_LIVE_TESTS=1; 1 Alpaca health check failure is pre-existing)
Last run:   2026-10-07
```

Run:
```bash
python3 -m pytest -q                    # offline tests
RUN_LIVE_TESTS=1 python3 -m pytest -q   # live tests
```

---

## Current Known Limitations

1. **BEA/Census APIs require free registration keys** — implemented but need keys for live tests
2. **Fed FOMC HTML parsing** — unreliable for upcoming meetings; uses fixtures for current year
3. **ISM/Conference Board/UMich/Industrial Production** — marked PROVIDER_PENDING (no reliable free API)
4. **SEC live ingestion** — requires genuine operator SEC_USER_AGENT; no API key needed
5. **Leadership coverage** — evidence-derived only; unparsed announcements remain unknown (Phase 9)
6. **No AI/evidence/answer engine yet** — Phase 8-9
7. **No website/frontend yet** — Phase 10

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

## NEXT ACTION

**Proceed to Phase 8 — News + Management Analysis** according to `docs/DEVELOPMENT_ROADMAP_UPDATED.md`.

Phase 7 complete with all nodes passing:
- Node A: Event/Data Contracts ✅ (timestamp semantics, provenance fields)
- Node B: EarningsIntelligenceProvider ✅ (SEC 8-K/10-Q/10-K earnings extraction)
- Node C: EarningsReactionProvider ✅ (reaction windows with Alpaca IEX)
- Node D: Offline Fixtures/Tests ✅ (74 unit tests passing)
- Node E: Live Integration Tests ✅ (8 live tests created, gated by RUN_LIVE_TESTS=1)
- Node F: Independent Audits — to be completed
- Node G: Integration + Docs + Commit/Push — to be completed

Key decisions implemented:
- SEC filing accepted_at != earnings announcement released_at (tracked separately: filing_accepted_at, announcement_released_at, release_time_source, release_time_precision)
- Reaction windows anchored to released_at, not scheduled_at
- Lookahead-safe: windows have explicit end boundaries
- Raw measurements only, no interpretation
- Missing consensus/guidance remain null (never interpolated)

---

## Document Authority Hierarchy

1. `docs/FINAL_PRODUCT_REQUIREMENTS.md` — what the finished product must do
2. `docs/SYSTEM_ARCHITECTURE_UPDATED.md` — approved architecture
3. `docs/DEVELOPMENT_ROADMAP_UPDATED.md` — build sequence and phase success criteria
4. `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` — model research, LLM policy, browser/serverless deployment
5. `docs/PROJECT_STATUS.md` — detailed implementation history/current factual state
6. `docs/START_HERE.md` — this file (concise current-session bootstrap/handoff)

**Do not let documentation describe an older system after implementation changes.**