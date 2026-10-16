"""Conservative, source-text-only official earnings schedule extraction.

No fiscal-cadence estimates, call-to-release substitution, or default clocks.
Offsets address the preserved document body/headline, not rewritten text.
"""
import re
from datetime import date
from urllib.parse import urlsplit

from trading_copilot.models.events import EventStatus, EventType, MarketEvent
from trading_copilot.models.news import NewsSourceType
from trading_copilot.providers.ir_release_provider import IR_RSS_FEEDS


MONTHS = "January February March April May June July August September October November December".split()
DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(20\d{2})\b", re.I)
RELEASE = re.compile(
    r"\b(?:will\s+(?:announce|release|report|publish)|to\s+(?:announce|release|report|publish))\b"
    r"[^.!?]{0,180}?\b(?:financial\s+results|(?:quarterly|annual|quarter|year)[^.!?]{0,50}?results|earnings)\b", re.I)
CALL = re.compile(r"\b(?:earnings\s+(?:conference\s+)?call|conference\s+call|earnings\s+webcast)\b", re.I)
CANCEL = re.compile(r"\b(?:cancel(?:led|ed|lation)?|postponed|will\s+not|no\s+longer|not\s+(?:announce|release|report))\b", re.I)
PERIOD = re.compile(r"\bfiscal\s+(first|second|third|fourth|[1-4])\s+quarter\s+(?:of\s+)?(?:and\s+full-year\s+)?(20\d{2})\b", re.I)
REPLACEMENT = re.compile(r"\brescheduled\s+from\s+(" + DATE.pattern + r")\s+to\s+(" + DATE.pattern + r")", re.I)


def fiscal_period(document):
    matches = {(m[1].lower(), m[2]) for m in PERIOD.finditer(document.body)}
    return ":".join(next(iter(matches))) if len(matches) == 1 else None


def authenticated_official_document(document):
    """Require the audited feed and observed HTTPS origin, including entry link."""
    approved = IR_RSS_FEEDS.get(document.symbol)
    if document.source_type != NewsSourceType.COMPANY_IR or not approved:
        return False
    if document.metadata.get("feed_url") != approved:
        return False
    expected = urlsplit(approved).hostname
    for url in (document.metadata.get("feed_response_url", ""), document.source_url):
        try:
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.hostname != expected or
                    parsed.username or parsed.password or parsed.port not in (None, 443)):
                return False
        except ValueError:
            return False
    return True


def extract_official_schedule(document, today: date):
    """Return one explicitly announced future schedule, or None if ambiguous.

    A title may evidence a call/date-only announcement. Session evidence must
    occur in the release clause, never a later webcast sentence.
    """
    if not authenticated_official_document(document):
        return None
    whole = document.body + "\n" + document.headline
    if CANCEL.search(whole):
        return None
    candidates = []
    for field, text in [("body", document.body), ("headline", document.headline)]:
        found = []
        schedule_language = False
        # Split only sentence terminators followed by whitespace; month/date
        # evidence needs an explicit year, not a publication-year assumption.
        for sentence in re.finditer(r"[^!?]+?(?:\.(?=\s|$)|$)", text):
            clause = sentence.group()
            release, call = RELEASE.search(clause), CALL.search(clause)
            # Dividends/record dates are not results announcements, even when
            # adjacent words include "earnings" or "financial results".
            if re.search(r"\b(?:dividend|shareholders?\s+of\s+record)\b", clause, re.I):
                release = None
            if not release and not call:
                continue
            schedule_language = True
            if re.search(r"\b(?:cancel(?:led|ed|lation)?|postponed|not\s+(?:announce|release|report)|may|might|tentative|expected|estimated)\b", clause, re.I):
                return None
            dates = list(DATE.finditer(clause))
            replacement = REPLACEMENT.search(clause)
            if replacement and len(dates) == 2:
                dates = dates[1:]
            if len(dates) != 1:
                return None
            match = dates[0]
            # A date preceding the announcement language can belong to another
            # fact in the sentence; it does not bind the future results/call.
            if match.start() < (release.end() if release else call.end()):
                return None
            try:
                day = date(int(match[3]), next(i + 1 for i, m in enumerate(MONTHS) if m.lower() == match[1].lower()), int(match[2]))
            except ValueError:
                return None
            if not today <= day <= date.fromordinal(today.toordinal() + 180):
                continue
            # A mixed results/call clause cannot establish a release date unless
            # the date occurs before the separate call clause.
            if release and call and call.start() < match.start():
                continue
            kind = "results_release" if release else "earnings_call"
            session = "unknown"
            if release:
                release_text = clause[:call.start()] if call else clause
                amc = bool(re.search(r"\bafter (?:the )?market clos(?:e|es|ing)\b", release_text, re.I))
                bmo = bool(re.search(r"\bbefore (?:the )?market open(?:s|ing)?\b", release_text, re.I))
                if amc != bmo:
                    session = "amc" if amc else "bmo"
            found.append((day, kind, session, field, sentence.start(), sentence.end(), clause))
        if found:
            candidates = found
            break
        if schedule_language:
            # A vague/conflicting body is not repaired by an older headline.
            return None
    if not candidates or len({(c[0], c[1], c[2]) for c in candidates}) != 1:
        return None
    day, kind, session, field, start, end, text = candidates[0]
    return MarketEvent(
        event_type=EventType.EARNINGS, symbol=document.symbol,
        title=document.headline, description=text, status=EventStatus.SCHEDULED,
        scheduled_at=None, source="company_ir_rss", source_url=document.source_url,
        source_id=f"{document.document_id}:schedule:{kind}",
        metadata={"event_date": day.isoformat(), "session": session, "time": session,
                  "scheduled_time_precision": "session" if session != "unknown" else "date",
                  "event_timezone": None, "event_kind": kind,
                  "verification_status": "verified", "verification_scope": "explicit_official_announcement",
                   "source_document_id": document.document_id,
                   "fiscal_period": fiscal_period(document),
                   "source_content_hash": document.content_hash,
                  "retrieved_at": document.retrieved_at.isoformat(),
                  "evidence_span": {"field": field, "start": start, "end": end, "text": text}},
    )


def reconcile_schedule_revision(document, schedule, existing_events):
    """Return non-destructive revisions only with a bounded identity/evidence link.

    Same-document loss of support becomes UNKNOWN, never a fabricated cancellation.
    Cross-document retirement requires explicit old-date reference, kind and fiscal
    period, not company/title/date proximity. Unsupported cases remain unlinked.
    """
    if not authenticated_official_document(document):
        return []
    text = document.body
    kind = ("results_release" if re.search(r"\b(?:financial\s+results|earnings\s+release|quarter[^.!?]{0,50}results)\b", text, re.I)
            else "earnings_call" if CALL.search(text) else None)
    period = fiscal_period(document)
    cited_dates = set()
    for match in DATE.finditer(text):
        try:
            cited_dates.add(date(int(match[3]), next(i + 1 for i, month in enumerate(MONTHS)
                                                   if month.lower() == match[1].lower()), int(match[2])).isoformat())
        except ValueError:
            pass
    revisions = []
    for old in existing_events:
        if old.source != "company_ir_rss" or old.symbol != document.symbol:
            continue
        if schedule and old.source_id == schedule.source_id:
            continue
        same_document = old.metadata.get("source_document_id") == document.document_id
        same_period_kind = (period and period == old.metadata.get("fiscal_period") and
                            kind == old.metadata.get("event_kind"))
        linked = same_period_kind and old.metadata.get("event_date") in cited_dates
        cancellation = any(CANCEL.search(clause) and
                           (re.search(r"\b(?:financial\s+results|earnings\s+release)\b", clause, re.I)
                            if old.metadata.get("event_kind") == "results_release" else CALL.search(clause))
                           for clause in re.split(r"[.!?](?:\s|$)", text))
        replacement_match = REPLACEMENT.search(text)
        replacement = False
        if replacement_match and schedule is not None:
            old_date = DATE.search(replacement_match.group())
            try:
                replacement = old.metadata.get("event_date") == date(
                    int(old_date[3]), next(i + 1 for i, month in enumerate(MONTHS)
                                          if month.lower() == old_date[1].lower()), int(old_date[2])).isoformat()
            except ValueError:
                pass
        ambiguous_period = same_period_kind and schedule is None
        if not same_document and not (linked and (cancellation or replacement)) and not ambiguous_period:
            continue
        # Unchanged unsupported documents need no additional history entries.
        evidence = {"source_document_id": document.document_id, "source_url": document.source_url,
                    "text": text, "field": "body", "start": 0, "end": len(text)}
        revised = old.model_copy(deep=True)
        explicit_retirement = (same_document or linked) and (cancellation or replacement)
        revised.status = EventStatus.CANCELLED if explicit_retirement else EventStatus.UNKNOWN
        revised.metadata.update(verification_status="stale_unverified", projection_eligible=False,
                                revision_reason="explicit_cancellation" if explicit_retirement and cancellation else
                                "explicit_replacement" if explicit_retirement and replacement else
                                "same_document_support_lost" if same_document else "ambiguous_period_claim",
                                revision_evidence=evidence)
        revisions.append(revised)
    return revisions
