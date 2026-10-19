"""Bounded, explicit provider refresh using Phase 4/6/7/8 service paths.

Only external read operations. Local writes go through EventStore revision upsert.
Unsafe fixture/default-time paths are deliberately not used in real mode.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import re
from urllib.parse import urlsplit, parse_qsl
from trading_copilot.models.events import MarketEvent, EventType, EventStatus
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.providers.macro_calendar import MacroCalendarProvider
from trading_copilot.providers.news_rss_provider import NewsRSSProvider
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.providers.official_earnings_schedule import extract_official_schedule
from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.management_extractor import (
    ManagementExtractor, ATTRIBUTION_PATTERNS, QUOTE_PATTERNS, linked_quote_speaker,
)
from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator
from trading_copilot.models.news import VerificationStatus, NewsDocument, NewsSourceType


def _exact_feed_timestamp(supplied, name):
    """A normalized tuple alone proves neither source time nor timezone.

    Accept explicit ISO/RFC clock+zone forms only; date-only, timezone-unknown,
    or unsupported date forms are deliberately omitted, never made midnight UTC.
    """
    raw, parsed = supplied.get(name), supplied.get(name + "_parsed")
    if not isinstance(raw, str) or not parsed or not re.search(
        r"(?:T|\s)\d{1,2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?\s*"
        r"(?:Z|[+-]\d{2}:?\d{2}|GMT|UTC|UT|EST|EDT|CST|CDT|MST|MDT|PST|PDT)$",
        raw.strip(), re.IGNORECASE,
    ):
        return None
    try:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class DatedRSSProvider(NewsRSSProvider):
    def _parse_entry(self, feed_name, entry, from_date, to_date):
        # Only actual publication evidence is eligible. FeedParserDict aliases
        # and update/create timestamps cannot establish original publication.
        supplied = dict(entry.items())
        published = _exact_feed_timestamp(supplied, "published")
        if published is None:
            return None
        if not from_date <= published.date() <= to_date:
            return None
        content = entry.get("content")
        raw = content[0].get("value", "") if isinstance(content, list) and content else entry.get("summary", entry.get("description", ""))
        body = self._clean_html(raw)
        link = entry.get("link") or entry.get("id", "")
        if len(body.strip()) < 50 or not link.startswith(("https://", "http://")):
            return None
        title = entry.get("title", "Financial News").strip()
        digest = hashlib.sha256(body.encode()).hexdigest()
        # Reuse Phase 8 cleaning/symbol extraction and document model, avoiding
        # its undefined `feed` publisher lookup as well as date fallback.
        return NewsDocument(document_id=f"news_rss:{feed_name}:{digest[:16]}",
            symbol=self._extract_symbol(title + " " + body), headline=title, body=body,
            summary=body[:500], publisher=feed_name, published_at=published,
            retrieved_at=datetime.now(timezone.utc), source_url=link,
            source_type=NewsSourceType.NEWS_RSS, provider_id=f"news_rss:{feed_name}",
            author=entry.get("author"), content_hash=digest,
            metadata={"feed_name":feed_name, "feed_url":self.feeds[feed_name],
                      "entry_id":entry.get("id", link), "timestamp_basis":"published_at"},
            dedup_key=f"news:{feed_name}:{published.date()}:{digest[:16]}")


class DatedIRProvider(IRReleaseProvider):
    schedule_mode = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.linked_body_budget = 4

    @staticmethod
    def safe_source_url(url):
        try:
            parsed = urlsplit(url)
            return bool(parsed.scheme in ("https", "http") and parsed.hostname and
                        not parsed.username and not parsed.password and
                        parsed.port in (None, 80, 443) and
                        not any(re.search(r"password|secret|token|api.?key|credential|authorization|signature", key, re.I)
                                for key, _ in parse_qsl(parsed.query)) and
                        not parsed.fragment)
        except (ValueError, TypeError):
            return False

    def _error(self, symbol, stage, source_id, exc):
        # Feed-controlled IDs and HTTP exception strings may contain credentials.
        self.errors.append({"symbol": symbol, "stage": stage,
                            "source_id": hashlib.sha256(str(source_id).encode()).hexdigest()[:24],
                            "error": type(exc).__name__, "message": "IR source request rejected or failed"})

    def _fetch_feed(self, symbol, feed_url, from_date, to_date):
        if not self.safe_source_url(feed_url):
            raise ValueError("Unsafe IR feed URL")
        documents = super()._fetch_feed(symbol, feed_url, from_date, to_date)
        return [document for document in documents
                if self.safe_source_url(document.metadata.get("feed_response_url", ""))]

    def _parse_entry(self, symbol, entry, from_date, to_date):
        # Validate before linked fetch, title fallback, or any raw document emission.
        link = entry.get("link", "")
        identity = str(entry.get("id") or link)
        if (not self.safe_source_url(link) or not self.safe_source_url(self.feeds.get(symbol, "")) or
                ("://" in identity and not self.safe_source_url(identity))):
            self._error(symbol, "parse_entry", identity, ValueError("Unsafe IR source URL"))
            return None
        # FeedParserDict.get/__getitem__ can alias absent updated_parsed to
        # published_parsed. Only underlying supplied keys establish provenance.
        supplied = dict(entry.items())
        timestamps = {name: value for name, key in [("published_at", "published"),
                                                   ("source_updated_at", "updated"),
                                                   ("source_created_at", "created")]
                      if (value := _exact_feed_timestamp(supplied, key)) is not None}
        basis = next((name for name in ["published_at", "source_updated_at", "source_created_at"] if name in timestamps), None)
        parsed = timestamps.get(basis)
        if not parsed:
            return None
        # NewsDocument requires a datetime. A non-publication placeholder is
        # explicitly tagged and never becomes released_at or claim publication.
        published = parsed
        if not from_date <= published.date() <= to_date:
            return None
        # Keep the website's strict timestamp parser, reusing Phase 8 feed
        # fetching/HTML cleaning and the existing source document model.
        content = entry.get("content")
        raw = content[0].get("value", "") if isinstance(content, list) and content else entry.get("summary", entry.get("description", ""))
        raw_feed_content = raw
        body = self._clean_html(raw)
        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        body_basis = "feed_content"
        if self.schedule_mode and len(body.strip()) < 50 and re.search(r"earnings|financial results", title, re.I):
            try:
                if self.linked_body_budget <= 0:
                    raise ValueError("Linked body request budget exhausted")
                self.linked_body_budget -= 1
                raw = self.fetch_linked_body(symbol, link)
                body = self._clean_html(raw)
                body_basis = "linked_official_body"
            except Exception as exc:
                self._error(symbol, "linked_body", link, exc)
            if len(body.strip()) < 50:
                body, body_basis = title, "feed_title_only"
        if not link.startswith(("https://", "http://")) or len(body.strip()) < 50:
            return None
        identity = str(entry.get("id") or link)
        return NewsDocument(document_id="ir_release:" + symbol + ":" + hashlib.sha256(identity.encode()).hexdigest()[:24],
            symbol=symbol, headline=entry.get("title", "").strip(), body=body,
            publisher=symbol, published_at=published, retrieved_at=datetime.now(timezone.utc),
            source_url=link, source_type=NewsSourceType.COMPANY_IR, provider_id="company_ir_rss",
            content_hash=hashlib.sha256(body.encode()).hexdigest(),
            metadata={"feed_url": self.feeds[symbol], "entry_id": identity,
                       "raw_content": raw, "raw_feed_content": raw_feed_content, "body_basis": body_basis,
                      "timestamp_basis": basis, "publication_time_unknown": basis != "published_at",
                      **{key: value.isoformat() for key, value in timestamps.items() if key != "published_at"}})


class WebsiteSECExhibitProvider(SECExhibitProvider):
    """A filing date is not an exhibit's exact announcement/publication time."""

    def _extract_exhibits(self, symbol, cik, filing_row):
        documents = super()._extract_exhibits(symbol, cik, filing_row)
        accepted = filing_row.get("acceptanceDateTime")
        for document in documents:
            document.metadata.update(event_date=filing_row["filingDate"],
                                     time_precision="date", publication_time_unknown=True)
            if accepted:
                timestamp = datetime.fromisoformat(accepted.replace("Z", "+00:00"))
                if timestamp.tzinfo is not None:
                    document.published_at = timestamp
                    document.metadata.update(filing_accepted_at=timestamp.isoformat(),
                                             timestamp_basis="filing_accepted_at", time_precision="exact")
        return documents


class EvidenceValidator:
    """Verify extraction against this exact document, not the headline's existence.

    Verification establishes attribution/text support, not the truth of a speaker's
    forecast. Keep these as attributed statements rather than observed facts.
    """

    @staticmethod
    def supports(statement, document):
        span = statement.evidence_span
        supported = bool(span and span.text and document.symbol and
                    statement.symbol == document.symbol and statement.speaker != "UNKNOWN" and
                    statement.source_document_id == document.document_id and
                    statement.source_url == document.source_url and
                    document.body[span.start:span.end] == span.text and
                    statement.statement == span.text)
        if not supported:
            return False
        # Quote-only evidence must be linked to the same adjacent speaker.
        if statement.statement_id.startswith("quote:"):
            return (span.start > 0 and span.end < len(document.body) and
                    document.body[span.start-1] in "\"'" and
                    document.body[span.end] == document.body[span.start-1] and
                    linked_quote_speaker(document.body, span.start-1, span.end+1) == statement.speaker)
        # Forward evidence must start with its own attribution and contain no
        # other speaker or quote attributed to somebody else outside the span.
        attributions = [m for pattern in ATTRIBUTION_PATTERNS for m in re.finditer(pattern, span.text)]
        if not any(m.start() == 0 and m.group(1).strip() == statement.speaker for m in attributions):
            return False
        if any(m.group(1).strip() != statement.speaker for m in attributions):
            return False
        for pattern in QUOTE_PATTERNS:
            for quote in re.finditer(pattern, document.body):
                if span.start <= quote.start() < span.end:
                    if quote.end() > span.end or linked_quote_speaker(document.body, quote.start(), quote.end()) != statement.speaker:
                        return False
        return True


class WebsiteSourceAdapter:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.state = {p: {"status": "not_refreshed", "retrieved_at": None, "reason": "Provider refresh not requested"} for p in ["sec", "earnings", "macro", "news", "ir_releases", "sec_exhibits"]}
        self.state.update({p: {"status":"unavailable", "retrieved_at":None, "reason":reason} for p, reason in {
            "bea":"Existing BEA response parser is incomplete; no live observations available",
            "census":"Existing Census response parser is incomplete; no live observations available",
            "earnings_calendar":"Partial official IR announcement coverage only; no comprehensive future calendar, estimates or inferred dates"}.items()})

    def _run(self, name, operation):
        try:
            counts = operation()
            errors = counts.get("ERROR", 0)
            total = counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0)
            self.state[name] = {"status": ("partial" if total else "provider_error") if errors else "available" if total else "empty",
                                "counts": counts, "retrieved_at": datetime.now(timezone.utc).isoformat(), "reason": "Some source requests failed" if errors else None}
            if counts.get("UNAVAILABLE"):
                self.state[name].update(status="partial" if total or errors else "unavailable",
                                        reason="No configured IR feed for one or more requested symbols")
        except Exception:
            self.state[name] = {"status": "provider_error", "retrieved_at": datetime.now(timezone.utc).isoformat(), "reason": "Source provider request failed"}

    def refresh(self, symbols):
        if self.settings.sec_user_agent:
            for name, cls in [("sec", SECFilingProvider), ("earnings", EarningsIntelligenceProvider)]:
                def operation(cls=cls):
                    provider = cls(self.store, user_agent=self.settings.sec_user_agent)
                    try:
                        return provider.refresh(symbols, lookback_days=45, max_per_symbol=4)
                    finally:
                        provider.close()
                self._run(name, operation)
        else:
            for name in ["sec", "earnings", "sec_exhibits"]:
                self.state[name] = {"status":"unavailable", "reason":"SEC operator identity missing", "retrieved_at":None}
        self._run("macro", self._macro)
        self._run("news", lambda: self._news(symbols))
        self._run("ir_releases", lambda: self._releases(symbols, "ir_releases"))
        if self.settings.sec_user_agent:
            self._run("sec_exhibits", lambda: self._releases(symbols, "sec_exhibits"))
        return self.state

    def _macro(self):
        provider = MacroCalendarProvider(self.store)
        counts = {"NEW":0,"CHANGED":0,"UNCHANGED":0,"ERROR":0}
        try:
            # No current-year fixtures and no fabricated 18:00 decision/minutes times.
            try:
                for raw in provider._fetch_fomc_from_fed(datetime.now(timezone.utc).year):
                    raw["scheduled_at"] = None
                    raw["metadata"].pop("minutes_date", None)
                    raw["metadata"].update(event_date=raw["metadata"]["meeting_end"], time_precision="date", retrieved_at=datetime.now(timezone.utc).isoformat())
                    raw["description"] = f"Federal Reserve calendar: meeting {raw['metadata']['meeting_start']} to {raw['metadata']['meeting_end']}; exact decision time unknown"
                    counts[self.store.upsert_event(provider._create_market_event(raw)).value] += 1
            except Exception:
                counts["ERROR"] += 1
            for key in ["cpi", "core_cpi", "nfp", "unemployment_rate", "ppi", "jolts"]:
                series = provider.MACRO_EVENTS[key].metadata.get("series_id")
                if not series:
                    continue
                try:
                    observations = provider.fetch_bls_series(series, start_year=datetime.now(timezone.utc).year-1)
                    if not observations:
                        continue
                    latest = max(observations, key=lambda row: row["date"])
                    # Reference month is NOT publication date. Preserve it explicitly.
                    event = MarketEvent(event_type=EventType.MACRO, title=f"BLS {key} observation", actual=str(latest["value"]),
                        status=EventStatus.UNKNOWN, source="bls", source_url="https://www.bls.gov/data/", source_id=f"bls:{series}:{latest['date']}",
                        metadata={"series_id":series, "observation_period":latest["date"].strftime("%Y-%m"), "time_precision":"unknown",
                                  "retrieved_at":datetime.now(timezone.utc).isoformat(), "data_kind":"observation_not_release"})
                    counts[self.store.upsert_event(event).value] += 1
                except Exception:
                    counts["ERROR"] += 1
        finally:
            provider.close()
        return counts

    def _news(self, symbols):
        provider = DatedRSSProvider(timeout=10)
        try:
            documents = provider.fetch_news(symbols, from_date=(datetime.now(timezone.utc)-timedelta(days=7)).date())
            return self._documents(documents, "news_rss", len(provider.errors))
        finally:
            provider.close()

    def _releases(self, symbols, name):
        from trading_copilot.providers.official_earnings_schedule import reconcile_schedule_revision, reinstatement_evidence
        provider = (WebsiteSECExhibitProvider(user_agent=self.settings.sec_user_agent) if name == "sec_exhibits"
                    else DatedIRProvider(timeout=10))
        try:
            if name == "ir_releases":
                provider.schedule_mode = True
            documents = provider.fetch_company_releases(symbols,
                from_date=(datetime.now(timezone.utc)-timedelta(days=45 if name == "sec_exhibits" else 90)).date(),
                to_date=datetime.now(timezone.utc).date())
            today = datetime.now(timezone.utc).date()
            schedules = {}
            known = {}
            if name == "ir_releases":
                for symbol in symbols:
                    for event in self.store.events_for_symbol(symbol, limit=-1, event_types=[EventType.EARNINGS]):
                        known[event.source_id] = event
                # Seed batch candidates so feed ordering cannot hide a referenced
                # old announcement during the first ingestion of a replacement.
                for document in documents:
                    candidate = extract_official_schedule(document, today)
                    if candidate:
                        known.setdefault(candidate.source_id, candidate)
            retained = []
            for document in sorted(documents, key=lambda d: d.published_at):
                schedule = extract_official_schedule(document, today) if name == "ir_releases" else None
                revisions = []
                prior = known.get(schedule.source_id) if schedule else None
                superseded = bool(prior and prior.metadata.get("revision_evidence", {}).get("source_document_id")
                                  not in (None, document.document_id))
                if superseded:
                    evidence = reinstatement_evidence(document, schedule, prior, list(known.values()))
                    if evidence:
                        superseded = False
                        schedule.metadata["reinstatement_evidence"] = evidence
                if name == "ir_releases" and not superseded:
                    revisions = reconcile_schedule_revision(document, schedule, list(known.values()))
                    for revision in revisions:
                        schedules[revision.source_id] = known[revision.source_id] = revision
                if superseded:
                    schedule = None
                if schedule:
                    schedules[schedule.source_id] = known[schedule.source_id] = schedule
                # Broader schedule discovery must not broaden news semantics.
                if name != "ir_releases" or schedule or revisions or superseded or document.published_at.date() >= today - timedelta(days=7):
                    retained.append(document)
            counts = self._documents(retained, name, len(provider.errors))
            for event in schedules.values():
                existing = self.store.get_event_by_source_id(event.source_id, EventType.EARNINGS)
                if existing:
                    event.metadata["_identity_key"] = existing.metadata["_identity_key"]
                counts[self.store.upsert_event(event).value] += 1
            if name == "ir_releases" and any(s not in provider.feeds for s in symbols):
                counts["UNAVAILABLE"] = sum(s not in provider.feeds for s in symbols)
            return counts
        finally:
            provider.close()

    def _documents(self, documents, source_type, errors=0):
        counts = {"NEW":0,"CHANGED":0,"UNCHANGED":0,"ERROR":errors}
        extractor, generator = ManagementExtractor(), EvidenceClaimGenerator()
        for document in documents:
            metadata = {"document":document.model_dump(mode="json"), "retrieved_at":document.retrieved_at.isoformat(),
                        "claim_type":"attributed_raw_content", "source_type":source_type,
                        "management_statements":[], "evidence_claims":[]}
            is_exhibit = source_type == "sec_exhibits"
            publication_unknown = document.metadata.get("publication_time_unknown", False)
            timestamp_known = bool(document.metadata.get("filing_accepted_at")) if is_exhibit else not publication_unknown
            if publication_unknown and not is_exhibit:
                metadata.update(timestamp_basis=document.metadata.get("timestamp_basis"), time_precision="unknown",
                                source_updated_at=document.metadata.get("source_updated_at"),
                                source_created_at=document.metadata.get("source_created_at"))
                metadata["document"]["published_at"] = None
            if is_exhibit:
                metadata.update(event_date=document.metadata.get("event_date", document.published_at.date().isoformat()),
                                filing_accepted_at=document.metadata.get("filing_accepted_at"),
                                time_precision="date", announcement_released_at=None)
                # Preserve original provider representation without endorsing its midnight as publication.
                metadata["document"]["published_at"] = None
                metadata["document"]["metadata"]["publication_time_unknown"] = True
            if timestamp_known:
                for statement in extractor.extract_statements(document):
                    if not EvidenceValidator.supports(statement, document):
                        continue
                    # Publication/filing acceptance does not establish when a
                    # statement was originally made.
                    statement.event_date = None
                    claim = generator.generate_from_statement(statement)
                    statement_payload = statement.model_dump(mode="json")
                    statement_payload["timestamp_basis"] = "filing_accepted_at" if is_exhibit else "published_at"
                    metadata["management_statements"].append(statement_payload)
                    if claim:
                        claim.verification_status = VerificationStatus.VERIFIED
                        payload = claim.model_dump(mode="json")
                        payload["retrieved_at"] = document.retrieved_at.isoformat()
                        payload["timestamp_basis"] = "filing_accepted_at" if is_exhibit else "published_at"
                        payload["verification_scope"] = "exact_text_and_attribution_not_forecast_truth"
                        metadata["evidence_claims"].append(payload)
            event = MarketEvent(event_type=EventType.NEWS, symbol=document.symbol, title=document.headline,
                description=document.body, released_at=None if is_exhibit or publication_unknown else document.published_at,
                status=EventStatus.UNKNOWN if publication_unknown and not is_exhibit else EventStatus.RELEASED,
                source=document.publisher, source_url=document.source_url, source_id=document.document_id,
                metadata=metadata)
            existing = self.store.get_event_by_source_id(document.document_id, EventType.NEWS)
            if existing:
                event.metadata["_identity_key"] = existing.metadata["_identity_key"]
                # The embedded document records its original observation; the
                # event's top-level retrieved_at tracks this refresh. Otherwise
                # a new nested observation clock fabricates a content revision.
                prior = existing.metadata.get("document", {})
                current = event.metadata["document"]
                if (prior.get("retrieved_at") and
                        {k: v for k, v in prior.items() if k != "retrieved_at"} ==
                        {k: v for k, v in current.items() if k != "retrieved_at"}):
                    event.metadata["document"]["retrieved_at"] = prior["retrieved_at"]
                event.content_hash = event.compute_content_hash()
            counts[self.store.upsert_event(event).value] += 1
        return counts
