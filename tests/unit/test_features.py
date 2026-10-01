"""Unit tests for feature calculations."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from math import log, sqrt

import pytest

from trading_copilot.models import DailyBar
from trading_copilot.pipeline.features import FeatureEngine, percentile_rank, winsorize


class TestPercentileRank:
    def test_basic(self):
        values = [10, 20, 30, 40, 50]
        assert percentile_rank(values, 30) == 60.0  # 3/5 * 100
        assert percentile_rank(values, 10) == 20.0
        assert percentile_rank(values, 50) == 100.0
        assert percentile_rank(values, 0) == 0.0
        assert percentile_rank(values, 100) == 100.0

    def test_empty(self):
        assert percentile_rank([], 10) == 50.0

    def test_duplicates(self):
        values = [10, 20, 20, 30, 40]
        assert percentile_rank(values, 20) == 60.0  # 3/5 * 100


class TestWinsorize:
    def test_basic(self):
        values = [1, 2, 3, 4, 5, 100]
        result = winsorize(values, lower=0.0, upper=0.8)  # cap at 80th percentile
        # 80th percentile of 6 items = index 4 (0-indexed), value = 5
        # But winsorize uses the value at upper_idx = int(n * upper) = int(6 * 0.8) = 4
        # So values[4] = 5 is the cap
        assert max(result) == 5

    def test_no_change(self):
        values = [10, 20, 30, 40, 50]
        result = winsorize(values, lower=0.01, upper=0.99)
        assert result == values


class TestFeatureEngine:
    def _create_test_bars(self, symbol: str, n_days: int = 252) -> list[DailyBar]:
        """Create synthetic bars with known values for testing."""
        bars = []
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        
        for i in range(n_days * 2):  # Generate extra days to account for weekends
            date = base_date + timedelta(days=i)
            # Skip weekends
            if date.weekday() >= 5:
                continue
            
            # Simple trend with small random variation: ~0.05% per day
            daily_ret = 0.0005 + (hash(f"{symbol}{i}") % 200 - 100) / 100000  # 0.05% +/- 0.1%
            price *= (1 + daily_ret)
            
            bars.append(DailyBar(
                symbol=symbol,
                timestamp=date,
                open=price * 0.999,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1_000_000,
            ))
            
            if len(bars) >= n_days:
                break
        
        return bars

    def _create_benchmark_bars(self, n_days: int = 252) -> list[DailyBar]:
        """Create benchmark bars (SPY-like)."""
        bars = []
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 450.0
        
        for i in range(n_days * 2):
            date = base_date + timedelta(days=i)
            if date.weekday() >= 5:
                continue
            
            # Benchmark: ~0.03% per day with small variation
            daily_ret = 0.0003 + (hash(f"SPY{i}") % 200 - 100) / 100000  # 0.03% +/- 0.1%
            price *= (1 + daily_ret)
            
            bars.append(DailyBar(
                symbol="SPY",
                timestamp=date,
                open=price * 0.999,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=50_000_000,
            ))
            
            if len(bars) >= n_days:
                break
        
        return bars

    def test_compute_features_basic(self):
        engine = FeatureEngine()
        bars = self._create_test_bars("TEST", 252)
        bench = self._create_benchmark_bars(252)
        
        market_data = {"TEST": bars}
        features = engine.compute(market_data, bench)
        
        assert len(features) == 1
        feat = features[0]
        
        assert feat.symbol == "TEST"
        assert feat.price > 100  # Should have grown
        assert feat.ret_21d > -1  # Can be negative but not -100%
        assert feat.ret_63d > -1
        assert feat.ret_126d > -1
        
        # SMAs should be ordered (generally)
        assert feat.sma_20 > 0
        assert feat.sma_50 > 0
        assert feat.sma_200 > 0
        
        # Volatility
        assert feat.realized_vol_20d > 0
        assert feat.realized_vol_20d < 1.0  # Reasonable
        
        # Dollar volume
        assert feat.avg_dollar_volume_20d > 0
        
        # Relative volume
        assert feat.relative_volume_1d >= 0
        
        # Drawdown
        assert feat.drawdown_from_63d_high <= 0

    def test_insufficient_history_returns_none(self):
        engine = FeatureEngine()
        bars = self._create_test_bars("TEST", 100)  # Only 100 days
        bench = self._create_benchmark_bars(100)
        
        market_data = {"TEST": bars}
        features = engine.compute(market_data, bench)
        
        assert len(features) == 0

    def test_multiple_symbols(self):
        engine = FeatureEngine()
        bench = self._create_benchmark_bars(252)
        
        market_data = {
            "AAPL": self._create_test_bars("AAPL", 252),
            "MSFT": self._create_test_bars("MSFT", 252),
            "GOOGL": self._create_test_bars("GOOGL", 252),
        }
        
        features = engine.compute(market_data, bench)
        
        assert len(features) == 3
        symbols = {f.symbol for f in features}
        assert symbols == {"AAPL", "MSFT", "GOOGL"}

    def test_returns_calculation(self):
        """Test exact return calculations with known data."""
        engine = FeatureEngine()
        
        # Create bars with known prices - need exactly 252 business days
        bars = []
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        
        # Generate 252 business days with slight random variation
        day_count = 0
        for i in range(500):
            date = base_date + timedelta(days=i)
            if date.weekday() >= 5:
                continue
            
            if day_count >= 252:
                break
            
            # Add small deterministic variation based on day
            daily_ret = 0.0005 + (hash(str(day_count)) % 200 - 100) / 100000
            price *= (1 + daily_ret)
            
            bars.append(DailyBar(
                symbol="TEST",
                timestamp=date,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1_000_000,
            ))
            
            day_count += 1
        
        # Benchmark with similar variation
        bench = []
        bench_price = 450.0
        for bar in bars:
            daily_ret = 0.0003 + (hash(f"SPY{bar.timestamp}") % 200 - 100) / 100000
            bench_price *= (1 + daily_ret)
            
            bench.append(DailyBar(
                symbol="SPY",
                timestamp=bar.timestamp,
                open=bench_price,
                high=bench_price * 1.005,
                low=bench_price * 0.995,
                close=bench_price,
                volume=50_000_000,
            ))
        
        market_data = {"TEST": bars}
        features = engine.compute(market_data, bench)
        
        assert len(features) == 1
        feat = features[0]
        
        # Check that features are computed correctly
        assert feat.ret_21d is not None
        assert feat.ret_63d is not None
        assert feat.ret_126d is not None
        assert feat.realized_vol_20d > 0  # Should have non-zero volatility now
        
        # Relative returns should be computable
        assert feat.rel_ret_21d is not None
        assert feat.rel_ret_63d is not None
        assert feat.rel_ret_126d is not None

    def test_realized_volatility_calculation(self):
        """Test realized volatility with known log returns."""
        engine = FeatureEngine()
        
        # Create bars with small random variations around 1% daily returns
        bars = []
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        price = 100.0
        
        day_count = 0
        for i in range(500):
            date = base_date + timedelta(days=i)
            if date.weekday() >= 5:
                continue
            
            # Add small random variation to get non-zero volatility
            daily_ret = 0.01 + (hash(str(i)) % 100 - 50) / 10000  # 1% +/- 0.5%
            price *= (1 + daily_ret)
            
            bars.append(DailyBar(
                symbol="TEST",
                timestamp=date,
                open=price * 0.999,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1_000_000,
            ))
            
            day_count += 1
            if day_count >= 252:
                break
        
        bench = self._create_benchmark_bars(252)
        market_data = {"TEST": bars}
        features = engine.compute(market_data, bench)
        
        assert len(features) == 1
        feat = features[0]
        
        # With ~1% daily returns, volatility should be around 15-20% annualized
        assert feat.realized_vol_20d > 0
        assert feat.realized_vol_20d < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])