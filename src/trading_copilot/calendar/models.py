"""Calendar models for .ics export."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class CalendarExportFormat(str, Enum):
    """Calendar export format."""
    ICS = "ics"


class CalendarEvent(BaseModel):
    """Calendar event for export."""
    uid: str
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    dtstart: datetime
    dtend: Optional[datetime] = None
    dtstamp: datetime
    url: Optional[str] = None
    categories: List[str] = Field(default_factory=list)


class CalendarExportRequest(BaseModel):
    """Request for calendar export."""
    format: CalendarExportFormat = CalendarExportFormat.ICS
    event_types: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    importance: Optional[List[str]] = None


class CalendarExportResponse(BaseModel):
    """Calendar export response."""
    format: CalendarExportFormat
    content: str
    filename: str
    event_count: int