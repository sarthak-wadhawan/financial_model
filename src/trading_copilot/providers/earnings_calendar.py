"""Earnings calendar provider for corporate earnings events."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.providers.base import BaseProvider


logger = logging.getLogger(__name__)


class EarningsCalendarProvider(BaseProvider):
    """Provider for earnings calendar events.

    Fetches scheduled earnings dates from various sources and upserts them
    into the event store. Supports multiple data sources with optional API keys.
    """

    # Supported sources
    SOURCE_ALPHA_VANTAGE = "alpha_vantage"
    SOURCE_FMP = "fmp"
    SOURCE_POLYGON = "polygon"
    SOURCE_TWELVE_DATA = "twelve_data"

    def __init__(
        self,
        event_store: Any,
        cache_dir: str | Path = "artifacts/cache/earnings_calendar",
        timeout: float = 30.0,
        alpha_vantage_api_key: str | None = None,
        fmp_api_key: str | None = None,
        polygon_api_key: str | None = None,
        twelve_data_api_key: str | None = None,
    ):
        super().__init__()
        self.event_store = event_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

        # API keys (optional)
        self.alpha_vantage_api_key = alpha_vantage_api_key
        self.fmp_api_key = fmp_api_key
        self.polygon_api_key = polygon_api_key
        self.twelve_data_api_key = twelve_data_api_key

        # Base URLs
        self.alpha_vantage_url = "https://www.alphavantage.co/query"
        self.fmp_url = "https://financialmodelingprep.com/api/v3"
        self.polygon_url = "https://api.polygon.io"
        self.twelve_data_url = "https://api.twelvedata.com"

    def _get_available_sources(self) -> list[str]:
        """Get list of sources with available API keys."""
        sources = []
        if self.alpha_vantage_api_key:
            sources.append(self.SOURCE_ALPHA_VANTAGE)
        if self.fmp_api_key:
            sources.append(self.SOURCE_FMP)
        if self.polygon_api_key:
            sources.append(self.SOURCE_POLYGON)
        if self.twelve_data_api_key:
            sources.append(self.SOURCE_TWELVE_DATA)
        return sources

    def fetch_earnings_calendar(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch earnings calendar events from available sources.

        Tries sources in order of preference until one succeeds.
        """
        available = self._get_available_sources()

        if not available:
            logger.warning("No earnings calendar API keys configured, using fixtures")
            return self._load_fixtures(symbols, from_date, to_date)

        # Try sources in order of preference
        for source in available:
            try:
                if source == self.SOURCE_ALPHA_VANTAGE:
                    events = self._fetch_alpha_vantage(symbols, from_date, to_date)
                elif source == self.SOURCE_FMP:
                    events = self._fetch_fmp(symbols, from_date, to_date)
                elif source == self.SOURCE_POLYGON:
                    events = self._fetch_polygon(symbols, from_date, to_date)
                elif source == self.SOURCE_TWELVE_DATA:
                    events = self._fetch_twelve_data(symbols, from_date, to_date)
                else:
                    continue

                if events:
                    logger.info(f"Fetched {len(events)} earnings events from {source}")
                    return events
            except Exception as e:
                logger.warning(f"Failed to fetch earnings from {source}: {e}")
                continue

        # Fallback to fixtures
        logger.info("All sources failed, using fixtures")
        return self._load_fixtures(symbols, from_date, to_date)

    def _fetch_alpha_vantage(
        self,
        symbols: list[str] | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        """Fetch earnings calendar from Alpha Vantage."""
        params = {
            "function": "EARNINGS_CALENDAR",
            "apikey": self.alpha_vantage_api_key,
        }
        if from_date:
            params["horizon"] = "3month"  # Alpha Vantage uses horizon parameter

        resp = self.client.get(self.alpha_vantage_url, params=params)
        resp.raise_for_status()

        # Alpha Vantage returns CSV format
        import csv
        import io
        content = resp.text
        reader = csv.DictReader(io.StringIO(content))

        events = []
        for row in reader:
            # Normalize to our format
            symbol = row.get("symbol", "").upper()
            if symbols and symbol not in [s.upper() for s in symbols]:
                continue

            # Parse date
            try:
                report_date = datetime.strptime(row.get("reportDate", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            if from_date and report_date < from_date:
                continue
            if to_date and report_date > to_date:
                continue

            # Determine time (BMO/AMC)
            fiscal_quarter = row.get("fiscalQuarter", "")
            fiscal_year = row.get("fiscalYear", "")
            estimate = row.get("estimate", "")
            currency = row.get("currency", "USD")

            events.append({
                "symbol": symbol,
                "title": f"{symbol} Q{fiscal_quarter} FY{fiscal_year} Earnings",
                "description": f"Estimated EPS: {estimate} {currency}",
                "scheduled_at": datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                "released_at": None,
                "importance": EventImportance.HIGH,
                "status": EventStatus.SCHEDULED,
                "source": "alpha_vantage",
                "source_url": "https://www.alphavantage.co",
                "source_id": f"av_earnings_{symbol}_{report_date}",
                "metadata": {
                    "event_subtype": "earnings",
                    "fiscal_quarter": fiscal_quarter,
                    "fiscal_year": fiscal_year,
                    "estimate": estimate,
                    "currency": currency,
                    "time": "unknown",  # Alpha Vantage doesn't provide time
                },
            })

        return events

    def _fetch_fmp(
        self,
        symbols: list[str] | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        """Fetch earnings calendar from Financial Modeling Prep."""
        events = []

        # FMP has an earnings calendar endpoint
        params = {
            "apikey": self.fmp_api_key,
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        resp = self.client.get(f"{self.fmp_url}/earning_calendar", params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data:
            symbol = item.get("symbol", "").upper()
            if symbols and symbol not in [s.upper() for s in symbols]:
                continue

            try:
                report_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            # Time: "bmo" (before market open), "amc" (after market close), or "dmc" (during market close)
            time_str = item.get("time", "").lower()
            if time_str == "bmo":
                time_of_day = "bmo"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=13, minute=30, tzinfo=timezone.utc)  # 8:30 AM ET
            elif time_str == "amc":
                time_of_day = "amc"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=21, minute=0, tzinfo=timezone.utc)  # 4:00 PM ET
            else:
                time_of_day = "unknown"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)

            events.append({
                "symbol": symbol,
                "title": f"{symbol} Q{item.get('quarter', '')} FY{item.get('year', '')} Earnings",
                "description": f"Estimated EPS: {item.get('epsEstimated', 'N/A')}",
                "scheduled_at": scheduled_time,
                "released_at": None,
                "importance": EventImportance.HIGH,
                "status": EventStatus.SCHEDULED,
                "source": "fmp",
                "source_url": "https://financialmodelingprep.com",
                "source_id": f"fmp_earnings_{symbol}_{report_date}",
                "metadata": {
                    "event_subtype": "earnings",
                    "fiscal_quarter": item.get("quarter", ""),
                    "fiscal_year": item.get("year", ""),
                    "estimate": str(item.get("epsEstimated", "")),
                    "currency": "USD",
                    "time": time_of_day,
                },
            })

        return events

    def _fetch_polygon(
        self,
        symbols: list[str] | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        """Fetch earnings calendar from Polygon.io."""
        # Polygon has an earnings endpoint
        events = []
        params = {
            "apiKey": self.polygon_api_key,
        }
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        resp = self.client.get(f"{self.polygon_url}/v2/reference/earnings", params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("results", []):
            symbol = item.get("ticker", "").upper()
            if symbols and symbol not in [s.upper() for s in symbols]:
                continue

            try:
                report_date = datetime.strptime(item.get("report_date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            time_str = item.get("time", "").lower()
            if time_str == "bmo":
                time_of_day = "bmo"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=13, minute=30, tzinfo=timezone.utc)
            elif time_str == "amc":
                time_of_day = "amc"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=21, minute=0, tzinfo=timezone.utc)
            else:
                time_of_day = "unknown"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)

            events.append({
                "symbol": symbol,
                "title": f"{symbol} Earnings",
                "description": f"Estimated EPS: {item.get('eps_estimate', 'N/A')}",
                "scheduled_at": scheduled_time,
                "released_at": None,
                "importance": EventImportance.HIGH,
                "status": EventStatus.SCHEDULED,
                "source": "polygon",
                "source_url": "https://polygon.io",
                "source_id": f"polygon_earnings_{symbol}_{report_date}",
                "metadata": {
                    "event_subtype": "earnings",
                    "fiscal_quarter": item.get("fiscal_quarter", ""),
                    "fiscal_year": item.get("fiscal_year", ""),
                    "estimate": str(item.get("eps_estimate", "")),
                    "currency": "USD",
                    "time": time_of_day,
                },
            })

        return events

    def _fetch_twelve_data(
        self,
        symbols: list[str] | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        """Fetch earnings calendar from Twelve Data."""
        events = []
        params = {
            "apikey": self.twelve_data_api_key,
        }
        if from_date:
            params["start_date"] = from_date.isoformat()
        if to_date:
            params["end_date"] = to_date.isoformat()

        resp = self.client.get(f"{self.twelve_data_url}/earnings", params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("data", []):
            symbol = item.get("symbol", "").upper()
            if symbols and symbol not in [s.upper() for s in symbols]:
                continue

            try:
                report_date = datetime.strptime(item.get("report_date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            time_str = item.get("time", "").lower()
            if time_str == "bmo":
                time_of_day = "bmo"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=13, minute=30, tzinfo=timezone.utc)
            elif time_str == "amc":
                time_of_day = "amc"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=21, minute=0, tzinfo=timezone.utc)
            else:
                time_of_day = "unknown"
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)

            events.append({
                "symbol": symbol,
                "title": f"{symbol} Earnings",
                "description": f"Estimated EPS: {item.get('eps_estimate', 'N/A')}",
                "scheduled_at": scheduled_time,
                "released_at": None,
                "importance": EventImportance.HIGH,
                "status": EventStatus.SCHEDULED,
                "source": "twelve_data",
                "source_url": "https://twelvedata.com",
                "source_id": f"twelve_earnings_{symbol}_{report_date}",
                "metadata": {
                    "event_subtype": "earnings",
                    "fiscal_quarter": item.get("fiscal_quarter", ""),
                    "fiscal_year": item.get("fiscal_year", ""),
                    "estimate": str(item.get("eps_estimate", "")),
                    "currency": "USD",
                    "time": time_of_day,
                },
            })

        return events

    def _load_fixtures(
        self,
        symbols: list[str] | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        """Load earnings events from fixture file."""
        fixture_path = Path("tests/fixtures/earnings_calendar.json")
        if not fixture_path.exists():
            return []

        with open(fixture_path) as f:
            data = json.load(f)

        events = []
        for item in data:
            symbol = item.get("symbol", "").upper()
            if symbols and symbol not in [s.upper() for s in symbols]:
                continue

            try:
                report_date = datetime.strptime(item.get("date", ""), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            if from_date and report_date < from_date:
                continue
            if to_date and report_date > to_date:
                continue

            time_str = item.get("time", "unknown")
            if time_str == "bmo":
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=13, minute=30, tzinfo=timezone.utc)
            elif time_str == "amc":
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(hour=21, minute=0, tzinfo=timezone.utc)
            else:
                scheduled_time = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=timezone.utc)

            events.append({
                "symbol": symbol,
                "title": f"{symbol} Q{item.get('quarter', '')} FY{item.get('year', '')} Earnings",
                "description": item.get("description", ""),
                "scheduled_at": scheduled_time,
                "released_at": None,
                "importance": EventImportance.HIGH,
                "status": EventStatus.SCHEDULED,
                "source": "fixture",
                "source_url": item.get("source_url", ""),
                "source_id": f"fixture_earnings_{symbol}_{report_date}",
                "metadata": {
                    "event_subtype": "earnings",
                    "fiscal_quarter": item.get("quarter", ""),
                    "fiscal_year": item.get("year", ""),
                    "estimate": item.get("estimate", ""),
                    "currency": item.get("currency", "USD"),
                    "time": item.get("time", "unknown"),
                },
            })

        return events

    def _create_market_event(self, event_data: dict[str, Any]) -> MarketEvent:
        """Create a MarketEvent from fetched earnings data."""
        return MarketEvent(
            event_type=EventType.EARNINGS,
            symbol=event_data.get("symbol"),
            title=event_data["title"],
            description=event_data.get("description", ""),
            scheduled_at=event_data.get("scheduled_at"),
            released_at=event_data.get("released_at"),
            timezone="UTC",
            importance=event_data.get("importance", EventImportance.HIGH),
            status=event_data.get("status", EventStatus.SCHEDULED),
            actual=event_data.get("actual"),
            forecast=event_data.get("forecast"),
            previous=event_data.get("previous"),
            unit=event_data.get("unit"),
            source=event_data.get("source", "earnings_calendar"),
            source_url=event_data.get("source_url"),
            source_id=event_data.get("source_id"),
            metadata=event_data.get("metadata", {}),
        )

    def refresh(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, int]:
        """Refresh earnings calendar: fetch new events and upsert to store.

        Returns counts of NEW/UNCHANGED/CHANGED events.
        """
        if from_date is None:
            from_date = date.today()
        if to_date is None:
            # Default to 90 days ahead
            from datetime import timedelta
            to_date = from_date + timedelta(days=90)

        counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": 0}

        events = self.fetch_earnings_calendar(symbols, from_date, to_date)
        for event_data in events:
            try:
                event = self._create_market_event(event_data)
                result = self.event_store.upsert_event(event)
                counts[result.value] += 1
            except Exception as e:
                logger.error(f"Failed to upsert earnings event: {e}")
                counts["ERROR"] += 1

        return counts

    def get_upcoming_earnings(
        self,
        symbol: str | None = None,
        days_ahead: int = 30,
    ) -> list[MarketEvent]:
        """Get upcoming earnings events."""
        from datetime import timedelta
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=days_ahead)

        if symbol:
            events = self.event_store.events_for_symbol(
                symbol=symbol,
                event_types=[EventType.EARNINGS],
                limit=100,
            )
        else:
            events = self.event_store.events_by_type(EventType.EARNINGS, limit=100)

        filtered = []
        for e in events:
            if e.scheduled_at and start <= e.scheduled_at <= end:
                filtered.append(e)

        return sorted(filtered, key=lambda x: x.scheduled_at or datetime.max.replace(tzinfo=timezone.utc))

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()

    def health_check(self) -> bool:
        """Check if provider is available."""
        return True


if __name__ == "__main__":
    # Quick test
    from trading_copilot.events.store import EventStore
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = EventStore(db_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = EarningsCalendarProvider(store, cache_dir=tmpdir)
        counts = provider.refresh()
        print(f"Refresh counts: {counts}")

        # Check events
        events = store.events_by_type(EventType.EARNINGS, limit=100)
        print(f"Total earnings events: {len(events)}")
        for e in events[:5]:
            print(f"  {e.symbol}: {e.scheduled_at} - {e.title}")

        provider.close()
    store.close()
    os.unlink(db_path)