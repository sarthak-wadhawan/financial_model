# AI Trading Research Copilot

A deterministic, auditable **AI Trading Research Copilot** that scans a liquid U.S. equity universe, computes quantitative features, applies eligibility filters, scores candidates using a transparent model, and outputs ranked artifacts for human review.

**Current state**: Research/scanning system only — **does not place trades, call LLMs, or execute orders.**

## Current Pipeline

```
Fixed symbol universe (47 symbols)
        ↓
Market Data Provider (mock or Alpaca, config-driven)
        ↓
FeatureEngine (14 deterministic features per symbol)
        ↓
EligibilityFilter (min price, min dollar volume, min history)
        ↓
QuantScorer (5 components, exact spec weights)
        ↓
Top 20 by quant_score (tie-break: dollar volume, then symbol)
        ↓
Output: top20.csv, all_features.csv, run_manifest.json
```

---

## 1. Current Features

| Feature | Status |
|---------|--------|
| Deterministic stock scanner | ✅ Working |
| Mock market data provider (GBM synthetic data) | ✅ Working |
| Alpaca market data provider (real data, caching, retries) | ✅ Implemented |
| Feature calculation (returns, SMAs, volatility, volumes) | ✅ Working |
| Eligibility filtering (price, dollar volume, history) | ✅ Working |
| Quant scoring (momentum, trend, liquidity, volume, vol quality) | ✅ Working |
| Top-N deterministic ranking with tie-breakers | ✅ Working |
| Artifact generation (top20, all_features, manifest, config) | ✅ Working |
| CLI: `scan`, `explain`, `validate-run` | ✅ Working |
| Unit test suite (38 + 24 events tests) | ✅ Passing |
| Integration test suite (4 tests) | ✅ Passing |
| Optional live Alpaca tests (gated) | ✅ Implemented |
| Structured logging (text + JSON) | ✅ Working |
| FileCache for market data (TTL-based) | ✅ Working |
| Config-driven provider selection | ✅ Working |
| **Unified persistent event store (SQLite)** | ✅ **Phase 3 Complete** |
| **Event upsert with revision history** | ✅ **Phase 3 Complete** |
| **Change detection (NEW/UNCHANGED/CHANGED)** | ✅ **Phase 3 Complete** |

**Not yet implemented** (future phases): SEC filings provider (Phase 4), news provider, LLM analysis, catalyst scoring, final top-3 research briefs, options module, broker execution.

---

## 2. Requirements

| Requirement | Version |
|-------------|---------|
| **Git** | Any recent version |
| **Python** | 3.9 – 3.12 (tested on 3.9+) |
| **pip** | ≥ 23.0 |
| **Internet** | Required only for Alpaca provider |

> **Recommended**: Python 3.11 or 3.12. The project supports Python ≥ 3.9 via `eval_type_backport` for modern union syntax.

---

## 3. Clone the Repository

```bash
git clone https://github.com/sarthak-wadhawan/financial_model.git
cd financial_model
```

---

## 4. Create a Python Virtual Environment

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

> After activation, your shell prompt will show `(.venv)` and `which python3` (or `where python` on Windows) will point to the virtual environment.

---

## 5. Install Dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

For development (includes pytest, ruff, mypy):

```bash
python3 -m pip install -e ".[dev]"
```

For **Alpaca real market data** (optional, requires credentials):

```bash
python3 -m pip install -e ".[alpaca]"
```

---

## 6. Environment Configuration

The **mock/offline scanner requires no environment variables** — it works out of the box.

For Alpaca real data, copy the example and fill in credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```text
# Alpaca API credentials (get from https://app.alpaca.markets/)
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here

# LLM configuration (for future phases)
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=

# SEC EDGAR User-Agent (for future Phase 3)
SEC_USER_AGENT=YourCompany your@email.com
```

> **Never commit `.env`** — it is in `.gitignore`.

---

## 7. Run the Test Suite

```bash
python3 -m pytest -q
```

**Expected result**: All tests pass, no failures.

```
76 passed, 4 skipped in ~27s
```

- 38 unit tests (features, eligibility, quant scoring, Alpaca provider)
- 24 event store tests (DB creation, insertion, upsert, revision history, queries)
- 4 integration tests (CLI scan, explain, validate-run, help)
- 4 live Alpaca tests skipped (require `RUN_LIVE_TESTS=1` and credentials)

---

## 8. Run the Project — Offline / Mock Mode

No credentials needed. Uses deterministic synthetic market data.

```bash
python3 -m trading_copilot scan --config tests/fixtures/config.yaml
```

**What happens**:

1. Loads 47 fixed symbols from the mock universe
2. Generates deterministic daily bars via GBM (per-symbol seeds)
3. Computes 14 features per symbol
4. Filters by eligibility (all 47 pass with 350-day history)
5. Scores using 5-component quant model
6. Ranks top 20, breaks ties by dollar volume then symbol
7. Writes artifacts to `artifacts/runs/<run_id>/`

**Sample output**:

```
                            Top 20 Quant Candidates
┏━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃      ┃        ┃     Quant ┃          ┃       ┃           ┃        ┃      Vol ┃
┃ Rank ┃ Symbol ┃     Score ┃ Momentum ┃ Trend ┃ Liquidity ┃ Volume ┃  Quality ┃
┡━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│    1 │ SPY    │      88.2 │     91.5 │  93.7 │     100.0 │   72.3 │     60.0 │
│    2 │ ADBE   │      86.1 │     93.6 │ 100.0 │      89.4 │   27.7 │     75.0 │
...
```

**Artifacts created**:

```
artifacts/runs/2026-10-01T174538Z/
├── config.yaml          # Exact config snapshot
├── top20.csv            # Ranked top 20 with all score components
├── all_features.csv     # Full feature matrix for all 47 symbols
└── run_manifest.json    # Run metadata (timestamps, counts, config_hash)
```

---

## 9. Run the Project — Real Market Data (Alpaca)

Requires: `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`, and `[alpaca]` dependencies installed.

```bash
# Install Alpaca dependencies if not already done
python3 -m pip install -e ".[alpaca]"

# Use the Alpaca config (or copy config.alpaca.yaml to config.local.yaml and edit)
python3 -m trading_copilot scan --config config.alpaca.yaml
```

**Notes**:

- Uses Alpaca SIP feed, 1Day bars, raw (unadjusted) prices
- Batches requests, retries with exponential backoff on 429/5xx/timeouts
- Caches bars in `artifacts/cache/market_data/` (7-day TTL)
- Benchmark: SPY

> The mock provider (`provider: mock` in config) is the default and requires no setup.

---

## 10. CLI Commands

```bash
python3 -m trading_copilot --help
```

### Scan

Run the scanner and produce artifacts.

```bash
python3 -m trading_copilot scan --config tests/fixtures/config.yaml
```

Options:
- `--config PATH` — Config file (default: `config.yaml`)
- `--output PATH` — Override artifact output directory

### Explain a Symbol

Show the full feature breakdown for a symbol from a previous run.

```bash
python3 -m trading_copilot explain SPY 2026-10-01T174538Z --config tests/fixtures/config.yaml
```

Arguments:
- `SYMBOL` — Ticker symbol (e.g., `SPY`, `AAPL`)
- `RUN_ID` — Timestamp from a previous scan (e.g., `2026-10-01T174538Z`)

### Validate a Run

Verify that a previous run's artifacts are present and reproducible.

```bash
python3 -m trading_copilot validate-run 2026-10-01T174538Z --config tests/fixtures/config.yaml
```

---

## 11. Output / Artifacts

```
artifacts/
├── runs/
│   └── <run_id>/
│       ├── config.yaml          # Exact configuration used
│       ├── top20.csv            # Ranked candidates + score components
│       ├── all_features.csv     # Full feature matrix (all symbols)
│       └── run_manifest.json    # Metadata for reproducibility
└── cache/
    └── market_data/
        ├── <hash>.cache         # Pickled cached bar data
        └── <hash>.meta          # JSON metadata with timestamp
```

### File Descriptions

| File | Purpose |
|------|---------|
| `top20.csv` | Rank, symbol, quant_score, 5 component scores, price, key features, as_of date |
| `all_features.csv` | Complete 14-feature matrix for every symbol in the universe |
| `run_manifest.json` | `run_id`, `started_at`, `completed_at`, `config_hash`, `git_commit`, `universe_size`, `eligible_count`, `top_n`, `failures` |
| `config.yaml` | Full config snapshot — enables exact reproduction |

---

## 12. How the Scoring Works

The quant score is a weighted sum of five components (weights are configurable but default to spec):

| Component | Weight | Description |
|-----------|--------|-------------|
| **Momentum** | 40% | Cross-sectional percentile of blended returns (21d, 63d, 126d) and relative returns vs SPY |
| **Trend** | 25% | Deterministic rules: close > SMA200 (+35), close > SMA50 (+25), SMA50 > SMA200 (+15), close > SMA20 (+15), distance to SMA50 capped (+10) |
| **Liquidity** | 15% | Percentile of 20-day average dollar volume |
| **Volume** | 10% | Percentile of relative volume (latest / 20-day mean, capped) |
| **Volatility Quality** | 10% | Piecewise mapping by realized vol percentile: 0–10→35, 10–30→60, 30–70→100, 70–90→75, 90–97→50, 97–100→20 |

**Tie-breaker**: Higher quant_score → higher avg_dollar_volume_20d → symbol (ascending).

All calculations are deterministic. Winsorization at 1%/99% is applied before percentile ranking.

---

## 13. Project Structure

```
financial_model/
├── docs/                    # Full specification documents
│   ├── 00_README.md
│   ├── 01_PRODUCT_REQUIREMENTS.md
│   ├── 02_SYSTEM_ARCHITECTURE.md
│   ├── 03_PIPELINE_SPEC.md
│   ├── 04_DATA_CONTRACTS.md
│   ├── 05_SCORING_AND_SIGNALS.md
│   ├── 06_AI_ANALYSIS_SPEC.md
│   ├── 07_IMPLEMENTATION_PLAN.md
│   ├── 08_TEST_AND_ACCEPTANCE.md
│   ├── 09_SECURITY_AND_RISK.md
│   ├── 10_CONFIG_SPEC.md
│   ├── 11_OPENCODE_MASTER_PROMPT.md
│   ├── 12_REPO_TREE.txt
│   ├── config.example.yaml
│   └── PROJECT_STATUS.md    # Current development status & handoff
├── src/
│   └── trading_copilot/     # Main package
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py           # Typer CLI (scan, explain, validate-run)
│       ├── config.py        # Pydantic Settings (YAML + env)
│       ├── logging.py       # Structured logging (text/JSON)
│       ├── models/          # Pydantic data contracts
│       ├── pipeline/        # Universe, features, eligibility, scoring, report
│       ├── providers/       # Market data providers (mock, Alpaca)
│       └── storage/         # Run storage, FileCache, content hashing
├── tests/
│   ├── unit/                # 38 unit tests
│   ├── integration/         # 4 integration tests
│   └── fixtures/            # Test config
├── artifacts/               # Generated at runtime (gitignored)
├── config.alpaca.yaml       # Example config for Alpaca provider
├── .env.example             # Environment variable template
├── pyproject.toml           # Package config, dependencies, optional groups
└── README.md                # This file
```

---

## 14. Configuration

The YAML config (`tests/fixtures/config.yaml`, `config.alpaca.yaml`, or your own) has these sections:

| Section | Purpose |
|---------|---------|
| `app` | Artifact directory, timezone |
| `universe` | Mode (`fixed_or_provider`), ETF inclusion |
| `market` | Provider (`mock` or `alpaca`), benchmark, history days |
| `eligibility` | Min price, min avg dollar volume 20d, min history days |
| `scan` | `top_n` (default 20), `final_n` (default 3, for future) |
| `scoring.quant` | Five component weights (must sum to 1.0) |
| `scoring.final` | Quant vs catalyst weights (catalyst not yet implemented) |
| `runtime` | `cache_enabled`, `provider_max_concurrency` |

**Most commonly changed**: `market.provider`, `market.history_days`, `eligibility` thresholds, `scan.top_n`.

See `docs/10_CONFIG_SPEC.md` for full specification.

---

## 15. Troubleshooting

### `python3: command not found` / `python: command not found`

Install Python 3.9+ from [python.org](https://python.org) or via your package manager (Homebrew: `brew install python`, apt: `apt install python3`).

### `No module named trading_copilot`

The package is not installed in the current environment.

```bash
# Ensure virtual environment is activated (prompt shows (.venv))
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\Activate.ps1  # Windows

# Install in editable mode
python3 -m pip install -e .
```

### Wrong Python environment

Verify:

```bash
which python3
python3 --version
python3 -m pip --version
```

All three should point to your `.venv` directory.

### Missing API credentials

**Mock mode works without any credentials.** Only the Alpaca provider needs `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`.

### Tests fail immediately

Reinstall development dependencies:

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest -q
```

### `ModuleNotFoundError: No module named 'alpaca'`

Install the optional Alpaca extra:

```bash
python3 -m pip install -e ".[alpaca]"
```

---

## 16. Development / Contributing

```bash
# Run tests
python3 -m pytest -q

# Lint
ruff check src tests

# Type check
mypy src
```

Project specifications live in `docs/`. Key reference:

- `docs/PROJECT_STATUS.md` — Current phase, completed work, next steps
- `docs/03_PIPELINE_SPEC.md` — Pipeline specification
- `docs/05_SCORING_AND_SIGNALS.md` — Quant scoring details
- `docs/10_CONFIG_SPEC.md` — Configuration reference

---

## 17. Current Project Status

| Item | Status |
|------|--------|
| **Completed phases** | Phase 0 (bootstrap), Phase 1 (offline scanner), Phase 2 (Alpaca provider), **Phase 3 (Unified Event Store)** |
| **Current phase** | Ready for Phase 4 — Macro Event Intelligence |
| **Tests** | 76 passed, 4 skipped (live Alpaca tests) |
| **Major limitation** | Mock data is synthetic (GBM); Alpaca provider not battle-tested in production |

See `docs/PROJECT_STATUS.md` for full development history and next steps.

---

## 18. Roadmap

Future phases (not yet implemented):

```
Market data (✓)
→ Unified event store (✓ Phase 3)
→ Macro event intelligence (Phase 4)
→ Company calendar / corporate events (Phase 5)
→ SEC + leadership + insider intelligence (Phase 6)
→ Earnings intelligence + reaction history (Phase 7)
→ News + management statement analysis (Phase 8)
→ Evidence validation + Answer Engine (Phase 9)
→ Website / dashboard (Phase 10)
→ Watchlists + calendar + alerts (Phase 11)
→ Historical event-impact analytics (Phase 12)
→ Strategy evaluation / paper trading (Phase 13)
```

---

## 19. Disclaimer

This software is intended for **research and educational purposes only**. It does not provide financial advice, guarantee profitability, or automatically place trades in its current version. Use at your own risk.

---

*Generated from a fresh-computer verification on a clean clone. All documented commands were tested and working.*