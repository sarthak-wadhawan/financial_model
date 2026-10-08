"""SEC Exhibit Provider — ingests company press releases from SEC filing exhibits (Exhibit 99.1, etc.).

Reuses Phase 6/7 SEC infrastructure: SECTransport, SECCIKMap, sec_parsers.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from trading_copilot.models.news import NewsDocument, NewsSourceType
from trading_copilot.models.sources import SourceDocument
from trading_copilot.providers.base import NewsProvider
from trading_copilot.providers.sec_cik_map import SECCIKMap
from trading_copilot.providers.sec_http import SECTransport, safe_sec_url
from trading_copilot.providers.sec_parsers import filing_text, sections

logger = logging.getLogger(__name__)

# SEC exhibit types that contain press releases / earnings releases
PRESS_RELEASE_EXHIBITS = {"99.1", "99.2", "99.3"}


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _preserve(content: bytes, cache_dir: Path, suffix: str = "") -> tuple[str, str]:
    """Preserve content to cache directory."""
    digest = _sha256(content)
    path = cache_dir / "documents" / (digest + suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as f:
            f.write(content)
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError("Cached SEC content hash mismatch")
    return digest, str(path.resolve())


class SECExhibitProvider:
    """
    Extracts company press releases from SEC filing exhibits.

    Reuses Phase 6/7 SEC infrastructure. Focuses on 8-K exhibits (99.1, 99.2, 99.3)
    which typically contain earnings press releases.
    """

    def __init__(
        self,
        cache_dir: str | Path = "artifacts/cache/sec_exhibits",
        user_agent: str | None = None,
        transport: SECTransport | None = None,
        cik_map: SECCIKMap | None = None,
    ):
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

    def fetch_company_releases(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]:
        """
        Fetch company press releases from SEC 8-K exhibits.

        Returns list of NewsDocument (one per exhibit).
        """
        if symbols is None:
            return []

        if from_date is None:
            from_date = date(2020, 1, 1)
        if to_date is None:
            to_date = datetime.now(timezone.utc).date()

        results: list[NewsDocument] = []

        for symbol in dict.fromkeys(s.upper() for s in symbols):
            try:
                cik = self.cik_map.get_cik(symbol)
                if cik is None or not re.fullmatch(r"\d{10}", cik):
                    raise ValueError("No valid SEC CIK for symbol")

                filings = self._fetch_filings_for_symbol(symbol, cik, from_date, to_date)

                for filing in filings:
                    exhibit_docs = self._extract_exhibits(symbol, cik, filing)
                    results.extend(exhibit_docs)

            except Exception as exc:
                self._error(symbol, "fetch", symbol, exc)

        return results

    def _fetch_filings_for_symbol(
        self,
        symbol: str,
        cik: str,
        from_date: date,
        to_date: date,
    ) -> list[dict]:
        """Fetch 8-K filings for a symbol within date range."""
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = self.transport.get(url)
        _preserve(response.content, self.cache_dir, ".json")
        data = response.json()

        filings = []
        rows = self._rows(data["filings"]["recent"])
        for row in rows:
            try:
                filing_date = date.fromisoformat(row["filingDate"])
                form = row["form"].removesuffix("/A")
                if form != "8-K" or not (from_date <= filing_date <= to_date):
                    continue
                items = row.get("items") or ""
                if not any(item in items for item in ["2.02", "7.01", "8.01"]):
                    continue  # Only 8-K with earnings/material events
                filings.append(row)
            except Exception as exc:
                self._error(symbol, "filing_row", row.get("accessionNumber", ""), exc)

        # Historical shards
        for shard in data["filings"].get("files", []):
            name = shard.get("name", "")
            try:
                if not re.fullmatch(rf"CIK{cik}-submissions-\d+\.json", name):
                    continue
                if (shard.get("filingFrom") and date.fromisoformat(shard["filingFrom"]) > to_date
                        or shard.get("filingTo") and date.fromisoformat(shard["filingTo"]) < from_date):
                    continue
                shard_response = self.transport.get("https://data.sec.gov/submissions/" + name)
                _preserve(shard_response.content, self.cache_dir, ".json")
                shard_rows = self._rows(shard_response.json())
                for row in shard_rows:
                    filing_date = date.fromisoformat(row["filingDate"])
                    form = row["form"].removesuffix("/A")
                    if form == "8-K" and from_date <= filing_date <= to_date:
                        items = row.get("items") or ""
                        if any(item in items for item in ["2.02", "7.01", "8.01"]):
                            filings.append(row)
            except Exception as exc:
                self._error(symbol, "historical_shard", name, exc)

        return filings

    def _rows(self, columns: dict) -> list[dict]:
        required = ("accessionNumber", "filingDate", "form", "primaryDocument")
        if not all(isinstance(columns.get(key), list) for key in required):
            raise ValueError("Malformed SEC submissions columns")
        count = len(columns["accessionNumber"])
        if any(len(v) != count for v in columns.values() if isinstance(v, list)):
            raise ValueError("Mismatched SEC submissions column lengths")
        return [{k: v[i] for k, v in columns.items() if isinstance(v, list)} for i in range(count)]

    def _extract_exhibits(self, symbol: str, cik: str, filing_row: dict) -> list[NewsDocument]:
        """Extract press release exhibits from an 8-K filing."""
        documents: list[NewsDocument] = []
        accession = filing_row["accessionNumber"]
        filing_date = filing_row["filingDate"]
        items = filing_row.get("items") or ""

        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"

        # Try to get the index.json to find exhibit files
        index_url = base + "index.json"
        exhibit_files = []

        try:
            index_response = self.transport.get(base + "index.json")
            _preserve(index_response.content, self.cache_dir, ".json")
            index_data = index_response.json()
            
            # Look for exhibit files in the directory listing
            for item in index_data.get("directory", {}).get("item", []):
                name = item.get("name", "")
                # Match exhibit files like a8-kex991q4202509272025.htm (ex991, ex992, ex993)
                import re
                match = re.search(r'(?:ex|EX)[-_]?(99[123])', name, re.IGNORECASE)
                if match:
                    # Convert 991 -> 99.1, 992 -> 99.2, 993 -> 99.3
                    num = match.group(1)
                    exhibit_num = f"{num[:2]}.{num[2]}"
                    exhibit_files.append((exhibit_num, name))
                # Also check for standard 99.1, 99.2, 99.3 in filename
                elif re.search(r'99\.[123]', name, re.IGNORECASE):
                    exhibit_match = re.search(r'(99\.[123])', name, re.IGNORECASE)
                    if exhibit_match:
                        exhibit_files.append((exhibit_match.group(1), name))
                        
        except Exception as exc:
            self._error(symbol, "index_json", accession, exc)

        # Also try the traditional method of finding exhibit references in the primary document
        primary = filing_row["primaryDocument"]
        filing_url = base + filing_row["primaryDocument"]

        try:
            filing_response = self.transport.get(base + filing_row["primaryDocument"])
            _preserve(filing_response.content, self.cache_dir, ".raw")
            filing_html = filing_response.text
        except Exception as exc:
            self._error(symbol, "filing_document", accession, exc)
            filing_html = ""

        # Find exhibit references in filing (EX-99.1, EX-99.2, etc.) - traditional method
        traditional_refs = self._find_exhibit_references(filing_html) if filing_html else []

        # Combine exhibit references from index.json and traditional method
        all_refs = []
        for exhibit_num, filename in exhibit_files:
            exhibit_url = base + filename
            all_refs.append((exhibit_num, exhibit_url))
        all_refs.extend(traditional_refs)

        # Deduplicate by exhibit number
        seen_exhibits = set()
        unique_refs = []
        for exhibit_num, exhibit_url in all_refs:
            if exhibit_num in PRESS_RELEASE_EXHIBITS and exhibit_num not in seen_exhibits:
                seen_exhibits.add(exhibit_num)
                unique_refs.append((exhibit_num, exhibit_url))

        for exhibit_num, exhibit_url in unique_refs:
            try:
                exhibit_response = self.transport.get(exhibit_url)
                _preserve(exhibit_response.content, self.cache_dir, ".raw")

                # Parse exhibit content
                content_type = exhibit_response.headers.get("Content-Type", "")
                exhibit_text = filing_text(exhibit_response.text) if content_type.startswith("text/html") else exhibit_response.text

                if not exhibit_text or not exhibit_text.strip():
                    continue

                # Create NewsDocument
                content_hash = _sha256(exhibit_response.content)
                retrieved = datetime.now(timezone.utc)

                # Preserve raw exhibit content
                _, raw_path = _preserve(exhibit_response.content, self.cache_dir, ".raw")

                # Extract headline from first line or title
                headline = self._extract_headline(exhibit_text, symbol)

                doc = NewsDocument(
                    document_id=f"sec_exhibit:{accession}:{exhibit_num}",
                    symbol=symbol,
                    headline=headline,
                    body=exhibit_text,
                    summary=exhibit_text[:500] if len(exhibit_text) > 500 else exhibit_text,
                    publisher=symbol,
                    published_at=datetime.fromisoformat(filing_date).replace(tzinfo=timezone.utc),
                    retrieved_at=retrieved,
                    source_url=exhibit_url,
                    source_type=NewsSourceType.SEC_EXHIBIT,
                    author=None,
                    provider_id="sec_edgar_exhibit",
                    content_hash=content_hash,
                    metadata={
                        "accession": accession,
                        "filing_date": filing_date,
                        "items": items,
                        "exhibit_number": exhibit_num,
                        "form": "8-K",
                        "raw_path": raw_path,
                    },
                    dedup_key=f"sec_exhibit:{symbol}:{exhibit_num}:{filing_date}",
                    sec_filing_id=f"sec_edgar:{accession}",
                    exhibit_number=exhibit_num,
                )
                documents.append(doc)

            except Exception as exc:
                self._error(symbol, "exhibit", f"{accession}:{exhibit_num}", exc)

        return documents

    def _find_exhibit_references(self, html: str) -> list[tuple[str, str]]:
        """Find exhibit references in 8-K filing HTML."""
        refs = []

        # Pattern 1: EX-99.1 in link text with href
        # <a href="...">EX-99.1</a> or <a href="...">Exhibit 99.1</a>
        link_pattern = r'<a\s+[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*(?:EX|Exhibit)\s*[-:]?\s*(99\.\d+)\s*</a>'
        for match in re.finditer(link_pattern, html, re.IGNORECASE):
            url = match.group(1)
            exhibit_num = match.group(2)
            if url.startswith("/"):
                url = "https://www.sec.gov" + url
            elif not url.startswith("http"):
                pass
            refs.append((exhibit_num, url))

        # Pattern 2: EX-99.1 appears before href in text
        exhibit_pattern = r'(?:EX|Exhibit)\s*[-:]?\s*(99\.\d+).*?href\s*=\s*["\']([^"\']+)["\']'
        for match in re.finditer(exhibit_pattern, html, re.IGNORECASE):
            exhibit_num = match.group(1)
            url = match.group(2)
            if url.startswith("/"):
                url = "https://www.sec.gov" + url
            elif not url.startswith("http"):
                pass
            refs.append((exhibit_num, url))

        # Also look for exhibit list tables
        table_pattern = r'<td[^>]*>\s*(?:EX|Exhibit)\s*[-:]?\s*(99\.\d+)\s*</td>.*?href\s*=\s*["\']([^"\']+)["\']'
        for match in re.finditer(table_pattern, html, re.IGNORECASE | re.DOTALL):
            exhibit_num = match.group(1)
            url = match.group(2)
            if url.startswith("/"):
                url = "https://www.sec.gov" + url
            refs.append((exhibit_num, url))

        return refs

    def _extract_headline(self, text: str, symbol: str) -> str:
        """Extract headline from press release text."""
        lines = text.strip().split("\n")
        for line in lines[:10]:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 200:
                return line
        return f"{symbol} Press Release"

    def close(self):
        self.transport.close()


if __name__ == "__main__":
    # Quick test with AAPL
    import os
    os.environ["SEC_USER_AGENT"] = "Test test@test.com"
    provider = SECExhibitProvider()
    docs = provider.fetch_company_releases(symbols=["AAPL"], from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))
    print(f"Found {len(docs)} exhibit documents")
    for doc in docs[:3]:
        print(f"  {doc.document_id}: {doc.headline[:80]}")
    provider.close()