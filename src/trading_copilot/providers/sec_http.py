"""Shared process-wide SEC fair-access transport. No invented contact identity."""
from __future__ import annotations

import math
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
    RETRY_TIME_BUDGET = 30.0
    MAX_RETRY_WAIT = 5.0

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise httpx.TimeoutException("SEC unavailable: request time budget exhausted")
        return remaining

    def _retry_wait(self, retry: str | None, attempt: int, deadline: float) -> None:
        wait = float(2 ** attempt)
        if retry is not None:
            try:
                try:
                    wait = float(retry)
                except ValueError:
                    parsed = parsedate_to_datetime(retry)
                    wait = (parsed - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                raise httpx.TransportError("SEC unavailable: invalid retry instruction") from None
        # Never cap a server instruction then retry earlier than requested.
        if not math.isfinite(wait) or wait < 0:
            raise httpx.TransportError("SEC unavailable: invalid retry instruction")
        if wait > self.MAX_RETRY_WAIT or wait >= self._remaining(deadline):
            raise httpx.TransportError("SEC unavailable: retry wait exceeds time budget")
        time.sleep(wait)
        self._remaining(deadline)

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
        deadline = time.monotonic() + self.RETRY_TIME_BUDGET
        for attempt in range(3):
            if not _LOCK.acquire(timeout=self._remaining(deadline)):
                raise httpx.TimeoutException("SEC unavailable: request time budget exhausted")
            try:
                spacing = max(0, 0.125 - (time.monotonic() - _LAST_REQUEST))
                if spacing >= self._remaining(deadline):
                    raise httpx.TimeoutException("SEC unavailable: request time budget exhausted")
                time.sleep(spacing)
                self._remaining(deadline)
                _LAST_REQUEST = time.monotonic()
            finally:
                _LOCK.release()
            retry = None
            try:
                # Enforce no-redirects even for injected clients; stream body to cap decoded size.
                with self.client.stream("GET", url, headers={"User-Agent": ua}, follow_redirects=False,
                                        timeout=min(30.0, self._remaining(deadline) / 4)) as stream:
                    self._remaining(deadline)
                    response = stream
                    if response.status_code == 200:
                        chunks = []
                        total = 0
                        for chunk in response.iter_bytes():
                            self._remaining(deadline)
                            total += len(chunk)
                            if total > self.MAX_DECODED:
                                raise ValueError("SEC response exceeds maximum decoded size")
                            chunks.append(chunk)
                        response._content = b"".join(chunks)
                    if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                        retry = response.headers.get("Retry-After")
                    else:
                        if not 200 <= response.status_code < 300:
                            raise httpx.HTTPStatusError(
                                f"SEC request failed (HTTP {response.status_code})",
                                request=response.request, response=response,
                            )
                        self._remaining(deadline)
                        return response
            except httpx.TransportError:
                if attempt == 2:
                    raise httpx.TransportError("SEC unavailable: transport request failed") from None
            # Release the response/connection before waiting; no throttle lock is held.
            self._retry_wait(retry, attempt, deadline)
        raise RuntimeError("SEC request exhausted")

    def close(self) -> None:
        self.client.close()
