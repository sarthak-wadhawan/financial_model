"""Live integration tests for CorporateActionsProvider."""

from __future__ import annotations

import os
import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType, EventImportance
from trading_copilot.providers.corporate_actions import CorporateActionsProvider


# Skip all tests in this module unless RUN_LIVE_TESTS=1
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 environment variable",
)


class TestCorporateActionsLive:
    """Live integration tests for corporate actions provider."""

    @pytest.fixture
    def event_store(self):
        """Create a temporary event store."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        store = EventStore(db_path)
        yield store
        store.close()
        import os
        os.unlink(db_path)

    @pytest.fixture
    def provider(self, event_store):
        """Create a corporate actions provider with temp event store."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = CorporateActionsProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_refresh_live(self, provider, event_store):
        """Test refresh fetches live corporate actions from Alpaca."""
        counts = provider.refresh()

        assert counts["NEW"] > 0
        assert counts["ERROR"] == 0

        # Verify events in store
        from trading_copilot.models.events import EventType
        
        # Check dividends
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        assert len(div_events) >= 1
        for e in div_events:
            assert e.event_type == EventType.DIVIDEND
            assert e.source == "alpaca"

        # Check splits
        split_events = event_store.events_by_type(EventType.STOCK_SPLIT, limit=100)
        # May or may not have splits in current data
        for e in split_events:
            assert e.event_type == EventType.STOCK_SPLIT
            assert e.source == "alpaca"

    def test_refresh_with_symbol_filter(self, provider, event_store):
        """Test refresh with symbol filter."""
        counts = provider.refresh(symbols=["AAPL"])
        
        # Should only have AAPL events (or zero if no AAPL actions in current data)
        from trading_copilot.models.events import EventType
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        for e in div_events:
            assert e.symbol == "AAPL"
        
        # If AAPL data exists, should have NEW events
        if div_events:
            assert counts["NEW"] >= 1

    def test_refresh_with_action_type_filter(self, provider, event_store):
        """Test refresh with action type filter."""
        counts = provider.refresh(action_types=["cash_dividends"])
        
        # Should only have dividends (no splits, mergers, etc.)
        from trading_copilot.models.events import EventType
        split_events = event_store.events_by_type(EventType.STOCK_SPLIT, limit=100)
        assert len(split_events) == 0
        
        # Should have dividends
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        if div_events:
            assert counts["NEW"] >= 1

    def test_get_upcoming_actions(self, provider, event_store):
        """Test getting upcoming corporate actions."""
        provider.refresh()
        
        upcoming = provider.get_upcoming_actions(days_ahead=60)
        
        assert len(upcoming) >= 1
        for event in upcoming:
            assert event.scheduled_at is not None
            assert event.scheduled_at.date() >= __import__('datetime').datetime.now(__import__('datetime').timezone.utc).date()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])