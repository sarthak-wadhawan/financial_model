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
| 8 | 🔄 IN PROGRESS (Node A-D ✅) | NewsDocument/ManagementStatement/EvidenceClaim models, NewsProvider protocol, SECExhibitProvider (8-K exhibits), IRReleaseProvider (50+ company IR feeds), NewsRSSProvider (15+ financial news feeds), ManagementExtractor (deterministic zero-LLM), LLMProvider abstraction (Disabled/Local), EvidenceClaimGenerator + DeduplicationEngine. All offline tests pass (250), Phase 7 live tests pass (8). |

---

## Current Phase

### Phase 8 — News + Management Statement Analysis

**Goal**: Build a structured evidence layer for NEWS + COMPANY PRESS RELEASES + MANAGEMENT STATEMENTS + MATERIAL COMPANY DEVELOPMENTS. Phase 8 is NOT the interpretation engine (that's Phase 9). Its output feeds Phase 9 as evidence claims with full provenance.

**State**: 🔄 IN PROGRESS — Node A-D COMPLETE. Node E (live integration tests), Node F (independent audits), Node G (integration/docs/commit) remaining.

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
```

**Core Principles**:
- Zero-LLM Core: All functionality works with `LLM_ENABLED=false`
- Source Priority: 1. Primary company sources (SEC, IR) 2. Regulatory 3. Reputable news 4. Optional free structured
- No Paid Dependencies: All providers use free official sources
- Deduplication: Canonical URLs, content hashes, normalized headlines
- Attribution: Speaker, role, company, statement_type, source_document
- Evidence Model: CLAIM + SOURCE + SOURCE_URL + EVENT_DATE + RETRIEVED_AT + EXACT_EVIDENCE + CONFIDENCE

**Delivered (Node A-D)**:
1. **NewsDocument, ManagementStatement, EvidenceClaim** models with full provenance
2. **NewsProvider protocol** with `fetch_news` / `fetch_company_releases`
3. **SECExhibitProvider**: Reuses Phase 6/7 SEC infrastructure for 8-K exhibits (99.1, etc.)
4. **IRReleaseProvider**: Company IR RSS feed ingestion (50+ known feeds)
5. **NewsRSSProvider**: Reputable financial news RSS ingestion (15+ feeds)
6. **ManagementExtractor**: Deterministic statement extraction (zero-LLM baseline)
7. **LLMProvider abstraction**: DisabledLLMProvider + LocalLLMProvider (Ollama)
8. **EvidenceClaimGenerator + DeduplicationEngine**
9. All offline tests pass (250), Phase 7 live tests pass (8)
10. No paid dependencies added

---

## Next Phases (Summary)

| Phase | Focus |
|-------|-------|
| 8 | 🔄 News + Management Analysis — Node A-D ✅, Node E/F/G remaining |
| 9 | **Interpretation + Impact Engine / Answer Engine** (What happened? What does it mean? Why does it matter? Company impact? Stock bias? Time horizon? Scenarios? Term definitions. Zero-LLM Core) |
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
Offline baseline: 250 passed, 34 skipped (includes Phase 7 earnings intelligence/reaction/parsers + Phase 8 news/management unit tests)
Live baseline: 257 passed, 34 skipped (includes SEC live + Phase 7 live integration tests gated by RUN_LIVE_TESTS=1; 1 Alpaca health check failure is pre-existing)
Last run:   2026-10-08
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

**Continue Phase 8 — News + Management Analysis** according to `docs/DEVELOPMENT_ROADMAP_UPDATED.md`.

Phase 8 Node A-D COMPLETE:
- Node A: Source/provider research & selection ✅
- Node B: News/document ingestion provider abstraction ✅
- Node C: SEC exhibit/IR release ingestion (reuses Phase 6/7) ✅
- Node D: News RSS ingestion ✅
- Node E: Management statement extraction (deterministic) ✅
- Node F: Optional local LLM extraction provider ✅
- Node G: Evidence claim generation ✅
- Node H: Deduplication engine ✅
- Node I: Fixtures/tests ✅ (250 offline tests passing)

Remaining:
- Node J: Live integration tests
- Node K: Independent audits (provenance, hallucination, duplicates, timestamps, zero-LLM)
- Node L: Integration/docs/commit

Key decisions implemented:
- Zero-LLM Core: All Phase 8 functionality works with `LLM_ENABLED=false`
- Source Priority: SEC/IR > regulatory > reputable news > optional free structured
- No paid dependencies added
- Deduplication: canonical URLs, content hashes, normalized headlines
- Attribution: speaker, role, company, statement_type, source_document
- Evidence Model: CLAIM + SOURCE + SOURCE_URL + EVENT_DATE + RETRIEVED_AT + EXACT_EVIDENCE + CONFIDENCE
- No Phase 9 leakage: Phase 8 outputs evidence only, no impact/bias/scenario conclusions

---

## Document Authority Hierarchy

1. `docs/FINAL_PRODUCT_REQUIREMENTS.md` — what the finished product must do
2. `docs/SYSTEM_ARCHITECTURE_UPDATED.md` — approved architecture
3. `docs/DEVELOPMENT_ROADMAP_UPDATED.md` — build sequence and phase success criteria
4. `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` — model research, LLM policy, browser/serverless deployment
5. `docs/PROJECT_STATUS.md` — detailed implementation history/current factual state
6. `docs/START_HERE.md` — this file (concise current-session bootstrap/handoff)

**Do not let documentation describe an older system after implementation changes.**