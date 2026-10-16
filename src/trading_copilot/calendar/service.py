"""Calendar service for .ics export."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List
from uuid import uuid4

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType, EventImportance
from trading_copilot.calendar.models import (
    CalendarEvent,
    CalendarExportRequest,
    CalendarExportResponse,
    CalendarExportFormat,
)
from trading_copilot.calendar.security import require_property_value, safe_calendar_url


def event_date(event) -> Optional[date]:
    """Known calendar date only; never promote a date/session to an instant."""
    timestamp = event.scheduled_at or event.released_at
    if timestamp:
        return timestamp.date()
    value = (event.metadata or {}).get("event_date")
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


class CalendarService:
    """Calendar export service."""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def export_events(self, request: CalendarExportRequest) -> CalendarExportResponse:
        """Export events to calendar format."""
        events = self._fetch_events(request)
        converted = [self._to_calendar_event(e) for e in events]
        calendar_events = [e for e in converted if e is not None]

        if request.format == CalendarExportFormat.ICS:
            content = self._generate_ics(calendar_events)
        else:
            raise ValueError(f"Unsupported format: {request.format}")

        filename = f"trading-copilot-calendar-{datetime.now().strftime('%Y%m%d')}.ics"

        return CalendarExportResponse(
            format=request.format,
            content=content,
            filename=filename,
            event_count=len(calendar_events),
            skipped_event_count=len(events) - len(calendar_events),
        )

    def _fetch_events(self, request: CalendarExportRequest) -> List:
        """Fetch events based on request filters."""
        all_events = []

        # Determine event types to fetch
        if request.event_types:
            event_types = [EventType(t) for t in request.event_types]
        else:
            # Default to all scheduled event types
            event_types = [
                EventType.MACRO,
                EventType.EARNINGS,
                EventType.EARNINGS_RESULT,
                EventType.EARNINGS_GUIDANCE,
                EventType.DIVIDEND,
                EventType.STOCK_SPLIT,
                EventType.MERGER_ACQUISITION,
                EventType.SPINOFF,
                EventType.CORPORATE_ACTION,
            ]

        for et in dict.fromkeys(event_types):
            offset = 0
            while True:
                events = self.event_store.events_by_type(et, limit=1000, offset=offset)
                all_events.extend(events)
                if len(events) < 1000:
                    break
                offset += len(events)

        # Filter by symbols
        if request.symbols:
            all_events = [e for e in all_events if e.symbol in [s.upper() for s in request.symbols]]

        # Filter by date range
        def bound_date(value):
            return value.date() if isinstance(value, datetime) else value
        if request.from_date and request.to_date and bound_date(request.from_date) > bound_date(request.to_date):
            raise ValueError("From date must not be after to date")
        if request.from_date:
            all_events = [
                e for e in all_events
                if event_date(e) and event_date(e) >= bound_date(request.from_date)
            ]
        if request.to_date:
            all_events = [
                e for e in all_events
                if event_date(e) and event_date(e) <= bound_date(request.to_date)
            ]

        # Filter by importance
        if request.importance:
            all_events = [e for e in all_events if e.importance.value in [i.lower() for i in request.importance]]

        # Sort by scheduled date
        all_events.sort(key=lambda e: event_date(e) or date.max)

        return all_events

    def _to_calendar_event(self, event) -> Optional[CalendarEvent]:
        """Convert MarketEvent to CalendarEvent with proper time semantics."""
        dtstart = event.scheduled_at or event.released_at or event_date(event)
        if dtstart is None:
            return None
        # An untrusted identity must not be repaired into a different UID. Omit
        # that export record, count it as skipped, and leave its evidence intact.
        try:
            require_property_value(event.event_id, "UID")
        except ValueError:
            return None
        metadata = event.metadata or {}
        session = metadata.get("session") or metadata.get("time")
        precision = metadata.get("scheduled_time_precision" if event.scheduled_at else "release_time_precision", metadata.get("time_precision"))
        # Precision is explicit, never inferred from an hour. Legacy providers may
        # encode sessions or estimated macro hours as timestamps. Conservatively
        # export a date unless source-supported precision is explicitly recorded.
        has_exact_time = isinstance(dtstart, datetime) and precision in ("exact", "exact_time", "datetime")
        if session or precision in ("date", "date_only", "session", "unknown", "filing_accepted"):
            has_exact_time = False
        if has_exact_time and dtstart.tzinfo is None:
            dtstart = dtstart.replace(tzinfo=ZoneInfo(event.timezone))

        # For date-only events (no exact time), use all-day event (DATE value in iCalendar)
        # For events with exact time, use timed event
        is_all_day = not has_exact_time

        # Source rarely supplies an end time; do not invent a duration.
        dtend = None

        # Build description with session semantics preserved
        description_parts = []
        description_parts.append(f"Event status: {event.status.value}")
        if event.description:
            description_parts.append(event.description)
        if event.actual is not None:
            description_parts.append(f"Actual: {event.actual}")
        if event.forecast is not None:
            description_parts.append(f"Forecast: {event.forecast}")
        if event.previous is not None:
            description_parts.append(f"Previous: {event.previous}")

        # Preserve BMO/AMC session semantics in description
        session_info = None
        if event.metadata:
            session_info = event.metadata.get('session') or event.metadata.get('time')
        if session_info:
            description_parts.append(f"Session: {session_info}")
        elif event.event_type == EventType.EARNINGS:
            # Try to infer from metadata or title
            title_lower = event.title.lower() if event.title else ""
            if 'bmo' in title_lower or 'before market' in title_lower:
                description_parts.append("Session: Before Market Open (BMO)")
            elif 'amc' in title_lower or 'after market' in title_lower:
                description_parts.append("Session: After Market Close (AMC)")

        if event.source_url:
            description_parts.append(f"Source: {event.source_url}")
        description_parts.append(f"Source provider: {event.source}; source ID: {event.source_id or 'unavailable'}")
        description_parts.append(f"Retrieved/last seen: {event.last_seen_at.isoformat()}")
        description_parts.append("Time precision: exact" if has_exact_time else "Time precision: date/session only; exact time unavailable")
        if metadata.get("release_time_precision") == "filing_accepted":
            description_parts.append("SEC filing acceptance is not the announcement release time.")

        # Categories
        categories = [event.event_type.value]
        if event.importance:
            categories.append(event.importance.value)

        return CalendarEvent(
            uid=f"{event.event_id}@trading-copilot",
            summary=f"{event.symbol}: {event.title}" if event.symbol else event.title,
            description="\n".join(description_parts) if description_parts else None,
            dtstart=dtstart,
            dtend=dtend,
            dtstamp=datetime.now(timezone.utc),
            url=safe_calendar_url(event.source_url),
            categories=categories,
            all_day=is_all_day,
        )

    def _generate_ics(self, events: List[CalendarEvent]) -> str:
        """Generate iCalendar format content."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Trading Copilot//Calendar Export//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Trading Copilot Events",
            "X-WR-TIMEZONE:UTC",
        ]

        for event in events:
            uid = require_property_value(event.uid, "UID")
            categories = [require_property_value(cat, "category") for cat in event.categories]
            if event.url is not None and safe_calendar_url(event.url) is None:
                raise ValueError("Invalid calendar URL")
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{self._escape_ics(uid)}")
            lines.append(f"DTSTAMP:{self._format_dt(event.dtstamp)}")
            if event.all_day:
                # All-day event uses DATE format (YYYYMMDD)
                lines.append(f"DTSTART;VALUE=DATE:{self._format_date(event.dtstart)}")
                if event.dtend:
                    lines.append(f"DTEND;VALUE=DATE:{self._format_date(event.dtend)}")
            else:
                # Timed event uses DATE-TIME format
                lines.append(f"DTSTART:{self._format_dt(event.dtstart)}")
                if event.dtend:
                    lines.append(f"DTEND:{self._format_dt(event.dtend)}")
            lines.append(f"SUMMARY:{self._escape_ics(event.summary)}")
            if event.description:
                lines.append(f"DESCRIPTION:{self._escape_ics(event.description)}")
            if event.location:
                lines.append(f"LOCATION:{self._escape_ics(event.location)}")
            if event.url:
                lines.append(f"URL:{event.url}")
            if categories:
                lines.append("CATEGORIES:" + ",".join(self._escape_ics(cat) for cat in categories))
            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")

        folded = []
        for line in lines:
            chunk = ""
            for character in line:
                if len((chunk + character).encode("utf-8")) > 75:
                    folded.append(chunk)
                    chunk = " "
                chunk += character
            folded.append(chunk)
        return "\r\n".join(folded) + "\r\n"

    def _format_dt(self, dt: datetime) -> str:
        """Format datetime for iCalendar (UTC)."""
        if dt.tzinfo is None:
            raise ValueError("Exact calendar timestamps require a timezone")
        return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def _format_date(self, dt: datetime | date) -> str:
        """Format date for iCalendar (DATE format YYYYMMDD)."""
        return dt.strftime("%Y%m%d")

    def _escape_ics(self, text: str) -> str:
        """Escape text for iCalendar format."""
        import unicodedata
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Retained evidence is untouched. Unrepresentable text controls are
        # displayed as codepoints rather than embedded in the exported file.
        text = "".join(f"[U+{ord(c):04X}]" if unicodedata.category(c) in ("Cc", "Cf") and c not in "\n\t" else c for c in text)
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
