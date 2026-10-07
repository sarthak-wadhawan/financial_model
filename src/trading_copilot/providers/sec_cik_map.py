"""SEC CIK (Central Index Key) mapping utility.

Provides symbol-to-CIK mapping using SEC's official company tickers JSON.
Caches locally to avoid repeated fetches.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from trading_copilot.providers.sec_http import SECTransport

logger = logging.getLogger(__name__)

# SEC company tickers endpoint (official, no auth required)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
# Alternative: https://www.sec.gov/files/company_tickers_exchange.json (includes exchange)


class SECCIKMap:
    """Manages symbol-to-CIK mapping with local caching."""

    def __init__(
        self,
        cache_dir: str | Path = "artifacts/cache/sec_cik",
        max_age_days: int = 30,
        user_agent: str | None = None,
        transport: SECTransport | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "company_tickers.json"
        self.max_age_seconds = max_age_days * 24 * 60 * 60

        self.user_agent = user_agent
        self.transport = transport or SECTransport(user_agent)

        self._mapping: dict[str, dict[str, Any]] = {}
        self._reverse_mapping: dict[str, str] = {}  # cik -> symbol
        self._loaded = False

    def _fetch_from_sec(self) -> dict[str, Any]:
        """Fetch company tickers from SEC."""
        return self.transport.get(SEC_TICKERS_URL).json()

    def _load_cache(self) -> bool:
        """Load mapping from cache file if fresh enough."""
        if not self.cache_file.exists():
            return False

        # Check cache age
        mtime = self.cache_file.stat().st_mtime
        if time.time() - mtime > self.max_age_seconds:
            logger.info("SEC CIK cache expired, will refresh")
            return False

        try:
            with open(self.cache_file) as f:
                data = json.load(f)
            self._mapping = data.get("mapping", {})
            self._reverse_mapping = data.get("reverse_mapping", {})
            self._loaded = True
            logger.info(f"Loaded {len(self._mapping)} symbol-CIK mappings from cache")
            return True
        except Exception as e:
            logger.warning(f"Failed to load CIK cache: {e}")
            return False

    def _save_cache(self) -> None:
        """Save mapping to cache file."""
        data = {
            "mapping": self._mapping,
            "reverse_mapping": self._reverse_mapping,
            "fetched_at": time.time(),
        }
        with open(self.cache_file, "w") as f:
            json.dump(data, f)
        logger.info(f"Saved {len(self._mapping)} symbol-CIK mappings to cache")

    def ensure_loaded(self) -> None:
        """Ensure mapping is loaded (fetch if needed)."""
        if self._loaded:
            return

        if not self._load_cache():
            logger.info("Fetching SEC company tickers...")
            try:
                raw_data = self._fetch_from_sec()
                # Official cik_str values are integers; normalize before zero-padding.
                for entry in raw_data.values():
                    cik = str(entry["cik_str"]).zfill(10)
                    if not cik.isdigit() or len(cik) != 10:
                        raise ValueError("Invalid SEC CIK")
                    ticker = entry["ticker"].upper()
                    title = entry["title"]

                    # Handle duplicate tickers (keep first, log warning)
                    if ticker in self._mapping:
                        logger.debug(f"Duplicate ticker {ticker}: {self._mapping[ticker]['cik']} vs {cik}")
                        continue

                    self._mapping[ticker] = {
                        "cik": cik,
                        "title": title,
                    }
                    self._reverse_mapping[cik] = ticker

                self._save_cache()
                self._loaded = True
            except Exception as e:
                logger.error(f"Failed to fetch SEC tickers: {e}")
                # Try to load stale cache as fallback
                if self.cache_file.exists():
                    with open(self.cache_file) as f:
                        data = json.load(f)
                    self._mapping = data.get("mapping", {})
                    self._reverse_mapping = data.get("reverse_mapping", {})
                    self._loaded = True
                    logger.warning("Using stale cache as fallback")
                else:
                    raise

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
    cache_dir: str | Path = "artifacts/cache/sec_cik",
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
