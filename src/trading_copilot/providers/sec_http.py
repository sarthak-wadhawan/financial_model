"""Shared process-wide SEC fair-access transport. No invented contact identity."""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlsplit

import httpx

from trading_copilot.config import load_settings

_LOCK = threading.Lock()
_LAST_REQUEST = 0.0


def safe_sec_url(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in {"www.sec.gov", "data.sec.gov"}
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or parsed.query or parsed.fragment
            or any(p in {".", ".."} for p in unquote(parsed.path).split("/"))
            or "\\" in unquote(parsed.path)):
        raise ValueError("Unsafe SEC URL")
    return url


class SECTransport:
    MAX_DECODED = 20_000_000

    def __init__(self, user_agent: str | None = None, client: httpx.Client | None = None):
        self.user_agent = user_agent or load_settings().sec_user_agent
        self.client = client or httpx.Client(timeout=30, follow_redirects=False, limits=httpx.Limits(max_connections=2))

    def get(self, url: str) -> httpx.Response:
        global _LAST_REQUEST
        safe_sec_url(url)
        ua = self.user_agent or ""
        if not re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", ua) or re.search(
            r"example\.(com|org|net)|your[_ -]?email", ua, re.I
        ):
            raise ValueError("SEC_USER_AGENT must identify your organization and real contact email")
        for attempt in range(3):
            with _LOCK:
                time.sleep(max(0, 0.125 - (time.monotonic() - _LAST_REQUEST)))
                _LAST_REQUEST = time.monotonic()
            try:
                # Enforce no-redirects even for injected clients; stream body to cap decoded size.
                with self.client.stream("GET", url, headers={"User-Agent": ua}, follow_redirects=False) as stream:
                    response = stream
                    if response.status_code == 200:
                        chunks = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > self.MAX_DECODED:
                                raise ValueError("SEC response exceeds maximum decoded size")
                            chunks.append(chunk)
                        response._content = b"".join(chunks)
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        retry = response.headers.get("Retry-After")
                        if retry:
                            try:
                                wait = float(retry)
                            except ValueError:
                                # HTTP-date Retry-After
                                wait = max(0, (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds())
                        else:
                            wait = 2 ** attempt
                        time.sleep(wait)
                        continue
                    response.raise_for_status()
                    return response
            except httpx.TransportError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        raise RuntimeError("SEC request exhausted")

    def close(self) -> None:
        self.client.close()
