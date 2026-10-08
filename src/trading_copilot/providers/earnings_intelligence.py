"""Earnings Intelligence Provider — extracts factual earnings results and guidance from SEC filings."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.models.sources import SourceDocument
from trading_copilot.providers.sec_cik_map import SECCIKMap
from trading_copilot.providers.sec_http import SECTransport, safe_sec_url
from trading_copilot.providers.sec_parsers import filing_text, sections
from trading_copilot.providers.earnings_parsers import extract_eps_revenue, extract_guidance_details, compute_surprise

logger = logging.getLogger(__name__)

# Supported forms for earnings extraction
EARNINGS_FORMS = {"8-K", "10-Q", "10-K"}

# 8-K items that indicate earnings releases
EARNINGS_ITEMS = {"2.02"}


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


class EarningsIntelligenceProvider:
    """
    Extracts earnings results (actual EPS/revenue, consensus, guidance) from SEC filings.

    Reuses Phase 6 SEC infrastructure: SECTransport, SECCIKMap, sec_parsers.
    Only extracts when directly supported by evidence. Missing fields remain missing.
    Surprise values are deterministic derivations only when both actual and consensus present.
    """

    def __init__(
        self,
        event_store: Any,
        cache_dir: str | Path = "artifacts/cache/earnings_intelligence",
        user_agent: str | None = None,
        transport: SECTransport | None = None,
        cik_map: SECCIKMap | None = None,
    ):
        self.event_store = event_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.transport = transport or SECTransport(user_agent)
        self.cik_map = cik_map or SECCIKMap(self.cache_dir / "cik", transport=self.transport)
        self.errors: list[dict[str, str]] = []

    def _error(self, symbol: str, stage: str, source_id: str, exc: Exception):
        self.errors.append({
            "symbol": symbol,
            "stage": stage,
            "source_id": source_id,
            "error": type(exc).__name__,
            "message": str(exc)[:300],
        })

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
                form_base = row["form"].removesuffix("/A")
                if form_base in EARNINGS_FORMS and start <= filing_date <= end:
                    # Only process 8-K with Item 2.02, or 10-Q/10-K
                    items = row.get("items") or ""
                    if form_base == "8-K" and not any(item in items for item in EARNINGS_ITEMS):
                        continue
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

        # Validate document body
        if form != "4":
            if not text or not text.strip():
                raise ValueError("SEC document body empty")
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
            from zoneinfo import ZoneInfo
            eastern = ZoneInfo("America/New_York")
            published = published.replace(tzinfo=eastern)
        published_utc = published.astimezone(timezone.utc) if published is not None else None

        metadata = {
            "cik": cik,
            "accession": accession,
            "form": row["form"],
            "is_amendment": row["form"].endswith("/A"),
            "amends_accession": None,
            "filing_date": row["filingDate"],
            "report_date": row.get("reportDate") or None,
            "acceptance_datetime": accepted or None,
            "listed_url": listed_url,
            "source_url": url,
            "source": "sec_edgar",
            "source_id": accession,
            "retrieved_at": retrieved.isoformat(),
            "raw_sha256": raw_hash,
            "raw_path": raw_path,
            "submission": row,
            "items": sorted(set(re.findall(r"\d+\.\d{2}", row.get("items") or "")
                            + (re.findall(r"\bItem\s+(\d+\.\d{2})\b", text, re.I)
                               if form == "8-K" else []))),
            "sections": sections(text) if form != "4" else [],
        }

        document = SourceDocument(
            source_id=accession,
            symbol=symbol,
            source_type=form.lower(),
            title=f"{symbol} {row['form']} {accession}",
            published_at=published_utc,
            url=url,
            provider="sec_edgar",
            text=text,
            retrieval_time=retrieved,
            content_hash=raw_hash,
            metadata=metadata,
        )

        # Preserve normalized evidence snapshot
        self._preserve(document.model_dump_json().encode(), ".document.json")
        return document

    def _extract_earnings_facts(self, document: SourceDocument) -> dict[str, Any] | None:
        """
        Extract earnings facts from a SEC filing document.

        Only processes 8-K with Item 2.02, 10-Q, 10-K.
        Returns None if no earnings data found.
        """
        form = document.metadata["form"].removesuffix("/A")
        items = document.metadata.get("items", [])

        # Check if this filing contains earnings data
        if form == "8-K" and "2.02" not in items:
            return None

        text = document.text
        if not text:
            return None

        # Extract EPS/revenue/consensus
        earnings_data = extract_eps_revenue(text)

        # Check if any actual data was found
        has_actual = any(v is not None for v in [
            earnings_data["eps_actual"],
            earnings_data["revenue_actual"],
        ])

        if not has_actual:
            return None

        # Extract guidance if present
        guidance = extract_guidance_details(text)

        # Compute surprises
        eps_surprise, eps_surprise_pct = compute_surprise(
            earnings_data["eps_actual"], earnings_data["eps_consensus"]
        )
        revenue_surprise, revenue_surprise_pct = compute_surprise(
            earnings_data["revenue_actual"], earnings_data["revenue_consensus"]
        )

        # Determine fiscal quarter/year from filing date or report date
        fiscal_quarter = None
        fiscal_year = None
        report_date = document.metadata.get("report_date") or document.metadata.get("filing_date")
        if report_date:
            try:
                rd = date.fromisoformat(report_date)
                fiscal_year = str(rd.year)
                # Rough quarter estimation
                if rd.month <= 3:
                    fiscal_quarter = "4"
                elif rd.month <= 6:
                    fiscal_quarter = "1"
                elif rd.month <= 9:
                    fiscal_quarter = "2"
                else:
                    fiscal_quarter = "3"
            except ValueError:
                pass

        # Also try to extract from document text
        quarter_match = re.search(r"(Q[1-4])\s+(FY|fiscal\s+year)\s*(\d{4})", text, re.IGNORECASE)
        if quarter_match:
            fiscal_quarter = quarter_match.group(1).upper().replace("Q", "")
            fiscal_year = quarter_match.group(3)

        # SEC acceptance time (filing_accepted_at) - when SEC accepted the filing
        filing_accepted_at = document.published_at.isoformat() if document.published_at else None
        
        # announcement_released_at: actual earnings release time (unknown from SEC filings alone)
        # SEC acceptance time != earnings announcement time. Track separately.
        # Only set if we have specific evidence (e.g., from 8-K Item 2.02 timestamp or press release)
        announcement_released_at = None
        release_time_source = "sec_filing_accepted"
        release_time_precision = "filing_accepted"

        return {
            "event_subtype": "earnings_result",
            "fiscal_quarter": fiscal_quarter,
            "fiscal_year": fiscal_year,
            "eps_actual": earnings_data["eps_actual"],
            "eps_consensus": earnings_data["eps_consensus"],
            "eps_surprise": eps_surprise,
            "eps_surprise_pct": eps_surprise_pct,
            "revenue_actual": earnings_data["revenue_actual"],
            "revenue_consensus": earnings_data["revenue_consensus"],
            "revenue_surprise": revenue_surprise,
            "revenue_surprise_pct": revenue_surprise_pct,
            "report_date": report_date,
            "report_time": "unknown",  # SEC filings don't reliably indicate BMO/AMC
            "source_document_id": f"sec_edgar:{document.source_id}",
            "source_document_type": form,
            "items": items,
            "guidance": earnings_data["guidance"],
            "guidance_details": guidance,
            "retrieved_at": document.retrieval_time.isoformat(),
            "filing_accepted_at": filing_accepted_at,
            "announcement_released_at": announcement_released_at,
            "release_time_source": release_time_source,
            "release_time_precision": release_time_precision,
        }

    def _extract_guidance_facts(self, document: SourceDocument) -> dict[str, Any] | None:
        """
        Extract guidance facts from a SEC filing document.

        Returns structured guidance when explicit ranges found.
        """
        form = document.metadata["form"].removesuffix("/A")
        text = document.text
        if not text:
            return None

        guidance = extract_guidance_details(text)
        if not guidance:
            return None

        return {
            "event_subtype": "earnings_guidance",
            "fiscal_quarter": guidance.get("period", "").split()[0] if guidance.get("period") else None,
            "fiscal_year": guidance.get("period", "").split()[-1] if guidance.get("period") else None,
            "guidance_type": guidance.get("guidance_type", "quarterly"),
            "period": guidance.get("period"),
            "eps_guidance_low": guidance.get("eps_guidance_low"),
            "eps_guidance_high": guidance.get("eps_guidance_high"),
            "revenue_guidance_low": guidance.get("revenue_guidance_low"),
            "revenue_guidance_high": guidance.get("revenue_guidance_high"),
            "guidance_change": guidance.get("guidance_change", "new"),
            "previous_eps_guidance_low": None,  # Would need historical comparison
            "previous_eps_guidance_high": None,
            "source_document_id": f"sec_edgar:{document.source_id}",
            "source_document_type": form,
            "items": document.metadata.get("items", []),
            "retrieved_at": document.retrieval_time.isoformat(),
            "filing_accepted_at": document.published_at.isoformat() if document.published_at else None,
            "announcement_released_at": None,
            "release_time_source": "sec_filing_accepted",
            "release_time_precision": "filing_accepted",
        }

    def _create_earnings_result_event(self, symbol: str, facts: dict[str, Any], document: SourceDocument) -> MarketEvent:
        """Create EARNINGS_RESULT event from extracted facts."""
        # Build identity key for correlation with scheduled earnings
        identity_parts = [
            EventType.EARNINGS_RESULT.value,
            symbol,
            facts.get("fiscal_quarter") or "",
            facts.get("fiscal_year") or "",
            facts.get("source_document_id") or "",
        ]
        identity_key = hashlib.sha256("|".join(identity_parts).encode()).hexdigest()[:32]

        # Use announcement_released_at as released_at (actual earnings release time).
        # SEC filing accepted_at != earnings announcement released_at.
        # Only use filing_accepted_at if announcement_released_at is not available AND
        # we have specific evidence linking them (not the case for SEC filings alone).
        released_at = None
        announcement_released_at = facts.get("announcement_released_at")
        if announcement_released_at:
            try:
                # Handle 'Z' suffix for UTC
                if announcement_released_at.endswith('Z'):
                    announcement_released_at = announcement_released_at[:-1] + '+00:00'
                released_at = datetime.fromisoformat(announcement_released_at)
            except (ValueError, TypeError):
                pass

        return MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol=symbol,
            title=f"{symbol} Q{facts.get('fiscal_quarter', '?')} FY{facts.get('fiscal_year', '?')} Earnings Result",
            description=_json({k: v for k, v in facts.items() if k not in {"retrieved_at"}}),
            released_at=released_at,
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url=document.url,
            source_id=f"{document.source_id}:result",
            metadata={
                **facts,
                "retrieved_at": facts.get("retrieved_at"),
                "raw_path": document.metadata["raw_path"],
                "_identity_key": identity_key,
            },
        )

    def _create_earnings_guidance_event(self, symbol: str, facts: dict[str, Any], document: SourceDocument) -> MarketEvent:
        """Create EARNINGS_GUIDANCE event from extracted facts."""
        identity_parts = [
            EventType.EARNINGS_GUIDANCE.value,
            symbol,
            facts.get("period") or "",
            facts.get("source_document_id") or "",
        ]
        identity_key = hashlib.sha256("|".join(identity_parts).encode()).hexdigest()[:32]

        # Guidance is announced at a specific time; SEC filing acceptance is not that time.
        released_at = None
        announcement_released_at = facts.get("announcement_released_at")
        if announcement_released_at:
            try:
                # Handle 'Z' suffix for UTC
                if announcement_released_at.endswith('Z'):
                    announcement_released_at = announcement_released_at[:-1] + '+00:00'
                released_at = datetime.fromisoformat(announcement_released_at)
            except (ValueError, TypeError):
                pass

        return MarketEvent(
            event_type=EventType.EARNINGS_GUIDANCE,
            symbol=symbol,
            title=f"{symbol} Guidance: {facts.get('period', 'Future Period')}",
            description=_json({k: v for k, v in facts.items() if k not in {"retrieved_at"}}),
            released_at=released_at,
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url=document.url,
            source_id=f"{document.source_id}:guidance",
            metadata={
                **facts,
                "retrieved_at": facts.get("retrieved_at"),
                "raw_path": document.metadata["raw_path"],
                "_identity_key": identity_key,
            },
        )

    def get_earnings_results(
        self,
        symbols: list[str],
        lookback_days: int = 365,
        max_per_symbol: int = 50,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, list[MarketEvent]]:
        """Fetch and extract earnings results for symbols. Returns {symbol: [MarketEvent]}."""
        if lookback_days < 0 or max_per_symbol < 1:
            raise ValueError("Invalid lookback/limit")
        end = to_date or datetime.now(timezone.utc).date()

        from datetime import timedelta

        start = from_date or end - timedelta(days=lookback_days)
        if start > end:
            raise ValueError("from_date must precede to_date")

        self.errors = []
        result = {}

        for symbol in dict.fromkeys(s.upper() for s in symbols):
            result[symbol] = []
            try:
                cik = self.cik_map.get_cik(symbol)
                if cik is None or not re.fullmatch(r"\d{10}", cik):
                    raise ValueError("No valid SEC CIK for symbol")
                rows = self._filing_rows(symbol, cik, start, end)
            except Exception as exc:
                self._error(symbol, "submissions", symbol, exc)
                continue

            for row in rows[:max_per_symbol]:
                try:
                    document = self._document(symbol, cik, row)
                    earnings_facts = self._extract_earnings_facts(document)
                    if earnings_facts:
                        event = self._create_earnings_result_event(symbol, earnings_facts, document)
                        result[symbol].append(event)

                    guidance_facts = self._extract_guidance_facts(document)
                    if guidance_facts:
                        event = self._create_earnings_guidance_event(symbol, guidance_facts, document)
                        result[symbol].append(event)

                except Exception as exc:
                    self._error(symbol, "document", str(row.get("accessionNumber")), exc)

        return result

    def refresh(
        self,
        symbols: list[str],
        lookback_days: int = 365,
        max_per_symbol: int = 50,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, int]:
        """Refresh earnings intelligence: fetch and upsert events to store."""
        if self.event_store is None:
            raise ValueError("EventStore required for earnings intelligence refresh")

        events_by_symbol = self.get_earnings_results(
            symbols, lookback_days, max_per_symbol, from_date=from_date, to_date=to_date
        )

        counts = {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0, "ERROR": len(self.errors)}

        for symbol, events in events_by_symbol.items():
            for event in events:
                try:
                    result = self.event_store.upsert_event(event)
                    counts[result.value] += 1
                except Exception as exc:
                    self._error(symbol, "upsert", event.source_id, exc)
                    counts["ERROR"] += 1

        return counts

    def get_earnings_history(
        self,
        symbol: str,
        limit: int = 20,
    ) -> list[MarketEvent]:
        """Get earnings history for a symbol (results + guidance)."""
        if self.event_store is None:
            raise ValueError("EventStore required for earnings history query")

        events = self.event_store.events_for_symbol(
            symbol=symbol,
            event_types=[EventType.EARNINGS_RESULT, EventType.EARNINGS_GUIDANCE],
            limit=limit,
        )
        return sorted(events, key=lambda e: e.released_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    def close(self):
        self.transport.close()