"""High-level event service for managing market events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import (
    EventImportance,
    EventRevision,
    EventStatus,
    EventType,
    MarketEvent,
    UpsertResult,
)


class EventService:
    """Service layer for event operations with business logic."""

    def __init__(self, store: Optional[EventStore] = None, db_path: str = "data/events.db"):
        self.store = store or EventStore(db_path)

    def upsert_event(self, event: MarketEvent) -> UpsertResult:
        """Upsert an event with automatic content hash computation."""
        if not event.content_hash:
            event.content_hash = event.compute_content_hash()
        return self.store.upsert_event(event)

    def create_macro_event(
        self,
        title: str,
        scheduled_at: datetime,
        event_type: EventType = EventType.MACRO,
        importance: EventImportance = EventImportance.HIGH,
        source: str = "manual",
        source_url: Optional[str] = None,
        source_id: Optional[str] = None,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
        unit: Optional[str] = None,
        description: Optional[str] = None,
        timezone: str = "UTC",
    ) -> MarketEvent:
        """Create a macro event (no symbol)."""
        event = MarketEvent(
            event_type=event_type,
            symbol=None,
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            timezone=timezone,
            importance=importance,
            status=EventStatus.SCHEDULED,
            forecast=forecast,
            previous=previous,
            unit=unit,
            source=source,
            source_url=source_url,
            source_id=source_id,
        )
        self.upsert_event(event)
        return event

    def create_company_event(
        self,
        symbol: str,
        title: str,
        event_type: EventType,
        scheduled_at: Optional[datetime] = None,
        released_at: Optional[datetime] = None,
        importance: EventImportance = EventImportance.MEDIUM,
        status: EventStatus = EventStatus.SCHEDULED,
        source: str = "manual",
        source_url: Optional[str] = None,
        source_id: Optional[str] = None,
        actual: Optional[str] = None,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
        unit: Optional[str] = None,
        description: Optional[str] = None,
        timezone: str = "UTC",
    ) -> MarketEvent:
        """Create a company-specific event."""
        event = MarketEvent(
            event_type=event_type,
            symbol=symbol.upper(),
            title=title,
            description=description,
            scheduled_at=scheduled_at,
            released_at=released_at,
            timezone=timezone,
            importance=importance,
            status=status,
            actual=actual,
            forecast=forecast,
            previous=previous,
            unit=unit,
            source=source,
            source_url=source_url,
            source_id=source_id,
        )
        self.upsert_event(event)
        return event

    def update_event_status(self, event_id: str, status: EventStatus) -> bool:
        """Update an event's status."""
        event = self.store.get_event(event_id)
        if not event:
            return False
        event.status = status
        event.updated_at = datetime.now(timezone.utc)
        if status == EventStatus.RELEASED and not event.released_at:
            event.released_at = datetime.now(timezone.utc)
        # Clear content_hash so it gets recomputed
        event.content_hash = ""
        self.upsert_event(event)
        return True

    def update_event_values(
        self,
        event_id: str,
        actual: Optional[str] = None,
        forecast: Optional[str] = None,
        previous: Optional[str] = None,
    ) -> bool:
        """Update event values (actual, forecast, previous)."""
        event = self.store.get_event(event_id)
        if not event:
            return False
        if actual is not None:
            event.actual = actual
        if forecast is not None:
            event.forecast = forecast
        if previous is not None:
            event.previous = previous
        event.updated_at = datetime.now(timezone.utc)
        # Clear content_hash so it gets recomputed
        event.content_hash = ""
        self.upsert_event(event)
        return True

    def reschedule_event(self, event_id: str, new_scheduled_at: datetime) -> bool:
        """Reschedule an event to a new time."""
        event = self.store.get_event(event_id)
        if not event:
            return False
        event.scheduled_at = new_scheduled_at
        event.status = EventStatus.UPDATED
        event.updated_at = datetime.now(timezone.utc)
        # Clear content_hash so it gets recomputed
        event.content_hash = ""
        self.upsert_event(event)
        return True

    # Query delegation

    def events_today(self, **kwargs) -> list[MarketEvent]:
        return self.store.events_today(**kwargs)

    def upcoming_events(self, **kwargs) -> list[MarketEvent]:
        return self.store.upcoming_events(**kwargs)

    def recent_events(self, **kwargs) -> list[MarketEvent]:
        return self.store.recent_events(**kwargs)

    def events_for_symbol(self, **kwargs) -> list[MarketEvent]:
        return self.store.events_for_symbol(**kwargs)

    def events_by_type(self, **kwargs) -> list[MarketEvent]:
        return self.store.events_by_type(**kwargs)

    def events_changed_since(self, **kwargs) -> list[MarketEvent]:
        return self.store.events_changed_since(**kwargs)

    def events_released_since(self, **kwargs) -> list[MarketEvent]:
        return self.store.events_released_since(**kwargs)

    def get_event(self, event_id: str) -> Optional[MarketEvent]:
        return self.store.get_event(event_id)

    def get_revisions(self, event_id: str) -> list[EventRevision]:
        return self.store.get_revisions(event_id)

    def close(self) -> None:
        self.store.close()