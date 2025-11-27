"""
Tests for the CacheManager class.
"""

import unittest
from pathlib import Path

from eplan_extractor.core.cache import CacheManager


class TestCacheManager(unittest.TestCase):
    """Tests for the CacheManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.cache = CacheManager(
            cache_file=Path("test_cache.json"),
            ttl_hours=1
        )

    def tearDown(self) -> None:
        """Clean up test artifacts."""
        test_file = Path("test_cache.json")
        if test_file.exists():
            test_file.unlink()

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        data = {"IW1.0": "Motor_Start", "QW2.1": "Valve_Open"}
        self.cache.set("TEST001", "Page1", data)

        result = self.cache.get("TEST001", "Page1")
        self.assertEqual(result, data)

    def test_get_nonexistent(self) -> None:
        """Test getting non-existent cache entry."""
        result = self.cache.get("NONEXISTENT", "Page1")
        self.assertIsNone(result)

    def test_clear(self) -> None:
        """Test cache clearing."""
        self.cache.set("TEST001", "Page1", {"key": "value"})
        self.cache.set("TEST001", "Page2", {"key": "value"})

        count = self.cache.clear("TEST001")
        self.assertEqual(count, 2)

        self.assertIsNone(self.cache.get("TEST001", "Page1"))


if __name__ == "__main__":
    unittest.main()
