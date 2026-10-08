"""News RSS Provider — ingests financial news from reputable RSS feeds.

Uses free RSS/Atom feeds from major financial news publishers.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date, datetime, timezone
from typing import Any

import feedparser
import httpx

from trading_copilot.models.news import NewsDocument, NewsSourceType
from trading_copilot.providers.base import NewsProvider

logger = logging.getLogger(__name__)

# Reputable financial news RSS feeds
NEWS_RSS_FEEDS = {
    "reuters_markets": "https://www.reuters.com/markets/feed/",
    "reuters_business": "https://www.reuters.com/business/feed/",
    "reuters_technology": "https://www.reuters.com/technology/feed/",
    "bloomberg": "https://www.bloomberg.com/feed/podcasts/etf-report.xml",  # Bloomberg has limited free RSS
    "cnbc_markets": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "cnbc_tech": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    "wsj_markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "marketwatch": "https://www.marketwatch.com/rss/topstories",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
    "seeking_alpha": "https://seekingalpha.com/feed.xml",
    "investing_com": "https://www.investing.com/rss/news.rss",
    "thestreet": "https://www.thestreet.com/.rss/full/",
    "benzinga": "https://www.benzinga.com/feed",
    "fxstreet": "https://www.fxstreet.com/rss/news",
    "finviz": "https://finviz.com/rss.ashx",
}


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class NewsRSSProvider:
    """
    Fetches financial news from reputable RSS/Atom feeds.

    Uses free RSS feeds from major financial news publishers.
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        timeout: int = 30,
        custom_feeds: dict[str, str] | None = None,
        symbol_filter: dict[str, list[str]] | None = None,
    ):
        self.feeds = {**NEWS_RSS_FEEDS, **(custom_feeds or {})}
        self.timeout = timeout
        # Optional: map feed -> relevant symbols for filtering
        self.symbol_filter = symbol_filter or {}
        self.errors: list[dict[str, str]] = []

    def _error(self, source: str, stage: str, source_id: str, exc: Exception):
        self.errors.append({
            "symbol": source,
            "stage": stage,
            "source_id": source_id,
            "error": type(exc).__name__,
            "message": str(exc)[:300],
        })

    def fetch_news(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]:
        """Fetch news articles from RSS feeds."""
        if symbols is None:
            # If no symbols specified, fetch from all feeds
            pass  # We'll fetch all and filter later

        if from_date is None:
            from_date = date(2020, 1, 1)
        if to_date is None:
            to_date = datetime.now(timezone.utc).date()

        results: list[NewsDocument] = []

        for feed_name, feed_url in self.feeds.items():
            try:
                docs = self._fetch_feed(feed_name, feed_url, from_date, to_date)
                results.extend(docs)
            except Exception as exc:
                self._error(feed_name, "fetch_feed", feed_url, exc)

        # Filter by symbols if provided
        if symbols:
            symbols_upper = {s.upper() for s in symbols}
            filtered = []
            for doc in results:
                if doc.symbol is None:
                    # Try to extract symbol from headline/body
                    doc.symbol = self._extract_symbol(doc.headline + " " + doc.body, symbols_upper)
                if doc.symbol and doc.symbol.upper() in symbols_upper:
                    filtered.append(doc)
            return filtered

        return results

    def _fetch_feed(
        self,
        feed_name: str,
        feed_url: str,
        from_date: date,
        to_date: date,
    ) -> list[NewsDocument]:
        """Fetch and parse a single RSS/Atom feed."""
        response = httpx.get(feed_url, timeout=self.timeout, follow_redirects=True)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parse warning for {feed_name}: {feed.bozo_exception}")

        documents: list[NewsDocument] = []

        for entry in feed.entries:
            try:
                doc = self._parse_entry(feed_name, entry, from_date, to_date)
                if doc:
                    documents.append(doc)
            except Exception as exc:
                self._error(feed_name, "parse_entry", entry.get("id", "unknown"), exc)

        return documents

    def _parse_entry(
        self,
        feed_name: str,
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
        title = entry.get("title", "Financial News").strip()

        # Try to extract symbol from content
        full_text = title + " " + clean_content
        symbol = self._extract_symbol(full_text)

        # Generate IDs
        entry_id = entry.get("id", link or title)
        content_hash = _sha256(clean_content)
        doc_id = f"news_rss:{feed_name}:{content_hash[:16]}"
        dedup_key = f"news:{feed_name}:{published_at.date()}:{content_hash[:16]}"

        retrieved = datetime.now(timezone.utc)

        # Extract publisher from feed
        publisher = feed.feed.get("title", feed_name) if hasattr(feed, "feed") else feed_name

        return NewsDocument(
            document_id=doc_id,
            symbol=symbol,
            headline=title,
            body=clean_content,
            summary=clean_content[:500] if len(clean_content) > 500 else clean_content,
            publisher=publisher,
            published_at=published_at,
            retrieved_at=retrieved,
            source_url=link,
            source_type=NewsSourceType.NEWS_RSS,
            author=entry.get("author"),
            provider_id=f"news_rss:{feed_name}",
            content_hash=content_hash,
            metadata={
                "feed_name": feed_name,
                "feed_url": self.feeds[feed_name],
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

    def _extract_symbol(self, text: str, known_symbols: set[str] | None = None) -> str | None:
        """Extract stock symbol from text."""
        # Common patterns for stock symbols in news
        patterns = [
            r"\b([A-Z]{1,5})\s*\((?:NYSE|NASDAQ|NYSE MKT)\)",  # AAPL (NASDAQ)
            r"\b(NYSE|NASDAQ):\s*([A-Z]{1,5})\b",  # NASDAQ: AAPL
            r"\$([A-Z]{1,5})\b",  # $AAPL
            r"\b([A-Z]{1,5})\s+stock\b",  # AAPL stock
            r"\b([A-Z]{1,5})\s+shares?\b",  # AAPL shares
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                symbol = match.group(1).upper()
                if known_symbols and symbol in known_symbols:
                    return symbol
                if not known_symbols:
                    # Basic validation: 1-5 chars, all caps
                    if 1 <= len(symbol) <= 5 and symbol.isalpha():
                        return symbol

        # Fallback: look for known symbols in text
        if known_symbols:
            for sym in known_symbols:
                if f" {sym} " in f" {text} " or f" {sym}." in text or f"({sym})" in text:
                    return sym

        return None

    def close(self):
        pass


if __name__ == "__main__":
    # Quick test
    provider = NewsRSSProvider()
    docs = provider.fetch_news(symbols=["AAPL"], from_date=date(2026, 1, 1), to_date=date(2026, 12, 31))
    print(f"Found {len(docs)} news articles for AAPL")
    for doc in docs[:3]:
        print(f"  {doc.publisher}: {doc.headline[:80]} ({doc.published_at.date()})")
    provider.close()