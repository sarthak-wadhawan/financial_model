"""Unit tests for MacroCalendarProvider."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from trading_copilot.models.events import EventImportance, EventStatus, EventType
from trading_copilot.providers.macro_calendar import MacroCalendarProvider


class TestMacroCalendarProvider:
    """Tests for MacroCalendarProvider."""

    @pytest.fixture
    def event_store(self):
        """Create a temporary event store."""
        from trading_copilot.events.store import EventStore

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
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = MacroCalendarProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_macro_events_config(self, provider):
        """Test that macro event configurations are defined."""
        assert "fomc_meeting" in provider.MACRO_EVENTS
        assert "cpi" in provider.MACRO_EVENTS
        assert "nfp" in provider.MACRO_EVENTS
        assert "gdp" in provider.MACRO_EVENTS

        fomc = provider.MACRO_EVENTS["fomc_meeting"]
        assert fomc.importance == EventImportance.CRITICAL
        assert fomc.event_type == EventType.MACRO
        assert fomc.frequency == "8_per_year"
        assert fomc.provider_status == "implemented"

        cpi = provider.MACRO_EVENTS["cpi"]
        assert cpi.importance == EventImportance.CRITICAL
        assert cpi.frequency == "monthly"
        assert cpi.provider_status == "implemented"

        jolts = provider.MACRO_EVENTS["jolts"]
        assert jolts.importance == EventImportance.MEDIUM
        assert jolts.provider_status == "implemented"

        # Provider pending events
        ism = provider.MACRO_EVENTS["ism_manufacturing"]
        assert ism.provider_status == "provider_pending"

        umich = provider.MACRO_EVENTS["umich_sentiment"]
        assert umich.provider_status == "provider_pending"

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
        assert "pce" in implemented
        assert "core_pce" in implemented
        assert "gdp" in implemented
        assert "retail_sales" in implemented
        assert "housing_starts" in implemented
        assert "building_permits" in implemented

        # Pending events
        assert "ism_manufacturing" in pending
        assert "ism_services" in pending
        assert "consumer_confidence" in pending
        assert "umich_sentiment" in pending
        assert "industrial_production" in pending

    def test_fetch_fomc_schedule_from_fixture(self, provider):
        """Test FOMC schedule fetching from fixture."""
        # Test 2024 (has fixture)
        events_2024 = provider._load_fomc_fixture(2024)
        assert len(events_2024) == 8

        for event in events_2024:
            assert "name" in event
            assert "scheduled_at" in event
            assert "importance" in event
            assert "event_key" in event
            assert event["event_key"].startswith("fomc_meeting_")
            assert event["importance"] == EventImportance.CRITICAL

        dates = [e["metadata"]["meeting_start"] for e in events_2024]
        assert "2024-01-30" in dates
        assert "2024-03-19" in dates
        assert "2024-12-17" in dates

    def test_fetch_fomc_schedule_2026_fixture(self, provider):
        """Test FOMC schedule for 2026 (current year)."""
        events_2026 = provider._load_fomc_fixture(2026)
        assert len(events_2026) == 8

        dates = [e["metadata"]["meeting_start"] for e in events_2026]
        assert "2026-01-27" in dates
        assert "2026-03-17" in dates
        assert "2026-12-15" in dates

    def test_parse_fomc_html(self, provider):
        """Test FOMC HTML parsing."""
        # Sample HTML similar to Fed page
        html = """
        <table>
            <tr><td class="date">January 28-29, 2026</td></tr>
            <tr><td class="date">March 17-18, 2026</td></tr>
            <tr><td class="date">April 28-29, 2026</td></tr>
        </table>
        """

        events = provider._parse_fomc_html(html, 2026)
        assert len(events) == 3

        for event in events:
            assert event["importance"] == EventImportance.CRITICAL
            assert event["source"] == "federal_reserve"
            assert "metadata" in event
            assert "minutes_date" in event["metadata"]

    def test_create_market_event(self, provider):
        """Test creating MarketEvent from fetched data."""
        event_data = {
            "name": "FOMC Meeting",
            "description": "Monetary policy decision",
            "scheduled_at": "2026-03-18T18:00:00Z",
            "released_at": None,
            "importance": EventImportance.CRITICAL,
            "status": EventStatus.SCHEDULED,
            "source": "federal_reserve",
            "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            "event_key": "fomc_meeting_2026-03-17",
            "metadata": {"event_subtype": "fomc_meeting", "meeting_end": "2026-03-18"},
        }

        event = provider._create_market_event(event_data)

        assert event.event_type == EventType.MACRO
        assert event.symbol is None
        assert event.title == "FOMC Meeting"
        assert event.description == "Monetary policy decision"
        assert event.scheduled_at == datetime(2026, 3, 18, 18, 0, tzinfo=timezone.utc)
        assert event.released_at is None
        assert event.importance == EventImportance.CRITICAL
        assert event.status == EventStatus.SCHEDULED
        assert event.source == "federal_reserve"
        assert event.source_id == "fomc_meeting_2026-03-17"
        assert event.metadata["event_subtype"] == "fomc_meeting"

    def test_refresh_upserts_fomc_events(self, provider, event_store):
        """Test that refresh upserts FOMC events to store."""
        counts = provider.refresh(years=[2024])

        assert counts["NEW"] == 8  # 8 FOMC meetings in 2024
        assert counts["UNCHANGED"] == 0
        assert counts["CHANGED"] == 0

        # Verify events in store
        macro_events = event_store.events_by_type(EventType.MACRO, limit=100)
        assert len(macro_events) == 8

        for event in macro_events:
            assert event.event_type == EventType.MACRO
            assert event.symbol is None
            assert event.importance == EventImportance.CRITICAL
            assert event.status == EventStatus.SCHEDULED
            assert event.source == "federal_reserve"

    def test_refresh_idempotent(self, provider, event_store):
        """Test that refresh is idempotent (second run = UNCHANGED)."""
        counts1 = provider.refresh(years=[2024])
        counts2 = provider.refresh(years=[2024])

        assert counts1["NEW"] == 8
        assert counts2["UNCHANGED"] == 8
        assert counts2["NEW"] == 0

    def test_get_scheduled_events(self, provider, event_store):
        """Test getting scheduled events in date range."""
        provider.refresh(years=[2024])

        start = datetime(2024, 3, 1, tzinfo=timezone.utc)
        end = datetime(2024, 6, 30, tzinfo=timezone.utc)

        events = provider.get_scheduled_events(start=start, end=end)

        # Should get March 20, May 1, June 12 meetings (3 total - fixture end dates)
        assert len(events) == 3
        for event in events:
            assert event.scheduled_at >= start
            assert event.scheduled_at <= end

        # Verify specific dates (meeting end dates from fixture)
        dates = sorted([e.scheduled_at.date() for e in events])
        assert dates == [date(2024, 3, 20), date(2024, 5, 1), date(2024, 6, 12)]

    def test_get_scheduled_events_by_importance(self, provider, event_store):
        """Test filtering scheduled events by importance."""
        provider.refresh(years=[2024])

        # Need to pass start date in the past to include 2024 events
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        events = provider.get_scheduled_events(start=start, importance=EventImportance.CRITICAL)
        assert len(events) == 8

        events = provider.get_scheduled_events(start=start, importance=EventImportance.HIGH)
        assert len(events) == 0

    def test_update_event_values(self, provider, event_store):
        """Test updating event with actual values after release."""
        provider.refresh(years=[2024])

        # Update first FOMC meeting with actual decision
        result = provider.update_event_values(
            event_key="fomc_meeting_2024-01-30",
            actual="5.25%-5.50%",
            forecast="5.25%-5.50%",
            previous="5.25%-5.50%",
            released_at=datetime(2024, 1, 31, 19, 0, tzinfo=timezone.utc),
        )

        assert result is True

        # Verify event was updated
        events = event_store.events_by_type(EventType.MACRO, limit=100)
        updated_event = None
        for e in events:
            if e.source_id == "fomc_meeting_2024-01-30":
                updated_event = e
                break

        assert updated_event is not None
        assert updated_event.actual == "5.25%-5.50%"
        assert updated_event.forecast == "5.25%-5.50%"
        assert updated_event.previous == "5.25%-5.50%"
        assert updated_event.released_at == datetime(2024, 1, 31, 19, 0, tzinfo=timezone.utc)
        assert updated_event.status == EventStatus.RELEASED

        # Check revision history
        revisions = event_store.get_revisions(updated_event.event_id)
        assert len(revisions) == 1
        assert "actual" in revisions[0].changed_fields
        assert "forecast" in revisions[0].changed_fields
        assert "previous" in revisions[0].changed_fields
        assert "released_at" in revisions[0].changed_fields
        assert "status" in revisions[0].changed_fields

    def test_update_nonexistent_event(self, provider):
        """Test updating non-existent event returns False."""
        result = provider.update_event_values(
            event_key="nonexistent_event",
            actual="1.0%",
        )
        assert result is False

    def test_get_released_events(self, provider, event_store):
        """Test getting released events."""
        provider.refresh(years=[2024])

        # Update one event as released
        provider.update_event_values(
            event_key="fomc_meeting_2024-01-30",
            actual="5.25%-5.50%",
            released_at=datetime(2024, 1, 31, 19, 0, tzinfo=timezone.utc),
        )

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        released = provider.get_released_events(since=since)

        assert len(released) == 1
        assert released[0].status == EventStatus.RELEASED
        assert released[0].actual == "5.25%-5.50%"

    def test_importance_tiers(self, provider):
        """Test that events have correct importance tiers."""
        critical_events = [
            "fomc_meeting", "cpi", "core_cpi",
            "nfp", "unemployment_rate", "pce", "core_pce", "gdp"
        ]
        high_events = [
            "fomc_minutes", "ppi", "avg_hourly_earnings", "retail_sales",
            "ism_manufacturing", "ism_services"
        ]
        medium_events = [
            "jolts", "industrial_production", "consumer_confidence",
            "umich_sentiment", "housing_starts", "building_permits"
        ]

        for key in critical_events:
            assert provider.MACRO_EVENTS[key].importance == EventImportance.CRITICAL, f"{key} should be CRITICAL"

        for key in high_events:
            assert provider.MACRO_EVENTS[key].importance == EventImportance.HIGH, f"{key} should be HIGH"

        for key in medium_events:
            assert provider.MACRO_EVENTS[key].importance == EventImportance.MEDIUM, f"{key} should be MEDIUM"

    def test_forecast_remains_null(self, provider):
        """Test that forecast field is null (not fabricated)."""
        event_data = {
            "name": "CPI",
            "description": "Consumer Price Index",
            "scheduled_at": "2026-10-15T12:30:00Z",
            "released_at": None,
            "importance": EventImportance.CRITICAL,
            "status": EventStatus.SCHEDULED,
            "source": "bls",
            "source_url": "https://www.bls.gov/cpi/",
            "event_key": "cpi_2026-10-15",
            "metadata": {},
        }

        event = provider._create_market_event(event_data)
        assert event.forecast is None  # No fabricated forecasts

    def test_fomc_minutes_event_type(self, provider):
        """Test that FOMC minutes are a separate event type."""
        assert "fomc_minutes" in provider.MACRO_EVENTS
        minutes = provider.MACRO_EVENTS["fomc_minutes"]
        assert minutes.importance == EventImportance.HIGH
        assert minutes.provider_status == "implemented"


class TestBLSIntegration:
    """Tests for BLS API integration (using fixtures)."""

    @pytest.fixture
    def event_store(self):
        from trading_copilot.events.store import EventStore
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = EventStore(db_path)
        yield store
        store.close()
        import os
        os.unlink(db_path)

    @pytest.fixture
    def provider(self, event_store):
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = MacroCalendarProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_fetch_bls_series_parsing(self, provider):
        """Test BLS response parsing with fixture."""
        with open("tests/fixtures/bls_cpi_response.json") as f:
            fixture = json.load(f)

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = fixture
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            results = provider.fetch_bls_series("CUSR0000SA0", 2026, 2026)

        assert len(results) == 3
        assert results[0]["series_id"] == "CUSR0000SA0"
        assert results[0]["date"] == date(2026, 9, 1)
        assert results[0]["value"] == "315.301"

    def test_fetch_latest_bls_release(self, provider):
        """Test fetching latest BLS release."""
        with open("tests/fixtures/bls_cpi_response.json") as f:
            fixture = json.load(f)

        mock_response = MagicMock()
        mock_response.json.return_value = fixture
        mock_response.raise_for_status = MagicMock()

        with patch.object(provider.client, "post", return_value=mock_response):
            release = provider.fetch_latest_bls_release("CUSR0000SA0")

        assert release is not None
        assert release["actual"] == "315.301"
        assert release["series_id"] == "CUSR0000SA0"
        assert release["release_date"] == date(2026, 9, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])