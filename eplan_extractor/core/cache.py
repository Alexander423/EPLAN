"""
Caching system for extracted data to avoid re-processing.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..constants import CACHE_ENABLED, CACHE_FILE, CACHE_TTL_HOURS, CacheEntry, ExtractedData
from ..utils.logging import get_logger


@dataclass
class CacheManager:
    """
    Manages caching of extracted data to avoid re-processing.

    Cache entries include a timestamp and project hash for validation.
    """

    cache_file: Path = field(default_factory=lambda: Path(CACHE_FILE))
    ttl_hours: int = CACHE_TTL_HOURS
    _cache: Dict[str, CacheEntry] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        """Load existing cache from file."""
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from file if it exists."""
        if not CACHE_ENABLED:
            return

        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                get_logger().debug(f"Loaded {len(self._cache)} cache entries")
        except (json.JSONDecodeError, IOError) as e:
            get_logger().warning(f"Failed to load cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to file."""
        if not CACHE_ENABLED:
            return

        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except IOError as e:
            get_logger().warning(f"Failed to save cache: {e}")

    def _generate_key(self, project: str, page_name: str) -> str:
        """Generate a unique cache key for a project and page."""
        content = f"{project}:{page_name}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if a cache entry is still valid (not expired)."""
        if "timestamp" not in entry:
            return False

        cached_time = datetime.fromisoformat(entry["timestamp"])
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        return age_hours < self.ttl_hours

    def get(self, project: str, page_name: str) -> Optional[ExtractedData]:
        """
        Get cached data for a project page.

        Args:
            project: Project number
            page_name: Page name

        Returns:
            Cached data if valid, None otherwise
        """
        if not CACHE_ENABLED:
            return None

        with self._lock:
            key = self._generate_key(project, page_name)
            entry = self._cache.get(key)

            if entry and self._is_entry_valid(entry):
                get_logger().debug(f"Cache hit for page: {page_name}")
                return entry.get("data")

            return None

    def set(self, project: str, page_name: str, data: ExtractedData) -> None:
        """
        Cache extracted data for a project page.

        Args:
            project: Project number
            page_name: Page name
            data: Extracted data to cache
        """
        if not CACHE_ENABLED:
            return

        with self._lock:
            key = self._generate_key(project, page_name)
            self._cache[key] = {
                "project": project,
                "page": page_name,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            self._save_cache()
            get_logger().debug(f"Cached data for page: {page_name}")

    def clear(self, project: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            project: If specified, only clear entries for this project

        Returns:
            Number of entries cleared
        """
        with self._lock:
            if project is None:
                count = len(self._cache)
                self._cache = {}
            else:
                keys_to_remove = [
                    k for k, v in self._cache.items()
                    if v.get("project") == project
                ]
                count = len(keys_to_remove)
                for key in keys_to_remove:
                    del self._cache[key]

            self._save_cache()
            get_logger().info(f"Cleared {count} cache entries")
            return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if not self._is_entry_valid(v)
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                self._save_cache()
                get_logger().info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)
