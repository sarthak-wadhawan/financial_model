"""Content hashing utilities for reproducibility."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def content_hash(obj: Any) -> str:
    """Generate a deterministic hash of any JSON-serializable object."""
    serialized = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def config_hash(config: dict) -> str:
    """Generate a hash of configuration (excluding secrets)."""
    # Remove any keys that might contain secrets
    sanitized = {k: v for k, v in config.items() if not _is_secret_key(k)}
    return content_hash(sanitized)


def _is_secret_key(key: str) -> bool:
    """Check if a key likely contains secrets."""
    secret_indicators = [
        "key", "secret", "password", "token", "api_key", "api_secret",
        "access_token", "private_key", "credential",
    ]
    key_lower = key.lower()
    return any(indicator in key_lower for indicator in secret_indicators)


def source_content_hash(text: str) -> str:
    """Generate hash of source document text for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def stable_source_id(symbol: str, source_type: str, published_at: str, url: str | None) -> str:
    """Generate a stable source ID from document metadata."""
    components = f"{symbol}|{source_type}|{published_at}|{url or ''}"
    return hashlib.sha256(components.encode()).hexdigest()[:12].upper()