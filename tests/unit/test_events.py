"""Unit tests for the unified event store."""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.events.service import EventService
from trading_copilot.events.detector import ChangeDetector
from trading_copilot.models.events import (
    EventType,
    EventStatus,
    EventImportance,
    UpsertResult,
    MarketEvent,
    EventRevision,
)


class TestEventStore:
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def store(self, temp_db):
        """Create an EventStore with temporary database."""
        return EventStore(temp_db)

    @pytest.fixture
    def service(self, store):
        """Create an EventService with test store."""
        return EventService(store)

    @pytest.fixture
    def detector(self, store):
        """Create a ChangeDetector with test store."""
        return ChangeDetector(store)

    def test_db_creation(self, temp_db):
        """Test that database and tables are created."""
        store = EventStore(temp_db)
        assert temp_db.exists()

        # Check tables exist
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "events" in tables
        assert "event_revisions" in tables

    def test_insert_event(self, store):
        """Test inserting a new event."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
            importance=EventImportance.HIGH,
        )

        result = store.upsert_event(event)
        assert result == UpsertResult.NEW

        # Verify it was stored
        retrieved = store.get_event(event.event_id)
        assert retrieved is not None
        assert retrieved.title == "CPI Release"
        assert retrieved.event_type == EventType.MACRO
        assert retrieved.symbol is None
        assert retrieved.importance == EventImportance.HIGH

    def test_upsert_unchanged(self, store):
        """Test upserting the same event returns UNCHANGED."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )

        result1 = store.upsert_event(event)
        assert result1 == UpsertResult.NEW

        result2 = store.upsert_event(event)
        assert result2 == UpsertResult.UNCHANGED

    def test_upsert_changed(self, store):
        """Test upserting a modified event returns CHANGED."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )

        store.upsert_event(event)

        # Modify the event
        event.scheduled_at = datetime(2026, 10, 15, 13, 30, tzinfo=timezone.utc)
        event.content_hash = event.compute_content_hash()

        result = store.upsert_event(event)
        assert result == UpsertResult.CHANGED

        # Verify revision was recorded
        revisions = store.get_revisions(event.event_id)
        assert len(revisions) == 1
        assert "scheduled_at" in revisions[0].changed_fields

    def test_company_event_with_symbol(self, store):
        """Test creating company-specific events."""
        event = MarketEvent(
            event_type=EventType.EARNINGS,
            symbol="NVDA",
            title="NVDA Q3 Earnings",
            scheduled_at=datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc),
            source="test",
        )

        result = store.upsert_event(event)
        assert result == UpsertResult.NEW

        retrieved = store.get_event(event.event_id)
        assert retrieved.symbol == "NVDA"
        assert retrieved.event_type == EventType.EARNINGS

    def test_events_for_symbol(self, store):
        """Test querying events for a specific symbol."""
        # Create events for NVDA
        for i in range(3):
            event = MarketEvent(
                event_type=EventType.EARNINGS,
                symbol="NVDA",
                title=f"NVDA Earnings Q{i}",
                scheduled_at=datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc),
                source="test",
            )
            store.upsert_event(event)

        # Create events for AAPL
        event = MarketEvent(
            event_type=EventType.EARNINGS,
            symbol="AAPL",
            title="AAPL Earnings",
            scheduled_at=datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event)

        nvda_events = store.events_for_symbol("NVDA")
        assert len(nvda_events) == 3

        aapl_events = store.events_for_symbol("AAPL")
        assert len(aapl_events) == 1

    def test_events_by_type(self, store):
        """Test querying events by type."""
        # Create macro events
        for i in range(2):
            event = MarketEvent(
                event_type=EventType.MACRO,
                symbol=None,
                title=f"Macro Event {i}",
                scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
                source="test",
            )
            store.upsert_event(event)

        # Create earnings event
        event = MarketEvent(
            event_type=EventType.EARNINGS,
            symbol="NVDA",
            title="NVDA Earnings",
            scheduled_at=datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event)

        macro_events = store.events_by_type(EventType.MACRO)
        assert len(macro_events) == 2

        earnings_events = store.events_by_type(EventType.EARNINGS)
        assert len(earnings_events) == 1

    def test_upcoming_events(self, store):
        """Test querying upcoming events."""
        now = datetime.now(timezone.utc)

        # Past event
        past_event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Past Event",
            scheduled_at=now - timedelta(days=1),
            source="test",
        )
        store.upsert_event(past_event)

        # Future event
        future_event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Future Event",
            scheduled_at=now + timedelta(days=1),
            source="test",
        )
        store.upsert_event(future_event)

        upcoming = store.upcoming_events(limit=10)
        assert len(upcoming) == 1
        assert upcoming[0].title == "Future Event"

    def test_recent_events(self, store):
        """Test querying recent events."""
        now = datetime.now(timezone.utc)

        # Old event
        old_event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Old Event",
            released_at=now - timedelta(days=10),
            status=EventStatus.RELEASED,
            source="test",
        )
        store.upsert_event(old_event)

        # Recent event
        recent_event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Recent Event",
            released_at=now - timedelta(days=2),
            status=EventStatus.RELEASED,
            source="test",
        )
        store.upsert_event(recent_event)

        recent = store.recent_events(days_back=7)
        assert len(recent) == 1
        assert recent[0].title == "Recent Event"

    def test_events_changed_since(self, store):
        """Test querying events changed since a timestamp."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event)

        # Wait a moment and modify
        import time
        time.sleep(0.01)

        since = datetime.now(timezone.utc)
        time.sleep(0.01)

        event.scheduled_at = datetime(2026, 10, 15, 13, 30, tzinfo=timezone.utc)
        event.content_hash = event.compute_content_hash()
        store.upsert_event(event)

        changed = store.events_changed_since(since)
        assert len(changed) == 1

    def test_events_released_since(self, store):
        """Test querying events released since a timestamp."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=1)

        # Not released
        not_released = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Not Released",
            scheduled_at=now + timedelta(days=1),
            status=EventStatus.SCHEDULED,
            source="test",
        )
        store.upsert_event(not_released)

        # Released
        released = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Released",
            scheduled_at=now - timedelta(days=2),
            released_at=now - timedelta(hours=1),
            status=EventStatus.RELEASED,
            source="test",
        )
        store.upsert_event(released)

        released_events = store.events_released_since(since)
        assert len(released_events) == 1
        assert released_events[0].title == "Released"

    def test_revision_history(self, store):
        """Test revision history tracking."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event)

        # Make multiple changes
        event.scheduled_at = datetime(2026, 10, 15, 13, 30, tzinfo=timezone.utc)
        event.content_hash = event.compute_content_hash()
        store.upsert_event(event)

        event.status = EventStatus.RELEASED
        event.content_hash = event.compute_content_hash()
        store.upsert_event(event)

        revisions = store.get_revisions(event.event_id)
        assert len(revisions) == 2

        # First revision should have scheduled_at change
        assert "scheduled_at" in revisions[1].changed_fields
        # Second revision should have status change
        assert "status" in revisions[0].changed_fields

    def test_timezone_handling(self, store):
        """Test timezone-aware timestamp handling."""
        # Create event with timezone-aware datetime
        scheduled = datetime(2026, 10, 15, 8, 30, tzinfo=timezone.utc)
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=scheduled,
            source="test",
            timezone="America/New_York",
        )
        store.upsert_event(event)

        retrieved = store.get_event(event.event_id)
        assert retrieved.scheduled_at is not None
        assert retrieved.scheduled_at.tzinfo is not None
        assert retrieved.timezone == "America/New_York"

    def test_macro_event_null_symbol(self, store):
        """Test that macro events have null symbol."""
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="FOMC Meeting",
            scheduled_at=datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event)

        retrieved = store.get_event(event.event_id)
        assert retrieved.symbol is None
        assert retrieved.event_type == EventType.MACRO

    def test_persistence_after_restart(self, temp_db):
        """Test that events persist after store restart."""
        store1 = EventStore(temp_db)
        event = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="Persistent Event",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )
        store1.upsert_event(event)
        event_id = event.event_id
        store1.close()

        # Create new store instance
        store2 = EventStore(temp_db)
        retrieved = store2.get_event(event_id)
        assert retrieved is not None
        assert retrieved.title == "Persistent Event"

    def test_deduplication_by_content_hash(self, store):
        """Test that events with same content hash are deduplicated."""
        event1 = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )
        store.upsert_event(event1)

        # Create another event with same content
        event2 = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )
        result = store.upsert_event(event2)
        assert result == UpsertResult.UNCHANGED

        # Count should still be 1
        count = store.count_events(event_type=EventType.MACRO)
        assert count == 1


class TestEventService:
    @pytest.fixture
    def service(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        service = EventService(db_path=db_path)
        yield service
        service.close()
        if db_path.exists():
            db_path.unlink()

    def test_create_macro_event(self, service):
        """Test creating a macro event via service."""
        event = service.create_macro_event(
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            source="test",
            forecast="3.2%",
            previous="3.1%",
            unit="%",
        )
        assert event.event_type == EventType.MACRO
        assert event.symbol is None
        assert event.forecast == "3.2%"
        assert event.previous == "3.1%"
        assert event.unit == "%"

    def test_create_company_event(self, service):
        """Test creating a company event via service."""
        event = service.create_company_event(
            symbol="NVDA",
            title="NVDA Q3 Earnings",
            event_type=EventType.EARNINGS,
            scheduled_at=datetime(2026, 11, 20, 21, 0, tzinfo=timezone.utc),
            source="test",
        )
        assert event.symbol == "NVDA"
        assert event.event_type == EventType.EARNINGS

    def test_update_event_status(self, service):
        """Test updating event status."""
        event = service.create_macro_event(
            title="Test Event",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )

        result = service.update_event_status(event.event_id, EventStatus.RELEASED)
        assert result is True

        updated = service.get_event(event.event_id)
        assert updated.status == EventStatus.RELEASED
        assert updated.released_at is not None

    def test_reschedule_event(self, service):
        """Test rescheduling an event."""
        event = service.create_macro_event(
            title="Test Event",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
        )

        new_time = datetime(2026, 10, 15, 14, 0, tzinfo=timezone.utc)
        result = service.reschedule_event(event.event_id, new_time)
        assert result is True

        updated = service.get_event(event.event_id)
        assert updated.scheduled_at == new_time
        assert updated.status == EventStatus.UPDATED

    def test_update_event_values(self, service):
        """Test updating event values."""
        event = service.create_macro_event(
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            source="test",
            forecast="3.2%",
        )

        result = service.update_event_values(event.event_id, actual="3.3%")
        assert result is True

        updated = service.get_event(event.event_id)
        assert updated.actual == "3.3%"


class TestChangeDetector:
    @pytest.fixture
    def detector(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        store = EventStore(db_path)
        yield ChangeDetector(store)
        if db_path.exists():
            db_path.unlink()

    def test_compare_events(self, detector):
        """Test comparing two events."""
        old = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
            status=EventStatus.SCHEDULED,
            source="test",
        )

        new = MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title="CPI Release",
            scheduled_at=datetime(2026, 10, 15, 13, 30, tzinfo=timezone.utc),
            status=EventStatus.UPDATED,
            source="test",
        )

        changes = detector.compare_events(old, new)
        assert "scheduled_at" in changes
        assert "status" in changes

    def test_classify_change(self, detector):
        """Test classifying changes."""
        changes = {
            "scheduled_at": (
                datetime(2026, 10, 15, 12, 30, tzinfo=timezone.utc),
                datetime(2026, 10, 15, 13, 30, tzinfo=timezone.utc),
            ),
            "actual": (None, "3.3%"),
        }

        descriptions = detector.classify_change(changes)
        assert any("event time changed" in d for d in descriptions)
        assert any("actual value appeared" in d for d in descriptions)

    def test_upsert_result_checks(self, detector):
        """Test upsert result classification."""
        assert detector.is_new_event(UpsertResult.NEW)
        assert not detector.is_new_event(UpsertResult.CHANGED)
        assert not detector.is_new_event(UpsertResult.UNCHANGED)

        assert detector.is_changed_event(UpsertResult.CHANGED)
        assert not detector.is_changed_event(UpsertResult.NEW)

        assert detector.is_unchanged_event(UpsertResult.UNCHANGED)
        assert not detector.is_unchanged_event(UpsertResult.NEW)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])