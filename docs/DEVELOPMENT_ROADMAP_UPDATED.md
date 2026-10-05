# Updated Development Roadmap

Authoritative requirements: `docs/FINAL_PRODUCT_REQUIREMENTS.md`

## Phase 0–1 — Core Scanner
Status: COMPLETE

## Phase 2 — Real Alpaca Market Data
Deliver:
- Alpaca daily bars
- latest-price abstraction
- batching
- retries
- caching
- validation
- provider selection
- offline regression tests
- optional live smoke tests

## Phase 3 — Unified Persistent Event Store
Deliver:
- MarketEvent model
- SQLite store
- event types/status
- upsert/deduplication
- source metadata
- today/upcoming/recent queries
- change detection
- tests

## Phase 4 — Macro Event Intelligence
Deliver:
- FOMC calendar
- employment/jobs releases
- CPI/PPI
- PCE/GDP
- JOLTS and configured releases
- actual/previous/forecast where available
- refresh behavior
- just-released logic
- importance tiers

## Phase 5 — Company Calendar / Corporate Events
Deliver:
- earnings dates/time (with timezone)
- dividend/ex-dividend
- splits
- corporate actions
- investor events
- M&A/spin-off events where available
- **Preserve structured fields needed for downstream impact reasoning: company_impact, stock_bias, confidence, time_horizon**

## Phase 6 — SEC + Leadership + Insider Intelligence
Deliver:
- EDGAR integration
- 8-K / 10-Q / 10-K / Form 4
- current CEO/CFO
- leadership changes
- insider transaction classification
- source preservation
- **Expose evidence and potential company relevance for interpretation engine**

## Phase 7 — Earnings Intelligence + Reaction History
Deliver:
- EPS/revenue results
- guidance
- management commentary
- after-hours / next-day / 5-session reaction
- earnings history
- evidence-backed explanations
- **Include surprise, guidance change, reaction, and inputs needed for scenario analysis (base/bull/bear cases)**

## Phase 8 — News + Management Statement Analysis
Deliver:
- meaningful news providers
- management statements
- deduplication
- structured AI extraction
- source-backed catalyst/risk claims
- **Produce structured evidence for interpretation engine, not generic summaries**

## Phase 9 — Interpretation + Impact Engine / Answer Engine
Deliver:
- evidence validator
- **Interpretation Engine: What happened? What does it mean? Why does it matter? Company impact? Stock bias? Time horizon?**
- **Scenario Analysis: Base case / Bull case / Bear case / What would change the view**
- Why is it moving?
- What changed?
- Investor concerns
- Why investors are interested
- Catalysts
- Risks
- Next important event
- market morning answers
- stock research brief
- **Term Definition Service (hover/tap popovers + Learn more links)**
- **Zero-LLM Core: all above works with LLM_ENABLED=false**

## Phase 10 — Website / Dashboard
Deliver:
- Home
- search
- market snapshot
- today / just released / upcoming events
- scanner
- stock page
- price chart
- **answer-focused UI with Interpretation Engine output**
- **Why It Matters + Market Impact sections**
- **Term hover/tap definitions + Learn More links**
- **Scenario sections (Base / Bull / Bear)**
- **Company Impact vs Stock Impact display**
- source links
- **progressive disclosure**
- **responsive/mobile behavior**

## Phase 11 — Watchlists + Calendar + Alerts
Deliver:
- watchlists
- meaningful change alerts
- `.ics` export
- scheduled refresh/notifications later

## Phase 12 — Historical Event Impact
Deliver:
- SPY reaction around macro events
- stock reaction around earnings/company events
- **Validate relationships used in impact statements (calibration)**

## Phase 13 — Strategy Evaluation / Paper Trading + Autonomous Model Discovery
Deliver:
- cost-aware momentum
- PEAD
- event-driven research
- mean reversion
- options-premium research
- Model A filter research
- paper-only workflows before any future execution
- **Autonomous Model Discovery: experiment registry, evaluation contracts, dataset versioning, leaderboard, promotion gate, leakage audit, competing hypotheses, reproducible experiments**

## Phase 14 — Deployment Hardening / Cross-Device Release
Deliver:
- browser inference where appropriate
- serverless backend for secrets/data
- mobile performance
- cross-device testing
- security review

Only implement the current phase.

At the end of every phase:
- run tests,
- run the relevant smoke test,
- update `docs/PROJECT_STATUS.md`,
- record limitations,
- define exactly one next phase.
