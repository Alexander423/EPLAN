#!/usr/bin/env python3
"""
EPLAN eVIEW Text Extractor

A desktop application for extracting PLC diagram variables from EPLAN eVIEW.
Features:
- Microsoft SSO authentication
- Automated web scraping with Selenium
- Encrypted credential storage
- File and GUI logging
- Extraction caching to avoid re-processing
- Network retry handling with exponential backoff
- Built-in unit tests

Usage:
    python main.py              # Run the GUI application
    python main.py --test       # Run unit tests
    python main.py --help       # Show help

Author: EPLAN Extractor Team
Version: 2.1.0
"""

from __future__ import annotations

import argparse
import os
import sys
import unittest

from eplan_extractor.constants import VERSION


def run_tests() -> bool:
    """
    Run all unit tests.

    Returns:
        True if all tests passed
    """
    print(f"\nEPLAN Extractor v{VERSION} - Running Unit Tests\n")
    print("=" * 60)

    # Import test modules
    from tests.test_cache import TestCacheManager
    from tests.test_config import TestConfigManager
    from tests.test_retry import TestRetryDecorator
    from tests.test_patterns import TestAddressRegex

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCacheManager))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryDecorator))
    suite.addTests(loader.loadTestsFromTestCase(TestAddressRegex))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)

    if result.wasSuccessful():
        print("All tests passed!")
        return True
    else:
        print(f"Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")
        return False


def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description=f"EPLAN eVIEW Text Extractor v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Run the GUI application
  python main.py --test       Run unit tests
  python main.py --version    Show version information
        """
    )

    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run unit tests"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"EPLAN eVIEW Text Extractor v{VERSION}"
    )

    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the extraction cache and exit"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # Handle --debug flag
    if args.debug:
        import eplan_extractor.constants as constants
        constants.DEBUG = True

    # Handle --test flag
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    # Handle --clear-cache flag
    if args.clear_cache:
        from eplan_extractor.core.cache import CacheManager
        cache = CacheManager()
        count = cache.clear()
        print(f"Cleared {count} cache entries")
        sys.exit(0)

    # Check for GUI availability
    try:
        import tkinter as tk
    except ImportError:
        print("Error: tkinter is not available.")
        print("Please install python3-tk or run with --test for unit tests.")
        sys.exit(1)

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run GUI application
    from eplan_extractor.gui.app import EPlanExtractorGUI

    root = tk.Tk()
    app = EPlanExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
