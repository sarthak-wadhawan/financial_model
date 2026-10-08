"""Unit tests for EarningsReactionProvider."""

from __future__ import annotations

import tempfile
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest
import pandas as pd

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.models.market import DailyBar
from trading_copilot.providers.earnings_reaction import (
    EarningsReactionProvider,
    ReactionWindow,
    BenchmarkReaction,
)
from trading_copilot.providers.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """Mock market data provider for testing."""
    
    def __init__(self, bars: dict[str, list[DailyBar]] | None = None):
        self._bars = bars or {}
    
    def get_daily_bars(
        self,
        symbols: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, list[DailyBar]]:
        result = {}
        for symbol in symbols:
            if symbol in self._bars:
                # Filter bars by date range
                filtered = [
                    bar for bar in self._bars[symbol]
                    if start <= bar.timestamp <= end
                ]
                result[symbol] = filtered
            else:
                result[symbol] = []
        return result
    
    def get_benchmark_bars(
        self,
        benchmark: str,
        start: datetime,
        end: datetime,
    ) -> list[DailyBar]:
        return self.get_daily_bars([benchmark], start, end).get(benchmark, [])


def create_daily_bars(
    symbol: str,
    start_date: date,
    days: int,
    base_price: float = 100.0,
    daily_change: float = 0.01,
) -> list[DailyBar]:
    """Create synthetic daily bars for testing."""
    bars = []
    current_price = base_price
    for i in range(days):
        dt = datetime.combine(start_date + timedelta(days=i), time(13, 30), tzinfo=timezone.utc)
        # Skip weekends
        if dt.weekday() >= 5:
            continue
        open_price = current_price
        close_price = open_price * (1 + daily_change)
        high_price = max(open_price, close_price) * 1.01
        low_price = min(open_price, close_price) * 0.99
        volume = 1000000
        bars.append(DailyBar(
            symbol=symbol,
            timestamp=dt,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        ))
        current_price = close_price
    return bars


class TestEarningsReactionProvider:
    """Tests for EarningsReactionProvider."""

    @pytest.fixture
    def mock_event_store(self):
        """Create a mock event store."""
        store = Mock()
        from trading_copilot.models.events import UpsertResult
        store.upsert_event = Mock(return_value=UpsertResult.NEW)
        store.get_event_by_source_id = Mock(return_value=None)
        store.events_for_symbol = Mock(return_value=[])
        store.events_by_type = Mock(return_value=[])
        return store

    @pytest.fixture
    def mock_market_data(self):
        """Create a mock market data provider with synthetic data."""
        # Create 30 days of bars for AAPL and SPY
        aapl_bars = create_daily_bars("AAPL", date(2026, 10, 1), 30, base_price=175.0, daily_change=0.01)
        spy_bars = create_daily_bars("SPY", date(2026, 10, 1), 30, base_price=450.0, daily_change=0.005)
        
        return MockMarketDataProvider({
            "AAPL": aapl_bars,
            "SPY": spy_bars,
        })

    @pytest.fixture
    def provider(self, mock_event_store, mock_market_data):
        """Create an earnings reaction provider with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = EarningsReactionProvider(
                event_store=mock_event_store,
                market_data_provider=mock_market_data,
                cache_dir=tmpdir,
                benchmark_symbol="SPY",
            )
            yield provider

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert provider.event_store is not None
        assert provider.market_data is not None
        assert provider.benchmark_symbol == "SPY"
        assert provider.errors == []

    def test_is_trading_day(self, provider):
        """Test trading day detection."""
        # Monday
        assert provider._is_trading_day(datetime(2026, 10, 5, tzinfo=timezone.utc)) is True
        # Tuesday
        assert provider._is_trading_day(datetime(2026, 10, 6, tzinfo=timezone.utc)) is True
        # Saturday
        assert provider._is_trading_day(datetime(2026, 10, 10, tzinfo=timezone.utc)) is False
        # Sunday
        assert provider._is_trading_day(datetime(2026, 10, 11, tzinfo=timezone.utc)) is False

    def test_next_trading_day(self, provider):
        """Test next trading day calculation."""
        # Friday -> Monday
        friday = datetime(2026, 10, 9, tzinfo=timezone.utc)  # Friday
        next_day = provider._next_trading_day(friday)
        assert next_day == date(2026, 10, 12)  # Monday
        
        # Wednesday -> Thursday
        wednesday = datetime(2026, 10, 7, tzinfo=timezone.utc)
        next_day = provider._next_trading_day(wednesday)
        assert next_day == date(2026, 10, 8)

    def test_nth_trading_day(self, provider):
        """Test nth trading day calculation."""
        start = date(2026, 10, 12)  # Monday
        # 1st trading day = Monday
        assert provider._nth_trading_day(start, 1) == date(2026, 10, 12)
        # 5th trading day = Friday
        assert provider._nth_trading_day(start, 5) == date(2026, 10, 16)

    def test_get_reaction_windows_bmo(self, provider):
        """Test reaction windows for BMO earnings."""
        released_at = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)  # Before market open
        windows = provider._get_reaction_windows("AAPL", released_at, "bmo")
        
        # Should have pre_market, immediate_ah, next_session, session_5
        window_names = [w.name for w in windows]
        assert "pre_market" in window_names
        assert "immediate_ah" in window_names
        assert "next_session" in window_names
        assert "session_5" in window_names
        
        # pre_market: prior close -> released_at
        pre_market = next(w for w in windows if w.name == "pre_market")
        assert pre_market.start.time() == time(20, 0)  # Prior close
        assert pre_market.end == released_at
        
        # immediate_ah: released_at -> market close
        immediate = next(w for w in windows if w.name == "immediate_ah")
        assert immediate.start == released_at
        assert immediate.end.time() == time(20, 0)  # Market close

    def test_get_reaction_windows_amc(self, provider):
        """Test reaction windows for AMC earnings."""
        released_at = datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc)  # After market close
        windows = provider._get_reaction_windows("AAPL", released_at, "amc")
        
        window_names = [w.name for w in windows]
        assert "pre_market" not in window_names  # No pre_market for AMC
        assert "immediate_ah" in window_names
        assert "next_session" in window_names
        assert "session_5" in window_names
        
        # immediate_ah: released_at -> 3 hours later
        immediate = next(w for w in windows if w.name == "immediate_ah")
        assert immediate.start == released_at
        assert immediate.end == released_at + timedelta(hours=3)

    def test_get_reaction_windows_unknown_early(self, provider):
        """Test reaction windows for unknown time before market open."""
        released_at = datetime(2026, 10, 29, 10, 0, tzinfo=timezone.utc)  # Before market open
        windows = provider._get_reaction_windows("AAPL", released_at, "unknown")
        
        window_names = [w.name for w in windows]
        assert "pre_market" in window_names
        assert "immediate_ah" in window_names
        assert "next_session" in window_names
        assert "session_5" in window_names

    def test_get_reaction_windows_unknown_late(self, provider):
        """Test reaction windows for unknown time after market open."""
        released_at = datetime(2026, 10, 29, 15, 0, tzinfo=timezone.utc)  # During market hours
        windows = provider._get_reaction_windows("AAPL", released_at, "unknown")
        
        window_names = [w.name for w in windows]
        assert "pre_market" not in window_names
        assert "immediate_ah" in window_names
        assert "next_session" in window_names
        assert "session_5" in window_names

    def test_fetch_window_data(self, provider):
        """Test fetching price data for a window."""
        # Create a window covering a known trading day
        window = ReactionWindow(
            name="next_session",
            start=datetime(2026, 10, 13, 13, 30, tzinfo=timezone.utc),  # Tuesday open
            end=datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc),     # Tuesday close
        )
        
        result = provider._fetch_window_data("AAPL", window)
        
        assert result.bars_available is True
        assert result.open_price is not None
        assert result.close_price is not None
        assert result.change_pct is not None
        assert result.volume is not None
        assert result.volume > 0

    def test_fetch_window_data_no_bars(self, provider):
        """Test fetching window data when no bars available."""
        # Use a symbol with no data
        window = ReactionWindow(
            name="next_session",
            start=datetime(2026, 10, 13, 13, 30, tzinfo=timezone.utc),
            end=datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc),
        )
        
        result = provider._fetch_window_data("NONEXISTENT", window)
        
        assert result.bars_available is False
        assert result.open_price is None
        assert result.close_price is None

    def test_fetch_benchmark_reaction(self, provider):
        """Test fetching benchmark (SPY) reaction."""
        released_at = datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc)
        benchmark = provider._fetch_benchmark_reaction(released_at)
        
        assert benchmark.symbol == "SPY"
        assert benchmark.session_5_change_pct is not None
        assert isinstance(benchmark.session_5_change_pct, float)

    def test_create_reaction_event_bmo(self, provider):
        """Test creating reaction event for BMO earnings."""
        # Create a mock earnings event
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 FY2026 Earnings Result",
            description="{}",
            released_at=datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000123:result",
            metadata={
                "report_time": "bmo",
                "report_date": "2026-09-26",
            },
        )
        
        reaction_event = provider._create_reaction_event(earnings_event)
        
        assert reaction_event is not None
        assert reaction_event.event_type == EventType.EARNINGS_REACTION
        assert reaction_event.symbol == "AAPL"
        assert "windows" in reaction_event.metadata
        assert "benchmark" in reaction_event.metadata
        
        # Check windows exist
        windows = reaction_event.metadata["windows"]
        assert "pre_market" in windows
        assert "immediate_ah" in windows
        assert "next_session" in windows
        assert "session_5" in windows

    def test_create_reaction_event_amc(self, provider):
        """Test creating reaction event for AMC earnings."""
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 FY2026 Earnings Result",
            description="{}",
            released_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000123:result",
            metadata={
                "report_time": "amc",
                "report_date": "2026-09-26",
            },
        )
        
        reaction_event = provider._create_reaction_event(earnings_event)
        
        assert reaction_event is not None
        windows = reaction_event.metadata["windows"]
        assert "pre_market" not in windows  # No pre_market for AMC
        assert "immediate_ah" in windows
        assert "next_session" in windows
        assert "session_5" in windows

    def test_create_reaction_event_no_released_at(self, provider):
        """Test that event without released_at returns None."""
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 FY2026 Earnings Result",
            description="{}",
            released_at=None,  # No release time
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000123:result",
            metadata={"report_time": "amc"},
        )
        
        reaction_event = provider._create_reaction_event(earnings_event)
        assert reaction_event is None

    def test_create_reaction_event_no_symbol(self, provider):
        """Test that event without symbol returns None."""
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol=None,
            title="Earnings Result",
            description="{}",
            released_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000123:result",
            metadata={"report_time": "amc"},
        )
        
        reaction_event = provider._create_reaction_event(earnings_event)
        assert reaction_event is None

    def test_compute_reactions_filters_by_date(self, provider, mock_event_store):
        """Test that compute_reactions filters by date range."""
        # Create earnings events with different dates
        event1 = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 FY2026 Earnings",
            description="{}",
            released_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000123:result",
            metadata={"report_time": "amc", "report_date": "2026-09-26"},
        )
        
        event2 = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q2 FY2026 Earnings",
            description="{}",
            released_at=datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="sec_edgar:0000320193-26-000124:result",
            metadata={"report_time": "amc", "report_date": "2026-06-27"},
        )
        
        mock_event_store.events_by_type.return_value = [event1, event2]
        
        # Only fetch October events
        counts = provider.compute_reactions(
            from_date=date(2026, 10, 1),
            to_date=date(2026, 10, 31),
        )
        
        # Should only process event1 (October)
        assert counts["NEW"] == 1 or counts["UNCHANGED"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])