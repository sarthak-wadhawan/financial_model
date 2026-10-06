"""Live integration tests for EarningsCalendarProvider."""

from __future__ import annotations

import os
import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType, EventImportance
from trading_copilot.providers.earnings_calendar import EarningsCalendarProvider


# Skip all tests in this module unless RUN_LIVE_TESTS=1
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 environment variable",
)


class TestEarningsCalendarLive:
    """Live integration tests for earnings calendar provider."""

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
        """Create an earnings calendar provider with temp event store."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = EarningsCalendarProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_refresh_from_fixtures(self, provider, event_store):
        """Test refresh loads events from fixtures."""
        counts = provider.refresh(
            symbols=["AAPL", "MSFT"],
            from_date=__import__('datetime').date(2026, 10, 1),
            to_date=__import__('datetime').date(2026, 11, 30),
        )

        assert counts["NEW"] >= 1
        assert counts["ERROR"] == 0

        # Verify events in store
        events = event_store.events_by_type(EventType.EARNINGS, limit=100)
        assert len(events) >= 1

        for event in events:
            assert event.event_type == EventType.EARNINGS
            assert event.symbol in ("AAPL", "MSFT")
            assert event.importance == EventImportance.HIGH
            assert event.status.__str__() in ("EventStatus.SCHEDULED", "scheduled")

    def test_get_upcoming_earnings(self, provider, event_store):
        """Test getting upcoming earnings events."""
        provider.refresh(
            symbols=["AAPL", "MSFT", "GOOGL"],
            from_date=__import__('datetime').date(2026, 10, 1),
            to_date=__import__('datetime').date(2026, 11, 30),
        )

        upcoming = provider.get_upcoming_earnings(days_ahead=60)

        assert len(upcoming) >= 1
        for event in upcoming:
            assert event.event_type == EventType.EARNINGS
            assert event.scheduled_at is not None
            assert event.scheduled_at >= __import__('datetime').datetime.now(__import__('datetime').timezone.utc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])