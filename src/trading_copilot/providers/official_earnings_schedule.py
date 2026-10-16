"""Conservative, source-text-only official earnings schedule extraction.

No fiscal-cadence estimates, call-to-release substitution, or default clocks.
Offsets address the preserved document body/headline, not rewritten text.
"""
import re
from datetime import date

from trading_copilot.models.events import EventStatus, EventType, MarketEvent
from trading_copilot.models.news import NewsSourceType


MONTHS = "January February March April May June July August September October November December".split()
DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+(20\d{2})\b", re.I)
RELEASE = re.compile(
    r"\b(?:will\s+(?:announce|release|report|publish)|to\s+(?:announce|release|report|publish))\b"
    r"[^.!?]{0,180}?\b(?:financial\s+results|(?:quarterly|annual|quarter|year)[^.!?]{0,50}?results|earnings)\b", re.I)
CALL = re.compile(r"\b(?:earnings\s+(?:conference\s+)?call|conference\s+call|earnings\s+webcast)\b", re.I)


def extract_official_schedule(document, today: date):
    """Return one explicitly announced future schedule, or None if ambiguous.

    A title may evidence a call/date-only announcement. Session evidence must
    occur in the release clause, never a later webcast sentence.
    """
    if document.source_type != NewsSourceType.COMPANY_IR:
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
            if not release and not call:
                continue
            schedule_language = True
            if re.search(r"\b(?:cancel(?:led|ed|lation)?|postponed|not\s+(?:announce|release|report)|may|might|tentative|expected|estimated)\b", clause, re.I):
                return None
            dates = list(DATE.finditer(clause))
            if len(dates) != 1:
                continue
            match = dates[0]
            try:
                day = date(int(match[3]), next(i + 1 for i, m in enumerate(MONTHS) if m.lower() == match[1].lower()), int(match[2]))
            except ValueError:
                continue
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
                  "retrieved_at": document.retrieved_at.isoformat(),
                  "evidence_span": {"field": field, "start": start, "end": end, "text": text}},
    )
