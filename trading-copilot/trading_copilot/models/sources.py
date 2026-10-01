"""Source document models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Normalized source document."""

    source_id: str
    symbol: str
    source_type: Literal[
        "news",
        "8-k",
        "10-q",
        "10-k",
        "earnings_release",
        "other_filing",
        "other",
    ]
    title: str
    published_at: datetime | None
    url: str | None
    provider: str
    text: str
    retrieval_time: datetime
    content_hash: str


class EvidenceClaim(BaseModel):
    """A factual claim with supporting source IDs."""

    claim: str
    source_ids: list[str] = Field(min_length=1)

    @property
    def has_sources(self) -> bool:
        return len(self.source_ids) > 0