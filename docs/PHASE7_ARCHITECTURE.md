# Phase 7 Architecture: Earnings Intelligence + Reaction History

## Overview

Phase 7 implements two interconnected capabilities:

1. **Earnings Intelligence** — Extract, normalize, and store historical earnings results (actual EPS/revenue, consensus estimates, guidance, management commentary) with full provenance.

2. **Reaction History** — Measure and preserve raw market behavior around earnings events across multiple time windows (pre-event, immediate, next-session, multi-session) without interpretation.

---

## Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Raw facts first** | Every external fact stored with source, source_url, source_id, retrieved_at |
| **Deterministic derivation** | Surprise = actual - consensus (only when both present); reaction = price change from preserved bars |
| **No invention** | Missing actual/consensus/guidance remains NULL; never interpolated |
| **Provenance preserved** | Content-addressed raw documents; normalized evidence snapshots; retrieval timestamps |
| **Leakage prevention** | Reaction windows anchored to `released_at` (event timestamp), never to scheduled_at |
| **Reproducibility** | All calculations derivable from stored events + market data; no hidden state |
| **Separation of concerns** | Earnings intelligence ≠ interpretation (Phase 9); reaction measurements ≠ catalyst scoring (Phase 8+) |

---

## Data Model Extensions

### New Event Types (added to `EventType` enum)

```python
EARNINGS_RESULT = "earnings_result"      # Actual EPS/revenue released
EARNINGS_GUIDANCE = "earnings_guidance"  # Forward guidance from company
EARNINGS_REACTION = "earnings_reaction"  # Measured price/volume reaction windows
```

### Extended `MarketEvent.metadata` for Earnings Intelligence

**EARNINGS_RESULT event:**
```json
{
  "event_subtype": "earnings_result",
  "fiscal_quarter": "3",
  "fiscal_year": "2026",
  "eps_actual": "1.55",
  "eps_consensus": "1.42",
  "eps_surprise": "0.13",
  "eps_surprise_pct": "9.15",
  "revenue_actual": "89500000000",
  "revenue_consensus": "89200000000",
  "revenue_surprise": "300000000",
  "revenue_surprise_pct": "0.34",
  "report_date": "2026-10-29",
  "report_time": "amc",
  "source_document_id": "sec_edgar:0000320193-26-000123",
  "source_document_type": "8-K",
  "items": ["2.02"],
  "retrieved_at": "2026-10-29T21:15:00Z"
}
```

**EARNINGS_GUIDANCE event:**
```json
{
  "event_subtype": "earnings_guidance",
  "fiscal_quarter": "3",
  "fiscal_year": "2026",
  "guidance_type": "quarterly|annual|long_term",
  "period": "Q4 FY2026",
  "eps_guidance_low": "1.60",
  "eps_guidance_high": "1.70",
  "revenue_guidance_low": "91000000000",
  "revenue_guidance_high": "93000000000",
  "guidance_change": "raised|lowered|maintained|new",
  "previous_eps_guidance_low": "1.50",
  "previous_eps_guidance_high": "1.60",
  "source_document_id": "sec_edgar:0000320193-26-000123",
  "source_document_type": "8-K",
  "items": ["2.02", "9.01"],
  "retrieved_at": "2026-10-29T21:15:00Z"
}
```

**EARNINGS_REACTION event:**
```json
{
  "event_subtype": "earnings_reaction",
  "earnings_event_id": "evt_abc123",  // links to EARNINGS_RESULT
  "symbol": "AAPL",
  "report_time": "amc",
  "windows": {
    "pre_market": {
      "start": "2026-10-29T13:30:00Z",
      "end": "2026-10-29T13:30:00Z",
      "open": 175.00,
      "close": 175.20,
      "change_pct": 0.11,
      "volume": 1500000,
      "bars_available": true
    },
    "immediate_ah": {
      "start": "2026-10-29T21:00:00Z",
      "end": "2026-10-30T00:00:00Z",
      "open": 175.20,
      "close": 178.50,
      "change_pct": 1.88,
      "volume": 12000000,
      "bars_available": true
    },
    "next_session": {
      "date": "2026-10-30",
      "open": 178.00,
      "close": 179.20,
      "change_pct": 0.67,
      "volume": 85000000,
      "bars_available": true
    },
    "session_5": {
      "start_date": "2026-10-30",
      "end_date": "2026-11-05",
      "start_close": 175.20,
      "end_close": 182.10,
      "change_pct": 3.94,
      "bars_available": true
    }
  },
  "benchmark": {
    "symbol": "SPY",
    "session_5_change_pct": 1.20
  },
  "calculated_at": "2026-11-06T00:00:00Z",
  "source": "alpaca_iex",
  "market_data_retrieved_at": "2026-11-06T00:00:00Z"
}
```

---

## Provider Architecture

### 1. `EarningsIntelligenceProvider`

**Responsibilities:**
- Fetch earnings results from SEC filings (8-K Item 2.02, 10-Q, 10-K)
- Fetch earnings results from earnings API providers (Alpha Vantage, FMP, Polygon, Twelve Data) when API keys available
- Extract: actual EPS, actual revenue, consensus estimates, guidance
- Create `EARNINGS_RESULT` and `EARNINGS_GUIDANCE` events
- Link to scheduled `EARNINGS` events via `identity_key` correlation

**Sources (priority order):**
1. SEC EDGAR (primary, authoritative, free) — 8-K Item 2.02, 10-Q, 10-K
2. Alpha Vantage (requires key) — earnings results + consensus
3. FMP (requires key) — earnings results + consensus + guidance
4. Polygon (requires key) — earnings results + consensus
5. Twelve Data (requires key) — earnings results + consensus

**Key Methods:**
```python
def fetch_earnings_results(
    self,
    symbols: list[str] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[dict]: ...

def refresh(
    self,
    symbols: list[str] | None = None,
    lookback_days: int = 365,
) -> dict[str, int]: ...  # NEW/UNCHANGED/CHANGED/ERROR counts

def get_earnings_history(
    self,
    symbol: str,
    limit: int = 20,
) -> list[MarketEvent]: ...
```

### 2. `EarningsReactionProvider`

**Responsibilities:**
- For each released `EARNINGS_RESULT` event, compute reaction windows using market data
- Use `MarketDataProvider` (Alpaca IEX) for price/volume data
- Create `EARNINGS_REACTION` events with raw measurements
- Handle BMO/AMC/unknown timing correctly
- Never use future data (lookahead-safe)

**Reaction Windows (all anchored to `released_at`):**

| Window | Definition | Notes |
|--------|------------|-------|
| `pre_market` | Regular session open → release time (BMO) or prior close → release time (AMC) | Only for BMO earnings |
| `immediate_ah` | Release time → 3 hours after (AMC) or release time → session close (BMO) | After-hours / same-session |
| `next_session` | Next regular trading session (full day) | Open-to-close |
| `session_5` | 5 trading sessions starting from next session | Cumulative |

**Key Methods:**
```python
def compute_reactions(
    self,
    symbols: list[str] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> dict[str, int]: ...

def get_reaction_history(
    self,
    symbol: str,
    limit: int = 20,
) -> list[MarketEvent]: ...
```

---

## Leakage Protections

| Risk | Mitigation |
|------|------------|
| Using `scheduled_at` instead of `released_at` for reaction anchoring | All windows computed from `released_at` (actual release timestamp from SEC acceptance time) |
| Using price data after reaction window | Windows have explicit end boundaries; data fetched only up to window end |
| Using revised consensus estimates | Consensus stored at time of earnings event; revisions create new `EARNINGS_RESULT` with `CHANGED` status |
| Benchmark contamination | Benchmark reaction computed separately, stored alongside |
| Pre-release price drift in `pre_market` | Window explicitly labeled; interpretation layer (Phase 9) decides significance |

---

## Integration with Existing Phases

| Phase | Integration Point |
|-------|-------------------|
| Phase 2 (Market Data) | `EarningsReactionProvider` uses `MarketDataProvider` protocol (Alpaca IEX) |
| Phase 3 (Event Store) | New event types upserted with same revision tracking |
| Phase 4 (Macro) | No direct dependency |
| Phase 5 (Earnings Calendar) | `EARNINGS_RESULT` links to scheduled `EARNINGS` via correlation |
| Phase 6 (SEC) | `EarningsIntelligenceProvider` reuses `SECTransport`, `SECCIKMap`, `sec_parsers` |
| Phase 8+ (News/AI) | Raw earnings events + reactions available as evidence |

---

## File Structure (New)

```
src/trading_copilot/
├── providers/
│   ├── earnings_intelligence.py   # Earnings results + guidance extraction
│   ├── earnings_reaction.py       # Reaction window computation
│   └── __init__.py                # Export new providers
├── models/
│   └── events.py                  # Add EARNINGS_RESULT, EARNINGS_GUIDANCE, EARNINGS_REACTION to EventType
└── intelligence/                  # (Phase 9) - not created yet
```

---

## Acceptance Criteria

### Earnings Intelligence
- [ ] SEC 8-K Item 2.02 parsing extracts actual EPS/revenue
- [ ] SEC 10-Q/10-K parsing extracts quarterly results
- [ ] Consensus estimates extracted when available from API providers
- [ ] Surprise calculated only when both actual and consensus present
- [ ] Guidance extracted with change classification (raised/lowered/maintained/new)
- [ ] All events have provenance: source, source_url, source_id, retrieved_at
- [ ] Amendments (8-K/A, 10-Q/A) create CHANGED events with revision history
- [ ] Offline tests with synthetic SEC filing fixtures pass
- [ ] Live test against SEC EDGAR passes (gated by RUN_LIVE_TESTS)

### Reaction History
- [ ] BMO earnings: pre_market, immediate_ah (to close), next_session, session_5
- [ ] AMC earnings: immediate_ah (3h), next_session, session_5
- [ ] Unknown time: conservative defaults, marked in metadata
- [ ] Benchmark (SPY) reaction computed for each window
- [ ] Raw measurements stored (open, close, change_pct, volume) — no interpretation
- [ ] Lookahead-safe: windows bounded, data fetched only through window end
- [ ] Reproducible: re-running with same market data produces identical reactions
- [ ] Offline tests with synthetic market data fixtures pass
- [ ] Live test with Alpaca IEX data passes (gated)

### Overall
- [ ] All existing Phase 1-6 tests still pass
- [ ] New unit tests: ≥20 for earnings intelligence, ≥15 for reaction history
- [ ] New integration tests: ≥2 live tests per provider
- [ ] Independent architecture review passes
- [ ] Independent provider/provenance review passes
- [ ] Independent test/edge-case review passes
- [ ] Documentation updated: START_HERE.md, PROJECT_STATUS.md

---

## Deferred to Later Phases

| Feature | Phase |
|---------|-------|
| Management commentary extraction (earnings call transcripts) | Phase 8 (News + Management Analysis) |
| AI-assisted extraction from unstructured text | Phase 8 |
| Catalyst/risk identification from earnings | Phase 8 |
| Interpretation Engine (company_impact, stock_bias, scenarios) | Phase 9 |
| Answer Engine integration | Phase 9 |
| Website display of earnings history/reactions | Phase 10 |
| Historical event impact validation (calibration) | Phase 12 |

---

## Implementation Order

1. **Extend `EventType` enum** — Add three new types
2. **Earnings Intelligence Provider** — SEC parsing + API providers for results/guidance
3. **Earnings Reaction Provider** — Market data reaction windows
4. **Unit Tests** — Fixtures for SEC earnings, reaction calculations
5. **Integration Tests** — Live SEC + Alpaca
6. **Independent Reviews** — Architecture, provider, test auditors
7. **Documentation Update** — START_HERE.md, PROJECT_STATUS.md
8. **Commit** — After all tests pass and reviews clear