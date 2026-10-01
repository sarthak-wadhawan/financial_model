"""Unit tests for eligibility filtering."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from trading_copilot.config import EligibilityConfig
from trading_copilot.models import DailyBar, FeatureRow
from trading_copilot.pipeline.eligibility import EligibilityFilter, get_eligibility_report


class TestEligibilityFilter:
    @pytest.fixture
    def config(self) -> EligibilityConfig:
        return EligibilityConfig(
            min_price=5.0,
            min_avg_dollar_volume_20d=50_000_000,
            min_history_days=220,
        )

    @pytest.fixture
    def filter(self, config: EligibilityConfig) -> EligibilityFilter:
        return EligibilityFilter(config)

    @pytest.fixture
    def valid_feature_row(self) -> FeatureRow:
        """Create a valid feature row that passes all filters."""
        return FeatureRow(
            symbol="VALID",
            as_of=datetime.now(timezone.utc),
            price=100.0,
            ret_21d=0.05,
            ret_63d=0.15,
            ret_126d=0.30,
            rel_ret_21d=0.02,
            rel_ret_63d=0.05,
            rel_ret_126d=0.10,
            sma_20=99.0,
            sma_50=95.0,
            sma_200=90.0,
            dist_sma_20_pct=0.01,
            dist_sma_50_pct=0.05,
            dist_sma_200_pct=0.11,
            realized_vol_20d=0.25,
            avg_dollar_volume_20d=100_000_000,
            relative_volume_1d=1.0,
            drawdown_from_63d_high=-0.05,
        )

    def test_valid_symbol_passes(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        result = filter._check_eligibility(valid_feature_row)
        assert result.eligible is True
        assert result.reasons == []

    def test_low_price_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"price": 4.0})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("price_below_min" in r for r in result.reasons)

    def test_low_liquidity_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"avg_dollar_volume_20d": 10_000_000})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("avg_dollar_volume_below_min" in r for r in result.reasons)

    def test_invalid_volatility_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"realized_vol_20d": 0.0})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("invalid_volatility" in r for r in result.reasons)

    def test_invalid_volume_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"avg_dollar_volume_20d": 0.0})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("invalid_volume" in r for r in result.reasons)

    def test_non_positive_price_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"price": 0.0})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("non_positive_price" in r for r in result.reasons)

    def test_invalid_moving_averages_rejected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={"sma_20": 0.0})
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert any("invalid_moving_averages" in r for r in result.reasons)

    def test_multiple_reasons_collected(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        row = valid_feature_row.model_copy(update={
            "price": 4.0,
            "avg_dollar_volume_20d": 10_000_000,
            "realized_vol_20d": 0.0,
        })
        result = filter._check_eligibility(row)
        assert result.eligible is False
        assert len(result.reasons) == 3

    def test_apply_filters_list(self, filter: EligibilityFilter, valid_feature_row: FeatureRow):
        rows = [
            valid_feature_row,
            valid_feature_row.model_copy(update={"symbol": "LOW_PRICE", "price": 4.0}),
            valid_feature_row.model_copy(update={"symbol": "LOW_VOL", "avg_dollar_volume_20d": 10_000_000}),
            valid_feature_row.model_copy(update={"symbol": "ALSO_VALID"}),
        ]
        
        eligible = filter.apply(rows)
        
        assert len(eligible) == 2
        symbols = {r.symbol for r in eligible}
        assert symbols == {"VALID", "ALSO_VALID"}

    def test_get_eligibility_report(self, config: EligibilityConfig, valid_feature_row: FeatureRow):
        rows = [
            valid_feature_row,
            valid_feature_row.model_copy(update={"symbol": "LOW_PRICE", "price": 4.0}),
        ]
        
        report = get_eligibility_report(rows, config)
        
        assert len(report) == 2
        assert report[0].symbol == "VALID"
        assert report[0].eligible is True
        assert report[1].symbol == "LOW_PRICE"
        assert report[1].eligible is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])