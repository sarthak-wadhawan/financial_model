"""Calendar service for .ics export."""
from __future__ import annotations

from datetime import datetime, timedelta
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


class CalendarService:
    """Calendar export service."""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def export_events(self, request: CalendarExportRequest) -> CalendarExportResponse:
        """Export events to calendar format."""
        events = self._fetch_events(request)
        calendar_events = [self._to_calendar_event(e) for e in events]

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

        for et in event_types:
            events = self.event_store.events_by_type(et, limit=1000)
            all_events.extend(events)

        # Filter by symbols
        if request.symbols:
            all_events = [e for e in all_events if e.symbol in [s.upper() for s in request.symbols]]

        # Filter by date range
        if request.from_date:
            all_events = [
                e for e in all_events
                if e.scheduled_at and e.scheduled_at >= request.from_date
            ]
        if request.to_date:
            all_events = [
                e for e in all_events
                if e.scheduled_at and e.scheduled_at <= request.to_date
            ]

        # Filter by importance
        if request.importance:
            all_events = [e for e in all_events if e.importance.value in request.importance]

        # Sort by scheduled date
        all_events.sort(key=lambda e: e.scheduled_at or datetime.max)

        return all_events

    def _to_calendar_event(self, event) -> CalendarEvent:
        """Convert MarketEvent to CalendarEvent with proper time semantics."""
        # Check if event has exact time (scheduled_at with time component, or released_at with time)
        has_exact_time = False
        dtstart = None

        if event.scheduled_at:
            dtstart = event.scheduled_at
            # Check if it has a time component (not midnight UTC)
            if dtstart.hour != 0 or dtstart.minute != 0 or dtstart.second != 0:
                has_exact_time = True
        elif event.released_at:
            dtstart = event.released_at
            # Check if it has a time component
            if dtstart.hour != 0 or dtstart.minute != 0 or dtstart.second != 0:
                has_exact_time = True

        # If no scheduled time at all, use released_at or date-only
        if dtstart is None:
            dtstart = event.released_at or datetime.now()
            has_exact_time = False

        # For date-only events (no exact time), use all-day event (DATE value in iCalendar)
        # For events with exact time, use timed event
        is_all_day = not has_exact_time

        # Default duration for timed events
        duration = timedelta(minutes=30)
        if event.event_type == EventType.MACRO:
            title_lower = event.title.lower() if event.title else ""
            if any(term in title_lower for term in ["fomc", "cpi", "nfm", "payroll", "gdp", "pce"]):
                duration = timedelta(hours=2)
            else:
                duration = timedelta(hours=1)
        elif event.event_type in [EventType.EARNINGS, EventType.EARNINGS_RESULT]:
            duration = timedelta(hours=1)

        dtend = dtstart + duration if has_exact_time else None

        # Build description with session semantics preserved
        description_parts = []
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
            session_info = event.metadata.get('release_time_source') or event.metadata.get('session')
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
            dtstamp=datetime.now(),
            url=event.source_url,
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
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{event.uid}")
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
            for cat in event.categories:
                lines.append(f"CATEGORIES:{cat}")
            lines.append("END:VEVENT")

        lines.append("END:VCALENDAR")

        return "\r\n".join(lines) + "\r\n"

    def _format_dt(self, dt: datetime) -> str:
        """Format datetime for iCalendar (UTC)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    def _format_date(self, dt: datetime) -> str:
        """Format date for iCalendar (DATE format YYYYMMDD)."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime("%Y%m%d")

    def _escape_ics(self, text: str) -> str:
        """Escape text for iCalendar format."""
        return text.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n").replace("\r", "")