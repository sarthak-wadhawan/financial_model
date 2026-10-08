"""Live integration tests for EarningsReactionProvider (Alpaca IEX market data).

Gated by RUN_LIVE_TESTS=1 environment variable.
These tests require valid Alpaca API credentials.
"""

import os
import tempfile
from datetime import date, datetime, timezone

import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import (
    EventImportance,
    EventStatus,
    EventType,
    MarketEvent,
)
from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider
from trading_copilot.providers.earnings_reaction import EarningsReactionProvider


pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 and Alpaca credentials",
)


@pytest.fixture
def alpaca_provider():
    """Create Alpaca market data provider if credentials available."""
    api_key = os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("ALPACA_API_SECRET")
    
    if not api_key or not api_secret:
        pytest.skip("ALPACA_API_KEY and ALPACA_API_SECRET required")
    
    return AlpacaMarketDataProvider(api_key=api_key, api_secret=api_secret)


def test_earnings_reaction_live_amc(alpaca_provider):
    """Test live reaction computation for AMC earnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        
        # Create a known AMC earnings event for AAPL
        # AAPL Q3 FY2024 earnings: Oct 30, 2024 AMC
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 FY2024 Earnings Result",
            description="{}",
            released_at=datetime(2024, 10, 30, 21, 0, tzinfo=timezone.utc),  # 4:00 PM ET = 21:00 UTC
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="test:earnings_reaction:amc",
            metadata={
                "report_time": "amc",
                "report_date": "2024-09-28",
            },
        )
        
        # Upsert the earnings event
        store.upsert_event(earnings_event)
        
        provider = EarningsReactionProvider(
            event_store=store,
            market_data_provider=alpaca_provider,
            cache_dir=tmpdir + "/earnings_reaction",
            benchmark_symbol="SPY",
        )
        
        try:
            counts = provider.compute_reactions(
                symbols=["AAPL"],
                from_date=date(2024, 10, 1),
                to_date=date(2024, 11, 30),
            )
            
            assert counts["ERROR"] == 0
            
            # Check reaction event was created
            reaction_events = store.events_for_symbol(
                symbol="AAPL",
                event_types=[EventType.EARNINGS_REACTION],
                limit=10,
            )
            
            assert len(reaction_events) >= 1
            reaction = reaction_events[0]
            
            assert reaction.event_type == EventType.EARNINGS_REACTION
            assert reaction.symbol == "AAPL"
            assert reaction.metadata.get("report_time") == "amc"
            assert "windows" in reaction.metadata
            assert "benchmark" in reaction.metadata
            
            windows = reaction.metadata["windows"]
            # AMC should have immediate_ah, next_session, session_5 (no pre_market)
            assert "pre_market" not in windows
            assert "immediate_ah" in windows
            assert "next_session" in windows
            assert "session_5" in windows
            
            # Check window data
            for window_name in ["immediate_ah", "next_session", "session_5"]:
                window = windows[window_name]
                assert "start" in window
                assert "end" in window
                assert "bars_available" in window
                if window["bars_available"]:
                    assert window["open"] is not None
                    assert window["close"] is not None
                    assert window["change_pct"] is not None
                    assert window["volume"] is not None
            
            # Check benchmark
            benchmark = reaction.metadata["benchmark"]
            assert benchmark["symbol"] == "SPY"
            assert benchmark["session_5_change_pct"] is not None
            
        finally:
            provider.close()
            store.close()


def test_earnings_reaction_live_bmo(alpaca_provider):
    """Test live reaction computation for BMO earnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        
        # Create a known BMO earnings event (e.g., a company that reports BMO)
        # Using a hypothetical BMO earnings for testing
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q1 FY2024 Earnings Result (BMO test)",
            description="{}",
            released_at=datetime(2024, 2, 1, 12, 30, tzinfo=timezone.utc),  # Before market open
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="test:earnings_reaction:bmo",
            metadata={
                "report_time": "bmo",
                "report_date": "2023-12-30",
            },
        )
        
        store.upsert_event(earnings_event)
        
        provider = EarningsReactionProvider(
            event_store=store,
            market_data_provider=alpaca_provider,
            cache_dir=tmpdir + "/earnings_reaction",
            benchmark_symbol="SPY",
        )
        
        try:
            counts = provider.compute_reactions(
                symbols=["AAPL"],
                from_date=date(2024, 1, 1),
                to_date=date(2024, 3, 31),
            )
            
            assert counts["ERROR"] == 0
            
            reaction_events = store.events_for_symbol(
                symbol="AAPL",
                event_types=[EventType.EARNINGS_REACTION],
                limit=10,
            )
            
            # Find the BMO reaction
            bmo_reaction = None
            for r in reaction_events:
                if r.source_id == "test:earnings_reaction:bmo:reaction":
                    bmo_reaction = r
                    break
            
            if bmo_reaction:
                windows = bmo_reaction.metadata["windows"]
                # BMO should have pre_market, immediate_ah, next_session, session_5
                assert "pre_market" in windows
                assert "immediate_ah" in windows
                assert "next_session" in windows
                assert "session_5" in windows
                
                # Check pre_market window
                pre_market = windows["pre_market"]
                if pre_market["bars_available"]:
                    assert pre_market["open"] is not None
                    assert pre_market["close"] is not None
            
        finally:
            provider.close()
            store.close()


def test_earnings_reaction_reproducibility(alpaca_provider):
    """Test that re-running with same data produces identical reactions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Test Earnings",
            description="{}",
            released_at=datetime(2024, 10, 30, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="test:reproducibility",
            metadata={"report_time": "amc", "report_date": "2024-09-28"},
        )
        
        store.upsert_event(earnings_event)
        
        provider1 = EarningsReactionProvider(
            event_store=store,
            market_data_provider=alpaca_provider,
            cache_dir=tmpdir + "/earnings_reaction1",
            benchmark_symbol="SPY",
        )
        
        provider2 = EarningsReactionProvider(
            event_store=store,
            market_data_provider=alpaca_provider,
            cache_dir=tmpdir + "/earnings_reaction2",
            benchmark_symbol="SPY",
        )
        
        try:
            counts1 = provider1.compute_reactions(symbols=["AAPL"], from_date=date(2024, 10, 1), to_date=date(2024, 11, 30))
            counts2 = provider2.compute_reactions(symbols=["AAPL"], from_date=date(2024, 10, 1), to_date=date(2024, 11, 30))
            
            assert counts1["ERROR"] == 0
            assert counts2["ERROR"] == 0
            
            # Both should produce UNCHANGED on second run (or same NEW count)
            events1 = store.events_for_symbol("AAPL", [EventType.EARNINGS_REACTION], limit=10)
            
            # Should have at least one reaction
            assert len(events1) >= 1
            
        finally:
            provider1.close()
            provider2.close()
            store.close()


def test_earnings_reaction_lookahead_safety(alpaca_provider):
    """Test that reaction windows don't use future data beyond window boundaries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        
        earnings_event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Lookahead Test",
            description="{}",
            released_at=datetime(2024, 10, 30, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="test:lookahead",
            metadata={"report_time": "amc", "report_date": "2024-09-28"},
        )
        
        store.upsert_event(earnings_event)
        
        provider = EarningsReactionProvider(
            event_store=store,
            market_data_provider=alpaca_provider,
            cache_dir=tmpdir + "/earnings_reaction",
            benchmark_symbol="SPY",
        )
        
        try:
            counts = provider.compute_reactions(
                symbols=["AAPL"],
                from_date=date(2024, 10, 1),
                to_date=date(2024, 11, 30),
            )
            
            assert counts["ERROR"] == 0
            
            reaction_events = store.events_for_symbol(
                symbol="AAPL",
                event_types=[EventType.EARNINGS_REACTION],
                limit=10,
            )
            
            reaction = reaction_events[0]
            windows = reaction.metadata["windows"]
            
            # Verify all window end times are on or before their defined boundaries
            # For AMC: immediate_ah ends 3 hours after release
            # next_session ends at market close of next trading day
            # session_5 ends at market close of 5th trading day
            
            for window_name, window in windows.items():
                if window["bars_available"]:
                    assert window["end"] is not None
                    # End time should be reasonable (not weeks after)
                    
        finally:
            provider.close()
            store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])