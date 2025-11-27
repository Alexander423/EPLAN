"""
Tests for the address pattern regex.
"""

import re
import unittest

from eplan_extractor.core.extractor import SeleniumEPlanExtractor


class TestAddressRegex(unittest.TestCase):
    """Tests for the address pattern regex."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.pattern = re.compile(SeleniumEPlanExtractor.ADDRESS_PATTERN)

    def test_valid_addresses(self) -> None:
        """Test that valid addresses are matched."""
        valid_addresses = [
            "I1.0", "I12.7", "Q0.0", "Q15.3",
            "IW0", "IW100", "QW5", "QW255",
            "IW1.0", "QW2.1"
        ]

        for addr in valid_addresses:
            self.assertIsNotNone(
                self.pattern.match(addr),
                f"Should match: {addr}"
            )

    def test_invalid_addresses(self) -> None:
        """Test that invalid addresses are not matched."""
        invalid_addresses = [
            "A1.0", "B12.7", "X0.0",
            "Motor_Start", "123", "IQ1.0"
        ]

        for addr in invalid_addresses:
            self.assertIsNone(
                self.pattern.match(addr),
                f"Should not match: {addr}"
            )


if __name__ == "__main__":
    unittest.main()
