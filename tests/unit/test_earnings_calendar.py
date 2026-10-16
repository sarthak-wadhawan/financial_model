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
        """Test loading earnings events from fixtures (demo mode)."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=None,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        assert len(events) > 0
        for event in events:
            assert "symbol" in event
            assert "event_date" in event["metadata"]
            assert "title" in event
            assert event["importance"] == EventImportance.HIGH
            assert event["status"] == EventStatus.SCHEDULED
            assert event["source"] == "fixture"
            assert event["metadata"]["verification_state"] == "demo_fixture"

    def test_load_fixtures_with_symbol_filter(self, provider):
        """Test loading fixtures with symbol filter."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )

        assert len(events) == 1
        assert events[0]["symbol"] == "AAPL"

    def test_load_fixtures_with_date_filter(self, provider):
        """Test loading fixtures with date filter."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=None,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 10, 31),
        )

        for event in events:
            event_date = date.fromisoformat(event["metadata"]["event_date"])
            assert event_date >= date(2026, 10, 1)
            assert event_date <= date(2026, 10, 31)

    def test_create_market_event(self, provider):
        """Test creating MarketEvent from earnings data (session-based, no exact time)."""
        event_data = {
            "symbol": "AAPL",
            "title": "AAPL Q4 FY2026 Earnings",
            "description": "Estimated EPS: 1.55 USD",
            "scheduled_at": None,  # Session-based, not exact
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
                "session": "amc",
                "event_date": "2026-10-28",
                "scheduled_time_precision": "session",
            },
        }

        event = provider._create_market_event(event_data)

        assert event.event_type == EventType.EARNINGS
        assert event.symbol == "AAPL"
        assert event.title == "AAPL Q4 FY2026 Earnings"
        assert event.scheduled_at is None  # No fabricated exact time
        assert event.released_at is None
        assert event.importance == EventImportance.HIGH
        assert event.status == EventStatus.SCHEDULED
        assert event.source == "fixture"
        assert event.source_id == "fixture_earnings_AAPL_2026-10-28"
        assert event.metadata["event_subtype"] == "earnings"
        assert event.metadata["fiscal_quarter"] == "4"
        assert event.metadata["session"] == "amc"
        assert event.metadata["event_date"] == "2026-10-28"
        assert event.metadata["scheduled_time_precision"] == "session"

    def test_refresh_from_fixtures(self, provider, event_store):
        """Test refresh loads events from fixtures in demo mode."""
        provider.mode = "demo"
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
            assert event.scheduled_at is None  # Session-based, no exact time

    def test_refresh_idempotent(self, provider, event_store):
        """Test that refresh is idempotent in demo mode."""
        provider.mode = "demo"
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
        """Test getting upcoming earnings events in demo mode."""
        provider.mode = "demo"
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
            # Date-only events have metadata["event_date"]
            assert event.metadata.get("event_date") is not None
            event_date = date.fromisoformat(event.metadata["event_date"])
            assert event_date >= date.today()

    def test_get_upcoming_earnings_with_symbol(self, provider, event_store):
        """Test getting upcoming earnings for specific symbol in demo mode."""
        provider.mode = "demo"
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
        """Test BMO (before market open) session parsing - no fake exact time."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=["AAPL"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        for event in events:
            if event["metadata"]["session"] == "bmo":
                # No fabricated exact timestamp; session semantics only
                assert event["scheduled_at"] is None
                assert event["metadata"]["scheduled_time_precision"] == "session"
                assert event["metadata"]["event_date"] == "2026-10-28"  # AAPL fixture date

    def test_time_parsing_amc(self, provider):
        """Test AMC (after market close) session parsing - no fake exact time."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=["MSFT"],
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        for event in events:
            if event["metadata"]["session"] == "amc":
                # No fabricated exact timestamp; session semantics only
                assert event["scheduled_at"] is None
                assert event["metadata"]["scheduled_time_precision"] == "session"
                assert event["metadata"]["event_date"] == "2026-10-29"  # MSFT fixture date

    def test_unknown_time_is_date_precision_not_midnight(self, provider):
        """Test unknown time gets date precision, not fabricated midnight."""
        provider.mode = "demo"
        events = provider._load_fixtures(
            symbols=None,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 11, 30),
        )
        for event in events:
            if event["metadata"]["session"] == "unknown":
                # No fabricated exact timestamp; date precision only
                assert event["scheduled_at"] is None
                assert event["metadata"]["scheduled_time_precision"] == "date"
                assert event["metadata"]["event_date"] is not None

    def test_earnings_event_metadata(self, provider, event_store):
        """Test that earnings event metadata is preserved."""
        provider.mode = "demo"
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
        assert "session" in event.metadata
        assert "event_date" in event.metadata
        assert "scheduled_time_precision" in event.metadata

    def test_api_methods_exist(self, provider):
        """Test that API parsing methods exist."""
        assert hasattr(provider, "_fetch_alpha_vantage")
        assert hasattr(provider, "_fetch_fmp")
        assert hasattr(provider, "_fetch_polygon")
        assert hasattr(provider, "_fetch_twelve_data")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])