"""Change detection utilities for events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventRevision, MarketEvent, UpsertResult


class ChangeDetector:
    """Detects and classifies changes between event versions."""

    def __init__(self, store: Optional[EventStore] = None):
        self.store = store

    @staticmethod
    def compare_events(old: MarketEvent, new: MarketEvent) -> dict[str, tuple[Any, Any]]:
        """
        Compare two events and return a dictionary of changed fields.
        Returns {field_name: (old_value, new_value)} for each changed field.
        """
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
            "metadata",
        ]

        for field in fields_to_check:
            old_val = getattr(old, field)
            new_val = getattr(new, field)

            # Normalize for comparison
            if isinstance(old_val, datetime) and isinstance(new_val, datetime):
                if old_val != new_val:
                    changes[field] = (old_val, new_val)
            elif old_val != new_val:
                changes[field] = (old_val, new_val)

        return changes

    @staticmethod
    def classify_change(changes: dict[str, tuple[Any, Any]]) -> list[str]:
        """
        Classify the type of changes detected.
        Returns a list of human-readable change descriptions.
        """
        descriptions = []

        field_labels = {
            "scheduled_at": "event time changed",
            "released_at": "release time changed",
            "status": "status changed",
            "actual": "actual value appeared/changed",
            "forecast": "forecast changed",
            "previous": "previous value changed",
            "title": "title changed",
            "description": "description changed",
            "importance": "importance changed",
            "timezone": "timezone changed",
            "unit": "unit changed",
            "source_url": "source URL changed",
            "source_id": "source ID changed",
            "metadata": "metadata changed",
        }

        for field, (old_val, new_val) in changes.items():
            label = field_labels.get(field, f"{field} changed")
            if isinstance(old_val, datetime) and isinstance(new_val, datetime):
                descriptions.append(
                    f"{label}: {old_val.isoformat()} → {new_val.isoformat()}"
                )
            elif old_val is None:
                descriptions.append(f"{label}: (new) {new_val}")
            elif new_val is None:
                descriptions.append(f"{label}: {old_val} → (removed)")
            else:
                descriptions.append(f"{label}: {old_val} → {new_val}")

        return descriptions

    @staticmethod
    def is_new_event(upsert_result: UpsertResult) -> bool:
        """Check if upsert result indicates a new event."""
        return upsert_result == UpsertResult.NEW

    @staticmethod
    def is_changed_event(upsert_result: UpsertResult) -> bool:
        """Check if upsert result indicates a changed event."""
        return upsert_result == UpsertResult.CHANGED

    @staticmethod
    def is_unchanged_event(upsert_result: UpsertResult) -> bool:
        """Check if upsert result indicates an unchanged event."""
        return upsert_result == UpsertResult.UNCHANGED

    def get_changed_events_summary(
        self, since: datetime, limit: int = 50
    ) -> list[dict[str, any]]:
        """
        Get a summary of events changed since a given timestamp.
        Returns list of dicts with event info and change descriptions.
        """
        if not self.store:
            return []

        changed_events = self.store.events_changed_since(since, limit=limit)
        summary = []

        for event in changed_events:
            revisions = self.store.get_revisions(event.event_id)
            if not revisions:
                continue

            # Get the most recent revision
            latest_revision = revisions[0]
            # The stored changed_fields only has old values, so we create tuples with (old, None)
            # to indicate we don't have the new value in the revision
            changes_for_display = {
                k: (v, None) for k, v in latest_revision.changed_fields.items()
            }
            descriptions = self.classify_change(changes_for_display)

            summary.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "symbol": event.symbol,
                    "title": event.title,
                    "changed_at": latest_revision.changed_at,
                    "changes": descriptions,
                }
            )

        return summary

    def get_released_events_summary(
        self, since: datetime, limit: int = 50
    ) -> list[dict[str, any]]:
        """
        Get a summary of events released since a given timestamp.
        """
        if not self.store:
            return []

        released_events = self.store.events_released_since(since, limit=limit)
        summary = []

        for event in released_events:
            summary.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "symbol": event.symbol,
                    "title": event.title,
                    "released_at": event.released_at,
                    "actual": event.actual,
                    "forecast": event.forecast,
                    "previous": event.previous,
                }
            )

        return summary