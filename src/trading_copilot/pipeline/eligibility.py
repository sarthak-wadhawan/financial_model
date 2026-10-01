"""Eligibility filtering for symbols."""

from __future__ import annotations

from trading_copilot.config import EligibilityConfig
from trading_copilot.models import FeatureRow, EligibilityResult


class EligibilityFilter:
    """Apply eligibility filters to feature rows."""

    def __init__(self, config: EligibilityConfig):
        self.config = config

    def apply(self, feature_rows: list[FeatureRow]) -> list[FeatureRow]:
        """Filter feature rows based on eligibility criteria."""
        eligible = []
        
        for row in feature_rows:
            result = self._check_eligibility(row)
            if result.eligible:
                eligible.append(row)
        
        return eligible

    def _check_eligibility(self, row: FeatureRow) -> EligibilityResult:
        """Check if a single symbol meets eligibility criteria."""
        reasons = []
        
        # Minimum price
        if row.price < self.config.min_price:
            reasons.append(f"price_below_min: {row.price:.2f} < {self.config.min_price}")
        
        # Minimum average dollar volume
        if row.avg_dollar_volume_20d < self.config.min_avg_dollar_volume_20d:
            reasons.append(
                f"avg_dollar_volume_below_min: "
                f"{row.avg_dollar_volume_20d:,.0f} < {self.config.min_avg_dollar_volume_20d:,.0f}"
            )
        
        # Minimum history - implicit in feature computation (requires 220 bars)
        # but we can also check data quality
        if row.realized_vol_20d <= 0:
            reasons.append("invalid_volatility: realized_vol_20d <= 0")
        
        if row.avg_dollar_volume_20d <= 0:
            reasons.append("invalid_volume: avg_dollar_volume_20d <= 0")
        
        # Check for extreme data corruption
        if row.price <= 0:
            reasons.append("non_positive_price")
        
        if row.sma_20 <= 0 or row.sma_50 <= 0 or row.sma_200 <= 0:
            reasons.append("invalid_moving_averages")
        
        eligible = len(reasons) == 0
        
        return EligibilityResult(
            symbol=row.symbol,
            eligible=eligible,
            reasons=reasons,
        )


def get_eligibility_report(
    feature_rows: list[FeatureRow],
    config: EligibilityConfig,
) -> list[EligibilityResult]:
    """Get detailed eligibility results for all symbols."""
    filter = EligibilityFilter(config)
    return [filter._check_eligibility(row) for row in feature_rows]