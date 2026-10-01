"""Simple file-based cache for provider responses."""

from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class FileCache:
    """File-based cache with TTL support."""

    def __init__(self, cache_dir: Path, ttl_days: int = 7):
        self.cache_dir = cache_dir
        self.ttl = timedelta(days=ttl_days)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        """Get file path for a cache key."""
        # Hash the key to avoid filesystem issues
        hashed = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{hashed}.cache"

    def _meta_path(self, key: str) -> Path:
        """Get metadata file path for a cache key."""
        hashed = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{hashed}.meta"

    def get(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        path = self._key_path(key)
        meta_path = self._meta_path(key)
        
        if not path.exists() or not meta_path.exists():
            return None
        
        # Check TTL
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            cached_time = datetime.fromisoformat(meta["timestamp"])
            if datetime.now() - cached_time > self.ttl:
                return None
        except Exception:
            return None
        
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp."""
        path = self._key_path(key)
        meta_path = self._meta_path(key)
        
        try:
            with open(path, "wb") as f:
                pickle.dump(value, f)
            
            meta = {"timestamp": datetime.now().isoformat()}
            with open(meta_path, "w") as f:
                json.dump(meta, f)
        except Exception:
            # Cache failures should not break the application
            pass

    def clear(self) -> None:
        """Clear all cache entries."""
        for path in self.cache_dir.glob("*.cache"):
            path.unlink(missing_ok=True)
        for path in self.cache_dir.glob("*.meta"):
            path.unlink(missing_ok=True)


class MemoryCache:
    """In-memory cache for testing."""

    def __init__(self):
        self._store: dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Any | None:
        if key in self._store:
            value, timestamp = self._store[key]
            return value
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, datetime.now())

    def clear(self) -> None:
        self._store.clear()