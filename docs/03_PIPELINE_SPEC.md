# Pipeline Specification

## Stage 0 — Run creation

Create:

```text
run_id = UTC timestamp
artifacts/runs/<run_id>/
```

Save:
- config snapshot,
- environment metadata excluding secrets,
- git commit if available,
- start time.

## Stage 1 — Build universe

Default universe strategy:
- U.S. listed common stocks,
- optionally ETFs,
- exclude symbols with insufficient history.

A simpler first implementation may use:
- S&P 500 constituents,
- or a fixed configurable watchlist.

The provider abstraction must allow the universe to change later.

## Stage 2 — Market eligibility

Default initial filters:

```yaml
min_price: 5
min_avg_dollar_volume_20d: 50_000_000
min_history_days: 220
```

These are configuration defaults, not universal truths.

Reject symbols with:
- stale data,
- missing close/volume,
- insufficient history,
- non-positive prices,
- extreme data corruption.

## Stage 3 — Feature calculation

Required features:

```text
ret_21d
ret_63d
ret_126d
spy_ret_21d
spy_ret_63d
spy_ret_126d
rel_ret_21d
rel_ret_63d
rel_ret_126d
sma_20
sma_50
sma_200
dist_sma_20_pct
dist_sma_50_pct
dist_sma_200_pct
realized_vol_20d
avg_dollar_volume_20d
relative_volume_1d
drawdown_from_63d_high
```

Definitions:

```text
ret_Nd = close_t / close_(t-N) - 1

rel_ret_Nd = stock_ret_Nd - SPY_ret_Nd

realized_vol_20d =
    std(daily_log_returns over 20 sessions) * sqrt(252)

avg_dollar_volume_20d =
    mean(close * volume over 20 sessions)

relative_volume_1d =
    latest_volume / mean(volume previous 20 sessions)
```

## Stage 4 — Quant normalization

Within the eligible universe:
- winsorize extreme values,
- percentile-rank or z-score features.

Prefer percentile ranks for V1 because they are easy to inspect.

## Stage 5 — Quant score

Use the scoring spec in `05_SCORING_AND_SIGNALS.md`.

Produce:
- total score,
- every component,
- every raw feature.

## Stage 6 — Top 20

Take top N by quant score.

Tie-breaker:
1. higher 20-day dollar volume,
2. symbol alphabetical.

This ensures deterministic ordering.

## Stage 7 — Collect evidence

For each top-20 symbol, retrieve source material from a configurable lookback.

Suggested initial lookbacks:
- news: 7 calendar days,
- filings: 45 calendar days,
- earnings-related source: most recent quarter plus prior quarter if available.

Prioritize:
- earnings release,
- 8-K,
- 10-Q,
- 10-K,
- guidance changes,
- material corporate announcements.

Do not analyze hundreds of articles.

Suggested maximum:
- 8 news items,
- 4 filings,
- 2 earnings-related documents per symbol.

## Stage 8 — Deduplicate

Deduplicate on:
- canonical URL,
- exact content hash,
- near-identical title + timestamp.

## Stage 9 — AI analysis

The LLM receives:
- symbol,
- feature summary,
- source bundle.

It does not receive final score weights.

It returns structured evidence analysis only.

## Stage 10 — Catalyst score

Convert structured output into deterministic points.

Examples:
- raised guidance supported by filing,
- positive earnings surprise supported by source,
- strong product/regulatory/company catalyst,
- negative legal/regulatory/earnings development,
- no meaningful catalyst.

LLM text does not directly add arbitrary points.

## Stage 11 — Risk gates

Potential disqualifiers:
- recent materially negative filing,
- imminent binary event if strategy forbids it,
- liquidity failure,
- source inconsistency,
- data quality failure.

A risk gate may:
- exclude candidate,
- cap final score,
- mark candidate "review required".

## Stage 12 — Optional options metrics

Only if data is available.

Collect:
- nearest liquid expirations,
- bid/ask,
- open interest,
- volume,
- IV,
- delta,
- spread percentage.

Do not use options data to select the stock in V1 unless explicitly enabled.

Use it only to answer:
"Is there a reasonably liquid options market if the human later chooses an options expression?"

## Stage 13 — Final ranking

Compute deterministic final score.

Generate top 3.

## Stage 14 — Report

Write:
- top20.csv
- top3.json
- top3.md
- all_features.parquet/csv
- sources.jsonl
- ai_analysis.jsonl
- errors.jsonl
- run_manifest.json

## Stage 15 — Human decision

End of V1 pipeline.

No broker execution.
