"""Feature engineering for market data."""

from __future__ import annotations

from datetime import datetime, timezone
from math import log, sqrt
from statistics import mean, stdev

import pandas as pd

from trading_copilot.models import DailyBar, FeatureRow


class FeatureEngine:
    """Compute deterministic features from daily bar data."""

    def compute(
        self,
        market_data: dict[str, list[DailyBar]],
        benchmark_bars: list[DailyBar] | None = None,
    ) -> list[FeatureRow]:
        """Compute features for all symbols with sufficient data."""
        # Build benchmark lookup
        bench_lookup = {}
        if benchmark_bars:
            for bar in benchmark_bars:
                bench_lookup[bar.timestamp.date()] = bar.close
        
        feature_rows = []
        
        for symbol, bars in market_data.items():
            try:
                row = self._compute_symbol_features(symbol, bars, bench_lookup)
                if row:
                    feature_rows.append(row)
            except Exception as e:
                # Log and continue - don't fail the entire batch
                import logging
                logging.getLogger(__name__).warning(
                    "Feature computation failed for %s: %s", symbol, e
                )
                continue
        
        return feature_rows

    def _compute_symbol_features(
        self,
        symbol: str,
        bars: list[DailyBar],
        bench_lookup: dict,
    ) -> FeatureRow | None:
        """Compute features for a single symbol."""
        if len(bars) < 220:  # Need at least 220 days for 126-day return + SMA200
            return None
        
        # Sort bars by timestamp
        bars = sorted(bars, key=lambda b: b.timestamp)
        
        # Convert to DataFrame for easier computation
        df = pd.DataFrame([
            {
                "date": b.timestamp.date(),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ])
        
        # Ensure we have enough data
        if len(df) < 220:
            return None
        
        # Latest values
        latest_close = df["close"].iloc[-1]
        latest_volume = df["volume"].iloc[-1]
        as_of = datetime.combine(df["date"].iloc[-1], datetime.min.time(), tzinfo=timezone.utc)
        
        # Returns
        close_t = df["close"].iloc[-1]
        close_21d = df["close"].iloc[-21] if len(df) >= 21 else df["close"].iloc[0]
        close_63d = df["close"].iloc[-63] if len(df) >= 63 else df["close"].iloc[0]
        close_126d = df["close"].iloc[-126] if len(df) >= 126 else df["close"].iloc[0]
        
        ret_21d = close_t / close_21d - 1
        ret_63d = close_t / close_63d - 1
        ret_126d = close_t / close_126d - 1
        
        # Benchmark returns
        spy_ret_21d = self._get_bench_return(bench_lookup, df["date"].iloc[-1], df["date"].iloc[-21])
        spy_ret_63d = self._get_bench_return(bench_lookup, df["date"].iloc[-1], df["date"].iloc[-63])
        spy_ret_126d = self._get_bench_return(bench_lookup, df["date"].iloc[-1], df["date"].iloc[-126])
        
        rel_ret_21d = ret_21d - spy_ret_21d
        rel_ret_63d = ret_63d - spy_ret_63d
        rel_ret_126d = ret_126d - spy_ret_126d
        
        # Moving averages
        sma_20 = df["close"].tail(20).mean()
        sma_50 = df["close"].tail(50).mean()
        sma_200 = df["close"].tail(200).mean()
        
        # Distance from MAs
        dist_sma_20_pct = (latest_close - sma_20) / sma_20
        dist_sma_50_pct = (latest_close - sma_50) / sma_50
        dist_sma_200_pct = (latest_close - sma_200) / sma_200
        
        # Realized volatility (20-day)
        log_returns = []
        for i in range(1, min(21, len(df))):
            log_returns.append(log(df["close"].iloc[-i] / df["close"].iloc[-i-1]))
        realized_vol_20d = stdev(log_returns) * sqrt(252) if len(log_returns) > 1 else 0.0
        
        # Average dollar volume (20-day)
        dollar_vols = (df["close"] * df["volume"]).tail(20)
        avg_dollar_volume_20d = dollar_vols.mean()
        
        # Relative volume (1-day vs 20-day avg)
        avg_volume_20d = df["volume"].tail(20).mean()
        relative_volume_1d = latest_volume / avg_volume_20d if avg_volume_20d > 0 else 0.0
        
        # Drawdown from 63-day high
        high_63d = df["close"].tail(63).max()
        drawdown_from_63d_high = (latest_close - high_63d) / high_63d
        
        return FeatureRow(
            symbol=symbol,
            as_of=as_of,
            price=latest_close,
            ret_21d=ret_21d,
            ret_63d=ret_63d,
            ret_126d=ret_126d,
            rel_ret_21d=rel_ret_21d,
            rel_ret_63d=rel_ret_63d,
            rel_ret_126d=rel_ret_126d,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            dist_sma_20_pct=dist_sma_20_pct,
            dist_sma_50_pct=dist_sma_50_pct,
            dist_sma_200_pct=dist_sma_200_pct,
            realized_vol_20d=realized_vol_20d,
            avg_dollar_volume_20d=avg_dollar_volume_20d,
            relative_volume_1d=relative_volume_1d,
            drawdown_from_63d_high=drawdown_from_63d_high,
        )

    def _get_bench_return(
        self,
        bench_lookup: dict,
        end_date,
        start_date,
    ) -> float:
        """Get benchmark return for a period."""
        end_close = bench_lookup.get(end_date)
        start_close = bench_lookup.get(start_date)
        
        if end_close is None or start_close is None or start_close == 0:
            return 0.0
        
        return end_close / start_close - 1


def percentile_rank(values: list[float], target: float) -> float:
    """Compute percentile rank (0-100) of target within values."""
    if not values:
        return 50.0
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    # Count values <= target
    count = sum(1 for v in sorted_vals if v <= target)
    
    # Percentile rank (0-100)
    return (count / n) * 100


def winsorize(values: list[float], lower: float = 0.01, upper: float = 0.99) -> list[float]:
    """Winsorize values at given percentiles."""
    if not values:
        return values
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    lower_idx = max(0, int(n * lower))
    upper_idx = min(n - 1, int(n * upper))
    
    lower_val = sorted_vals[lower_idx]
    upper_val = sorted_vals[upper_idx]
    
    return [max(lower_val, min(upper_val, v)) for v in values]