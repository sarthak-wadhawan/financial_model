"""Unit tests for quant scoring."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_copilot.config import QuantWeights
from trading_copilot.models import FeatureRow
from trading_copilot.pipeline.quant_score import QuantScorer


class TestQuantScorer:
    @pytest.fixture
    def weights(self) -> QuantWeights:
        return QuantWeights(
            momentum_weight=0.40,
            trend_weight=0.25,
            liquidity_weight=0.15,
            volume_weight=0.10,
            volatility_weight=0.10,
        )

    @pytest.fixture
    def scorer(self, weights: QuantWeights) -> QuantScorer:
        return QuantScorer(weights)

    @pytest.fixture
    def feature_rows(self) -> list[FeatureRow]:
        """Create diverse feature rows for testing scoring."""
        base_time = datetime.now(timezone.utc)
        rows = []
        
        # Strong momentum, strong trend, high liquidity
        rows.append(FeatureRow(
            symbol="STRONG",
            as_of=base_time,
            price=150.0,
            ret_21d=0.10, ret_63d=0.25, ret_126d=0.50,
            rel_ret_21d=0.05, rel_ret_63d=0.15, rel_ret_126d=0.30,
            sma_20=145.0, sma_50=130.0, sma_200=110.0,
            dist_sma_20_pct=0.034, dist_sma_50_pct=0.154, dist_sma_200_pct=0.364,
            realized_vol_20d=0.25,
            avg_dollar_volume_20d=500_000_000,
            relative_volume_1d=1.2,
            drawdown_from_63d_high=-0.02,
        ))
        
        # Weak momentum, weak trend, low liquidity
        rows.append(FeatureRow(
            symbol="WEAK",
            as_of=base_time,
            price=20.0,
            ret_21d=-0.05, ret_63d=-0.10, ret_126d=-0.20,
            rel_ret_21d=-0.03, rel_ret_63d=-0.08, rel_ret_126d=-0.15,
            sma_20=21.0, sma_50=22.0, sma_200=25.0,
            dist_sma_20_pct=-0.048, dist_sma_50_pct=-0.091, dist_sma_200_pct=-0.200,
            realized_vol_20d=0.60,
            avg_dollar_volume_20d=10_000_000,
            relative_volume_1d=0.5,
            drawdown_from_63d_high=-0.30,
        ))
        
        # Medium everything
        rows.append(FeatureRow(
            symbol="MEDIUM",
            as_of=base_time,
            price=100.0,
            ret_21d=0.02, ret_63d=0.05, ret_126d=0.10,
            rel_ret_21d=0.01, rel_ret_63d=0.02, rel_ret_126d=0.03,
            sma_20=99.0, sma_50=98.0, sma_200=95.0,
            dist_sma_20_pct=0.01, dist_sma_50_pct=0.02, dist_sma_200_pct=0.05,
            realized_vol_20d=0.30,
            avg_dollar_volume_20d=100_000_000,
            relative_volume_1d=1.0,
            drawdown_from_63d_high=-0.05,
        ))
        
        # High volatility (should get lower vol quality score)
        rows.append(FeatureRow(
            symbol="HIGHVOL",
            as_of=base_time,
            price=80.0,
            ret_21d=0.15, ret_63d=0.30, ret_126d=0.40,
            rel_ret_21d=0.10, rel_ret_63d=0.20, rel_ret_126d=0.25,
            sma_20=75.0, sma_50=70.0, sma_200=65.0,
            dist_sma_20_pct=0.067, dist_sma_50_pct=0.143, dist_sma_200_pct=0.231,
            realized_vol_20d=0.80,  # Very high vol
            avg_dollar_volume_20d=200_000_000,
            relative_volume_1d=1.5,
            drawdown_from_63d_high=-0.10,
        ))
        
        # Low volatility (should get lower vol quality score)
        rows.append(FeatureRow(
            symbol="LOWVOL",
            as_of=base_time,
            price=120.0,
            ret_21d=0.01, ret_63d=0.03, ret_126d=0.05,
            rel_ret_21d=0.005, rel_ret_63d=0.01, rel_ret_126d=0.015,
            sma_20=119.0, sma_50=118.0, sma_200=115.0,
            dist_sma_20_pct=0.008, dist_sma_50_pct=0.017, dist_sma_200_pct=0.043,
            realized_vol_20d=0.05,  # Very low vol
            avg_dollar_volume_20d=80_000_000,
            relative_volume_1d=0.8,
            drawdown_from_63d_high=-0.02,
        ))
        
        return rows

    def test_scores_in_bounds(self, scorer: QuantScorer, feature_rows: list[FeatureRow]):
        scores = scorer.score(feature_rows)
        
        for s in scores:
            assert 0 <= s.quant_score <= 100
            assert 0 <= s.momentum_score <= 100
            assert 0 <= s.trend_score <= 100
            assert 0 <= s.liquidity_score <= 100
            assert 0 <= s.volume_score <= 100
            assert 0 <= s.volatility_score <= 100

    def test_components_dict_complete(self, scorer: QuantScorer, feature_rows: list[FeatureRow]):
        scores = scorer.score(feature_rows)
        
        for s in scores:
            assert set(s.components.keys()) == {
                "momentum", "trend", "liquidity", "volume", "volatility_quality"
            }
            for v in s.components.values():
                assert 0 <= v <= 100

    def test_ranking_order(self, scorer: QuantScorer, feature_rows: list[FeatureRow]):
        scores = scorer.score(feature_rows)
        
        # Should be sorted by quant_score descending
        quant_scores = [s.quant_score for s in scores]
        assert quant_scores == sorted(quant_scores, reverse=True)

    def test_strong_beats_weak(self, scorer: QuantScorer, feature_rows: list[FeatureRow]):
        scores = scorer.score(feature_rows)
        
        symbols = [s.symbol for s in scores]
        strong_idx = symbols.index("STRONG")
        weak_idx = symbols.index("WEAK")
        
        assert strong_idx < weak_idx  # STRONG should rank higher

    def test_deterministic_output(self, scorer: QuantScorer, feature_rows: list[FeatureRow]):
        scores1 = scorer.score(feature_rows)
        scores2 = scorer.score(feature_rows)
        
        for s1, s2 in zip(scores1, scores2):
            assert s1.symbol == s2.symbol
            assert s1.quant_score == s2.quant_score
            assert s1.momentum_score == s2.momentum_score
            assert s1.trend_score == s2.trend_score
            assert s1.liquidity_score == s2.liquidity_score
            assert s1.volume_score == s2.volume_score
            assert s1.volatility_score == s2.volatility_score

    def test_tie_breaker_by_volume(self, scorer: QuantScorer):
        """Test tie-breaking by dollar volume then symbol."""
        base_time = datetime.now(timezone.utc)
        
        # Two symbols with identical features except volume
        rows = [
            FeatureRow(
                symbol="HIGHVOL",
                as_of=base_time,
                price=100.0,
                ret_21d=0.05, ret_63d=0.10, ret_126d=0.20,
                rel_ret_21d=0.02, rel_ret_63d=0.05, rel_ret_126d=0.10,
                sma_20=98.0, sma_50=95.0, sma_200=90.0,
                dist_sma_20_pct=0.02, dist_sma_50_pct=0.05, dist_sma_200_pct=0.11,
                realized_vol_20d=0.25,
                avg_dollar_volume_20d=200_000_000,  # Higher volume
                relative_volume_1d=1.0,
                drawdown_from_63d_high=-0.02,
            ),
            FeatureRow(
                symbol="LOWVOL",
                as_of=base_time,
                price=100.0,
                ret_21d=0.05, ret_63d=0.10, ret_126d=0.20,
                rel_ret_21d=0.02, rel_ret_63d=0.05, rel_ret_126d=0.10,
                sma_20=98.0, sma_50=95.0, sma_200=90.0,
                dist_sma_20_pct=0.02, dist_sma_50_pct=0.05, dist_sma_200_pct=0.11,
                realized_vol_20d=0.25,
                avg_dollar_volume_20d=100_000_000,  # Lower volume
                relative_volume_1d=1.0,
                drawdown_from_63d_high=-0.02,
            ),
        ]
        
        scores = scorer.score(rows)
        assert scores[0].symbol == "HIGHVOL"
        assert scores[1].symbol == "LOWVOL"

    def test_tie_breaker_by_symbol(self, scorer: QuantScorer):
        """Test tie-breaking by symbol when volume also equal."""
        base_time = datetime.now(timezone.utc)
        
        rows = [
            FeatureRow(
                symbol="BBB",
                as_of=base_time,
                price=100.0,
                ret_21d=0.05, ret_63d=0.10, ret_126d=0.20,
                rel_ret_21d=0.02, rel_ret_63d=0.05, rel_ret_126d=0.10,
                sma_20=98.0, sma_50=95.0, sma_200=90.0,
                dist_sma_20_pct=0.02, dist_sma_50_pct=0.05, dist_sma_200_pct=0.11,
                realized_vol_20d=0.25,
                avg_dollar_volume_20d=100_000_000,
                relative_volume_1d=1.0,
                drawdown_from_63d_high=-0.02,
            ),
            FeatureRow(
                symbol="AAA",
                as_of=base_time,
                price=100.0,
                ret_21d=0.05, ret_63d=0.10, ret_126d=0.20,
                rel_ret_21d=0.02, rel_ret_63d=0.05, rel_ret_126d=0.10,
                sma_20=98.0, sma_50=95.0, sma_200=90.0,
                dist_sma_20_pct=0.02, dist_sma_50_pct=0.05, dist_sma_200_pct=0.11,
                realized_vol_20d=0.25,
                avg_dollar_volume_20d=100_000_000,
                relative_volume_1d=1.0,
                drawdown_from_63d_high=-0.02,
            ),
        ]
        
        scores = scorer.score(rows)
        assert scores[0].symbol == "AAA"  # Alphabetical
        assert scores[1].symbol == "BBB"

    def test_volatility_quality_mapping(self, scorer: QuantScorer):
        """Test that volatility quality score follows the specified mapping."""
        base_time = datetime.now(timezone.utc)
        
        # Create symbols with different volatility percentiles
        rows = []
        for i, vol in enumerate([0.05, 0.15, 0.25, 0.35, 0.55, 0.75, 0.95]):
            rows.append(FeatureRow(
                symbol=f"VOL{i}",
                as_of=base_time,
                price=100.0,
                ret_21d=0.05, ret_63d=0.10, ret_126d=0.20,
                rel_ret_21d=0.02, rel_ret_63d=0.05, rel_ret_126d=0.10,
                sma_20=98.0, sma_50=95.0, sma_200=90.0,
                dist_sma_20_pct=0.02, dist_sma_50_pct=0.05, dist_sma_200_pct=0.11,
                realized_vol_20d=vol,
                avg_dollar_volume_20d=100_000_000,
                relative_volume_1d=1.0,
                drawdown_from_63d_high=-0.02,
            ))
        
        scores = scorer.score(rows)
        
        # Find volatility scores
        vol_scores = {s.symbol: s.volatility_score for s in scores}
        
        # Check mapping: 0-10->35, 10-30->60, 30-70->100, 70-90->75, 90-97->50, 97-100->20
        # With 7 symbols, percentiles are roughly: 14, 29, 43, 57, 71, 86, 100
        # So: 14->60, 29->60, 43->100, 57->100, 71->75, 86->75, 100->20
        assert vol_scores["VOL0"] == 60.0   # 10-30 percentile (14th percentile)
        assert vol_scores["VOL1"] == 60.0   # 10-30
        assert vol_scores["VOL2"] == 100.0  # 30-70
        assert vol_scores["VOL3"] == 100.0  # 30-70
        assert vol_scores["VOL4"] == 75.0   # 70-90
        assert vol_scores["VOL5"] == 75.0   # 70-90
        assert vol_scores["VOL6"] == 20.0   # 97-100

    def test_empty_input(self, scorer: QuantScorer):
        scores = scorer.score([])
        assert scores == []

    def test_weight_validation(self):
        """Test that weights must sum to 1.0."""
        with pytest.raises(ValueError):
            QuantWeights(
                momentum_weight=0.50,
                trend_weight=0.25,
                liquidity_weight=0.15,
                volume_weight=0.10,
                volatility_weight=0.10,  # Sums to 1.1
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])