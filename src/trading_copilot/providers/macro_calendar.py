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
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

import httpx

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.providers.base import BaseProvider


logger = logging.getLogger(__name__)


class _FedCalendarHTML(HTMLParser):
    """Minimal tree reader for the Fed's year panels."""

    def __init__(self):
        super().__init__()
        self.root = {"tag": "root", "attrs": {}, "children": [], "text": ""}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "text": ""}
        self.stack[-1]["children"].append(node)
        if tag not in {"br", "hr", "img", "input", "meta", "link", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    @staticmethod
    def walk(node):
        yield node
        for child in node["children"]:
            yield from _FedCalendarHTML.walk(child)


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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
            provider_status="provider_pending",
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
        mode: str = "live",
        fixture_dir: str | Path | None = None,
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
        if mode not in {"live", "demo"}:
            raise ValueError("mode must be live or demo")
        self.mode = mode
        self.fixture_dir = Path(fixture_dir).resolve() if fixture_dir else Path(__file__).resolve().parents[3] / "tests/fixtures"
        self.last_fetch_status: dict[str, Any] = {}

    # ==================== FEDERAL RESERVE ====================

    def fetch_fomc_schedule(self, year: int | None = None) -> list[dict[str, Any]]:
        """Fetch official schedules; fixtures are exclusive to explicit demo mode."""
        if year is None:
            year = datetime.now().year

        if self.mode == "demo":
            self.last_fetch_status["fomc"] = {"status": "demo", "year": year}
            return self._load_fomc_fixture(year)
        try:
            events = self._fetch_fomc_from_fed(year)
        except Exception as exc:
            self.last_fetch_status["fomc"] = {"status": "error", "year": year, "error_type": type(exc).__name__}
            raise
        self.last_fetch_status["fomc"] = {"status": "ok", "year": year, "count": len(events)}
        return events

    def _fetch_fomc_from_fed(self, year: int) -> list[dict[str, Any]]:
        """Parse FOMC calendar from Federal Reserve website."""
        # The Fed publishes calendars at URLs like:
        # https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (current year)
        # https://www.federalreserve.gov/monetarypolicy/fomccalendars_2025.htm (historical)

        # The main calendar contains multiple year panels, including upcoming years.
        url = self.FED_FOMC_CALENDAR_URL

        response = self.client.get(url)
        response.raise_for_status()

        # Parse HTML for meeting dates
        # The page has a table with meeting dates
        html = response.text
        events = self._parse_fomc_html(html, year)

        if not events:
            raise ValueError("No FOMC meetings parsed from HTML")

        retrieved_at = datetime.now(timezone.utc).isoformat()
        for event in events:
            event["source_url"] = str(response.url)
            event["metadata"]["retrieved_at"] = retrieved_at

        return events

    def _parse_fomc_html(self, html: str, year: int) -> list[dict[str, Any]]:
        """Parse year-scoped Fed panels, never arbitrary dates in page prose.

        A meeting date does not prove an exact statement time. The customary
        14:00 Eastern time is retained only as an explicitly derived expectation.
        """
        parser = _FedCalendarHTML()
        parser.feed(html)
        nodes = list(parser.walk(parser.root))
        rows = []
        months = r"January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
        for panel in nodes:
            if "panel" not in panel["attrs"].get("class", "").split():
                continue
            descendants = list(parser.walk(panel))
            if not any(n["tag"] in {"h2", "h3", "h4"} and re.search(rf"\b{year}\s+FOMC\s+Meetings\b", n["text"]) for n in descendants):
                continue
            for row in descendants:
                classes = row["attrs"].get("class", "").split()
                if "fomc-meeting" not in classes:
                    continue
                cells = list(parser.walk(row))
                month = next((n["text"].strip() for n in cells if "fomc-meeting__month" in n["attrs"].get("class", "").split()), None)
                days = next((n["text"].strip() for n in cells if "fomc-meeting__date" in n["attrs"].get("class", "").split()), None)
                if month and days:
                    rows.append((month, days, row["text"].strip()))
        # Older/table-based calendars carry the year in the date cell itself.
        for node in nodes:
            if node["tag"] == "td" and "date" in node["attrs"].get("class", "").split():
                match = re.fullmatch(rf"({months})\s+(\d{{1,2}}(?:[-–]\d{{1,2}})?),?\s+{year}", node["text"].strip())
                if match:
                    rows.append((match[1], match[2], node["text"].strip()))
        events = {}
        for month, days, evidence in rows:
            if re.fullmatch(r"\d{1,2}\s+\(notation vote\)", days):
                # A notation vote is not a scheduled FOMC meeting.
                continue
            month_match = re.fullmatch(rf"({months})(?:\s*/\s*({months}))?", month)
            day_match = re.fullmatch(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s*\*?", days)
            if not month_match or not day_match:
                raise ValueError("Unsupported Fed meeting date format")
            start = date(year, self._month_name_to_num(month_match[1]), int(day_match[1]))
            end = date(year, self._month_name_to_num(month_match[2] or month_match[1]), int(day_match[2] or day_match[1]))
            if end < start:
                raise ValueError("Invalid Fed meeting date range")
            event = self._fomc_date_event(start, end)
            event["metadata"]["evidence"] = evidence
            events[event["event_key"]] = event
        return sorted(events.values(), key=lambda e: e["metadata"]["meeting_start"])

    def _fomc_date_event(self, start: date, end: date) -> dict[str, Any]:
        expected = datetime(end.year, end.month, end.day, 14, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
        return {
            "name": "FOMC Meeting",
            "description": "Federal Open Market Committee meeting - monetary policy decision",
            "scheduled_at": None,
            "released_at": None,
            "importance": EventImportance.CRITICAL,
            "status": EventStatus.SCHEDULED,
            "source": "federal_reserve",
            "source_url": self.FED_FOMC_CALENDAR_URL,
            "event_key": f"fomc_meeting_{start.isoformat()}",
            "metadata": {
                "event_subtype": "fomc_meeting",
                "event_date": end.isoformat(),
                "meeting_start": start.isoformat(),
                "meeting_end": end.isoformat(),
                "minutes_date": None,
                "scheduled_time_precision": "date",
                "event_timezone": "America/New_York",
                "expected_statement_at": expected.isoformat(),
                "expected_statement_time_source": "derived_customary_14_ET_not_verified",
                "verification_state": "official_date_only",
            },
        }

    def _load_fomc_fixture(self, year: int) -> list[dict[str, Any]]:
        """Load FOMC schedule from fixture file."""
        fixture_path = self.fixture_dir / f"fomc_{year}.json"
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)
            events = []
            for meeting in data:
                start = meeting["meeting_date"]
                end = meeting["meeting_end"]
                event = self._fomc_date_event(date.fromisoformat(start), date.fromisoformat(end))
                event["source"] = "fixture"
                event["event_key"] = f"fixture_fomc_meeting_{start}"
                event["source_url"] = fixture_path.as_uri()
                event["metadata"].update({"minutes_date": meeting.get("minutes_date"), "verification_state": "demo_fixture", "data_mode": "demo"})
                events.append(event)
            return events

        # If no fixture, return empty (will be handled gracefully)
        return []

    def _month_name_to_num(self, name: str) -> int:
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12,
        }
        if name in months:
            return months[name]
        abbreviations = {month[:3]: number for month, number in months.items()}
        abbreviations["Sept"] = 9
        if name not in abbreviations:
            raise ValueError("Unknown month name")
        return abbreviations[name]

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
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for series in data.get("Results", {}).get("series", []):
            if series.get("seriesID") != series_id:
                continue
            for item in series.get("data", []):
                year = int(item["year"])
                period = item["period"]  # e.g., "M01", "M02", etc.
                if period.startswith("M"):
                    month = int(period[1:])
                    if not 1 <= month <= 12:  # M13 is an annual average, not a month.
                        continue
                    value = item["value"]
                    if value != ".":
                        results.append({
                            "date": date(year, month, 1),
                            "observation_period": f"{year}-{month:02d}",
                            "release_date": None,
                            "released_at": None,
                            "value": value,
                            "series_id": series_id,
                            "source": "bls",
                            "source_url": self.BLS_API_URL,
                            "retrieved_at": retrieved_at,
                            "footnotes": item.get("footnotes", []),
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
            "observation_date": latest["date"],
            "observation_period": latest["observation_period"],
            "release_date": None,
            "released_at": None,
            "series_id": series_id,
            "source": latest["source"],
            "source_url": latest["source_url"],
            "retrieved_at": latest["retrieved_at"],
            "footnotes": latest["footnotes"],
        }

    # ==================== BUREAU OF ECONOMIC ANALYSIS ====================

    def fetch_bea_series(
        self,
        series_name: str,
        frequency: str = "M",  # M=monthly, Q=quarterly
    ) -> list[dict[str, Any]]:
        """Explicitly unavailable until official table/line contracts are supported.

        These series names are not valid NIPA API selection parameters. Having a
        free API key does not turn the previous placeholder into a real parser.
        """
        self.last_fetch_status["bea"] = {"status": "unavailable", "reason": "unsupported_official_parser"}
        raise NotImplementedError("BEA official table/line parsing is not implemented")

    # ==================== CENSUS BUREAU ====================

    def fetch_census_series(self, series_id: str) -> list[dict[str, Any]]:
        """Do not issue invalid marts queries or represent a stub as real empty."""
        self.last_fetch_status["census"] = {"status": "unavailable", "reason": "unsupported_official_parser"}
        raise NotImplementedError("Census dataset-specific official parsing is not implemented")

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
            try:
                fomc_events = self.fetch_fomc_schedule(year)
            except Exception as exc:
                logger.warning("FOMC fetch failed (%s)", type(exc).__name__)
                counts["ERROR"] += 1
                fomc_events = []
            for event_data in fomc_events:
                try:
                    event = self._create_market_event(event_data)
                    result = self.event_store.upsert_event(event)
                    counts[result.value] += 1
                except Exception as e:
                    logger.error(f"Failed to upsert FOMC event: {e}")
                    counts["ERROR"] += 1

            # Fetch economic calendar (placeholder for other providers)
            try:
                econ_events = self.fetch_economic_calendar(year)
            except NotImplementedError:
                counts["ERROR"] += 1
                econ_events = []
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
        self.last_fetch_status["economic_calendar"] = {"status": "unavailable", "reason": "official_release_calendar_not_implemented"}
        raise NotImplementedError("Official economic release calendar parsing is not implemented")

    def fetch_released_values(self, since: datetime | None = None) -> dict[str, int]:
        """Fetch latest released values for all implemented series.

        Updates existing scheduled events with actual values.
        Returns counts of updated events.
        """
        if since is None:
            since = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=30)

        counts = {"UPDATED": 0, "ERROR": 0, "UNMATCHED": 0}

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
                if release:
                    # Observation APIs contain neither release time nor a safe
                    # schedule identity. Do not guess a release or overwrite an
                    # unrelated event based on its reference month.
                    counts["UNMATCHED"] += 1
                    self.last_fetch_status[key] = {"status": "unmatched", "reason": "release_time_and_schedule_identity_unknown", "observation_period": release["observation_period"], "retrieved_at": release["retrieved_at"]}
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

        # Date-only schedules deliberately have no fabricated scheduled_at.
        events = self.event_store.events_by_type(EventType.MACRO, limit=1000)
        selected = []
        for event in events:
            if event.status != EventStatus.SCHEDULED:
                continue
            event_date = event.scheduled_at.date() if event.scheduled_at else None
            if event_date is None and event.metadata.get("event_date"):
                event_date = date.fromisoformat(event.metadata["event_date"])
            if event_date is None or event_date < start.date() or end and event_date > end.date():
                continue
            selected.append(event)
        events = sorted(selected, key=lambda e: e.metadata.get("event_date") or e.scheduled_at.date().isoformat())

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
        """True only after a successful official schedule retrieval, not a stub."""
        return self.last_fetch_status.get("fomc", {}).get("status") == "ok"
