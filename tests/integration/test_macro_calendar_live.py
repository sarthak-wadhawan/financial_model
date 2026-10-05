"""Live integration tests for MacroCalendarProvider.

These tests require internet access and are gated by RUN_LIVE_TESTS=1.
"""

from __future__ import annotations

import os
import pytest

from trading_copilot.models.events import EventType, EventImportance
from trading_copilot.providers.macro_calendar import MacroCalendarProvider
from trading_copilot.events.store import EventStore


# Skip all tests in this module unless RUN_LIVE_TESTS=1
pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 environment variable",
)


class TestMacroCalendarLive:
    """Live integration tests for macro calendar provider."""

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
        """Create a macro calendar provider with temp event store."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = MacroCalendarProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_fed_fomc_current_year(self, provider):
        """Test fetching current year FOMC schedule from Federal Reserve."""
        current_year = __import__('datetime').datetime.now().year
        events = provider.fetch_fomc_schedule(current_year)

        # Fed calendar shows upcoming meetings (may be fewer than 8 if some have passed)
        # At minimum should have some meetings
        assert len(events) >= 4

        # All should be CRITICAL importance
        for event in events:
            assert event["importance"] == EventImportance.CRITICAL
            assert event["source"] == "federal_reserve"
            assert event["event_key"].startswith("fomc_meeting_")

        # Verify dates are in current year
        for event in events:
            scheduled = __import__('datetime').datetime.fromisoformat(
                event["scheduled_at"].replace("Z", "+00:00")
            )
            assert scheduled.year == current_year

    def test_fed_fomc_parsing(self, provider):
        """Test that Fed HTML parsing works for current year."""
        current_year = __import__('datetime').datetime.now().year
        events = provider._fetch_fomc_from_fed(current_year)

        # Fed calendar shows upcoming meetings (may be fewer than 8)
        assert len(events) >= 4

        # Verify structure
        for event in events:
            assert "metadata" in event
            assert "minutes_date" in event["metadata"]
            assert "meeting_start" in event["metadata"]
            assert "meeting_end" in event["metadata"]

    def test_fed_fomc_fallback_to_fixture(self, provider):
        """Test that fallback to fixture works for historical years."""
        # 2024 should have a fixture
        events = provider.fetch_fomc_schedule(2024)
        assert len(events) == 8

    def test_bls_cpi_live(self, provider):
        """Test fetching latest CPI from BLS API."""
        release = provider.fetch_latest_bls_release("CUSR0000SA0")

        assert release is not None
        assert "actual" in release
        assert "release_date" in release
        assert release["series_id"] == "CUSR0000SA0"

        # Verify it's a valid release date (not in the future)
        from datetime import date
        assert release["release_date"] <= date.today()

    def test_bls_unemployment_live(self, provider):
        """Test fetching latest unemployment rate from BLS API."""
        release = provider.fetch_latest_bls_release("LNS14000000")

        assert release is not None
        assert "actual" in release
        assert release["series_id"] == "LNS14000000"

    def test_bls_nfp_live(self, provider):
        """Test fetching latest NFP from BLS API."""
        release = provider.fetch_latest_bls_release("CES0000000001")

        assert release is not None
        assert "actual" in release
        assert release["series_id"] == "CES0000000001"

    def test_refresh_current_year(self, provider, event_store):
        """Test refresh for current year."""
        current_year = __import__('datetime').datetime.now().year
        counts = provider.refresh(years=[current_year])

        # Fed calendar shows upcoming meetings (may be fewer than 8)
        assert counts["NEW"] >= 4
        assert counts["ERROR"] == 0

        # Verify events in store
        macro_events = event_store.events_by_type(EventType.MACRO, limit=100)
        assert len(macro_events) >= 4

    def test_provider_status_report(self, provider):
        """Test provider status reporting."""
        status = provider.get_provider_status()

        implemented = [k for k, v in status.items() if v == "implemented"]
        pending = [k for k, v in status.items() if v == "provider_pending"]

        # Core implemented events
        assert "fomc_meeting" in implemented
        assert "cpi" in implemented
        assert "nfp" in implemented
        assert "unemployment_rate" in implemented

        # Pending events
        assert "ism_manufacturing" in pending
        assert "consumer_confidence" in pending


if __name__ == "__main__":
    pytest.main([__file__, "-v"])