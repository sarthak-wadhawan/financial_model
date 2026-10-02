"""Events package for unified persistent event store."""

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
    EventQueryResult,
)

__all__ = [
    "EventStore",
    "EventService",
    "ChangeDetector",
    "EventType",
    "EventStatus",
    "EventImportance",
    "UpsertResult",
    "MarketEvent",
    "EventRevision",
    "EventQueryResult",
]