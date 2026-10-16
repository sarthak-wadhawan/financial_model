"""Read-only, fail-closed projection of retained official earnings announcements.

Calendar dates and sessions are facts, not instants. This module never refreshes
providers, resolves hosts, or infers consensus, timezones, or price reactions.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import ipaddress
import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit

from trading_copilot.models.events import EventStatus, EventType, MarketEvent
from trading_copilot.providers.ir_release_provider import IR_RSS_FEEDS


EARNINGS_QUERY_LIMIT = 1000


def _official_origin(url: object) -> tuple[str, int] | None:
    if not isinstance(url, str) or any(c.isspace() for c in url) or "\\" in url:
        return None
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.port not in (None, 443)
                or parsed.fragment or host.endswith(".") or "." not in host):
            return None
        try:
            ipaddress.ip_address(host)
            return None  # Configured company origins must be public DNS names.
        except ValueError:
            pass
        if (not re.fullmatch(r"[a-z0-9.-]+", host)
                or host.rsplit(".", 1)[-1] in {"local", "localhost", "internal", "test", "invalid"}):
            return None
        return host, 443
    except ValueError:
        return None


def _observed_at(value: object, now: datetime) -> str | None:
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
        if observed is None or observed.tzinfo is None or observed > now:
            return None
        return observed.isoformat()
    except (ValueError, TypeError):
        return None


def _candidate(event: MarketEvent, symbol: str, now: datetime, feeds: Mapping[str, str]) -> dict | None:
    m = event.metadata
    expected_origin = _official_origin(feeds.get(symbol))
    if (event.symbol != symbol or event.event_type != EventType.EARNINGS
            or event.status != EventStatus.SCHEDULED or event.source != "company_ir_rss"
            or not expected_origin or _official_origin(event.source_url) != expected_origin
            or m.get("event_kind") != "results_release"
            or m.get("verification_status") != "verified"
            or m.get("verification_scope") != "explicit_official_announcement"):
        return None
    document_id = m.get("source_document_id")
    content_hash = m.get("source_content_hash")
    observed = _observed_at(m.get("retrieved_at"), now)
    span = m.get("evidence_span")
    if (not isinstance(document_id, str) or not document_id.strip()
            or not isinstance(content_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", content_hash)
            or observed is None or not isinstance(span, dict)):
        return None
    start, end, text = span.get("start"), span.get("end"), span.get("text")
    if (span.get("field") not in ("body", "headline")
            or type(start) is not int or type(end) is not int or start < 0 or end <= start
            or not isinstance(text, str) or not text.strip() or len(text) != end - start
            or not any(text in value for value in (event.description or "", event.title))):
        return None
    try:
        raw_date = m.get("event_date")
        if not isinstance(raw_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            return None
        calendar_date = date.fromisoformat(raw_date)
    except ValueError:
        return None
    month = rf"(?:{calendar_date.strftime('%B')}|{calendar_date.strftime('%b')}\.?)"
    month_date = rf"\b{month}\s+{calendar_date.day}(?:st|nd|rd|th)?\s*,?\s+{calendar_date.year}\b"
    release_claim = re.search(
        r"\b(?:announce|report|release|publish)\w*\b(?P<between>[^.!?;]*?)\b(?:financial results|quarterly results|earnings)\b",
        text, re.I,
    )
    if (not (re.search(month_date, text, re.I) or calendar_date.isoformat() in text)
            or release_claim is None
            or re.search(r"\b(?:call|conference|discuss)\b", release_claim.group("between"), re.I)
            or re.search(r"\bearnings\s+(?:conference\s+)?call\b", text, re.I)
            or re.search(r"\b(?:cancelled|canceled|tentative|estimated|expected|unconfirmed|may|might)\b", text, re.I)):
        return None
    precision, session = m.get("scheduled_time_precision"), m.get("session")
    if not ((precision == "date" and session == "unknown")
            or (precision == "session" and session in ("bmo", "amc"))):
        return None
    if session == "amc" and not re.search(r"after (?:the )?(?:market close|close of (?:the )?market|market closes)", text, re.I):
        return None
    if session == "bmo" and not re.search(r"before (?:the )?(?:market open|opening of (?:the )?market|market opens)", text, re.I):
        return None
    # A date/session assertion must not smuggle in a synthesized midnight/clock.
    if event.scheduled_at is not None or event.released_at is not None or m.get("event_timezone") is not None:
        return None
    period = m.get("fiscal_period")
    if not isinstance(period, str) or not re.fullmatch(r"(?:first|second|third|fourth|full_year):\d{4}", period):
        period = None
    return {
        "event_date": calendar_date.isoformat(), "session": session,
        "scheduled_time_precision": precision, "fiscal_period": period,
        "evidence": {"event_id": event.event_id, "source": event.source,
                     "source_url": event.source_url, "source_document_id": document_id,
                     "source_content_hash": content_hash, "retrieved_at": observed,
                     "evidence_span": dict(span)},
    }


def project_next_earnings(
    symbol: str, events: Sequence[MarketEvent], *, now: datetime | None = None,
    checked_state: Mapping[str, object] | None = None,
    trusted_feeds: Mapping[str, str] | None = None,
) -> dict:
    """Project a bounded EARNINGS query, without mutating events or global state.

    ``checked_state`` is explicitly per-symbol provider state, never global state.
    Omitted state means *not refreshed*, even when stored evidence is available.
    Hitting the query cap suppresses selection: unseen rows may contain conflicts.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    symbol = symbol.upper()
    coverage = {
        "status": "not_refreshed", "confirmation_status": "not_confirmed",
        "checked_at": None, "query_limit": EARNINGS_QUERY_LIMIT,
        "query_truncated": len(events) >= EARNINGS_QUERY_LIMIT,
        "selection_scope": "retained_events_only",
        "reason": "Per-symbol official source has not been refreshed by this projection.",
    }
    if checked_state is not None and checked_state.get("symbol") == symbol:
        checked_at = _observed_at(checked_state.get("checked_at"), now)
        status = checked_state.get("status")
        if checked_at and status in ("checked", "empty", "partial", "error", "unavailable"):
            coverage.update(status=status, checked_at=checked_at,
                            reason="Explicit per-symbol provider check state; selection uses retained events only.")
    result = {"next_earnings": None, "earnings_coverage": coverage}
    if coverage["query_truncated"]:
        coverage["reason"] = "Stored earnings query reached its cap; next announcement completeness is unknown."
        return result
    candidates = [candidate for event in events
                  if (candidate := _candidate(event, symbol, now, trusted_feeds if trusted_feeds is not None else IR_RSS_FEEDS))]
    future = [c for c in candidates if c["event_date"] >= now.date().isoformat()]
    # Unknown periods cannot be assumed distinct. Conflicting active evidence
    # must be reconciled by ingestion, never by picking newest/earliest here.
    for candidate in future:
        for other in candidates:
            same_or_unknown_period = (not candidate["fiscal_period"] or not other["fiscal_period"]
                                      or candidate["fiscal_period"] == other["fiscal_period"])
            contradictory = (candidate["event_date"] != other["event_date"]
                             or {candidate["session"], other["session"]} == {"bmo", "amc"})
            if same_or_unknown_period and contradictory:
                coverage.update(confirmation_status="conflicting_announcements",
                                reason="Contradictory active official announcements require reconciliation.")
                return result
    if not future:
        return result
    earliest = min(c["event_date"] for c in future)
    group = [c for c in future if c["event_date"] == earliest]
    periods = {c["fiscal_period"] for c in group if c["fiscal_period"]}
    sessions = {c["session"] for c in group if c["session"] != "unknown"}
    if len(periods) > 1 or len(sessions) > 1:
        coverage.update(confirmation_status="conflicting_announcements", reason="Non-equivalent announcements tie on the earliest date.")
        return result
    session = next(iter(sessions), "unknown")
    evidence = sorted((c["evidence"] for c in group), key=lambda e: e["event_id"])
    result["next_earnings"] = {
        "symbol": symbol, "event_kind": "results_release", "event_date": earliest,
        "session": session, "scheduled_time_precision": "session" if sessions else "date",
        "scheduled_at": None, "event_timezone": None,
        "days_until": (date.fromisoformat(earliest) - now.date()).days,
        "countdown_basis": "calendar_days", "fiscal_period": next(iter(periods), None),
        "verification_status": "verified", "verification_scope": "explicit_official_announcement",
        "event_ids": [e["event_id"] for e in evidence], "evidence": evidence,
    }
    coverage.update(confirmation_status="retained_official_announcement",
                    reason="Retained official announcement; this GET did not refresh or recheck the provider.")
    return result
