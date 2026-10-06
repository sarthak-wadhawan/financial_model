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

---

## Current Phase

### Phase 5 — Company Calendar / Corporate Events

**Goal**: Implement earnings calendar, dividends, splits, corporate actions, investor events. Preserve structured FACTS and EVIDENCE for downstream Phase 9 Interpretation Engine.

**State**: Not started.

**Architecture**:
- Phase 5 = RAW EVENT/EVIDENCE INGESTION ONLY
- Phase 9 = INTERPRETATION ENGINE (computes company_impact, stock_bias, scenarios, confidence, time_horizon)
- Do NOT populate `company_impact`, `stock_bias`, `base_case`, `bull_case`, `bear_case`, `confidence`, `time_horizon` in Phase 5

**Must Preserve for Phase 9**:
- Earnings: date/time/timezone, EPS actual/consensus, revenue actual/consensus, guidance, management commentary source
- Dividends: ex-dividend date, payment date, amount, type
- Splits: ratio, effective date
- Corporate actions: type, terms, dates, source documents
- Investor events: date, type, presentation materials
- All with provenance: source, source_url, source_id, retrieved_at

**Next Actions**:
1. EarningsCalendarProvider (dates, times, timezone)
2. Dividend/ex-dividend tracking
3. Stock split events
4. Corporate actions (M&A, spin-offs)
5. Investor events
6. Importance tiers per event type
7. Refresh behavior: load → fetch → compare → upsert
8. Unit tests with mock responses
9. Live test gated by `RUN_LIVE_TESTS=1`

---

## Next Phases (Summary)

| Phase | Focus |
|-------|-------|
| 6 | SEC + Leadership + Insider Intelligence (EDGAR, 8-K/10-Q/10-K/Form 4, CEO/CFO, leadership changes, insider classification) |
| 7 | Earnings Intelligence + Reaction History (EPS/revenue, guidance, commentary, reaction windows, surprise, scenario inputs) |
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
| SEC EDGAR | 🔄 PROVIDER PENDING | Phase 6 |
| Earnings Calendar | 🔄 PROVIDER PENDING | Phase 5 |
| News/Management | 🔄 PROVIDER PENDING | Phase 8 |

---

## Tests

```
Offline:    92 passed (10 features, 10 eligibility, 10 quant, 18 Alpaca, 24 events, 18 macro calendar, 2 BLS fixture)
Live:       8 passed (Fed FOMC parsing, BLS CPI/NFP/Unemployment, refresh current year)
Skipped:    12 (4 Alpaca + 8 macro when RUN_LIVE_TESTS not set)
Last run:   2026-10-06
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
3. **No earnings/dividend/split/insider/SEC data yet** — Phase 5-6
4. **No AI/evidence/answer engine yet** — Phase 8-9
5. **No website/frontend yet** — Phase 10

---

## Important Commands

```bash
# Run all offline tests
python3 -m pytest -q

# Run live tests (requires API keys for Alpaca, BEA, Census)
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

**Implement Phase 5 — Company Calendar / Corporate Events** according to `docs/DEVELOPMENT_ROADMAP_UPDATED.md`.

Start with `EarningsCalendarProvider` for earnings dates/times/timezone, then dividend/ex-dividend, splits, corporate actions, investor events. Preserve structured fields for downstream interpretation engine.

---

## Document Authority Hierarchy

1. `docs/FINAL_PRODUCT_REQUIREMENTS.md` — what the finished product must do
2. `docs/SYSTEM_ARCHITECTURE_UPDATED.md` — approved architecture
3. `docs/DEVELOPMENT_ROADMAP_UPDATED.md` — build sequence and phase success criteria
4. `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` — model research, LLM policy, browser/serverless deployment
5. `docs/PROJECT_STATUS.md` — detailed implementation history/current factual state
6. `docs/START_HERE.md` — this file (concise current-session bootstrap/handoff)

**Do not let documentation describe an older system after implementation changes.**