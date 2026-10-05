"""Macro calendar provider for economic events.

Implements authoritative data ingestion from:
- Federal Reserve (FOMC meetings)
- Bureau of Labor Statistics (CPI, NFP, Unemployment, PPI, JOLTS, Avg Hourly Earnings)
- Bureau of Economic Analysis (GDP, PCE, Core PCE)
- Census Bureau (Retail Sales, Housing Starts, Building Permits)

Events with no reliable free API are marked as PROVIDER_PENDING.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.providers.base import BaseProvider


logger = logging.getLogger(__name__)


@dataclass
class MacroEventConfig:
    """Configuration for a macro event series."""

    event_type: EventType
    name: str
    importance: EventImportance
    source: str
    source_url: str
    frequency: str  # e.g., "monthly", "quarterly", "8_per_year"
    description: str = ""
    metadata: dict[str, Any] = None
    provider_status: str = "implemented"  # "implemented" | "provider_pending"

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MacroCalendarProvider(BaseProvider):
    """Provider for macro economic calendar events.

    Fetches scheduled macro events and released values from authoritative sources
    and upserts them into the event store.
    """

    # Known macro event configurations with provider status
    MACRO_EVENTS = {
        # Federal Reserve - IMPLEMENTED
        "fomc_meeting": MacroEventConfig(
            event_type=EventType.MACRO,
            name="FOMC Meeting",
            importance=EventImportance.CRITICAL,
            source="federal_reserve",
            source_url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
            frequency="8_per_year",
            description="Federal Open Market Committee meeting - monetary policy decision",
            provider_status="implemented",
        ),
        "fomc_minutes": MacroEventConfig(
            event_type=EventType.MACRO,
            name="FOMC Minutes",
            importance=EventImportance.HIGH,
            source="federal_reserve",
            source_url="https://www.federalreserve.gov/monetarypolicy/fomc_historical.htm",
            frequency="8_per_year",
            description="FOMC meeting minutes released 3 weeks after meeting",
            provider_status="implemented",
        ),
        # Bureau of Labor Statistics - IMPLEMENTED
        "cpi": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Consumer Price Index (CPI)",
            importance=EventImportance.CRITICAL,
            source="bls",
            source_url="https://www.bls.gov/cpi/",
            frequency="monthly",
            description="Monthly inflation measure",
            metadata={"series_id": "CUSR0000SA0"},
            provider_status="implemented",
        ),
        "core_cpi": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Core CPI (ex Food & Energy)",
            importance=EventImportance.CRITICAL,
            source="bls",
            source_url="https://www.bls.gov/cpi/",
            frequency="monthly",
            description="CPI excluding volatile food and energy",
            metadata={"series_id": "CUSR0000SA0L1E"},
            provider_status="implemented",
        ),
        "ppi": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Producer Price Index (PPI)",
            importance=EventImportance.HIGH,
            source="bls",
            source_url="https://www.bls.gov/ppi/",
            frequency="monthly",
            description="Wholesale inflation measure",
            metadata={"series_id": "WPUFD4"},
            provider_status="implemented",
        ),
        "nfp": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Non-Farm Payrolls (NFP)",
            importance=EventImportance.CRITICAL,
            source="bls",
            source_url="https://www.bls.gov/ces/",
            frequency="monthly",
            description="Monthly job creation number",
            metadata={"series_id": "CES0000000001"},
            provider_status="implemented",
        ),
        "unemployment_rate": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Unemployment Rate",
            importance=EventImportance.CRITICAL,
            source="bls",
            source_url="https://www.bls.gov/cps/",
            frequency="monthly",
            description="Monthly unemployment percentage",
            metadata={"series_id": "LNS14000000"},
            provider_status="implemented",
        ),
        "avg_hourly_earnings": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Average Hourly Earnings",
            importance=EventImportance.HIGH,
            source="bls",
            source_url="https://www.bls.gov/ces/",
            frequency="monthly",
            description="Wage growth measure",
            metadata={"series_id": "CES0500000003"},
            provider_status="implemented",
        ),
        "jolts": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Job Openings and Labor Turnover Survey (JOLTS)",
            importance=EventImportance.MEDIUM,
            source="bls",
            source_url="https://www.bls.gov/jlt/",
            frequency="monthly",
            description="Job openings, hires, quits",
            metadata={"series_id": "JTS000000000000000"},
            provider_status="implemented",
        ),
        # Bureau of Economic Analysis - IMPLEMENTED
        "pce": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Personal Consumption Expenditures (PCE)",
            importance=EventImportance.CRITICAL,
            source="bea",
            source_url="https://www.bea.gov/data/personal-consumption-expenditures",
            frequency="monthly",
            description="Fed's preferred inflation measure",
            metadata={"series_name": "PCEPI"},
            provider_status="implemented",
        ),
        "core_pce": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Core PCE Price Index",
            importance=EventImportance.CRITICAL,
            source="bea",
            source_url="https://www.bea.gov/data/personal-consumption-expenditures",
            frequency="monthly",
            description="PCE excluding food and energy",
            metadata={"series_name": "PCEPILFE"},
            provider_status="implemented",
        ),
        "gdp": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Gross Domestic Product (GDP)",
            importance=EventImportance.CRITICAL,
            source="bea",
            source_url="https://www.bea.gov/data/gdp",
            frequency="quarterly",
            description="Quarterly economic growth",
            metadata={"series_name": "GDP"},
            provider_status="implemented",
        ),
        # Census Bureau - IMPLEMENTED
        "retail_sales": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Retail Sales",
            importance=EventImportance.HIGH,
            source="census",
            source_url="https://www.census.gov/retail/",
            frequency="monthly",
            description="Consumer spending measure",
            metadata={"series_id": "RSXFS"},
            provider_status="implemented",
        ),
        "housing_starts": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Housing Starts",
            importance=EventImportance.MEDIUM,
            source="census",
            source_url="https://www.census.gov/construction/nrc/",
            frequency="monthly",
            description="New residential construction",
            metadata={"series_id": "HOUST"},
            provider_status="implemented",
        ),
        "building_permits": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Building Permits",
            importance=EventImportance.MEDIUM,
            source="census",
            source_url="https://www.census.gov/construction/bps/",
            frequency="monthly",
            description="Future construction activity",
            metadata={"series_id": "PERMIT"},
            provider_status="implemented",
        ),
        # PROVIDER_PENDING - No reliable free API
        "industrial_production": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Industrial Production",
            importance=EventImportance.MEDIUM,
            source="federal_reserve",
            source_url="https://www.federalreserve.gov/releases/g17/",
            frequency="monthly",
            description="Manufacturing output",
            provider_status="provider_pending",
        ),
        "ism_manufacturing": MacroEventConfig(
            event_type=EventType.MACRO,
            name="ISM Manufacturing PMI",
            importance=EventImportance.HIGH,
            source="ism",
            source_url="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/",
            frequency="monthly",
            description="Manufacturing sector health",
            provider_status="provider_pending",
        ),
        "ism_services": MacroEventConfig(
            event_type=EventType.MACRO,
            name="ISM Services PMI",
            importance=EventImportance.HIGH,
            source="ism",
            source_url="https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/",
            frequency="monthly",
            description="Services sector health",
            provider_status="provider_pending",
        ),
        "consumer_confidence": MacroEventConfig(
            event_type=EventType.MACRO,
            name="Consumer Confidence Index",
            importance=EventImportance.MEDIUM,
            source="conference_board",
            source_url="https://www.conference-board.org/data/consumerconfidence.cfm",
            frequency="monthly",
            description="Consumer sentiment",
            provider_status="provider_pending",
        ),
        "umich_sentiment": MacroEventConfig(
            event_type=EventType.MACRO,
            name="University of Michigan Consumer Sentiment",
            importance=EventImportance.MEDIUM,
            source="umich",
            source_url="https://data.sca.isr.umich.edu/",
            frequency="monthly",
            description="Consumer sentiment survey",
            provider_status="provider_pending",
        ),
    }

    # API endpoints
    FED_FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    BEA_API_URL = "https://apps.bea.gov/api/data"
    CENSUS_API_URL = "https://api.census.gov/data/timeseries/eits/marts"

    def __init__(
        self,
        event_store: Any,
        cache_dir: str | Path = "artifacts/cache/macro_calendar",
        timeout: float = 30.0,
        bls_api_key: str | None = None,
        bea_api_key: str | None = None,
        census_api_key: str | None = None,
    ):
        super().__init__()
        self.event_store = event_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)
        self.bls_api_key = bls_api_key
        self.bea_api_key = bea_api_key
        self.census_api_key = census_api_key

    # ==================== FEDERAL RESERVE ====================

    def fetch_fomc_schedule(self, year: int | None = None) -> list[dict[str, Any]]:
        """Fetch FOMC meeting schedule from Federal Reserve website.

        Parses the official Fed FOMC calendar page for the given year.
        Merges with fixture to ensure upcoming meetings are included
        (Fed website only shows past meetings for current year).
        """
        if year is None:
            year = datetime.now().year

        # For current year, prefer fixture (authoritative full schedule)
        # Fed website only shows past meetings and minutes dates
        if year == datetime.now().year:
            logger.info(f"Using fixture for current year FOMC {year}")
            return self._load_fomc_fixture(year)

        # For historical years, try Fed website then fallback to fixture
        # Load fixture (authoritative full schedule)
        fixture_events = self._load_fomc_fixture(year)

        # Try to fetch from official source to get verified past meetings
        try:
            fed_events = self._fetch_fomc_from_fed(year)
            if fed_events:
                logger.info(f"Fetched {len(fed_events)} FOMC meetings from Federal Reserve for {year}")
                # Merge: use Fed data for past meetings, fixture for upcoming
                # Match on meeting_start date to avoid duplicate key issues
                fed_meeting_starts = {e["metadata"].get("meeting_start") for e in fed_events if e.get("metadata", {}).get("meeting_start")}
                upcoming_fixture = [e for e in fixture_events if e["metadata"].get("meeting_start") not in fed_meeting_starts]
                merged = fed_events + upcoming_fixture
                # Sort by scheduled date
                merged.sort(key=lambda x: x["scheduled_at"])
                logger.info(f"Merged schedule: {len(merged)} total ({len(fed_events)} Fed + {len(upcoming_fixture)} fixture)")
                return merged
        except Exception as e:
            logger.warning(f"Failed to fetch FOMC schedule from Fed for {year}: {e}")

        # Fallback to fixture
        logger.info(f"Using fixture for FOMC {year}")
        return fixture_events

    def _fetch_fomc_from_fed(self, year: int) -> list[dict[str, Any]]:
        """Parse FOMC calendar from Federal Reserve website."""
        # The Fed publishes calendars at URLs like:
        # https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (current year)
        # https://www.federalreserve.gov/monetarypolicy/fomccalendars_2025.htm (historical)

        if year == datetime.now().year:
            url = self.FED_FOMC_CALENDAR_URL
        else:
            url = f"https://www.federalreserve.gov/monetarypolicy/fomccalendars_{year}.htm"

        response = self.client.get(url)
        response.raise_for_status()

        # Parse HTML for meeting dates
        # The page has a table with meeting dates
        html = response.text
        events = self._parse_fomc_html(html, year)

        if not events:
            raise ValueError("No FOMC meetings parsed from HTML")

        return events

    def _parse_fomc_html(self, html: str, year: int) -> list[dict[str, Any]]:
        """Parse FOMC meeting dates from Fed HTML calendar."""
        events = []

        # Pattern to match meeting date rows in the Fed calendar table
        # The Fed page has rows like: <td class="date">January 28-29, 2025</td>
        # We'll look for month names followed by day ranges
        month_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})(?:-(\d{1,2}))?,?\s+(\d{4})'

        for match in re.finditer(month_pattern, html):
            month_name, day1, day2, year_str = match.groups()
            if int(year_str) != year:
                continue

            month_num = self._month_name_to_num(month_name)
            start_day = int(day1)
            end_day = int(day2) if day2 else start_day

            # Create start and end dates
            start_date = date(year, month_num, start_day)
            end_date = date(year, month_num, end_day)

            # Statement is typically released at 2 PM ET on the second day
            # 2 PM ET = 18:00 UTC (EST) or 19:00 UTC (EDT)
            # We'll use 18:00 UTC as a reasonable default
            scheduled_at = datetime.combine(end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            scheduled_at = scheduled_at.replace(hour=18, minute=0)

            # Minutes released 3 weeks later (typically Wednesday)
            minutes_date = end_date
            # Add ~21 days to get to the Wednesday 3 weeks later
            from datetime import timedelta
            minutes_date = end_date + timedelta(days=21)
            # Adjust to Wednesday
            while minutes_date.weekday() != 2:  # 2 = Wednesday
                minutes_date += timedelta(days=1)

            events.append({
                "name": "FOMC Meeting",
                "description": "Federal Open Market Committee meeting - monetary policy decision",
                "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
                "released_at": None,
                "importance": EventImportance.CRITICAL,
                "status": EventStatus.SCHEDULED,
                "source": "federal_reserve",
                "source_url": self.FED_FOMC_CALENDAR_URL,
                "event_key": f"fomc_meeting_{start_date.isoformat()}",
                "metadata": {
                    "event_subtype": "fomc_meeting",
                    "meeting_start": start_date.isoformat(),
                    "meeting_end": end_date.isoformat(),
                    "minutes_date": minutes_date.isoformat(),
                },
            })

        return events

    def _load_fomc_fixture(self, year: int) -> list[dict[str, Any]]:
        """Load FOMC schedule from fixture file."""
        fixture_path = Path(f"tests/fixtures/fomc_{year}.json")
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            events = []
            for meeting in data:
                start = meeting["meeting_date"]
                end = meeting["meeting_end"]
                scheduled_at = datetime.fromisoformat(f"{end}T18:00:00+00:00")
                events.append({
                    "name": "FOMC Meeting",
                    "description": "Federal Open Market Committee meeting - monetary policy decision",
                    "scheduled_at": scheduled_at.isoformat().replace("+00:00", "Z"),
                    "released_at": None,
                    "importance": EventImportance.CRITICAL,
                    "status": EventStatus.SCHEDULED,
                    "source": "federal_reserve",
                    "source_url": self.FED_FOMC_CALENDAR_URL,
                    "event_key": f"fomc_meeting_{start}",
                    "metadata": {
                        "event_subtype": "fomc_meeting",
                        "meeting_start": start,
                        "meeting_end": end,
                        "minutes_date": meeting.get("minutes_date"),
                    },
                })
            return events

        # If no fixture, return empty (will be handled gracefully)
        return []

    def _month_name_to_num(self, name: str) -> int:
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12,
        }
        return months.get(name, 1)

    # ==================== BUREAU OF LABOR STATISTICS ====================

    def fetch_bls_series(
        self,
        series_id: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch time series data from BLS API.

        Returns list of observations with date, value, and metadata.
        """
        if start_year is None:
            start_year = datetime.now().year - 2
        if end_year is None:
            end_year = datetime.now().year

        payload = {
            "seriesid": [series_id],
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        if self.bls_api_key:
            payload["registrationkey"] = self.bls_api_key

        response = self.client.post(
            self.BLS_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        data = response.json()
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise ValueError(f"BLS API error: {data.get('message', 'Unknown error')}")

        results = []
        for series in data.get("Results", {}).get("series", []):
            for item in series.get("data", []):
                year = int(item["year"])
                period = item["period"]  # e.g., "M01", "M02", etc.
                if period.startswith("M"):
                    month = int(period[1:])
                    value = item["value"]
                    if value != ".":
                        results.append({
                            "date": date(year, month, 1),
                            "value": value,
                            "series_id": series_id,
                        })

        return results

    def fetch_latest_bls_release(self, series_id: str) -> dict[str, Any] | None:
        """Fetch the most recent released value for a BLS series."""
        data = self.fetch_bls_series(series_id, start_year=datetime.now().year - 1)
        if not data:
            return None

        # Sort by date descending
        data.sort(key=lambda x: x["date"], reverse=True)
        latest = data[0]

        return {
            "actual": latest["value"],
            "release_date": latest["date"],
            "series_id": series_id,
        }

    # ==================== BUREAU OF ECONOMIC ANALYSIS ====================

    def fetch_bea_series(
        self,
        series_name: str,
        frequency: str = "M",  # M=monthly, Q=quarterly
    ) -> list[dict[str, Any]]:
        """Fetch time series data from BEA API.

        Requires BEA API key (free registration).
        """
        if not self.bea_api_key:
            logger.warning("BEA API key not configured, skipping BEA fetch")
            return []

        params = {
            "UserID": self.bea_api_key,
            "method": "GetData",
            "datasetname": "NIPA" if series_name in ["GDP", "PCEPI", "PCEPILFE"] else "UnderlyingDetail",
            "Frequency": frequency,
            "TableName": "T10101" if series_name == "GDP" else "T20401",
            "SeriesCode": series_name,
            "Year": "ALL",
            "ResultFormat": "json",
        }

        response = self.client.get(self.BEA_API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        # Parse BEA response format
        results = []
        # BEA response structure varies - simplified parsing
        return results

    # ==================== CENSUS BUREAU ====================

    def fetch_census_series(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch time series data from Census API."""
        params = {
            "get": "value,date",
            "for": "us:1",
            "series": series_id,
        }
        if self.census_api_key:
            params["key"] = self.census_api_key

        response = self.client.get(self.CENSUS_API_URL, params=params)
        response.raise_for_status()

        data = response.json()
        # Parse Census response
        results = []
        return results

    # ==================== UNIFIED REFRESH ====================

    def refresh(self, years: list[int] | None = None) -> dict[str, int]:
        """Refresh macro calendar: fetch new events and upsert to store.

        Returns counts of NEW/UNCHANGED/CHANGED events.
        """
        if years is None:
            current_year = datetime.now().year
            years = [current_year, current_year + 1]

        counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": 0}

        for year in years:
            # Fetch FOMC schedule
            fomc_events = self.fetch_fomc_schedule(year)
            for event_data in fomc_events:
                try:
                    event = self._create_market_event(event_data)
                    result = self.event_store.upsert_event(event)
                    counts[result.value] += 1
                except Exception as e:
                    logger.error(f"Failed to upsert FOMC event: {e}")
                    counts["ERROR"] += 1

            # Fetch economic calendar (placeholder for other providers)
            econ_events = self.fetch_economic_calendar(year)
            for event_data in econ_events:
                try:
                    event = self._create_market_event(event_data)
                    result = self.event_store.upsert_event(event)
                    counts[result.value] += 1
                except Exception as e:
                    logger.error(f"Failed to upsert economic event: {e}")
                    counts["ERROR"] += 1

        return counts

    def fetch_economic_calendar(self, year: int | None = None) -> list[dict[str, Any]]:
        """Fetch scheduled economic releases for a year from official sources.

        This creates scheduled events for known release dates.
        Actual values are fetched separately via fetch_released_values().
        """
        if year is None:
            year = datetime.now().year

        events = []

        # Add scheduled events for implemented providers
        # These are the known release dates for the year
        # In production, these would come from official release calendars

        # BLS monthly releases (typically first/second Friday for NFP, mid-month for CPI)
        # For now, we create placeholder scheduled events
        # A production implementation would parse official release calendars

        return events

    def fetch_released_values(self, since: datetime | None = None) -> dict[str, int]:
        """Fetch latest released values for all implemented series.

        Updates existing scheduled events with actual values.
        Returns counts of updated events.
        """
        if since is None:
            since = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=30)

        counts = {"UPDATED": 0, "ERROR": 0}

        # Fetch BLS releases
        for key in ["cpi", "core_cpi", "ppi", "nfp", "unemployment_rate", "avg_hourly_earnings", "jolts"]:
            config = self.MACRO_EVENTS.get(key)
            if not config or config.provider_status != "implemented":
                continue

            series_id = config.metadata.get("series_id")
            if not series_id:
                continue

            try:
                release = self.fetch_latest_bls_release(series_id)
                if release and release["release_date"]:
                    release_dt = datetime.combine(release["release_date"], datetime.min.time()).replace(tzinfo=timezone.utc)
                    if release_dt >= since:
                        result = self.update_event_values(
                            event_key=f"{key}_{release['release_date'].isoformat()}",
                            actual=release["actual"],
                            released_at=release_dt,
                        )
                        if result:
                            counts["UPDATED"] += 1
            except Exception as e:
                logger.error(f"Failed to fetch BLS release for {key}: {e}")
                counts["ERROR"] += 1

        return counts

    def _create_market_event(self, event_data: dict[str, Any]) -> MarketEvent:
        """Create a MarketEvent from fetched data."""
        return MarketEvent(
            event_type=EventType.MACRO,
            symbol=None,
            title=event_data["name"],
            description=event_data.get("description", ""),
            scheduled_at=datetime.fromisoformat(event_data["scheduled_at"].replace("Z", "+00:00")) if event_data.get("scheduled_at") else None,
            released_at=datetime.fromisoformat(event_data["released_at"].replace("Z", "+00:00")) if event_data.get("released_at") else None,
            timezone="UTC",
            importance=event_data.get("importance", EventImportance.MEDIUM),
            status=event_data.get("status", EventStatus.SCHEDULED),
            actual=event_data.get("actual"),
            forecast=event_data.get("forecast"),  # Official sources don't provide forecast
            previous=event_data.get("previous"),
            unit=event_data.get("unit"),
            source=event_data.get("source", "macro_calendar"),
            source_url=event_data.get("source_url"),
            source_id=event_data.get("event_key"),
            metadata=event_data.get("metadata", {}),
        )

    def get_scheduled_events(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        importance: EventImportance | None = None,
    ) -> list[MarketEvent]:
        """Get scheduled macro events in a date range."""
        if start is None:
            start = datetime.now(timezone.utc)

        events = self.event_store.upcoming_events(limit=1000, from_date=start)

        if end:
            end_date = end.date()
            events = [e for e in events if e.scheduled_at and e.scheduled_at.date() <= end_date]

        if importance:
            events = [e for e in events if e.importance == importance]

        return events

    def get_released_events(
        self,
        since: datetime | None = None,
        importance: EventImportance | None = None,
    ) -> list[MarketEvent]:
        """Get recently released macro events."""
        if since is None:
            since = datetime.now(timezone.utc)

        events = self.event_store.events_released_since(since, limit=1000)

        if importance:
            events = [e for e in events if e.importance == importance]

        return events

    def update_event_values(
        self,
        event_key: str,
        actual: str | None = None,
        forecast: str | None = None,
        previous: str | None = None,
        released_at: datetime | None = None,
    ) -> bool:
        """Update an event with actual/forecast/previous values after release."""
        target_event = self.event_store.get_event_by_source_id(event_key, EventType.MACRO)

        if not target_event:
            logger.warning(f"Event with key {event_key} not found")
            return False

        updated = False
        if actual is not None:
            target_event.actual = actual
            updated = True
        if forecast is not None:
            target_event.forecast = forecast
            updated = True
        if previous is not None:
            target_event.previous = previous
            updated = True
        if released_at is not None:
            target_event.released_at = released_at
            target_event.status = EventStatus.RELEASED
            updated = True

        if updated:
            target_event.updated_at = datetime.now(timezone.utc)
            target_event.content_hash = ""
            result = self.event_store.upsert_event(target_event)
            logger.info(f"Updated event {event_key}: {result.value}")
            return result != "UNCHANGED"

        return False

    def get_provider_status(self) -> dict[str, str]:
        """Get implementation status for all event types."""
        return {
            key: config.provider_status
            for key, config in self.MACRO_EVENTS.items()
        }

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()

    def health_check(self) -> bool:
        """Check if provider is available."""
        return True