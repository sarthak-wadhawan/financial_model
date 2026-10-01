"""Quant scoring implementation."""

from __future__ import annotations

from trading_copilot.config import QuantWeights
from trading_copilot.models import FeatureRow, QuantScore
from trading_copilot.pipeline.features import percentile_rank, winsorize


class QuantScorer:
    """Compute deterministic quant scores from features."""

    def __init__(self, weights: QuantWeights):
        self.weights = weights

    def score(self, feature_rows: list[FeatureRow]) -> list[QuantScore]:
        """Score all eligible feature rows."""
        if not feature_rows:
            return []
        
        # Extract raw component values for cross-sectional ranking
        momentum_raw_values = [self._momentum_raw(row) for row in feature_rows]
        trend_raw_values = [self._trend_raw(row) for row in feature_rows]
        liquidity_raw_values = [row.avg_dollar_volume_20d for row in feature_rows]
        volume_raw_values = [row.relative_volume_1d for row in feature_rows]
        volatility_raw_values = [row.realized_vol_20d for row in feature_rows]
        
        # Winsorize extreme values
        momentum_raw_values = winsorize(momentum_raw_values)
        trend_raw_values = winsorize(trend_raw_values)
        liquidity_raw_values = winsorize(liquidity_raw_values)
        volume_raw_values = winsorize(volume_raw_values)
        volatility_raw_values = winsorize(volatility_raw_values)
        
        # Compute scores for each symbol
        scores = []
        for i, row in enumerate(feature_rows):
            # Momentum score (percentile rank of momentum_raw)
            momentum_score = percentile_rank(momentum_raw_values, momentum_raw_values[i])
            
            # Trend score (deterministic mapping)
            trend_score = self._trend_score(row)
            
            # Liquidity score (percentile rank of avg dollar volume)
            liquidity_score = percentile_rank(liquidity_raw_values, liquidity_raw_values[i])
            
            # Volume confirmation score (percentile rank of relative volume, capped)
            volume_score = min(percentile_rank(volume_raw_values, volume_raw_values[i]), 100)
            
            # Volatility quality score (deterministic mapping by percentile)
            vol_percentile = percentile_rank(volatility_raw_values, volatility_raw_values[i])
            volatility_score = self._volatility_quality_score(vol_percentile)
            
            # Total quant score (weighted average)
            quant_score = (
                self.weights.momentum_weight * momentum_score
                + self.weights.trend_weight * trend_score
                + self.weights.liquidity_weight * liquidity_score
                + self.weights.volume_weight * volume_score
                + self.weights.volatility_weight * volatility_score
            )
            
            components = {
                "momentum": momentum_score,
                "trend": trend_score,
                "liquidity": liquidity_score,
                "volume": volume_score,
                "volatility_quality": volatility_score,
            }
            
            scores.append(QuantScore(
                symbol=row.symbol,
                momentum_score=momentum_score,
                trend_score=trend_score,
                liquidity_score=liquidity_score,
                volume_score=volume_score,
                volatility_score=volatility_score,
                quant_score=quant_score,
                components=components,
            ))
        
        # Sort by quant_score descending, tie-break by avg_dollar_volume_20d descending, then symbol
        scores.sort(
            key=lambda s: (
                -s.quant_score,
                -next(r.avg_dollar_volume_20d for r in feature_rows if r.symbol == s.symbol),
                s.symbol,
            )
        )
        
        return scores

    def _momentum_raw(self, row: FeatureRow) -> float:
        """Compute raw momentum composite."""
        return (
            0.20 * row.rel_ret_21d
            + 0.35 * row.rel_ret_63d
            + 0.30 * row.rel_ret_126d
            + 0.15 * row.ret_63d
        )

    def _trend_raw(self, row: FeatureRow) -> float:
        """Compute raw trend composite for winsorizing."""
        score = 0.0
        if row.price > row.sma_200:
            score += 35
        if row.price > row.sma_50:
            score += 25
        if row.sma_50 > row.sma_200:
            score += 15
        if row.price > row.sma_20:
            score += 15
        # Distance from SMA50 (capped)
        dist_pct = row.dist_sma_50_pct
        if dist_pct > 0:
            score += min(dist_pct * 100, 10)  # Cap at 10 points
        return score

    def _trend_score(self, row: FeatureRow) -> float:
        """Compute trend score (0-100)."""
        score = 0.0
        if row.price > row.sma_200:
            score += 35
        if row.price > row.sma_50:
            score += 25
        if row.sma_50 > row.sma_200:
            score += 15
        if row.price > row.sma_20:
            score += 15
        # Distance from SMA50 (capped)
        dist_pct = row.dist_sma_50_pct
        if dist_pct > 0:
            score += min(dist_pct * 100, 10)  # Cap at 10 points
        return min(score, 100.0)

    def _volatility_quality_score(self, vol_percentile: float) -> float:
        """Map volatility percentile to quality score."""
        if vol_percentile <= 10:
            return 35.0
        elif vol_percentile <= 30:
            return 60.0
        elif vol_percentile <= 70:
            return 100.0
        elif vol_percentile <= 90:
            return 75.0
        elif vol_percentile <= 97:
            return 50.0
        else:
            return 20.0