# Scoring and Signal Specification

The scoring system must be simple enough to audit by hand.

V1 is not an optimizer.

## 1. Quant score

Total deterministic quant score:

```text
Quant Score =
    40% Momentum
  + 25% Trend
  + 15% Liquidity
  + 10% Volume Confirmation
  + 10% Volatility Quality
```

Each component is 0–100.

## 2. Momentum score

Use cross-sectional percentile ranks.

Suggested raw composite:

```text
momentum_raw =
    0.20 * rel_ret_21d
  + 0.35 * rel_ret_63d
  + 0.30 * rel_ret_126d
  + 0.15 * ret_63d
```

Then percentile-rank `momentum_raw` across eligible stocks.

Why:
- relative returns matter,
- 1–6 month horizons are represented,
- the score remains explainable.

## 3. Trend score

Example:

```text
+35 if close > SMA200
+25 if close > SMA50
+15 if SMA50 > SMA200
+15 if close > SMA20
+10 based on positive distance from SMA50, capped
```

Cap at 100.

Do not reward extreme distance indefinitely.

## 4. Liquidity score

Percentile-rank 20-day average dollar volume.

Highly liquid names should score higher.

## 5. Volume confirmation

Percentile-rank relative volume, but cap the effect.

Do not make one abnormal volume day dominate the system.

## 6. Volatility quality

This is not "higher volatility = better."

Goal:
avoid both:
- dead names,
- chaotic names.

Simple V1 approach:
- percentile-rank realized volatility,
- reward middle-to-upper-middle range,
- penalize the extreme top tail.

Example deterministic mapping by volatility percentile:

```text
0–10 percentile   -> 35
10–30             -> 60
30–70             -> 100
70–90             -> 75
90–97             -> 50
97–100            -> 20
```

## 7. Catalyst score

The LLM does not emit this directly.

Map structured analysis:

### Direction base points

```text
positive -> 70
neutral  -> 50
mixed    -> 40
negative -> 10
```

### Strength adjustment

```text
high   +20
medium +10
low     +0
none   -10
```

### Evidence adjustment

```text
+10 if key catalyst has primary-source support
-20 if only weak/secondary source support
-40 if source validation fails
```

Clamp to [0, 100].

## 8. Final score

Recommended V1:

```text
Final Score =
    0.80 * Quant Score
  + 0.20 * Catalyst Score
```

Reason:
the LLM-supported catalyst layer should confirm or weaken a quantitatively interesting setup, not dominate it.

## 9. Hard risk gates

Exclude or mark review required if:

- critical market features are missing,
- primary source contradicts AI summary,
- evidence claims cite nonexistent source IDs,
- security is below liquidity threshold,
- source bundle contains a recent major negative event,
- optional event-exclusion rule is triggered.

## 10. Optional event exclusions

Configurable:

```yaml
exclude_earnings_within_days: 2
exclude_recent_major_negative_event_days: 3
```

These can be disabled for an earnings-drift strategy.

## 11. Top 20 and top 3

Top 20:
- rank by Quant Score.

Top 3:
- rank by Final Score after evidence analysis and risk gates.

This keeps LLM costs bounded and preserves the concept:

```text
quant first → AI research second
```

## 12. Score transparency

Every score must be decomposable.

Output example:

```json
{
  "symbol": "XYZ",
  "quant_score": 82.4,
  "components": {
    "momentum": 91.0,
    "trend": 85.0,
    "liquidity": 78.0,
    "volume": 70.0,
    "volatility_quality": 73.0
  },
  "catalyst_score": 76.0,
  "final_score": 81.1
}
```

Never output a mysterious "AI score."
