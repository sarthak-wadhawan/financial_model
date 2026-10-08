"""Company IR Release Provider — ingests press releases from company investor relations RSS feeds.

Uses RSS/Atom feeds from company IR websites. No paid dependencies.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin

import feedparser
import httpx

from trading_copilot.models.news import NewsDocument, NewsSourceType
from trading_copilot.providers.base import NewsProvider

logger = logging.getLogger(__name__)

# Known company IR RSS feeds (subset - can be extended)
IR_RSS_FEEDS = {
    "AAPL": "https://www.apple.com/newsroom/rss-feed.rss",
    "MSFT": "https://news.microsoft.com/feed/",
    "GOOGL": "https://blog.google/rss/",
    "AMZN": "https://www.aboutamazon.com/news/rss",
    "META": "https://about.fb.com/news/feed/",
    "NVDA": "https://investor.nvidia.com/rss/news-releases.xml",
    "TSLA": "https://ir.tesla.com/rss/news-releases.xml",
    "JPM": "https://www.jpmorganchase.com/content/dam/jpmorganchase/documents/investor-relations/press-releases.rss",
    "V": "https://investor.visa.com/rss/news-releases.xml",
    "MA": "https://investor.mastercard.com/rss/news-releases.xml",
    "UNH": "https://www.unitedhealthgroup.com/rss/news-releases.xml",
    "HD": "https://newsroom.homedepot.com/rss.xml",
    "PFE": "https://www.pfizer.com/news/rss",
    "KO": "https://www.coca-colacompany.com/rss.xml",
    "PEP": "https://www.pepsico.com/rss/news-releases.xml",
    "COST": "https://investor.costco.com/rss/news-releases.xml",
    "AVGO": "https://investors.broadcom.com/rss/news-releases.xml",
    "CSCO": "https://investor.cisco.com/rss/news-releases.xml",
    "ADBE": "https://news.adobe.com/rss/",
    "CRM": "https://www.salesforce.com/news/rss/",
    "AMD": "https://ir.amd.com/rss/news-releases.xml",
    "NFLX": "https://about.netflix.com/en/newsroom/rss",
    "INTC": "https://newsroom.intel.com/rss.xml",
    "QCOM": "https://investor.qcom.com/rss/news-releases.xml",
    "TXN": "https://investor.ti.com/rss/news-releases.xml",
    "AMAT": "https://investor.appliedmaterials.com/rss/news-releases.xml",
    "HON": "https://investor.honeywell.com/rss/news-releases.xml",
    "LIN": "https://investor.linde.com/rss/news-releases.xml",
    "PM": "https://www.pmi.com/rss/news-releases.xml",
    "LOW": "https://newsroom.lowes.com/rss.xml",
    "IBM": "https://newsroom.ibm.com/rss.xml",
    "ORCL": "https://www.oracle.com/rss.xml",
    "NOW": "https://www.servicenow.com/rss.xml",
    "AMGN": "https://www.amgen.com/rss.xml",
    "GE": "https://www.ge.com/news/rss.xml",
    "CAT": "https://www.caterpillar.com/en/news/rss.xml",
    "RTX": "https://www.rtx.com/rss.xml",
    "SPGI": "https://newsroom.spglobal.com/rss.xml",
    "BKNG": "https://news.bookingholdings.com/rss.xml",
    "MDLZ": "https://www.mondelezinternational.com/rss.xml",
    "GILD": "https://investors.gilead.com/rss/news-releases.xml",
    "ADP": "https://investors.adp.com/rss/news-releases.xml",
    "TMO": "https://www.thermofisher.com/rss.xml",
    "ISRG": "https://investor.intuitive.com/rss/news-releases.xml",
    "REGN": "https://investor.regeneron.com/rss/news-releases.xml",
    "VRTX": "https://investor.vrtx.com/rss/news-releases.xml",
    "MU": "https://investors.micron.com/rss/news-releases.xml",
    "PANW": "https://investors.paloaltonetworks.com/rss/news-releases.xml",
    "SNPS": "https://investors.synopsys.com/rss/news-releases.xml",
    "CDNS": "https://investors.cadence.com/rss/news-releases.xml",
    "KLAC": "https://investor.kla.com/rss/news-releases.xml",
    "LRCX": "https://investor.lamresearch.com/rss/news-releases.xml",
    "MCHP": "https://investor.microchip.com/rss/news-releases.xml",
    "MRVL": "https://investor.marvell.com/rss/news-releases.xml",
    "FTNT": "https://investor.fortinet.com/rss/news-releases.xml",
    "CRWD": "https://investors.crowdstrike.com/rss/news-releases.xml",
    "ZS": "https://ir.zscaler.com/rss/news-releases.xml",
    "OKTA": "https://investor.okta.com/rss/news-releases.xml",
    "DDOG": "https://investors.datadoghq.com/rss/news-releases.xml",
    "NET": "https://investors.cloudflare.com/rss/news-releases.xml",
    "SNOW": "https://investors.snowflake.com/rss/news-releases.xml",
    "PLTR": "https://investors.palantir.com/rss/news-releases.xml",
    "U": "https://investors.unity.com/rss/news-releases.xml",
    "RBLX": "https://investor.roblox.com/rss/news-releases.xml",
    "COIN": "https://investor.coinbase.com/rss/news-releases.xml",
    "HOOD": "https://investors.robinhood.com/rss/news-releases.xml",
    "SOFI": "https://investors.sofi.com/rss/news-releases.xml",
    "UPST": "https://investors.upstart.com/rss/news-releases.xml",
    "AFRM": "https://investors.affirm.com/rss/news-releases.xml",
    "PYPL": "https://investor.pypl.com/rss/news-releases.xml",
    "SQ": "https://investors.block.xyz/rss/news-releases.xml",
    "SHOP": "https://news.shopify.com/rss.xml",
    "TWLO": "https://investors.twilio.com/rss/news-releases.xml",
    "ZM": "https://investors.zoom.us/rss/news-releases.xml",
    "DOCU": "https://investors.docusign.com/rss/news-releases.xml",
    "ZEN": "https://investor.zendesk.com/rss/news-releases.xml",
    "TEAM": "https://investors.atlassian.com/rss/news-releases.xml",
    "WDAY": "https://investor.workday.com/rss/news-releases.xml",
    "VEEV": "https://investor.veeva.com/rss/news-releases.xml",
    "PAYC": "https://investor.paycom.com/rss/news-releases.xml",
    "ANSS": "https://investors.ansys.com/rss/news-releases.xml",
    "TYL": "https://investor.tylertech.com/rss/news-releases.xml",
    "MANH": "https://investor.manh.com/rss/news-releases.xml",
    "APPF": "https://investors.appfolio.com/rss/news-releases.xml",
    "HUBS": "https://investors.hubspot.com/rss/news-releases.xml",
    "DT": "https://investors.dynatrace.com/rss/news-releases.xml",
    "GTLB": "https://investors.gitlab.com/rss/news-releases.xml",
    "MNDY": "https://ir.monday.com/rss/news-releases.xml",
    "ASAN": "https://investors.asana.com/rss/news-releases.xml",
    "SMAR": "https://investors.smartsheet.com/rss/news-releases.xml",
    "DOCU": "https://investors.docusign.com/rss/news-releases.xml",
    "PRO": "https://investors.procore.com/rss/news-releases.xml",
    "ZI": "https://investors.zoominfo.com/rss/news-releases.xml",
}


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class IRReleaseProvider:
    """
    Fetches company press releases from investor relations RSS feeds.

    Uses free RSS/Atom feeds from company IR websites.
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        timeout: int = 30,
        custom_feeds: dict[str, str] | None = None,
    ):
        self.feeds = {**IR_RSS_FEEDS, **(custom_feeds or {})}
        self.timeout = timeout
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
        """Fetch company press releases from IR RSS feeds."""
        if symbols is None:
            symbols = list(self.feeds.keys())

        if from_date is None:
            from_date = date(2020, 1, 1)
        if to_date is None:
            to_date = datetime.now(timezone.utc).date()

        results: list[NewsDocument] = []

        for symbol in dict.fromkeys(s.upper() for s in symbols):
            feed_url = self.feeds.get(symbol)
            if not feed_url:
                logger.debug(f"No IR RSS feed configured for {symbol}")
                continue

            try:
                docs = self._fetch_feed(symbol, feed_url, from_date, to_date)
                results.extend(docs)
            except Exception as exc:
                self._error(symbol, "fetch_feed", feed_url, exc)

        return results

    def _fetch_feed(
        self,
        symbol: str,
        feed_url: str,
        from_date: date,
        to_date: date,
    ) -> list[NewsDocument]:
        """Fetch and parse a single RSS/Atom feed."""
        response = httpx.get(feed_url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parse warning for {symbol}: {feed.bozo_exception}")

        documents: list[NewsDocument] = []

        for entry in feed.entries:
            try:
                doc = self._parse_entry(symbol, entry, from_date, to_date)
                if doc:
                    documents.append(doc)
            except Exception as exc:
                self._error(symbol, "parse_entry", entry.get("id", "unknown"), exc)

        return documents

    def _parse_entry(
        self,
        symbol: str,
        entry: Any,
        from_date: date,
        to_date: date,
    ) -> NewsDocument | None:
        """Parse a single feed entry into NewsDocument."""
        # Get published date
        published_at = None
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    parsed = getattr(entry, date_field)
                    published_at = datetime(*parsed[:6], tzinfo=timezone.utc)
                    break
                except (TypeError, ValueError):
                    continue

        if published_at is None:
            published_at = datetime.now(timezone.utc)

        # Check date range
        if not (from_date <= published_at.date() <= to_date):
            return None

        # Get content
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
        elif hasattr(entry, "summary"):
            content = entry.summary
        elif hasattr(entry, "description"):
            content = entry.description

        # Clean HTML from content
        clean_content = self._clean_html(content)
        if not clean_content or len(clean_content.strip()) < 50:
            return None

        # Get link
        link = entry.get("link", "")
        if not link:
            link = entry.get("id", "")

        # Get title
        title = entry.get("title", f"{symbol} Press Release").strip()

        # Generate IDs
        entry_id = entry.get("id", link or title)
        content_hash = _sha256(clean_content)
        doc_id = f"ir_release:{symbol}:{content_hash[:16]}"
        dedup_key = f"ir:{symbol}:{published_at.date()}:{content_hash[:16]}"

        retrieved = datetime.now(timezone.utc)

        return NewsDocument(
            document_id=doc_id,
            symbol=symbol,
            headline=title,
            body=clean_content,
            summary=clean_content[:500] if len(clean_content) > 500 else clean_content,
            publisher=symbol,
            published_at=published_at,
            retrieved_at=retrieved,
            source_url=link,
            source_type=NewsSourceType.COMPANY_IR,
            author=entry.get("author"),
            provider_id="company_ir_rss",
            content_hash=content_hash,
            metadata={
                "feed_url": feed_url,
                "entry_id": entry_id,
                "tags": [tag.term for tag in entry.get("tags", [])] if hasattr(entry, "tags") else [],
            },
            dedup_key=dedup_key,
        )

    def _clean_html(self, html: str) -> str:
        """Strip HTML tags and clean whitespace."""
        if not html:
            return ""
        # Remove script/style
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.IGNORECASE | re.DOTALL)
        # Replace block elements with newlines
        text = re.sub(r"</(p|div|br|h[1-6]|li|tr|td|th)>", "\n", text, flags=re.IGNORECASE)
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ").replace("&", "&").replace("<", "<").replace(">", ">")
        text = text.replace('"', '"').replace('\'', "'")
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def close(self):
        pass


if __name__ == "__main__":
    # Quick test
    provider = IRReleaseProvider()
    docs = provider.fetch_company_releases(symbols=["AAPL"], from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))
    print(f"Found {len(docs)} IR releases for AAPL")
    for doc in docs[:3]:
        print(f"  {doc.headline[:80]} ({doc.published_at.date()})")
    provider.close()