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
- Multi-language support (English/German)
- Desktop notifications
- System tray integration
- Built-in unit tests

Usage:
    python main.py                          # Run the GUI application
    python main.py --extract -p PROJECT     # CLI extraction mode
    python main.py --test                   # Run unit tests
    python main.py --help                   # Show help

Author: EPLAN Extractor Team
Version: 2.2.0
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import time
import unittest
from datetime import datetime
from typing import Optional

from eplan_extractor.constants import VERSION, BASE_URL


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


def run_cli_extraction(
    project: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    output_dir: Optional[str] = None,
    output_format: str = "xlsx",
    headless: bool = True,
    use_cache: bool = True
) -> bool:
    """
    Run extraction in CLI mode.

    Args:
        project: Project number to extract
        email: Microsoft account email
        password: Microsoft account password
        output_dir: Output directory for exported files
        output_format: Output format (xlsx, csv, json, or all)
        headless: Run browser in headless mode
        use_cache: Use cached data if available

    Returns:
        True if extraction succeeded
    """
    from eplan_extractor.core.cache import CacheManager
    from eplan_extractor.core.config import ConfigManager, ExtractionRecord
    from eplan_extractor.core.extractor import SeleniumEPlanExtractor
    from eplan_extractor.utils.logging import get_logger

    logger = get_logger()
    config_manager = ConfigManager()
    cache_manager = CacheManager() if use_cache else None

    # Load saved credentials if not provided
    config = config_manager.load()

    if not email:
        email = config.email
        if not email:
            email = input("Email: ")

    if not password:
        if config.password_encrypted:
            password = config_manager.decrypt_password(config.password_encrypted)
        if not password:
            password = getpass.getpass("Password: ")

    if not output_dir:
        output_dir = config.export_directory or os.getcwd()

    print(f"\nEPLAN eVIEW Extractor v{VERSION}")
    print("=" * 50)
    print(f"Project: {project}")
    print(f"Email: {email}")
    print(f"Output: {output_dir}")
    print(f"Format: {output_format}")
    print(f"Headless: {headless}")
    print(f"Cache: {'enabled' if use_cache else 'disabled'}")
    print("=" * 50 + "\n")

    start_time = time.time()
    pages_extracted = 0
    variables_found = 0
    output_file = ""
    success = False
    error_message = ""

    try:
        extractor = SeleniumEPlanExtractor(
            base_url=BASE_URL,
            username=email,
            password=password,
            project_number=project,
            headless=headless,
            cache_manager=cache_manager
        )

        print("[1/4] Setting up browser...")
        extractor.setup_driver()

        print("[2/4] Logging in to Microsoft...")
        if not extractor.click_on_login_with_microsoft():
            raise Exception("Failed to find Microsoft login button")

        if not extractor.login():
            raise Exception("Login failed - check credentials")

        print("[3/4] Opening project...")
        if not extractor.open_project():
            raise Exception(f"Failed to open project '{project}'")

        if not extractor.switch_to_list_view():
            raise Exception("Failed to switch to list view")

        print("[4/4] Extracting variables...")
        if not extractor.extract_variables():
            raise Exception("Extraction failed")

        # Get statistics
        pages_extracted = getattr(extractor, '_pages_processed', 0)
        variables_found = getattr(extractor, '_variables_found', 0)
        output_file = f"{project} IO-List.xlsx"

        duration = time.time() - start_time
        print(f"\nExtraction completed in {duration:.1f} seconds")
        print(f"Pages processed: {pages_extracted}")
        print(f"Variables found: {variables_found}")
        print(f"Output file: {output_file}")

        success = True

    except KeyboardInterrupt:
        print("\nExtraction cancelled by user")
        error_message = "Cancelled by user"

    except Exception as e:
        logger.error(f"Extraction error: {e}")
        print(f"\nError: {e}")
        error_message = str(e)

    finally:
        # Record in history
        record = ExtractionRecord(
            project=project,
            timestamp=datetime.now().isoformat(),
            duration_seconds=time.time() - start_time,
            pages_extracted=pages_extracted,
            variables_found=variables_found,
            output_file=output_file,
            success=success,
            error_message=error_message
        )
        config_manager.add_history_entry(record)

        # Add to recent projects
        if success:
            config_manager.add_recent_project(project)

    return success


def show_history() -> None:
    """Display extraction history."""
    from eplan_extractor.core.config import ConfigManager

    config_manager = ConfigManager()
    history = config_manager.get_history()

    print(f"\nEPLAN Extractor v{VERSION} - Extraction History")
    print("=" * 80)

    if not history:
        print("No extraction history found.")
        return

    print(f"{'Date':<20} {'Project':<20} {'Duration':<10} {'Variables':<10} {'Status':<10}")
    print("-" * 80)

    for record in history[:20]:  # Show last 20
        date = record.timestamp[:19].replace("T", " ") if record.timestamp else "Unknown"
        duration = f"{record.duration_seconds:.1f}s"
        status = "OK" if record.success else "FAILED"
        print(f"{date:<20} {record.project:<20} {duration:<10} {record.variables_found:<10} {status:<10}")

    print("-" * 80)

    stats = config_manager.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total extractions: {stats['total_extractions']}")
    print(f"  Successful: {stats['successful_extractions']}")
    print(f"  Failed: {stats['failed_extractions']}")
    print(f"  Unique projects: {stats['unique_projects']}")
    print(f"  Total variables: {stats['total_variables']}")


def show_statistics() -> None:
    """Display detailed statistics."""
    from eplan_extractor.core.config import ConfigManager

    config_manager = ConfigManager()
    stats = config_manager.get_statistics()

    print(f"\nEPLAN Extractor v{VERSION} - Statistics")
    print("=" * 50)
    print(f"Total Extractions:     {stats['total_extractions']}")
    print(f"Successful:            {stats['successful_extractions']}")
    print(f"Failed:                {stats['failed_extractions']}")
    print(f"Success Rate:          {stats['successful_extractions'] / stats['total_extractions'] * 100:.1f}%" if stats['total_extractions'] > 0 else "N/A")
    print(f"")
    print(f"Total Pages:           {stats['total_pages']}")
    print(f"Total Variables:       {stats['total_variables']}")
    print(f"Unique Projects:       {stats['unique_projects']}")
    print(f"")
    print(f"Total Time:            {stats['total_time_seconds'] / 60:.1f} minutes")
    print(f"Average Time:          {stats['average_time_seconds']:.1f} seconds")
    print("=" * 50)


def check_for_updates() -> None:
    """Check for updates from GitHub."""
    from eplan_extractor.core.updater import UpdateChecker

    print(f"\nEPLAN Extractor v{VERSION} - Checking for Updates...")

    checker = UpdateChecker()

    try:
        release = checker.check_for_updates()

        if release:
            print(f"\nUpdate available: v{release.version}")
            print(f"Release: {release.name}")
            print(f"URL: {release.html_url}")

            if release.body:
                print(f"\nRelease Notes:")
                print("-" * 40)
                print(release.body[:500])
                if len(release.body) > 500:
                    print("...")
        else:
            print("You are running the latest version!")

    except Exception as e:
        print(f"Error checking for updates: {e}")


def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description=f"EPLAN eVIEW Text Extractor v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                              Run the GUI application
  python main.py --extract -p PROJECT-001     Extract in CLI mode
  python main.py --extract -p PRJ -e user@company.com
  python main.py --history                    Show extraction history
  python main.py --stats                      Show statistics
  python main.py --check-update               Check for updates
  python main.py --test                       Run unit tests
  python main.py --lang de                    Run GUI in German
        """
    )

    # Mode flags
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run unit tests"
    )

    parser.add_argument(
        "--extract", "-x",
        action="store_true",
        help="Run extraction in CLI mode (requires -p/--project)"
    )

    parser.add_argument(
        "--history",
        action="store_true",
        help="Show extraction history"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show extraction statistics"
    )

    parser.add_argument(
        "--check-update",
        action="store_true",
        help="Check for updates"
    )

    # Extraction options
    parser.add_argument(
        "--project", "-p",
        type=str,
        help="Project number to extract (required for --extract)"
    )

    parser.add_argument(
        "--email", "-e",
        type=str,
        help="Microsoft account email"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for exported files"
    )

    parser.add_argument(
        "--format", "-f",
        type=str,
        choices=["xlsx", "csv", "json", "all"],
        default="xlsx",
        help="Output format (default: xlsx)"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Show browser window during extraction"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable extraction cache"
    )

    # General options
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
        "--clear-history",
        action="store_true",
        help="Clear extraction history and exit"
    )

    parser.add_argument(
        "--lang", "-l",
        type=str,
        choices=["en", "de"],
        default="en",
        help="Language for GUI (en=English, de=German)"
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

    # Set language
    if args.lang:
        from eplan_extractor.utils.i18n import I18n
        I18n.set_language(args.lang)

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

    # Handle --clear-history flag
    if args.clear_history:
        from eplan_extractor.core.config import ConfigManager
        config_manager = ConfigManager()
        count = config_manager.clear_history()
        print(f"Cleared {count} history entries")
        sys.exit(0)

    # Handle --history flag
    if args.history:
        show_history()
        sys.exit(0)

    # Handle --stats flag
    if args.stats:
        show_statistics()
        sys.exit(0)

    # Handle --check-update flag
    if args.check_update:
        check_for_updates()
        sys.exit(0)

    # Handle --extract flag (CLI mode)
    if args.extract:
        if not args.project:
            print("Error: --project/-p is required for CLI extraction")
            print("Example: python main.py --extract -p PROJECT-001")
            sys.exit(1)

        success = run_cli_extraction(
            project=args.project,
            email=args.email,
            output_dir=args.output,
            output_format=args.format,
            headless=not args.no_headless,
            use_cache=not args.no_cache
        )
        sys.exit(0 if success else 1)

    # Check for GUI availability
    try:
        import tkinter as tk
    except ImportError:
        print("Error: tkinter is not available.")
        print("Please install python3-tk or run with --extract for CLI mode.")
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
