"""Unified event models for the persistent event store."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of market events."""

    MACRO = "macro"
    EARNINGS = "earnings"
    DIVIDEND = "dividend"
    STOCK_SPLIT = "stock_split"
    MERGER_ACQUISITION = "merger_acquisition"
    SPINOFF = "spinoff"
    CORPORATE_ACTION = "corporate_action"
    LEADERSHIP = "leadership"
    INSIDER = "insider"
    SEC_FILING = "sec_filing"
    REGULATORY = "regulatory"
    INVESTOR_EVENT = "investor_event"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    NEWS = "news"
    OTHER = "other"


class EventStatus(str, Enum):
    """Status of an event."""

    SCHEDULED = "scheduled"
    RELEASED = "released"
    UPDATED = "updated"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class EventImportance(str, Enum):
    """Importance level of an event."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UpsertResult(str, Enum):
    """Result of an upsert operation."""

    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    CHANGED = "CHANGED"


class MarketEvent(BaseModel):
    """Unified market event model."""

    # Core identity
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    symbol: Optional[str] = None  # None for macro events

    # Event details
    title: str
    description: Optional[str] = None

    # Timing
    scheduled_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    timezone: str = "UTC"

    # Classification
    importance: EventImportance = EventImportance.MEDIUM
    status: EventStatus = EventStatus.SCHEDULED

    # Values (for economic data, earnings, etc.)
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    unit: Optional[str] = None

    # Source tracking
    source: str
    source_url: Optional[str] = None
    source_id: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    first_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Deduplication
    content_hash: str = ""

    # Flexible metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_content_hash(self) -> str:
        """Compute a hash of the event's content for change detection."""
        import hashlib

        # Fields that determine if an event's content has changed
        # Note: event_id, created_at, first_seen_at, last_seen_at, updated_at, metadata are excluded
        key_parts = [
            self.event_type.value,
            self.symbol or "",
            self.title,
            self.description or "",
            self.scheduled_at.isoformat() if self.scheduled_at else "",
            self.released_at.isoformat() if self.released_at else "",
            self.timezone,
            self.importance.value,
            self.status.value,
            self.actual or "",
            self.forecast or "",
            self.previous or "",
            self.unit or "",
            self.source,
            self.source_url or "",
            self.source_id or "",
        ]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = self.compute_content_hash()


class EventRevision(BaseModel):
    """Revision history entry for an event."""

    revision_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changed_fields: dict[str, Any]  # field_name -> old_value
    changed_by: str = "system"  # Could be provider name in future


class EventQueryResult(BaseModel):
    """Result of an event query with pagination."""

    events: list[MarketEvent]
    total: int
    limit: int
    offset: int