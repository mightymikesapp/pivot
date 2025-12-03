"""Cache management for Legal Research Assistant.

This module provides a file-based cache implementation with granular TTLs
and statistics tracking.
"""

import hashlib
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """Types of cached data with different TTLs."""

    METADATA = "metadata"
    TEXT = "text"
    SEARCH = "search"


class CacheManager:
    """Manages file-based caching with statistics and TTL enforcement."""

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize the cache manager.

        Args:
            base_dir: Base directory for cache storage. If None, uses settings.
        """
        self.settings = get_settings()
        self.base_dir = base_dir or self.settings.courtlistener_cache_dir
        self.enabled = self.settings.cache_enabled
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }

        # Ensure base directory exists
        if self.enabled:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            # Create subdirectories for each type
            for cache_type in CacheType:
                (self.base_dir / cache_type.value).mkdir(exist_ok=True)

    def _get_ttl(self, cache_type: CacheType) -> int:
        """Get TTL in seconds for a specific cache type."""
        match cache_type:
            case CacheType.METADATA:
                return self.settings.courtlistener_ttl_metadata
            case CacheType.TEXT:
                return self.settings.courtlistener_ttl_text
            case CacheType.SEARCH:
                return self.settings.courtlistener_ttl_search
        return 3600  # Fallback

    def _build_key(self, params: dict[str, Any] | str) -> str:
        """Generate a stable cache key from parameters."""
        if isinstance(params, str):
            content = params
        else:
            # Normalize dictionary to ensure stable key
            def normalize(value: Any) -> Any:
                if isinstance(value, str):
                    return value.strip().lower()
                if isinstance(value, (list, tuple)):
                    return sorted([normalize(v) for v in value], key=str)
                if isinstance(value, dict):
                    return {k: normalize(v) for k, v in value.items()}
                return value

            normalized = {k: normalize(v) for k, v in params.items() if v not in (None, "")}
            content = json.dumps(normalized, sort_keys=True, separators=(",", ":"))

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_path(self, cache_type: CacheType, key: str) -> Path:
        """Get the file path for a cache entry."""
        suffix = "txt" if cache_type == CacheType.TEXT else "json"
        return self.base_dir / cache_type.value / f"{key}.{suffix}"

    def get(self, cache_type: CacheType, key_params: dict[str, Any] | str) -> Any | None:
        """Retrieve an item from the cache.

        Args:
            cache_type: The type of data being retrieved
            key_params: Parameters used to generate the cache key

        Returns:
            Cached data if available and valid, None otherwise
        """
        if not self.enabled:
            return None

        key = self._build_key(key_params)
        path = self._get_path(cache_type, key)

        if not path.exists():
            self.stats["misses"] += 1
            return None

        # Check TTL
        age = time.time() - path.stat().st_mtime
        if age > self._get_ttl(cache_type):
            self.stats["misses"] += 1
            # Lazy deletion
            try:
                path.unlink()
            except OSError:
                pass
            return None

        # Read data
        try:
            if cache_type == CacheType.TEXT:
                with path.open("r", encoding="utf-8") as f:
                    data = f.read()
            else:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)

            self.stats["hits"] += 1
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read cache {path}: {e}")
            self.stats["errors"] += 1
            return None

    def set(self, cache_type: CacheType, key_params: dict[str, Any] | str, data: Any) -> None:
        """Save an item to the cache.

        Args:
            cache_type: The type of data being saved
            key_params: Parameters used to generate the cache key
            data: The data to save
        """
        if not self.enabled:
            return

        key = self._build_key(key_params)
        path = self._get_path(cache_type, key)

        try:
            # Ensure directory exists (in case it was deleted)
            path.parent.mkdir(parents=True, exist_ok=True)

            if cache_type == CacheType.TEXT:
                with path.open("w", encoding="utf-8") as f:
                    if not isinstance(data, str):
                        data = str(data)
                    f.write(data)
            else:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except OSError as e:
            logger.warning(f"Failed to write cache {path}: {e}")
            self.stats["errors"] += 1

    def clear(self, cache_type: CacheType | None = None) -> int:
        """Clear the cache.

        Args:
            cache_type: Specific type to clear, or None for all.

        Returns:
            Number of files deleted.
        """
        if not self.enabled:
            return 0

        count = 0
        targets = [cache_type] if cache_type else list(CacheType)

        for target in targets:
            dir_path = self.base_dir / target.value
            if dir_path.exists():
                for file_path in dir_path.glob("*"):
                    try:
                        file_path.unlink()
                        count += 1
                    except OSError:
                        pass
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, errors, and size information.
        """
        size_bytes = 0
        file_count = 0

        if self.enabled and self.base_dir.exists():
            for p in self.base_dir.rglob("*"):
                if p.is_file():
                    try:
                        size_bytes += p.stat().st_size
                        file_count += 1
                    except OSError:
                        pass

        return {
            "enabled": self.enabled,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "files": file_count,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "base_dir": str(self.base_dir),
            "ttls": {
                t.value: self._get_ttl(t) for t in CacheType
            }
        }

# Global instance
_cache_manager: CacheManager | None = None

def get_cache_manager() -> CacheManager:
    """Get or create the global cache manager."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
