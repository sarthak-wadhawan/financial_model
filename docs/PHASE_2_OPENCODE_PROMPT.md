# OpenCode Prompt — Phase 2 Real Market Data

Read:
- `docs/FINAL_PRODUCT_REQUIREMENTS.md`
- `docs/SYSTEM_ARCHITECTURE_UPDATED.md`
- `docs/DEVELOPMENT_ROADMAP_UPDATED.md`
- `docs/PROJECT_STATUS.md`
- current provider interfaces
- current tests

Implement Phase 2 only.

## Goal

Add a real Alpaca market-data provider while preserving the existing deterministic scanner and mock provider.

Current flow must remain:

```text
Universe
→ MarketDataProvider
→ FeatureEngine
→ EligibilityFilter
→ QuantScorer
→ Top candidates
→ Artifacts
```

## Implement

Create/complete `src/trading_copilot/providers/alpaca_market.py`.

Support:
- historical daily OHLCV,
- multiple symbols,
- benchmark data,
- latest/current available price abstraction,
- daily change / daily percentage change where cleanly supported,
- batching,
- pagination if needed,
- timezone-aware timestamps,
- retries/backoff,
- missing-symbol handling,
- provider error handling,
- normalization into existing project models.

Do not create a second scanner for Alpaca.

## Credentials

Use:
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`

Do not hard-code credentials.

## Configuration

Support config-driven provider selection, e.g.:

```yaml
market:
  provider: alpaca
  benchmark: SPY
  history_days: 300
```

Mock mode must continue working.

## History requirement

Retrieve enough data for:
- 21d / 63d / 126d returns,
- SMA20 / SMA50 / SMA200,
- realized volatility,
- dollar volume,
- relative volume,
- benchmark-relative returns.

Do not alter feature definitions or score weights.

## Latest-price abstraction

Create the smallest clean abstraction needed for future website use:

```text
symbol
latest price
daily change
daily percentage change
timestamp
```

Update mocks/tests if the provider protocol changes.

Do not build the website.

## Caching

Integrate the existing cache layer.

Historical cache identity should consider:
- provider
- symbols
- timeframe
- start/end

Document the cache location.

## Data quality

Handle safely:
- empty responses,
- duplicate timestamps,
- invalid OHLC,
- missing close,
- missing volume,
- insufficient history,
- stale latest-price data.

Do not fabricate values.

## Tests

All normal tests must work offline without credentials.

Add tests for:
- Alpaca normalization,
- multi-symbol requests,
- batching,
- empty data,
- malformed data,
- caching,
- provider failures,
- latest-price normalization.

Live tests run only when:
`RUN_LIVE_TESTS=1`
and credentials exist.

## Real smoke test

If credentials exist, test:
- SPY
- AAPL
- MSFT
- NVDA
- AMD

Verify bars, features, eligibility, quant scores, artifacts, and latest-price retrieval.

## Do not implement yet

Do not implement:
- event store,
- macro events,
- earnings calendar,
- SEC/leadership/insider intelligence,
- news/LLM,
- Answer Engine,
- website,
- watchlists,
- calendar,
- broker execution.

## Verification

Run:
```bash
python -m pytest -q
```

Run the existing mock scanner.

If credentials exist, run the small Alpaca smoke test.

## Update status

Update `docs/PROJECT_STATUS.md` with:
- Phase 2 status,
- files changed,
- provider/interface changes,
- test results,
- mock scan,
- live smoke test if run,
- symbols tested,
- cache location,
- latest-price result,
- limitations,
- next phase.

Next phase after successful completion:
**Phase 3 — Unified Persistent Event Store**

Do not start Phase 3.

## Final response

Report only:
1. Phase 2 status
2. Files created/modified
3. Test result
4. Mock scan result
5. Real Alpaca smoke-test result
6. Latest-price result
7. Cache location
8. Blockers
9. Next phase
