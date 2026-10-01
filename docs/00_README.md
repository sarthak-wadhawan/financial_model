# AI Trading Research Copilot — Development Handoff

## Goal

Build a small, auditable research system that:

1. Scans a liquid U.S. equity universe.
2. Scores stocks using deterministic market features.
3. Keeps the top 20 candidates.
4. Pulls recent earnings/news/SEC filings for those candidates.
5. Uses an LLM only to extract and summarize catalysts, guidance changes, risks, and source-backed facts.
6. Combines deterministic quant scores with structured catalyst information.
7. Produces the top 3 research candidates.
8. Generates a concise research brief for human review.
9. Does **not** place trades automatically in V1.

The system is a research copilot, not an autonomous trading bot.

## Core design principle

The trading hypothesis must remain understandable without the LLM.

The LLM may:
- summarize documents,
- compare new language with prior language,
- classify catalysts,
- identify risks,
- structure unstructured information.

The LLM may not:
- invent market data,
- invent earnings figures,
- create undocumented news,
- override hard risk filters,
- submit orders,
- silently alter deterministic scores.

## V1 Output

For each run:

- Run timestamp
- Universe size
- Eligible stock count
- Top 20 quant candidates
- Sources collected for each candidate
- AI catalyst analysis
- Final ranked shortlist
- Top 3 research briefs
- Full audit log

## Recommended implementation stack

- Python 3.12+
- pandas or polars
- numpy
- pydantic
- httpx
- typer
- pytest
- python-dotenv
- tenacity
- rich
- optional: duckdb
- optional: scikit-learn only for scaling/utility work, not required for V1 signals

## Data providers

Use provider interfaces.

Preferred initial providers:
- Market data: Alpaca
- News: Alpaca News if available, otherwise another provider adapter
- SEC filings: SEC EDGAR
- Options metrics: Alpaca options if entitlement exists; otherwise leave module disabled
- Benchmark: SPY

Do not hard-code the system to one provider.

## V1 CLI

Example:

```bash
python -m trading_copilot scan --config config.yaml
python -m trading_copilot run --config config.yaml
python -m trading_copilot explain AAPL --run-id 2026-09-30T160000Z
python -m trading_copilot validate-run --run-id 2026-09-30T160000Z
```

## Non-goals for V1

Do not build:
- automated brokerage execution,
- portfolio optimization,
- reinforcement learning,
- neural price prediction,
- intraday HFT,
- market making,
- social-media sentiment scraping,
- a giant agent framework,
- a web dashboard before the CLI works,
- an options strategy optimizer.

## Success definition

V1 is successful when one command reliably produces a reproducible, source-backed top-3 research shortlist from the same frozen inputs.
