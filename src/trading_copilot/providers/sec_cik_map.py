"""SEC CIK (Central Index Key) mapping utility.

Provides symbol-to-CIK mapping using SEC's official company tickers JSON.
Caches locally to avoid repeated fetches.
"""

from __future__ import annotations

import json
import logging
import time
import hashlib
import os
import uuid
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from trading_copilot.providers.sec_http import SECTransport

logger = logging.getLogger(__name__)

# SEC company tickers endpoint (official, no auth required)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_EXCHANGE_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / "artifacts/cache/sec_cik"


class SECCIKMap:
    """Manages symbol-to-CIK mapping with local caching."""

    def __init__(
        self,
        cache_dir: str | Path = DEFAULT_CACHE_DIR,
        max_age_days: int = 30,
        user_agent: str | None = None,
        transport: SECTransport | None = None,
        source_url: str = SEC_TICKERS_URL,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "company_tickers.json"
        self.max_age_seconds = max_age_days * 24 * 60 * 60

        self.user_agent = user_agent
        self.source_url = source_url
        self.snapshot: dict[str, Any] = {}
        self.transport = transport or SECTransport(user_agent)

        self._mapping: dict[str, dict[str, Any]] = {}
        self._reverse_mapping: dict[str, str] = {}  # cik -> symbol
        self._loaded = False

    def _fetch_from_sec(self) -> dict[str, Any]:
        """Fetch company tickers from SEC."""
        return self.transport.get(self.source_url).json()

    @staticmethod
    def normalize(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Accept both official SEC schemas; preserve legacy cik/title consumers."""
        if "fields" in raw:
            fields = raw["fields"]
            if not {"cik", "name", "ticker", "exchange"}.issubset(fields):
                raise ValueError("Invalid SEC exchange schema")
            rows = [dict(zip(fields, row, strict=True)) for row in raw["data"]]
        else:
            rows = list(raw.values())
        mapping = {}
        for entry in rows:
            cik = str(entry.get("cik_str", entry.get("cik"))).zfill(10)
            ticker = entry["ticker"].strip().upper()
            title = entry.get("title", entry.get("name"))
            exchange = entry.get("exchange")
            if (not cik.isdigit() or len(cik) != 10 or not ticker
                    or not isinstance(title, str) or not title.strip()
                    or (exchange is not None and not isinstance(exchange, str))):
                raise ValueError("Invalid SEC identity row")
            mapping.setdefault(ticker, {"cik": cik, "title": title, "exchange": exchange or None})
        if not mapping:
            raise ValueError("Empty SEC mapping")
        return mapping

    def _load_cache(self, allow_stale: bool = False) -> bool:
        """Load mapping from cache file if fresh enough."""
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            mapping = data["mapping"]
            if not isinstance(mapping, dict) or not mapping:
                return False
            # Validate old and new normalized caches before exposing any entry.
            normalized = self.normalize({s: {"ticker": s, "cik_str": e["cik"],
                "title": e["title"], "exchange": e.get("exchange")} for s, e in mapping.items()})
            version = data.get("schema_version")
            source = data.get("source_url")
            fetched_at = data.get("fetched_at")
            retrieved_at = data.get("retrieved_at")
            if (version is not None and (type(version) is not int or version not in {1, 2})
                    or source is not None and source not in {SEC_TICKERS_URL, SEC_EXCHANGE_TICKERS_URL}
                    or type(fetched_at) not in {int, float} or not math.isfinite(fetched_at)
                    or not 0 <= fetched_at <= time.time()):
                return False
            if retrieved_at is not None:
                observed = self.observation_epoch(retrieved_at)
                if not 0 <= observed <= time.time() or abs(observed - fetched_at) > 1:
                    return False
            if version == 2:
                digest_data = {k: v for k, v in data.items() if k != "snapshot_id"}
                digest = hashlib.sha256(json.dumps(digest_data, sort_keys=True).encode()).hexdigest()
                if (data.get("snapshot_id") != digest
                        or source not in {SEC_TICKERS_URL, SEC_EXCHANGE_TICKERS_URL}
                        or retrieved_at is None
                        or (source == SEC_EXCHANGE_TICKERS_URL) != ("fields" in data["raw"])
                        or self.normalize(data["raw"]) != normalized):
                    return False
            if not allow_stale and (not isinstance(fetched_at, (int, float))
                    or not 0 <= time.time() - fetched_at <= self.max_age_seconds):
                return False
            self._mapping = normalized
            self._reverse_mapping = {e["cik"]: s for s, e in normalized.items()}
            self.snapshot = {k: data.get(k) for k in
                ("schema_version", "source_url", "retrieved_at", "snapshot_id", "fetched_at")}
            if not self.snapshot["retrieved_at"] and source is not None:
                self.snapshot["retrieved_at"] = datetime.fromtimestamp(fetched_at, timezone.utc).isoformat()
            if source is None:
                # Old mapping remains useful, but an unknown origin cannot verify it.
                self.snapshot["retrieved_at"] = None
            self._loaded = True
            logger.info(f"Loaded {len(self._mapping)} symbol-CIK mappings from cache")
            return True
        except Exception:
            logger.warning("Failed to load CIK cache")
            return False

    @staticmethod
    def observation_epoch(value: str) -> float:
        """Parse an actual timezone-qualified observation, never the response clock."""
        if not isinstance(value, str):
            raise ValueError("Invalid observation time")
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("Observation time requires timezone")
        return observed.timestamp()

    def _save_cache(self, raw: dict[str, Any] | None = None) -> None:
        """Save mapping to cache file."""
        observed = datetime.now(timezone.utc)
        data = {
            "mapping": self._mapping,
            "reverse_mapping": self._reverse_mapping,
            "fetched_at": observed.timestamp(),
            "schema_version": 2,
            "source_url": self.source_url,
            "retrieved_at": observed.isoformat(),
            "raw": raw,
        }
        history = self.cache_dir / "snapshots"
        history.mkdir(exist_ok=True)
        # Preserve the previous bytes too, including legacy or corrupt caches.
        if self.cache_file.exists():
            previous = self.cache_file.read_bytes()
            old = history / (hashlib.sha256(previous).hexdigest() + ".json")
            if not old.exists():
                old.write_bytes(previous)
        data["snapshot_id"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        encoded = json.dumps(data)
        (history / (data["snapshot_id"] + ".json")).write_text(encoded)
        temporary = self.cache_file.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(encoded)
        os.replace(temporary, self.cache_file)
        self.snapshot = {k: data[k] for k in
            ("schema_version", "source_url", "retrieved_at", "snapshot_id", "fetched_at")}
        logger.info(f"Saved {len(self._mapping)} symbol-CIK mappings to cache")

    def ensure_loaded(self) -> None:
        """Ensure mapping is loaded (fetch if needed)."""
        if self._loaded:
            return

        if not self._load_cache():
            logger.info("Fetching SEC company tickers...")
            try:
                raw_data = self._fetch_from_sec()
                self.refresh(raw_data)
            except Exception:
                logger.error("Failed to fetch SEC tickers")
                # Try to load stale cache as fallback
                if self._load_cache(allow_stale=True):
                    logger.warning("Using stale cache as fallback")
                else:
                    raise

    def refresh(self, raw: dict[str, Any] | None = None) -> None:
        """Explicit refresh retains raw observations and all previous cache versions."""
        raw = self._fetch_from_sec() if raw is None else raw
        mapping = self.normalize(raw)
        previous = self._mapping, self._reverse_mapping
        self._mapping = mapping
        self._reverse_mapping = {e["cik"]: s for s, e in mapping.items()}
        try:
            self._save_cache(raw)
        except Exception:
            self._mapping, self._reverse_mapping = previous
            raise
        self._loaded = True

    def get_cik(self, symbol: str) -> Optional[str]:
        """Get CIK for a symbol (returns 10-digit zero-padded string)."""
        self.ensure_loaded()
        symbol = symbol.upper()
        entry = self._mapping.get(symbol)
        return entry["cik"] if entry else None

    def get_title(self, symbol: str) -> Optional[str]:
        """Get company title for a symbol."""
        self.ensure_loaded()
        symbol = symbol.upper()
        entry = self._mapping.get(symbol)
        return entry["title"] if entry else None

    def get_symbol(self, cik: str) -> Optional[str]:
        """Get symbol for a CIK."""
        self.ensure_loaded()
        cik = str(cik).zfill(10)
        return self._reverse_mapping.get(cik)

    def get_all_symbols(self) -> list[str]:
        """Get all known symbols."""
        self.ensure_loaded()
        return sorted(self._mapping.keys())

    def resolve_symbols(self, symbols: list[str]) -> dict[str, str]:
        """Resolve a list of symbols to CIKs. Returns {symbol: cik} for found symbols."""
        self.ensure_loaded()
        result = {}
        for sym in symbols:
            cik = self.get_cik(sym)
            if cik:
                result[sym.upper()] = cik
            else:
                logger.warning(f"No CIK found for symbol: {sym}")
        return result


# Global instance for convenience
_global_cik_map: SECCIKMap | None = None


def get_cik_map(
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    max_age_days: int = 30,
    user_agent: str | None = None,
) -> SECCIKMap:
    """Get or create global CIK map instance."""
    global _global_cik_map
    if _global_cik_map is None:
        _global_cik_map = SECCIKMap(cache_dir=cache_dir, max_age_days=max_age_days, user_agent=user_agent)
    return _global_cik_map


if __name__ == "__main__":
    # Quick test
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        cik_map = SECCIKMap(cache_dir=tmpdir, max_age_days=0)  # Force refresh
        print(f"Total symbols: {len(cik_map.get_all_symbols())}")

        for sym in ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "SPY"]:
            cik = cik_map.get_cik(sym)
            title = cik_map.get_title(sym)
            print(f"  {sym}: CIK={cik}, Title={title}")
