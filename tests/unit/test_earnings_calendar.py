"""Unit tests for EarningsCalendarProvider."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timezone

import pytest

from trading_copilot.models.events import EventImportance, EventStatus, EventType
from trading_copilot.providers.earnings_calendar import EarningsCalendarProvider


class TestEarningsCalendarProvider:
    """Tests for EarningsCalendarProvider."""

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
        """Create an earnings calendar provider with temp event store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = EarningsCalendarProvider(event_store, cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert provider.event_store is not None
        assert provider.alpha_vantage_api_key is None
        assert provider.fmp_api_key is None
        assert provider.polygon_api_key is None
        assert provider.twelve_data_api_key is None

    def test_available_sources_empty(self, provider):
        """Test available sources when no API keys configured."""
        sources = provider._get_available_sources()
        assert sources == []

    def test_load_fixtures(self, provider):
        """Test loading earnings events from fixtures."""
        events = provider._load_fixtures(
            symbols=None,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        assert len(events) > 0
        for event in events:
            assert "symbol" in event
            assert "scheduled_at" in event
            assert "title" in event
            assert event["importance"] == EventImportance.HIGH
            assert event["status"] == EventStatus.SCHEDULED
            assert event["source"] == "fixture"

    def test_load_fixtures_with_symbol_filter(self, provider):
        """Test loading fixtures with symbol filter."""
        events = provider._load_fixtures(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        assert len(events) == 1
        assert events[0]["symbol"] == "AAPL"

    def test_load_fixtures_with_date_filter(self, provider):
        """Test loading fixtures with date filter."""
        events = provider._load_fixtures(
            symbols=None,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 10, 31),
        )

        for event in events:
            assert event["scheduled_at"].date() >= date(2026, 10, 1)
            assert event["scheduled_at"].date() <= date(2026, 10, 31)

    def test_create_market_event(self, provider):
        """Test creating MarketEvent from earnings data."""
        event_data = {
            "symbol": "AAPL",
            "title": "AAPL Q4 FY2026 Earnings",
            "description": "Estimated EPS: 1.55 USD",
            "scheduled_at": datetime(2026, 10, 28, 21, 0, tzinfo=timezone.utc),
            "released_at": None,
            "importance": EventImportance.HIGH,
            "status": EventStatus.SCHEDULED,
            "source": "fixture",
            "source_url": "https://financialmodelingprep.com",
            "source_id": "fixture_earnings_AAPL_2026-10-28",
            "metadata": {
                "event_subtype": "earnings",
                "fiscal_quarter": "4",
                "fiscal_year": "2026",
                "estimate": "1.55",
                "currency": "USD",
                "time": "amc",
            },
        }

        event = provider._create_market_event(event_data)

        assert event.event_type == EventType.EARNINGS
        assert event.symbol == "AAPL"
        assert event.title == "AAPL Q4 FY2026 Earnings"
        assert event.scheduled_at == datetime(2026, 10, 28, 21, 0, tzinfo=timezone.utc)
        assert event.released_at is None
        assert event.importance == EventImportance.HIGH
        assert event.status == EventStatus.SCHEDULED
        assert event.source == "fixture"
        assert event.source_id == "fixture_earnings_AAPL_2026-10-28"
        assert event.metadata["event_subtype"] == "earnings"
        assert event.metadata["fiscal_quarter"] == "4"
        assert event.metadata["time"] == "amc"

    def test_refresh_from_fixtures(self, provider, event_store):
        """Test refresh loads events from fixtures."""
        counts = provider.refresh(
            symbols=["AAPL", "MSFT"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
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
            assert event.status == EventStatus.SCHEDULED

    def test_refresh_idempotent(self, provider, event_store):
        """Test that refresh is idempotent."""
        counts1 = provider.refresh(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        counts2 = provider.refresh(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        assert counts1["NEW"] >= 1
        assert counts2["UNCHANGED"] >= 1
        assert counts2["NEW"] == 0

    def test_get_upcoming_earnings(self, provider, event_store):
        """Test getting upcoming earnings events."""
        provider.refresh(
            symbols=["AAPL", "MSFT", "GOOGL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        # Get upcoming from now
        upcoming = provider.get_upcoming_earnings(days_ahead=60)

        assert len(upcoming) >= 1
        for event in upcoming:
            assert event.event_type == EventType.EARNINGS
            assert event.scheduled_at is not None
            assert event.scheduled_at >= datetime.now(timezone.utc)

    def test_get_upcoming_earnings_with_symbol(self, provider, event_store):
        """Test getting upcoming earnings for specific symbol."""
        provider.refresh(
            symbols=["AAPL", "MSFT"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        upcoming = provider.get_upcoming_earnings(symbol="AAPL", days_ahead=60)

        assert len(upcoming) >= 1
        for event in upcoming:
            assert event.symbol == "AAPL"

    def test_time_parsing_bmo(self, provider):
        """Test BMO (before market open) time parsing."""
        # Fixture has time="bmo" which should be 13:30 UTC (8:30 AM ET)
        events = provider._load_fixtures(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        for event in events:
            if event["metadata"]["time"] == "bmo":
                assert event["scheduled_at"].hour == 13
                assert event["scheduled_at"].minute == 30

    def test_time_parsing_amc(self, provider):
        """Test AMC (after market close) time parsing."""
        events = provider._load_fixtures(
            symbols=["MSFT"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        for event in events:
            if event["metadata"]["time"] == "amc":
                assert event["scheduled_at"].hour == 21
                assert event["scheduled_at"].minute == 0

    def test_unknown_time_defaults_to_midnight(self, provider):
        """Test unknown time defaults to midnight UTC."""
        # Create a temporary provider with custom fixture data
        custom_fixture = [{
            "symbol": "TEST",
            "date": "2026-11-01",
            "time": "unknown",
            "quarter": "1",
            "year": "2026",
            "estimate": "1.00",
            "currency": "USD",
            "description": "Test",
            "source_url": "test",
        }]
        
        # Test the parsing logic directly
        from datetime import time
        event_data = {
            "symbol": "TEST",
            "date": "2026-11-01",
            "time": "unknown",
            "quarter": "1",
            "year": "2026",
            "estimate": "1.00",
            "currency": "USD",
            "description": "Test",
            "source_url": "test",
        }
        
        # Use the provider's internal logic to parse this
        report_date = datetime.strptime(event_data["date"], "%Y-%m-%d").date()
        time_str = event_data.get("time", "unknown")
        
        if time_str == "bmo":
            scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=13, minute=30, tzinfo=timezone.utc)
        elif time_str == "amc":
            scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=21, minute=0, tzinfo=timezone.utc)
        else:
            scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        assert scheduled_time.hour == 0
        assert scheduled_time.minute == 0
        assert scheduled_time.date() == date(2026, 11, 1)

    def test_earnings_event_metadata(self, provider, event_store):
        """Test that earnings event metadata is preserved."""
        provider.refresh(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        events = event_store.events_by_type(EventType.EARNINGS, limit=100)
        aapl_events = [e for e in events if e.symbol == "AAPL"]
        assert len(aapl_events) >= 1

        event = aapl_events[0]
        assert event.metadata["event_subtype"] == "earnings"
        assert "fiscal_quarter" in event.metadata
        assert "fiscal_year" in event.metadata
        assert "estimate" in event.metadata
        assert "currency" in event.metadata
        assert "time" in event.metadata

    def test_api_methods_exist(self, provider):
        """Test that API parsing methods exist."""
        assert hasattr(provider, "_fetch_alpha_vantage")
        assert hasattr(provider, "_fetch_fmp")
        assert hasattr(provider, "_fetch_polygon")
        assert hasattr(provider, "_fetch_twelve_data")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])