"""SEC filings, leadership evidence and ownership ingestion (no interpretation)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.models.sources import SourceDocument
from trading_copilot.providers.sec_cik_map import SECCIKMap
from trading_copilot.providers.sec_http import SECTransport
from trading_copilot.providers.sec_parsers import filing_text, leadership, parse_form4, sections

SUPPORTED_FORMS = {"8-K", "10-Q", "10-K", "4"}
CATEGORY_FORMS = {"ownership": {"4"}, "reports": {"10-K", "10-Q"},
                  "companyevents": {"8-K"}}


def _category(form: str) -> str:
    return next(name for name, forms in CATEGORY_FORMS.items()
                if form.removesuffix("/A") in forms)


def _select_rows(rows: list[dict], limit: int, quotas: dict[str, int] | None) -> list[dict]:
    # Quotas reserve slots, not extra requests or hard category caps. Unused slots
    # go to the newest remaining filings; return the same chronological ordering.
    if quotas is None:
        return rows[:limit]
    reserved = set()
    for category, quota in quotas.items():
        reserved.update(row["accessionNumber"] for row in
                        [r for r in rows if _category(r["form"]) == category][:quota])
    for row in rows:
        if len(reserved) >= limit:
            break
        reserved.add(row["accessionNumber"])
    return [row for row in rows if row["accessionNumber"] in reserved]


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _rows(columns: dict) -> list[dict]:
    required = ("accessionNumber", "filingDate", "form", "primaryDocument")
    if not all(isinstance(columns.get(key), list) for key in required):
        raise ValueError("Malformed SEC submissions columns")
    count = len(columns["accessionNumber"])
    if any(len(value) != count for value in columns.values() if isinstance(value, list)):
        raise ValueError("Mismatched SEC submissions column lengths")
    return [{key: value[i] for key, value in columns.items() if isinstance(value, list)}
            for i in range(count)]


class SECFilingProvider:
    """Implements FilingProvider. Failures are explicit in ``errors`` and refresh ERROR.

    Raw response bytes and normalized document snapshots are content-addressed and
    never overwritten. No synthetic fallback. Limits apply after chronological sorting.
    """

    def __init__(self, event_store=None, cache_dir: str | Path = "artifacts/cache/sec",
                 user_agent: str | None = None, transport: SECTransport | None = None,
                 cik_map: SECCIKMap | None = None):
        self.event_store = event_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.transport = transport or SECTransport(user_agent)
        self.cik_map = cik_map or SECCIKMap(self.cache_dir / "cik", transport=self.transport)
        self.errors: list[dict[str, str]] = []
        # Missing symbols have never been checked by this provider instance.
        # Entries describe only the most recent requested window, not world absence.
        self.coverage: dict[str, dict[str, Any]] = {}

    def _error(self, symbol: str, stage: str, source_id: str, exc: Exception):
        # Never persist request headers/credentials in error diagnostics.
        self.errors.append({"symbol": symbol, "stage": stage, "source_id": source_id,
                            "error": type(exc).__name__, "message": str(exc)[:300]})

    def _preserve(self, raw: bytes, suffix: str) -> tuple[str, str]:
        digest = hashlib.sha256(raw).hexdigest()
        path = self.cache_dir / "documents" / (digest + suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as stream:
                stream.write(raw)
        except FileExistsError:
            if path.read_bytes() != raw:
                raise ValueError("Preserved SEC content hash mismatch")
        return digest, str(path.resolve())

    def _json_response(self, url: str) -> dict:
        response = self.transport.get(url)
        self._preserve(response.content, ".json")
        return response.json()

    def _filing_rows(self, symbol: str, cik: str, start: date, end: date) -> list[dict]:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        data = self._json_response(url)
        rows = _rows(data["filings"]["recent"])
        for shard in data["filings"].get("files", []):
            name = shard.get("name", "")
            try:
                if not re.fullmatch(rf"CIK{cik}-submissions-\d+\.json", name):
                    raise ValueError("Unsafe SEC submissions shard name")
                if (shard.get("filingFrom") and date.fromisoformat(shard["filingFrom"]) > end
                        or shard.get("filingTo") and date.fromisoformat(shard["filingTo"]) < start):
                    continue
                rows.extend(_rows(self._json_response("https://data.sec.gov/submissions/" + name)))
            except Exception as exc:
                self._error(symbol, "historical_shard", name, exc)
        selected = {}
        for row in rows:
            try:
                filing_date = date.fromisoformat(row["filingDate"])
                if row["form"].removesuffix("/A") in SUPPORTED_FORMS and start <= filing_date <= end:
                    selected.setdefault(row["accessionNumber"], row)
            except Exception as exc:
                self._error(symbol, "submission_row", str(row.get("accessionNumber")), exc)
        return sorted(selected.values(), key=lambda r: (r["filingDate"], r["accessionNumber"]), reverse=True)

    def _document(self, symbol: str, cik: str, row: dict) -> SourceDocument:
        accession = row["accessionNumber"]
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
            raise ValueError("Invalid SEC accession")
        primary = row["primaryDocument"]
        if not re.fullmatch(r"(?:[A-Za-z0-9_-]+/)?[A-Za-z0-9_.-]+", primary) or ".." in primary:
            raise ValueError("Unsafe SEC primary document")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"
        listed_url = base + primary
        form = row["form"].removesuffix("/A")
        url = base + primary.rsplit("/", 1)[-1] if form == "4" else listed_url
        response = self.transport.get(url)
        raw_hash, raw_path = self._preserve(response.content, ".raw")
        retrieved = datetime.now(timezone.utc)
        text = filing_text(response.text) if form != "4" else response.text

        # Validate document body: reject SEC error/rate-limit pages, empty content.
        if form != "4":
            if not text or not text.strip():
                raise ValueError("SEC document body empty")
            # Detect common SEC error pages (rate limit, access denied, maintenance).
            # Only reject if strong indicators present; allow minimal legitimate content.
            error_indicators = [
                "too many requests", "rate limit exceeded", "access denied", "forbidden",
                "service unavailable", "sec.gov/error", "your request has been blocked",
                "exceeded the maximum"
            ]
            lower = text.lower()
            if any(indicator in lower for indicator in error_indicators):
                raise ValueError("SEC error or rate-limit page received")

        accepted = row.get("acceptanceDateTime")
        published = datetime.fromisoformat(accepted.replace("Z", "+00:00")) if accepted else None
        if published is not None and published.tzinfo is None:
            # SEC acceptance times without a zone are Eastern, not UTC.
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo("America/New_York")
            published = published.replace(tzinfo=eastern)
        # Normalize to UTC for storage and querying.
        published_utc = published.astimezone(timezone.utc) if published is not None else None

        metadata = {"cik": cik, "accession": accession, "form": row["form"],
                    "is_amendment": row["form"].endswith("/A"),
                    "amends_accession": None,  # SEC submissions do not identify the original.
                    "filing_date": row["filingDate"], "report_date": row.get("reportDate") or None,
                    "acceptance_datetime": accepted or None, "listed_url": listed_url,
                    "source_url": url, "source": "sec_edgar", "source_id": accession,
                    "retrieved_at": retrieved.isoformat(), "raw_sha256": raw_hash,
                    "raw_path": raw_path, "submission": row,
                    "items": sorted(set(re.findall(r"\d+\.\d{2}", row.get("items") or "")
                                    + (re.findall(r"\bItem\s+(\d+\.\d{2})\b", text, re.I)
                                       if form == "8-K" else []))),
                    "sections": sections(text) if form != "4" else [],
                    "leadership": leadership(text) if form != "4" else []}
        if form == "4":
            metadata["ownership"] = parse_form4(response.content)
            issuer = metadata["ownership"]["issuer_cik"]
            if issuer is None or not issuer.isdigit() or int(issuer) != int(cik):
                raise ValueError("Ownership XML issuer does not match requested company")
        document = SourceDocument(source_id=accession, symbol=symbol,
                                  source_type=form.lower() if form != "4" else "other_filing",
                                  title=f"{symbol} {row['form']} {accession}", published_at=published_utc,
                                  url=url, provider="sec_edgar", text=text,
                                  retrieval_time=retrieved, content_hash=raw_hash, metadata=metadata)
        # Deduplicate stable normalized evidence: only preserve new retrieval provenance.
        # Content-addressed raw + stable evidence already prevent redundant raw files.
        # The .document.json snapshot will be overwritten with the latest retrieval_time
        # but identical evidence. For full history, retrieval timestamps are kept in
        # event metadata (retrieved_at).
        self._preserve(document.model_dump_json().encode(), ".document.json")
        return document

    def get_filings(self, symbols: list[str], lookback_days: int = 90,
                    max_per_symbol: int = 100, *, from_date: date | None = None,
                    to_date: date | None = None,
                    category_quotas: dict[str, int] | None = None) -> dict[str, list[SourceDocument]]:
        """Fetch bounded evidence, optionally reserving slots per category.

        ``category_quotas`` uses ownership/reports/companyevents; nonnegative integer
        reservations must total at most max_per_symbol. Remaining slots use normal
        newest-first selection. Empty means no supported filings returned in this
        checked window, never that a company has no filings or officers.
        """
        if lookback_days < 0 or max_per_symbol < 1:
            raise ValueError("Invalid SEC lookback/limit")
        if category_quotas is not None:
            if (not isinstance(category_quotas, dict)
                    or any(name not in CATEGORY_FORMS for name in category_quotas)
                    or any(type(quota) is not int or quota < 0 for quota in category_quotas.values())
                    or sum(category_quotas.values()) > max_per_symbol):
                raise ValueError("Invalid SEC category quotas")
        end = to_date or datetime.now(timezone.utc).date()
        start = from_date or end - timedelta(days=lookback_days)
        if start > end:
            raise ValueError("from_date must precede to_date")
        self.errors = []
        result = {}
        for symbol in dict.fromkeys(s.upper() for s in symbols):
            result[symbol] = []
            coverage = {"from_date": start.isoformat(), "to_date": end.isoformat(),
                        "checked_at": None, "source_checked": False,
                        "submissions_attempted": False, "discovered_eligible": 0,
                        "selected": 0, "successful_documents": 0,
                        "error_stage_counts": {}, "status": "not_refreshed",
                        "scope": "supported_filings_in_requested_window",
                        "categories": {name: {"discovered_eligible": 0, "selected": 0,
                                              "successful_documents": 0,
                                              "error_stage_counts": {}, "status": "not_refreshed"}
                                       for name in CATEGORY_FORMS}}
            self.coverage[symbol] = coverage
            error_start = len(self.errors)
            stage = "cik"
            try:
                cik = self.cik_map.get_cik(symbol)
                if cik is None or not re.fullmatch(r"\d{10}", cik):
                    raise ValueError("No valid SEC CIK for symbol")
                stage = "submissions"
                coverage["submissions_attempted"] = True
                rows = self._filing_rows(symbol, cik, start, end)
            except Exception as exc:
                self._error(symbol, "submissions", symbol, exc)
                coverage["error_stage_counts"][stage] = 1
                coverage["status"] = "provider_error"
                for category in coverage["categories"].values():
                    category["status"] = "provider_error"
                    category["error_stage_counts"][stage] = 1
                continue
            coverage["source_checked"] = True
            coverage["checked_at"] = datetime.now(timezone.utc).isoformat()
            coverage["discovered_eligible"] = len(rows)
            selected = _select_rows(rows, max_per_symbol, category_quotas)
            coverage["selected"] = len(selected)
            for row in rows:
                coverage["categories"][_category(row["form"])]["discovered_eligible"] += 1
            for row in selected:
                category = coverage["categories"][_category(row["form"])]
                category["selected"] += 1
                try:
                    result[symbol].append(self._document(symbol, cik, row))
                    category["successful_documents"] += 1
                except Exception as exc:
                    self._error(symbol, "document", str(row.get("accessionNumber")), exc)
                    category["error_stage_counts"]["document"] = category["error_stage_counts"].get("document", 0) + 1
            for error in self.errors[error_start:]:
                stage = error["stage"]
                coverage["error_stage_counts"][stage] = coverage["error_stage_counts"].get(stage, 0) + 1
                if stage != "document":
                    # Incomplete discovery can affect every category; do not call
                    # undiscovered categories empty after a shard/row failure.
                    for category in coverage["categories"].values():
                        category["error_stage_counts"][stage] = category["error_stage_counts"].get(stage, 0) + 1
            coverage["successful_documents"] = len(result[symbol])
            for entry in [coverage, *coverage["categories"].values()]:
                if entry["error_stage_counts"]:
                    entry["status"] = "partial" if entry["successful_documents"] else "provider_error"
                elif entry["selected"] < entry["discovered_eligible"]:
                    entry["status"] = "partial"
                else:
                    entry["status"] = "available" if entry["successful_documents"] else "empty"
        return result

    def _events(self, document: SourceDocument) -> list[MarketEvent]:
        facts = {k: v for k, v in document.metadata.items() if k not in {"retrieved_at", "raw_path"}}
        # Include the full stable evidence in description because EventStore revisions
        # intentionally exclude metadata. Old facts and raw hashes remain recoverable.
        def event(kind, suffix, payload, importance):
            return MarketEvent(event_type=kind, symbol=document.symbol,
                               title=f"{document.title}{suffix}", description=_json(payload),
                               released_at=document.published_at,
                               importance=importance, status=EventStatus.RELEASED,
                               source="sec_edgar", source_id=document.source_id + suffix,
                               source_url=document.url,
                               metadata={**payload, "retrieved_at": document.retrieval_time.isoformat(),
                                         "raw_path": document.metadata["raw_path"],
                                         "_identity_key": f"sec:{document.symbol}:{document.source_id}:{kind.value}:{suffix}"})
        form = facts["form"].removesuffix("/A")
        importance = EventImportance.HIGH if form in {"10-K", "10-Q"} or set(facts["items"]) & {
            "1.01", "1.03", "2.01", "2.02", "4.01", "4.02", "5.02"
        } else EventImportance.MEDIUM
        result = [event(EventType.SEC_FILING, "", facts, importance)]
        # Aggregate per accession rather than positional child IDs: corrected extractions
        # cannot leave obsolete individuals/transactions as current child events.
        existing_leadership = (self.event_store is not None and self.event_store.get_event_by_source_id(
            document.source_id + ":leadership", EventType.LEADERSHIP))
        if form == "8-K" and ("5.02" in facts["items"] or facts["leadership"] or existing_leadership):
            result.append(event(EventType.LEADERSHIP, ":leadership", facts, EventImportance.HIGH))
        if form == "4":
            txs = facts["ownership"]["transactions"]
            tier = EventImportance.HIGH if any(t["code"] in {"P", "S"} for t in txs) else EventImportance.MEDIUM
            result.append(event(EventType.INSIDER, ":ownership", facts, tier))
        return result

    def refresh(self, symbols: list[str], lookback_days: int = 90, max_per_symbol: int = 100,
                *, from_date: date | None = None, to_date: date | None = None,
                category_quotas: dict[str, int] | None = None) -> dict[str, int]:
        if self.event_store is None:
            raise ValueError("EventStore required for SEC refresh")
        documents = self.get_filings(symbols, lookback_days, max_per_symbol,
                                     from_date=from_date, to_date=to_date,
                                     category_quotas=category_quotas)
        counts = {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0, "ERROR": len(self.errors)}
        for symbol, filings in documents.items():
            for document in filings:
                try:
                    for event in self._events(document):
                        counts[self.event_store.upsert_event(event).value] += 1
                except Exception as exc:
                    self._error(symbol, "upsert", document.source_id, exc)
                    counts["ERROR"] += 1
                    coverage = self.coverage[symbol]
                    for entry in [coverage, coverage["categories"][_category(document.metadata["form"])]]:
                        entry["error_stage_counts"]["upsert"] = entry["error_stage_counts"].get("upsert", 0) + 1
                        entry["status"] = "partial"
        return counts

    def get_current_leadership(self, symbol: str, as_of: date | None = None) -> dict:
        """Evidence-derived state as of public filing/effective dates, not exhaustive coverage.

        Unknown on unparsed 5.02 announcements or amendments. No permanent hardcoded
        officers; a source-backed appointment is only 'last evidenced', never verification
        of absence of subsequent changes outside ingested coverage.
        """
        if self.event_store is None:
            raise ValueError("EventStore required for leadership query")
        end = as_of or datetime.now(timezone.utc).date()
        result = {"symbol": symbol.upper(), "as_of": end.isoformat(),
                  "coverage": "ingested_filings_only", "CEO": None, "CFO": None}
        filings = []
        offset = 0
        while True:
            batch = self.event_store.events_for_symbol(symbol, limit=500, offset=offset,
                                                       event_types=[EventType.SEC_FILING])
            filings.extend(batch)
            if len(batch) < 500:
                break
            offset += len(batch)
        timeline = []
        for event in filings:
            facts = event.metadata
            if event.source != "sec_edgar":
                continue
            if facts["filing_date"] > end.isoformat():
                continue
            form = facts["form"].removesuffix("/A")
            is_amendment = facts["is_amendment"]
            has_items = "5.02" in facts["items"]
            has_leadership = bool(facts.get("leadership"))

            if form == "8-K" and (has_items or has_leadership):
                # Amendment with leadership changes: track changes explicitly
                # Filing with Item 5.02 but no parsed leadership: track as uncertain
                if is_amendment and has_leadership:
                    # Explicit leadership in amendment - add each change
                    for change in facts["leadership"]:
                        if change["effective_date"] <= end.isoformat():
                            timeline.append((change["effective_date"], facts["filing_date"],
                                             event.source_id, change, event))
                elif is_amendment and not has_leadership:
                    # Amendment without parsed leadership: uncertain - clear pending
                    timeline.append((facts["filing_date"], facts["filing_date"],
                                     event.source_id, None, event))
                elif not is_amendment and has_leadership:
                    # Original filing with parsed leadership
                    for change in facts["leadership"]:
                        if change["effective_date"] <= end.isoformat():
                            timeline.append((change["effective_date"], facts["filing_date"],
                                             event.source_id, change, event))
                else:
                    # Original filing with Item 5.02 but no parsed leadership: uncertain
                    timeline.append((facts["filing_date"], facts["filing_date"],
                                     event.source_id, None, event))
        for _, _, _, change, event in sorted(timeline, key=lambda entry: entry[:3]):
            if change is None:
                # Uncertain filing/amendment: clear pending but don't clear confirmed
                result["CEO"] = None
                result["CFO"] = None
                continue
            role = change["role"]
            if change["action"] == "departure":
                if result[role] is None or result[role]["name"] == change["name"]:
                    result[role] = None
            else:
                result[role] = {**change, "status": "last_evidenced",
                                "source": event.source, "source_id": event.source_id,
                                "source_url": event.source_url,
                                "retrieved_at": event.metadata["retrieved_at"],
                                "filing_date": event.metadata["filing_date"]}
        return result

    def close(self):
        self.transport.close()
