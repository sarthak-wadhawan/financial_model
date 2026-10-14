"""Website Evidence Adapter — orchestrates Phase 4–8 provider refresh for website data.

Sync methods only. No background jobs, no paid APIs, no trades.
Real mode ONLY: credentials missing = explicit unavailable.
Persists lightweight sync status (JSON file) — NOT editing event store.
Filters synthetic test/fixture rows non-destructively in website results.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from trading_copilot.models.events import EventType, EventStatus, MarketEvent
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.providers.macro_calendar import MacroCalendarProvider
from trading_copilot.providers.earnings_calendar import EarningsCalendarProvider
from trading_copilot.providers.news_rss_provider import NewsRSSProvider, NewsDocument
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.events.store import EventStore
from trading_copilot.config import Config, Settings


# Per-provider outcome statuses
PROVIDER_SUCCESS = "success"
PROVIDER_REAL_EMPTY = "real_empty"
PROVIDER_UNAVAILABLE = "unavailable"
PROVIDER_ERROR = "provider_error"


@dataclass
class ProviderOutcome:
    """Outcome of a single provider refresh attempt."""
    provider: str
    status: str  # success | real_empty | unavailable | provider_error
    count_new: int = 0
    count_unchanged: int = 0
    count_changed: int = 0
    count_errors: int = 0
    reason: Optional[str] = None
    retrieved_at: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RefreshReport:
    """Aggregated report of a full refresh cycle."""
    started_at: str
    completed_at: str
    symbols: list[str]
    outcomes: list[ProviderOutcome]
    errors: list[dict[str, str]] = field(default_factory=list)

    @property
    def overall_status(self) -> str:
        """Overall status: success if at least one provider succeeded, partial if mixed, failed if all error/unavailable."""
        statuses = [o.status for o in self.outcomes]
        if all(s == PROVIDER_ERROR for s in statuses):
            return "failed"
        if all(s == PROVIDER_UNAVAILABLE for s in statuses):
            return "unavailable"
        if any(s == PROVIDER_SUCCESS for s in statuses):
            return "success"
        return "partial"

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "symbols": self.symbols,
            "overall_status": self.overall_status,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "errors": self.errors,
        }


class WebsiteEvidenceAdapter:
    """
    Orchestrates real-mode refresh of all website evidence providers.

    Interface:
        WebsiteEvidenceAdapter(config, settings, event_store)
        refresh(symbols: list[str]) -> RefreshReport
        status(scope: str | None = None) -> dict

    Real mode ONLY: no fixture fallback.
    Credentials missing = explicit unavailable.
    Persists lightweight sync status to JSON file (configurable).
    Does NOT edit event store — providers upsert directly.
    """

    def __init__(
        self,
        config: Config,
        settings: Settings,
        event_store: EventStore,
        status_path: Optional[str | Path] = None,
    ):
        self.config = config
        self.settings = settings
        self.event_store = event_store
        self._status_lock = threading.Lock()
        self._last_report: Optional[RefreshReport] = None

        # Status persistence (JSON file, not DB)
        if status_path is None:
            status_path = Path("artifacts/cache/website_evidence_status.json")
        self.status_path = Path(status_path)
        self.status_path.parent.mkdir(parents=True, exist_ok=True)

    def refresh(self, symbols: list[str]) -> RefreshReport:
        """
        Run full evidence refresh for the given symbols.

        Providers invoked (real mode only):
        - SEC Filings (45 days, leadership changes, insider Form 4)
        - Earnings Intelligence (extracted EPS/revenue/consensus/guidance/surprise)
        - Macro Calendar (schedules + released values)
        - Earnings Calendar (scheduled earnings)
        - News RSS (7 days, normalized to events)
        - IR Releases (company press releases)
        - SEC Exhibits (8-K exhibits 99.1/99.2/99.3)

        Returns RefreshReport with per-provider outcomes and provenance.
        """
        started = datetime.now(timezone.utc)
        started_iso = started.isoformat()
        symbols_upper = [s.upper() for s in symbols]

        outcomes: list[ProviderOutcome] = []
        errors: list[dict[str, str]] = []

        # ---- SEC Filings + Earnings Intelligence (require SEC_USER_AGENT) ----
        if self.settings.sec_user_agent:
            # SEC Filings
            outcomes.append(self._run_sec_filings(symbols_upper))
            # Earnings Intelligence (extracts EPS/revenue/consensus/guidance from SEC)
            outcomes.append(self._run_earnings_intelligence(symbols_upper))
        else:
            outcomes.append(ProviderOutcome(
                provider="sec_filings",
                status=PROVIDER_UNAVAILABLE,
                reason="SEC operator identity (SEC_USER_AGENT) missing",
                retrieved_at=started_iso,
            ))
            outcomes.append(ProviderOutcome(
                provider="earnings_intelligence",
                status=PROVIDER_UNAVAILABLE,
                reason="SEC operator identity (SEC_USER_AGENT) missing",
                retrieved_at=started_iso,
            ))

        # ---- Macro Calendar (no credentials required for BLS/Fed) ----
        outcomes.append(self._run_macro_calendar())

        # ---- Earnings Calendar (requires at least one API key) ----
        outcomes.append(self._run_earnings_calendar(symbols_upper))

        # ---- News RSS (no credentials) ----
        outcomes.append(self._run_news_rss(symbols_upper))

        # ---- IR Releases (no credentials) ----
        outcomes.append(self._run_ir_releases(symbols_upper))

        # ---- SEC Exhibits (requires SEC_USER_AGENT) ----
        if self.settings.sec_user_agent:
            outcomes.append(self._run_sec_exhibits(symbols_upper))
        else:
            outcomes.append(ProviderOutcome(
                provider="sec_exhibits",
                status=PROVIDER_UNAVAILABLE,
                reason="SEC operator identity (SEC_USER_AGENT) missing",
                retrieved_at=started_iso,
            ))

        completed = datetime.now(timezone.utc)
        report = RefreshReport(
            started_at=started_iso,
            completed_at=completed.isoformat(),
            symbols=symbols_upper,
            outcomes=outcomes,
            errors=errors,
        )

        # Persist lightweight sync status (not editing event store)
        with self._status_lock:
            self._last_report = report
            self._persist_status(report)

        return report

    def _run_sec_filings(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh SEC filings: recent 45 days, leadership changes, insider Form 4."""
        started = datetime.now(timezone.utc)
        provider = SECFilingProvider(
            event_store=self.event_store,
            user_agent=self.settings.sec_user_agent,
        )
        try:
            counts = provider.refresh(
                symbols,
                lookback_days=self.config.sources.filings_lookback_days,
                max_per_symbol=self.config.sources.max_filings_per_symbol,
            )
            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="sec_filings",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No new filings in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "lookback_days": self.config.sources.filings_lookback_days,
                    "max_per_symbol": self.config.sources.max_filings_per_symbol,
                    "errors": provider.errors,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="sec_filings",
                status=PROVIDER_ERROR,
                reason=f"SEC Filing Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_earnings_intelligence(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh earnings intelligence: extracted EPS/revenue/consensus/guidance/surprise."""
        started = datetime.now(timezone.utc)
        provider = EarningsIntelligenceProvider(
            event_store=self.event_store,
            user_agent=self.settings.sec_user_agent,
        )
        try:
            counts = provider.refresh(
                symbols,
                lookback_days=365,
                max_per_symbol=50,
            )
            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="earnings_intelligence",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No earnings results in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "lookback_days": 365,
                    "max_per_symbol": 50,
                    "errors": provider.errors,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="earnings_intelligence",
                status=PROVIDER_ERROR,
                reason=f"Earnings Intelligence Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_macro_calendar(self) -> ProviderOutcome:
        """Refresh macro calendar: Fed schedules + BLS released values."""
        started = datetime.now(timezone.utc)
        provider = MacroCalendarProvider(event_store=self.event_store)
        try:
            # Fetch FOMC schedule for current and next year
            counts = provider.refresh()
            # Also fetch released values for BLS series
            released_counts = provider.fetch_released_values()
            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="macro_calendar",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No macro events in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "years": [datetime.now().year, datetime.now().year + 1],
                    "released_updated": released_counts.get("UPDATED", 0),
                    "released_unmatched": released_counts.get("UNMATCHED", 0),
                    "errors": provider.errors,
                    "provider_status": provider.get_provider_status(),
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="macro_calendar",
                status=PROVIDER_ERROR,
                reason=f"Macro Calendar Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_earnings_calendar(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh earnings calendar: scheduled earnings from available sources."""
        started = datetime.now(timezone.utc)
        provider = EarningsCalendarProvider(event_store=self.event_store)
        try:
            from_date = date.today()
            to_date = from_date + timedelta(days=90)
            counts = provider.refresh(symbols, from_date=from_date, to_date=to_date)
            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            # Check if no sources configured
            if not provider._get_available_sources():
                status = PROVIDER_UNAVAILABLE
            return ProviderOutcome(
                provider="earnings_calendar",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else (
                    "No earnings calendar source configured" if status == PROVIDER_UNAVAILABLE
                    else ("No scheduled earnings in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors")
                ),
                retrieved_at=started.isoformat(),
                details={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "available_sources": provider._get_available_sources(),
                    "last_fetch_status": provider.last_fetch_status,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="earnings_calendar",
                status=PROVIDER_ERROR,
                reason=f"Earnings Calendar Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_news_rss(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh news RSS: normalized to events preserving evidence timestamps."""
        started = datetime.now(timezone.utc)
        provider = NewsRSSProvider(timeout=10)
        try:
            from_date = (datetime.now(timezone.utc) - timedelta(days=7)).date()
            to_date = datetime.now(timezone.utc).date()
            documents = provider.fetch_news(symbols, from_date=from_date, to_date=to_date)

            counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": len(provider.errors)}
            for document in documents:
                event = MarketEvent(
                    event_type=EventType.NEWS,
                    symbol=document.symbol,
                    title=document.headline,
                    description=document.body,
                    released_at=document.published_at,
                    status=EventStatus.RELEASED,
                    source=document.publisher,
                    source_url=document.source_url,
                    source_id=document.document_id,
                    metadata={
                        "document": document.model_dump(mode="json"),
                        "retrieved_at": document.retrieved_at.isoformat(),
                        "claim_type": "attributed_statement",
                    },
                )
                result = self.event_store.upsert_event(event)
                counts[result.value] += 1

            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="news_rss",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No news in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "feeds_queried": list(provider.feeds.keys()),
                    "errors": provider.errors,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="news_rss",
                status=PROVIDER_ERROR,
                reason=f"News RSS Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_ir_releases(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh IR releases: company press releases from IR RSS feeds."""
        started = datetime.now(timezone.utc)
        provider = IRReleaseProvider(timeout=10)
        try:
            from_date = (datetime.now(timezone.utc) - timedelta(days=7)).date()
            to_date = datetime.now(timezone.utc).date()
            documents = provider.fetch_company_releases(symbols, from_date=from_date, to_date=to_date)

            counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": len(provider.errors)}
            for document in documents:
                event = MarketEvent(
                    event_type=EventType.NEWS,
                    symbol=document.symbol,
                    title=document.headline,
                    description=document.body,
                    released_at=document.published_at,
                    status=EventStatus.RELEASED,
                    source=document.publisher,
                    source_url=document.source_url,
                    source_id=document.document_id,
                    metadata={
                        "document": document.model_dump(mode="json"),
                        "retrieved_at": document.retrieved_at.isoformat(),
                        "claim_type": "company_statement",
                        "source_type": "ir_release",
                    },
                )
                result = self.event_store.upsert_event(event)
                counts[result.value] += 1

            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="ir_releases",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No IR releases in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "feeds_queried": list(provider.feeds.keys()),
                    "errors": provider.errors,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="ir_releases",
                status=PROVIDER_ERROR,
                reason=f"IR Release Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def _run_sec_exhibits(self, symbols: list[str]) -> ProviderOutcome:
        """Refresh SEC exhibits: 8-K exhibits 99.1/99.2/99.3 (press releases)."""
        started = datetime.now(timezone.utc)
        provider = SECExhibitProvider(user_agent=self.settings.sec_user_agent)
        try:
            from_date = (datetime.now(timezone.utc) - timedelta(days=45)).date()
            to_date = datetime.now(timezone.utc).date()
            documents = provider.fetch_company_releases(symbols, from_date=from_date, to_date=to_date)

            counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": len(provider.errors)}
            for document in documents:
                event = MarketEvent(
                    event_type=EventType.NEWS,
                    symbol=document.symbol,
                    title=document.headline,
                    description=document.body,
                    released_at=document.published_at,
                    status=EventStatus.RELEASED,
                    source=document.publisher,
                    source_url=document.source_url,
                    source_id=document.document_id,
                    metadata={
                        "document": document.model_dump(mode="json"),
                        "retrieved_at": document.retrieved_at.isoformat(),
                        "claim_type": "company_statement",
                        "source_type": "sec_exhibit",
                    },
                )
                result = self.event_store.upsert_event(event)
                counts[result.value] += 1

            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            status = PROVIDER_SUCCESS if total > 0 else PROVIDER_REAL_EMPTY
            if counts.get("ERROR", 0) > 0:
                status = PROVIDER_ERROR
            return ProviderOutcome(
                provider="sec_exhibits",
                status=status,
                count_new=counts.get("NEW", 0),
                count_unchanged=counts.get("UNCHANGED", 0),
                count_changed=counts.get("CHANGED", 0),
                count_errors=counts.get("ERROR", 0),
                reason=None if status == PROVIDER_SUCCESS else ("No SEC exhibits in window" if status == PROVIDER_REAL_EMPTY else "Provider reported errors"),
                retrieved_at=started.isoformat(),
                details={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "errors": provider.errors,
                },
            )
        except Exception as exc:
            return ProviderOutcome(
                provider="sec_exhibits",
                status=PROVIDER_ERROR,
                reason=f"SEC Exhibit Provider failed: {type(exc).__name__}",
                retrieved_at=started.isoformat(),
                details={"error": str(exc)[:300]},
            )
        finally:
            provider.close()

    def status(self, scope: Optional[str] = None) -> dict[str, Any]:
        """
        Get current sync status.

        Args:
            scope: Optional provider name to filter (e.g., "sec_filings", "news_rss")

        Returns:
            Dict with overall status and per-provider details
        """
        with self._status_lock:
            if self._last_report is None:
                self._last_report = self._load_status()

            if self._last_report is None:
                return {
                    "overall_status": "not_refreshed",
                    "last_refresh": None,
                    "providers": {},
                }

            report = self._last_report
            result = {
                "overall_status": report.overall_status,
                "last_refresh": report.completed_at,
                "providers": {o.provider: o.to_dict() for o in report.outcomes},
            }

            if scope:
                provider_data = result["providers"].get(scope)
                if provider_data:
                    return {"provider": scope, **provider_data}
                return {"provider": scope, "status": "not_refreshed"}

            return result

    def _persist_status(self, report: RefreshReport) -> None:
        """Persist lightweight sync status to JSON file."""
        try:
            with open(self.status_path, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
        except Exception:
            # Status persistence is best-effort; don't fail the refresh
            pass

    def _load_status(self) -> Optional[RefreshReport]:
        """Load last sync status from JSON file."""
        if not self.status_path.exists():
            return None
        try:
            with open(self.status_path) as f:
                data = json.load(f)
            outcomes = [ProviderOutcome(**o) for o in data.get("outcomes", [])]
            return RefreshReport(
                started_at=data["started_at"],
                completed_at=data["completed_at"],
                symbols=data["symbols"],
                outcomes=outcomes,
                errors=data.get("errors", []),
            )
        except Exception:
            return None


def create_website_evidence_adapter(
    config: Config,
    settings: Settings,
    event_store: EventStore,
) -> WebsiteEvidenceAdapter:
    """Factory function for WebsiteEvidenceAdapter."""
    return WebsiteEvidenceAdapter(config, settings, event_store)