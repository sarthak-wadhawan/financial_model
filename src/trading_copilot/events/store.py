"""SQLite-based persistent event store."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from trading_copilot.models.events import (
    EventImportance,
    EventRevision,
    EventStatus,
    EventType,
    MarketEvent,
    UpsertResult,
)


class EventStore:
    """SQLite-backed event store with full CRUD and revision history."""

    def __init__(self, db_path: str | Path = "data/events.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    identity_key TEXT NOT NULL UNIQUE,
                    event_type TEXT NOT NULL,
                    symbol TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    scheduled_at TEXT,
                    released_at TEXT,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    importance TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    actual TEXT,
                    forecast TEXT,
                    previous TEXT,
                    unit TEXT,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    source_id TEXT,
                    created_at TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol);
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
                CREATE INDEX IF NOT EXISTS idx_events_scheduled_at ON events(scheduled_at);
                CREATE INDEX IF NOT EXISTS idx_events_released_at ON events(released_at);
                CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
                CREATE INDEX IF NOT EXISTS idx_events_identity_key ON events(identity_key);
                CREATE INDEX IF NOT EXISTS idx_events_symbol_type ON events(symbol, event_type);

                CREATE TABLE IF NOT EXISTS event_revisions (
                    revision_id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    changed_fields TEXT NOT NULL,
                    changed_by TEXT NOT NULL DEFAULT 'system',
                    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_revisions_event_id ON event_revisions(event_id);
                CREATE INDEX IF NOT EXISTS idx_revisions_changed_at ON event_revisions(changed_at);
                """
            )

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _compute_identity_key(event: MarketEvent) -> str:
        """Compute a stable identity key for an event (doesn't change with content updates)."""
        key_parts = [
            event.event_type.value,
            event.symbol or "",
            event.title,
            event.scheduled_at.isoformat() if event.scheduled_at else "",
            event.source,
            event.source_id or "",
        ]
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:32]

    def _row_to_event(self, row: sqlite3.Row) -> MarketEvent:
        """Convert a database row to a MarketEvent."""
        return MarketEvent(
            event_id=row["event_id"],
            event_type=EventType(row["event_type"]),
            symbol=row["symbol"] if row["symbol"] else None,
            title=row["title"],
            description=row["description"] if row["description"] else None,
            scheduled_at=(
                datetime.fromisoformat(row["scheduled_at"].replace("Z", "+00:00"))
                if row["scheduled_at"]
                else None
            ),
            released_at=(
                datetime.fromisoformat(row["released_at"].replace("Z", "+00:00"))
                if row["released_at"]
                else None
            ),
            timezone=row["timezone"],
            importance=EventImportance(row["importance"]),
            status=EventStatus(row["status"]),
            actual=row["actual"] if row["actual"] else None,
            forecast=row["forecast"] if row["forecast"] else None,
            previous=row["previous"] if row["previous"] else None,
            unit=row["unit"] if row["unit"] else None,
            source=row["source"],
            source_url=row["source_url"] if row["source_url"] else None,
            source_id=row["source_id"] if row["source_id"] else None,
            created_at=datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")
            ),
            first_seen_at=datetime.fromisoformat(
                row["first_seen_at"].replace("Z", "+00:00")
            ),
            last_seen_at=datetime.fromisoformat(
                row["last_seen_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"].replace("Z", "+00:00")
            ),
            content_hash=row["content_hash"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def _event_to_row(self, event: MarketEvent) -> dict[str, Any]:
        """Convert a MarketEvent to a dictionary for database insertion."""
        return {
            "event_id": event.event_id,
            "identity_key": event.metadata.get("_identity_key", self._compute_identity_key(event)),
            "event_type": event.event_type.value,
            "symbol": event.symbol,
            "title": event.title,
            "description": event.description,
            "scheduled_at": (
                event.scheduled_at.isoformat().replace("+00:00", "Z")
                if event.scheduled_at
                else None
            ),
            "released_at": (
                event.released_at.isoformat().replace("+00:00", "Z")
                if event.released_at
                else None
            ),
            "timezone": event.timezone,
            "importance": event.importance.value,
            "status": event.status.value,
            "actual": event.actual,
            "forecast": event.forecast,
            "previous": event.previous,
            "unit": event.unit,
            "source": event.source,
            "source_url": event.source_url,
            "source_id": event.source_id,
            "created_at": event.created_at.isoformat().replace("+00:00", "Z"),
            "first_seen_at": event.first_seen_at.isoformat().replace("+00:00", "Z"),
            "last_seen_at": event.last_seen_at.isoformat().replace("+00:00", "Z"),
            "updated_at": event.updated_at.isoformat().replace("+00:00", "Z"),
            "content_hash": event.content_hash,
            "metadata": json.dumps(event.metadata),
        }

    def upsert_event(self, event: MarketEvent) -> UpsertResult:
        """
        Insert or update an event, tracking changes.

        Uses identity_key for stable deduplication (same event across updates).
        Uses content_hash to detect content changes.

        Returns:
            UpsertResult.NEW if inserted
            UpsertResult.UNCHANGED if event exists and is identical
            UpsertResult.CHANGED if event was updated with modifications
        """
        # Compute identity key if not already in metadata
        identity_key = event.metadata.get("_identity_key", self._compute_identity_key(event))
        event.metadata["_identity_key"] = identity_key

        # Compute content hash if not provided
        if not event.content_hash:
            event.content_hash = event.compute_content_hash()

        with self._conn() as conn:
            # Check if event with same identity_key exists
            cursor = conn.execute(
                "SELECT * FROM events WHERE identity_key = ?", (identity_key,)
            )
            existing = cursor.fetchone()

            if existing:
                existing_event = self._row_to_event(existing)

                # Check if content changed
                if existing_event.content_hash == event.content_hash:
                    # No content change - just update last_seen_at
                    conn.execute(
                        "UPDATE events SET last_seen_at = ? WHERE identity_key = ?",
                        (
                            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            identity_key,
                        ),
                    )
                    return UpsertResult.UNCHANGED

                # Content changed - detect what changed
                changed_fields = self._detect_changes(existing_event, event)

                # Update event with new content_hash but same event_id
                now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                row = self._event_to_row(event)
                row["event_id"] = existing_event.event_id  # Preserve original event_id
                row["last_seen_at"] = now
                row["updated_at"] = now

                conn.execute(
                    """
                    UPDATE events SET
                        event_type = :event_type,
                        symbol = :symbol,
                        title = :title,
                        description = :description,
                        scheduled_at = :scheduled_at,
                        released_at = :released_at,
                        timezone = :timezone,
                        importance = :importance,
                        status = :status,
                        actual = :actual,
                        forecast = :forecast,
                        previous = :previous,
                        unit = :unit,
                        source = :source,
                        source_url = :source_url,
                        source_id = :source_id,
                        last_seen_at = :last_seen_at,
                        updated_at = :updated_at,
                        content_hash = :content_hash,
                        metadata = :metadata
                    WHERE identity_key = :identity_key
                    """,
                    row,
                )

                # Record revision using original event_id
                self._record_revision(conn, existing_event.event_id, changed_fields)

                return UpsertResult.CHANGED

            # New event - insert
            row = self._event_to_row(event)
            conn.execute(
                """
                INSERT INTO events (
                    event_id, identity_key, event_type, symbol, title, description,
                    scheduled_at, released_at, timezone, importance, status,
                    actual, forecast, previous, unit,
                    source, source_url, source_id,
                    created_at, first_seen_at, last_seen_at, updated_at,
                    content_hash, metadata
                ) VALUES (
                    :event_id, :identity_key, :event_type, :symbol, :title, :description,
                    :scheduled_at, :released_at, :timezone, :importance, :status,
                    :actual, :forecast, :previous, :unit,
                    :source, :source_url, :source_id,
                    :created_at, :first_seen_at, :last_seen_at, :updated_at,
                    :content_hash, :metadata
                )
                """,
                row,
            )
            return UpsertResult.NEW

    def _detect_changes(self, existing: MarketEvent, new: MarketEvent) -> dict[str, Any]:
        """Detect meaningful changes between two events."""
        changes = {}
        fields_to_check = [
            "title",
            "description",
            "scheduled_at",
            "released_at",
            "timezone",
            "importance",
            "status",
            "actual",
            "forecast",
            "previous",
            "unit",
            "source_url",
            "source_id",
        ]

        for field in fields_to_check:
            old_val = getattr(existing, field)
            new_val = getattr(new, field)

            # Normalize datetime for comparison
            if isinstance(old_val, datetime) and isinstance(new_val, datetime):
                if old_val != new_val:
                    changes[field] = old_val.isoformat()
            elif old_val != new_val:
                changes[field] = old_val

        return changes

    def _record_revision(
        self, conn: sqlite3.Connection, event_id: str, changed_fields: dict[str, Any]
    ) -> None:
        """Record a revision in the history table."""
        revision = EventRevision(
            event_id=event_id,
            changed_at=datetime.now(timezone.utc),
            changed_fields=changed_fields,
        )
        conn.execute(
            """
            INSERT INTO event_revisions (revision_id, event_id, changed_at, changed_fields, changed_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                revision.revision_id,
                revision.event_id,
                revision.changed_at.isoformat().replace("+00:00", "Z"),
                json.dumps(
                    {k: v.isoformat() if isinstance(v, datetime) else v for k, v in changed_fields.items()}
                ),
                revision.changed_by,
            ),
        )

    # Query methods

    def get_event(self, event_id: str) -> Optional[MarketEvent]:
        """Get a single event by ID."""
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None

    def get_event_by_hash(self, content_hash: str) -> Optional[MarketEvent]:
        """Get a single event by content hash."""
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE content_hash = ?", (content_hash,)
            )
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None

    def get_event_by_source_id(self, source_id: str, event_type: EventType | None = None) -> Optional[MarketEvent]:
        """Get a single event by source_id and optionally event_type."""
        with self._conn() as conn:
            if event_type:
                cursor = conn.execute(
                    "SELECT * FROM events WHERE source_id = ? AND event_type = ?",
                    (source_id, event_type.value),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM events WHERE source_id = ?",
                    (source_id,),
                )
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None

    def events_today(
        self, timezone: str = "UTC", limit: int = 100, offset: int = 0
    ) -> list[MarketEvent]:
        """Get events scheduled for today."""
        from datetime import date

        today = date.today().isoformat()
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE date(scheduled_at) = ?
                ORDER BY scheduled_at ASC
                LIMIT ? OFFSET ?
                """,
                (today, limit, offset),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def upcoming_events(
        self, limit: int = 100, offset: int = 0, from_date: Optional[datetime] = None
    ) -> list[MarketEvent]:
        """Get upcoming scheduled events."""
        if from_date is None:
            from_date = datetime.now(timezone.utc)
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE scheduled_at >= ? AND status IN ('scheduled', 'updated')
                ORDER BY scheduled_at ASC
                LIMIT ? OFFSET ?
                """,
                (
                    from_date.isoformat().replace("+00:00", "Z"),
                    limit,
                    offset,
                ),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def recent_events(
        self, limit: int = 100, offset: int = 0, days_back: int = 7
    ) -> list[MarketEvent]:
        """Get recently released events."""
        from datetime import timedelta

        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE released_at >= ? AND status = 'released'
                ORDER BY released_at DESC
                LIMIT ? OFFSET ?
                """,
                (
                    since.isoformat().replace("+00:00", "Z"),
                    limit,
                    offset,
                ),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def events_for_symbol(
        self,
        symbol: str,
        limit: int = 100,
        offset: int = 0,
        event_types: Optional[list[EventType]] = None,
    ) -> list[MarketEvent]:
        """Get events for a specific symbol."""
        symbol = symbol.upper()
        with self._conn() as conn:
            if event_types:
                placeholders = ",".join("?" * len(event_types))
                query = f"""
                    SELECT * FROM events
                    WHERE symbol = ? AND event_type IN ({placeholders})
                    ORDER BY COALESCE(scheduled_at, created_at) DESC
                    LIMIT ? OFFSET ?
                """
                params = [symbol] + [t.value for t in event_types] + [limit, offset]
            else:
                query = """
                    SELECT * FROM events
                    WHERE symbol = ?
                    ORDER BY COALESCE(scheduled_at, created_at) DESC
                    LIMIT ? OFFSET ?
                """
                params = [symbol, limit, offset]
            cursor = conn.execute(query, params)
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def events_by_type(
        self,
        event_type: EventType,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MarketEvent]:
        """Get events by type."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE event_type = ?
                ORDER BY COALESCE(scheduled_at, created_at) DESC
                LIMIT ? OFFSET ?
                """,
                (event_type.value, limit, offset),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def events_changed_since(
        self, since: datetime, limit: int = 100, offset: int = 0
    ) -> list[MarketEvent]:
        """Get events that have changed since a given timestamp."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT e.* FROM events e
                JOIN event_revisions r ON e.event_id = r.event_id
                WHERE r.changed_at >= ?
                ORDER BY r.changed_at DESC
                LIMIT ? OFFSET ?
                """,
                (
                    since.isoformat().replace("+00:00", "Z"),
                    limit,
                    offset,
                ),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def events_released_since(
        self, since: datetime, limit: int = 100, offset: int = 0
    ) -> list[MarketEvent]:
        """Get events that were released since a given timestamp."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM events
                WHERE released_at >= ? AND status = 'released'
                ORDER BY released_at ASC
                LIMIT ? OFFSET ?
                """,
                (
                    since.isoformat().replace("+00:00", "Z"),
                    limit,
                    offset,
                ),
            )
            return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_revisions(self, event_id: str) -> list[EventRevision]:
        """Get revision history for an event."""
        with self._conn() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM event_revisions
                WHERE event_id = ?
                ORDER BY changed_at DESC
                """,
                (event_id,),
            )
            revisions = []
            for row in cursor.fetchall():
                revisions.append(
                    EventRevision(
                        revision_id=row["revision_id"],
                        event_id=row["event_id"],
                        changed_at=datetime.fromisoformat(
                            row["changed_at"].replace("Z", "+00:00")
                        ),
                        changed_fields=json.loads(row["changed_fields"]),
                        changed_by=row["changed_by"],
                    )
                )
            return revisions

    def count_events(
        self,
        symbol: Optional[str] = None,
        event_type: Optional[EventType] = None,
        status: Optional[EventStatus] = None,
    ) -> int:
        """Count events matching criteria."""
        with self._conn() as conn:
            query = "SELECT COUNT(*) FROM events WHERE 1=1"
            params = []
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)
            if status:
                query += " AND status = ?"
                params.append(status.value)
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]

    def close(self) -> None:
        """Close any open connections (no-op for sqlite3)."""
        pass