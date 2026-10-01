# Project Status

## 1. Current Project Goal

Build a small, auditable **AI Trading Research Copilot V1** that:
- Scans a liquid U.S. equity universe
- Computes deterministic market features (returns, moving averages, volatility, volume)
- Filters by eligibility criteria (min price, min dollar volume, min history)
- Scores using a transparent quant model (momentum 40%, trend 25%, liquidity 15%, volume 10%, volatility quality 10%)
- Ranks top 20 candidates deterministically
- Outputs artifacts for human review
- Does **not** place trades, call LLMs, or use live market data in V1

The system is a research copilot, not an autonomous trading bot.

---

## 2. Current Development Phase

**Phase 0 + Phase 1 + Phase 2 — COMPLETE**

- **Phase 0 (Bootstrap)**: Python package skeleton, pyproject.toml, CLI, config loader, Pydantic models, logging, test setup
- **Phase 1 (Offline Deterministic Scanner)**: Fixture market data, feature calculations, eligibility filters, quant scoring, top-N ranking, output artifacts, golden test
- **Phase 2 (Alpaca Market Data Provider)**: Real Alpaca daily market data provider with batching, retry/backoff, caching, and config-driven provider selection

All Phase 0, 1, and 2 acceptance criteria met:
- Offline tests pass without API keys
- CLI works (`--help`, `scan`, `explain`, `validate-run`)
- Deterministic ranked output from frozen inputs
- Score components inspectable
- Top-N artifacts written
- Golden test protects against regressions
- Alpaca provider implements `MarketDataProvider` protocol
- Provider selectable via config (`provider: alpaca` or `provider: mock`)
- FileCache integrated for historical bar caching
- Retry/backoff with tenacity for transient failures
- Optional live smoke test gated by `RUN_LIVE_TESTS=1`

---

## 3. Completed Work

| Feature | Modules |
|---------|---------|
| Configuration loading (YAML + env vars) | `src/trading_copilot/config.py` |
| Structured logging (text + JSON) | `src/trading_copilot/logging.py` |
| Pydantic data contracts | `src/trading_copilot/models/` (market.py, features.py, sources.py, analysis.py, results.py) |
| Provider interfaces | `src/trading_copilot/providers/base.py` |
| Mock universe provider (fixed 47 symbols) | `src/trading_copilot/pipeline/universe.py` |
| FeatureEngine (14 deterministic features) | `src/trading_copilot/pipeline/features.py` |
| EligibilityFilter (price, volume, history) | `src/trading_copilot/pipeline/eligibility.py` |
| QuantScorer (exact spec weights) | `src/trading_copilot/pipeline/quant_score.py` |
| Deterministic Top-N with tie-breakers | `src/trading_copilot/pipeline/quant_score.py` |
| ReportGenerator (top20.csv, all_features.csv, run_manifest.json) | `src/trading_copilot/pipeline/report.py` |
| MockMarketDataProvider (deterministic synthetic OHLCV) | `src/trading_copilot/providers/mock.py` |
| **AlpacaMarketDataProvider (real market data)** | `src/trading_copilot/providers/alpaca_market.py` |
| **Provider factory & config-driven selection** | `src/trading_copilot/providers/__init__.py` |
| Run storage & manifest | `src/trading_copilot/storage/runs.py` |
| Content hashing utilities | `src/trading_copilot/storage/hashes.py` |
| **FileCache integration for market data** | `src/trading_copilot/storage/cache.py` |
| CLI with scan/explain/validate-run | `src/trading_copilot/cli.py`, `__main__.py` |
| Unit tests (features, eligibility, quant, Alpaca) | `tests/unit/test_*.py` |
| Integration test (full pipeline) | `tests/integration/test_scan.py` |
| **Optional live Alpaca smoke test** | `tests/integration/test_alpaca_live.py` |
| Fixture config for reproducible runs | `tests/fixtures/config.yaml` |
| **Alpaca config example** | `config.alpaca.yaml` |
| Environment variable template | `.env.example` |

---

## 4. Files Created or Modified

```
src/trading_copilot/__init__.py
  - Package init with eval_type_backport patch for Python 3.9 union syntax

src/trading_copilot/__main__.py
  - Entry point that patches eval_type_backport before importing CLI

src/trading_copilot/config.py
  - Pydantic Settings for config.yaml + environment variables
  - Validates weights sum to 1.0, final_n <= top_n

src/trading_copilot/logging.py
  - Standard and JSON formatters
  - Reduces third-party noise (httpx, httpcore)

src/trading_copilot/cli.py
  - Typer app with scan, explain, validate-run commands
  - Uses extra={} for structured logging compatibility
  - run_id = UTC timestamp (YYYY-MM-DDTHHMMSSZ)
  - Artifacts saved to artifacts/runs/<run_id>/
  - **Provider factory creates MarketDataProvider from config**
  - **FileCache integration when cache_enabled=true**

src/trading_copilot/models/market.py
  - SymbolInfo, DailyBar (validated), MarketSnapshot

src/trading_copilot/models/features.py
  - FeatureRow (all 14 fields from spec)
  - QuantScore (components dict + total)
  - EligibilityResult

src/trading_copilot/models/sources.py
  - SourceDocument, EvidenceClaim

src/trading_copilot/models/analysis.py
  - CatalystAnalysis (for future LLM phase)

src/trading_copilot/models/results.py
  - FinalCandidate, ResearchBrief, RunManifest

src/trading_copilot/providers/base.py
  - Protocols: UniverseProvider, MarketDataProvider, NewsProvider, FilingProvider, OptionsProvider
  - BaseProvider abstract class

src/trading_copilot/providers/mock.py
  - MockMarketDataProvider: deterministic synthetic daily bars via GBM
  - Per-symbol seeds for reproducibility
  - SPY-like benchmark generation

src/trading_copilot/providers/alpaca_market.py
  - **AlpacaMarketDataProvider: real Alpaca daily bars via REST API**
  - **Batching (configurable max symbols per request)**
  - **Retry/backoff with tenacity (timeout, 429, 5xx)**
  - **FileCache integration with TTL**
  - **Proper timezone-aware timestamp parsing**
  - **Conversion to DailyBar model**
  - **Graceful handling of missing symbols / partial responses**
  - **Clear auth/config errors**

src/trading_copilot/providers/__init__.py
  - Exports AlpacaMarketDataProvider, create_market_data_provider factory

src/trading_copilot/pipeline/universe.py
  - MockUniverseProvider (47 liquid US symbols)
  - FileUniverseProvider (read from file)

src/trading_copilot/pipeline/features.py
  - FeatureEngine.compute(): returns, SMAs, distances, realized vol, dollar volume, relative volume, drawdown
  - percentile_rank(), winsorize() utilities

src/trading_copilot/pipeline/eligibility.py
  - EligibilityFilter with configurable thresholds
  - Returns detailed reasons for rejection

src/trading_copilot/pipeline/quant_score.py
  - QuantScorer: exact weights from spec
  - Momentum: cross-sectional percentile of (0.2*rel_21d + 0.35*rel_63d + 0.3*rel_126d + 0.15*ret_63d)
  - Trend: deterministic rules (close>SMA200 +35, close>SMA50 +25, SMA50>SMA200 +15, close>SMA20 +15, dist SMA50 capped +10)
  - Liquidity: percentile of avg dollar volume 20d
  - Volume: percentile of relative volume (capped)
  - Volatility quality: piecewise mapping by percentile (0-10→35, 10-30→60, 30-70→100, 70-90→75, 90-97→50, 97-100→20)
  - Tie-break: quant_score desc, avg_dollar_volume_20d desc, symbol asc

src/trading_copilot/pipeline/report.py
  - ReportGenerator writes top20.csv, all_features.csv, run_manifest.json

src/trading_copilot/storage/cache.py
  - FileCache, MemoryCache (now used by Alpaca provider)

src/trading_copilot/storage/runs.py
  - RunStore: create_run, save_manifest, load_manifest, list_runs

src/trading_copilot/storage/hashes.py
  - content_hash, config_hash, source_content_hash, stable_source_id

tests/fixtures/config.yaml
  - Complete config matching docs/config.example.yaml
  - provider: mock, history_days: 350 (ensures 220+ bars)

config.alpaca.yaml
  - Example config with provider: alpaca

.env.example
  - Template for ALPACA_API_KEY, ALPACA_API_SECRET, LLM_*, SEC_USER_AGENT

tests/unit/test_features.py
  - 10 tests: percentile_rank, winsorize, FeatureEngine (5 tests)

tests/unit/test_eligibility.py
  - 10 tests: all filter cases, multi-reason, apply, report

tests/unit/test_quant_score.py
  - 10 tests: bounds, components, ordering, determinism, tie-breakers, vol mapping, empty input, weight validation

tests/unit/test_alpaca_market.py
  - **18 tests: provider init, cache keys, bar parsing, batching, caching, retries, auth errors, benchmark bars**

tests/integration/test_scan.py
  - 4 tests: CLI help, scan command, validate-run, explain

tests/integration/test_alpaca_live.py
  - **4 optional live tests: daily bars, benchmark, health check, cache persistence**
  - Gated by RUN_LIVE_TESTS=1

pyproject.toml
  - Python >=3.9, deps: pydantic, pydantic-settings, pyyaml, typer, rich, pandas, numpy, httpx, python-dotenv, tenacity
  - Optional: dev (pytest, ruff, mypy), alpaca (alpaca-py>=0.33), duckdb
  - eval_type_backport for Python 3.9 union syntax support
```

---

## 5. Current Pipeline

```text
Fixed symbol list (47 symbols)
      ↓
MarketDataProvider (mock or alpaca, config-driven)
      ↓
FeatureEngine (14 features per symbol)
      ↓
EligibilityFilter (min_price=5, min_avg_dollar_volume_20d=50M, min_history=220)
      ↓
QuantScorer (5 components, exact spec weights)
      ↓
Top 20 by quant_score (tie-break: dollar volume, then symbol)
      ↓
Output: top20.csv, all_features.csv, run_manifest.json
```

### Future Target Pipeline

```text
Liquid U.S. stock universe
→ Eligibility filters
→ Deterministic market features
→ Quant score
→ Top 20
→ Recent news / earnings / SEC filings
→ LLM structured evidence extraction
→ Evidence validation
→ Deterministic catalyst score
→ Final rank
→ Top 3 research briefs
→ Human review
```

---

## 6. Commands to Run

### Environment/setup
```bash
cd /Users/sarthakwadhawan/Desktop/financial_models/new_model
python3 -m pip install -e ".[dev]"
# For Alpaca provider:
python3 -m pip install -e ".[alpaca]"
```

### Running the application
```bash
# Scan with fixture config (mock provider)
python3 -m trading_copilot scan --config tests/fixtures/config.yaml

# Scan with Alpaca provider (requires credentials in .env)
python3 -m trading_copilot scan --config config.alpaca.yaml

# Explain a symbol from a run
python3 -m trading_copilot explain NVDA 2026-09-30T194958Z --config tests/fixtures/config.yaml

# Validate a run
python3 -m trading_copilot validate-run 2026-09-30T194958Z --config tests/fixtures/config.yaml

# Help
python3 -m trading_copilot --help
```

### Running tests
```bash
# All tests (offline only)
python3 -m pytest -q

# Unit only
python3 -m pytest tests/unit -v

# Integration only
python3 -m pytest tests/integration -v

# Live Alpaca tests (requires credentials)
RUN_LIVE_TESTS=1 python3 -m pytest tests/integration/test_alpaca_live.py -v -s
```

---

## 7. Latest Test Results

```text
Command:
python3 -m pytest -q

Result:
52 passed, 4 skipped
```

- Unit tests: 38 passed (10 features, 10 eligibility, 10 quant, 18 Alpaca)
- Integration tests: 4 passed (scan, validate-run, explain, CLI help)
- Live Alpaca tests: 4 skipped (require RUN_LIVE_TESTS=1 and credentials)

All tests pass. No warnings relevant to application logic.

---

## 8. Latest Program Output

```text
Run ID: 2026-09-30T194958Z
Universe size: 47 symbols
Eligible symbols: 47 (all passed with history_days=350)
Top-N: 20
Artifacts: artifacts/runs/2026-09-30T194958Z/

Top 5:
  1. XLP   — Quant: 93.0 (Mom: 100.0, Trend: 100.0, Liq: 95.7, Vol: 36.2, VolQ: 100.0)
  2. GOOGL — Quant: 84.2 (Mom: 78.7, Trend: 93.3, Liq: 68.1, Vol: 91.5, VolQ: 100.0)
  3. CSCO  — Quant: 83.3 (Mom: 87.2, Trend: 100.0, Liq: 63.8, Vol: 38.3, VolQ: 100.0)
  4. MRK   — Quant: 82.8 (Mom: 95.7, Trend: 95.3, Liq: 42.6, Vol: 68.1, VolQ: 75.0)
  5. QQQ   — Quant: 82.4 (Mom: 89.4, Trend: 77.0, Liq: 91.5, Vol: 87.2, VolQ: 50.0)
```

No errors encountered. Deterministic output: re-running with same config produces identical rankings and scores.

---

## 9. Generated Artifacts

```
artifacts/runs/<run_id>/
├── config.yaml          # Exact config snapshot used for this run
├── top20.csv            # Ranked top 20 with all score components
├── all_features.csv     # Full feature matrix for all 47 symbols
└── run_manifest.json    # Run metadata (run_id, timestamps, counts, config_hash)
```

```
artifacts/cache/market_data/
├── <hash>.cache         # Pickled cached bar data
├── <hash>.meta          # JSON metadata with timestamp
```

**top20.csv columns:** rank, symbol, quant_score, momentum_score, trend_score, liquidity_score, volume_score, volatility_quality_score, price, returns, SMAs, volumes, as_of

**run_manifest.json:** run_id, started_at, completed_at, config_hash, git_commit, universe_size, eligible_count, top_n, failures

**Cache key format:** `alpaca|bars|1Day|SYM1,SYM2|2024-01-01|2024-01-31` (SHA256 truncated to 32 chars)

---

## 10. Important Technical Decisions

1. **Deterministic scanner before AI** — Quant ranking is pure math; LLM only researches top 20 later
2. **AI does not control final scoring** — Catalyst score is a deterministic mapping from structured LLM output, not LLM-generated numbers
3. **No broker execution in V1** — CLI has no order-placement commands
4. **Provider interfaces** — UniverseProvider, MarketDataProvider protocols allow swapping Alpaca/mock without pipeline changes
5. **Tests must work without API keys** — All tests use MockMarketDataProvider and fixed fixtures
6. **Python 3.9 compatibility** — Used `eval_type_backport` for `|` union syntax; target-version py39
7. **Structured logging with extra={}** — Avoids TypeError on Python 3.9 logger._log()
8. **Tie-breaker is dollar volume then symbol** — Guarantees deterministic ordering
9. **Winsorization at 1%/99%** — Applied to all cross-sectional values before percentile ranking
10. **Run artifacts are self-contained** — Each run directory has config, data, and manifest for full reproducibility
11. **Config-driven provider selection** — `market.provider` in YAML selects mock/alpaca
12. **FileCache outside run artifacts** — Cache at `artifacts/cache/market_data/` to avoid polluting run globs
13. **Retry with exponential backoff + jitter** — Handles 429, timeouts, 5xx without hammering API
14. **Cache key includes provider + symbols + timeframe + date range** — Prevents collisions

---

## 11. Assumptions

| Area | Assumption |
|------|------------|
| Universe | Fixed 47 liquid symbols (no live universe API) |
| Benchmark | SPY only |
| History | 350 calendar days requested → ~252 business days (meets 220 min) |
| Volatility | Realized vol = std(log returns 20d) * sqrt(252) |
| Dollar volume | close * volume averaged over 20 sessions |
| Relative volume | latest volume / mean(volume previous 20 sessions) |
| Returns | close_t / close_(t-N) - 1 |
| Relative returns | stock_ret_Nd - SPY_ret_Nd |
| Missing benchmark dates | Return 0.0 (no crash) |
| Mock data | GBM with per-symbol seed = hash(symbol, global_seed) |
| ETFs | Included in universe (SPY, QQQ, IWM, DIA, XLF, XLK, XLE, XLV, XLI, XLP) |
| Alpaca feed | SIP feed with raw (unadjusted) prices |
| Alpaca timeframe | 1Day bars |
| Cache TTL | 7 days default for market data |

---

## 12. Known Problems / Limitations

1. **Mock data is synthetic** — Not real market data; GBM parameters are arbitrary (drift=10%, vol=20%)
2. **No data quality checks beyond Pydantic** — No detection of stale data, splits, dividends
3. **ETFs in universe** — Spec says "optionally ETFs may be allowed"; currently included
4. **No git commit in manifest** — `git_commit` field is None (not a git repo or not implemented)
5. **Python 3.9 requires eval_type_backport** — Minor runtime dependency for type hints
6. **Explain command only shows features** — No score decomposition or eligibility reasons
7. **No golden master CSV** — Integration test verifies structure but not exact values against a frozen reference
8. **Alpaca provider not battle-tested** — Live smoke test not yet run (no credentials in this env)
9. **Cache not used by mock provider** — Only Alpaca provider uses cache currently

---

## 13. Current Blockers

**None.** Phase 0, 1, and 2 are complete and tested.

---

## 14. Next Recommended Step

**Next objective: Phase 3 — SEC EDGAR Filing Provider**

Tasks:
1. Implement `SECFilingProvider` in `src/trading_copilot/providers/sec_edgar.py`
2. Add SEC-compliant User-Agent configuration
3. Implement filing metadata retrieval (index files)
4. Implement filing text retrieval (HTML/text parsing)
5. Add rate-limit handling (10 req/sec per SEC guidelines)
6. Normalize filings to `SourceDocument` model
7. Add source normalization and deduplication
8. Add unit tests with mock SEC responses
9. Add optional live test gated by `RUN_LIVE_TESTS=1`

---

## 15. Do Not Do Yet

- News provider (Phase 4)
- LLM client / analysis (Phase 5-6)
- Catalyst scoring (Phase 7)
- Final ranking with catalyst (Phase 8)
- Options module (Phase 9)
- Run manifest hardening / historical evaluation (Phase 10-11)
- Web dashboard
- Broker execution

---

## 16. Questions / Decisions Needed

**None.** Ready for Phase 3.

---

## 17. Development History

### 2026-09-30 — Phase 0 + Phase 1 Complete
- Work completed: All Phase 0 bootstrap (config, logging, models, CLI) + Phase 1 offline scanner (mock data, features, eligibility, quant scoring, top-N, reports)
- Tests: 34 passed (10 unit features, 10 unit eligibility, 10 unit quant, 4 integration)
- Important result: Deterministic top-20 output from frozen fixture config; all CLI commands work
- Next step: Phase 2 — Alpaca market data integration

### 2026-09-30 — Phase 2 Complete
- Work completed: AlpacaMarketDataProvider with batching, retry/backoff, FileCache integration, config-driven provider selection, optional live test
- Files added: alpaca_market.py, config.alpaca.yaml, .env.example, test_alpaca_market.py (18 tests), test_alpaca_live.py (4 skipped tests)
- Tests: 52 passed, 4 skipped (38 unit, 4 integration, 4 live skipped)
- Important result: Mock provider still works identically; Alpaca provider implements full protocol with caching and retries
- Next step: Phase 3 — SEC EDGAR filing provider

### 2026-10-01 — GitHub Repository Connected
- GitHub repository: https://github.com/sarthak-wadhawan/financial_model
- Branch: main
- Commit: cd8a230 "Build AI trading research copilot foundation"
- Test result before push: 52 passed, 4 skipped
- Push status: Success (new repository, no force push needed)
- Working tree: Clean except for .gitignore modification (unstaged)

### 2026-10-01 — Comprehensive README Added
- Added professional root-level README.md with fresh-computer setup guide
- Documented: prerequisites, clone, venv, install, env config, tests, mock scan, Alpaca scan, CLI commands, artifacts, scoring, project structure, config, troubleshooting, roadmap
- Verified all documented commands: pytest, scan (mock), explain, validate-run
- Tests: 52 passed, 4 skipped
- Mock scan result: 47 symbols processed, 20 ranked, artifacts written
- GitHub commit: cc446a6 "Add fresh setup and usage guide"
- Push status: Success