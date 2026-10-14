"""Pure validation at the ICS export boundary; never repair retained evidence."""
from __future__ import annotations

import ipaddress
import re
import unicodedata
from urllib.parse import unquote_to_bytes, urlsplit


def require_property_value(value: str, field: str) -> str:
    """Reject line folding, control characters and empty non-text properties."""
    if not value or any(unicodedata.category(c) in ("Cc", "Cf") for c in value):
        raise ValueError(f"Invalid calendar {field}")
    return value


def safe_calendar_url(value: str | None) -> str | None:
    """HTTP(S)-only navigation URI, returned verbatim or omitted; no network IO.

    This is not an SSRF filter or a guarantee about the destination. Literal and
    percent-encoded controls, credentials and parser-confusing syntax are rejected.
    """
    if not value or any(c.isspace() or unicodedata.category(c) in ("Cc", "Cf") for c in value):
        return None
    if any(c in value for c in '\\<>"`') or re.search(r"%(?![0-9a-fA-F]{2})", value):
        return None
    try:
        decoded = unquote_to_bytes(value).decode("utf-8", errors="strict")
        if any(unicodedata.category(c) in ("Cc", "Cf") for c in decoded):
            return None
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            return None
        if "@" in parsed.netloc or "%" in parsed.netloc or not parsed.hostname:
            return None
        # Accessing .port also detects malformed/non-numeric/out-of-range ports.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
        host = parsed.hostname
        if ":" in host:
            if not re.fullmatch(r"\[[0-9a-fA-F:.]+\](?::[0-9]+)?", parsed.netloc):
                return None
            ipaddress.IPv6Address(host)
        else:
            if not re.fullmatch(r"[^:]+(?::[0-9]+)?", parsed.netloc):
                return None
            if len(host) > 253 or not all(re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) for label in host.rstrip(".").split(".")):
                return None
        return value
    except (ValueError, UnicodeError):
        return None
