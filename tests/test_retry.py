"""
Tests for the retry_with_backoff decorator.
"""

import unittest

from eplan_extractor.utils.retry import retry_with_backoff


class TestRetryDecorator(unittest.TestCase):
    """Tests for the retry_with_backoff decorator."""

    def test_successful_call(self) -> None:
        """Test that successful calls return immediately."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def always_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = always_succeeds()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_retry_on_failure(self) -> None:
        """Test that failures trigger retries."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = fails_twice()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_max_retries_exceeded(self) -> None:
        """Test that max retries raises exception."""
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fails() -> None:
            raise ValueError("Permanent error")

        with self.assertRaises(ValueError):
            always_fails()


if __name__ == "__main__":
    unittest.main()
