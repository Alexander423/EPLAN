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
    python "TextExtractor 2.py"           # Run the GUI application
    python "TextExtractor 2.py" --test    # Run unit tests
    python "TextExtractor 2.py" --help    # Show help

Author: EPLAN Extractor Team
Version: 2.0.0
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
import unittest
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
from urllib.request import urlopen

# Third-party imports
try:
    import pandas
    from bs4 import BeautifulSoup
    from cryptography.fernet import Fernet, InvalidToken
    from selenium import webdriver
    from selenium.common.exceptions import (
        ElementClickInterceptedException,
        NoSuchElementException,
        StaleElementReferenceException,
        TimeoutException,
        WebDriverException,
    )
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.remote.webelement import WebElement
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

# GUI imports (optional for testing)
try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL: str = "https://eview.eplan.com/"
DEBUG: bool = True
VERSION: str = "2.0.0"

# Retry configuration
MAX_RETRIES: int = 3
RETRY_BASE_DELAY: float = 2.0  # seconds
RETRY_MAX_DELAY: float = 30.0  # seconds

# Cache configuration
CACHE_ENABLED: bool = True
CACHE_FILE: str = "eplan_cache.json"
CACHE_TTL_HOURS: int = 24  # Cache time-to-live in hours

# Logging configuration
LOG_FILE: str = "eplan_extractor.log"
LOG_MAX_SIZE: int = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT: int = 3

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

T = TypeVar("T")
ExtractedData = Dict[str, str]
CacheEntry = Dict[str, Any]


# =============================================================================
# LOGGING SYSTEM
# =============================================================================

class LogLevel:
    """Log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class FileLogger:
    """
    Thread-safe file logger with rotation support.

    Logs messages to both file and optionally to a callback function.
    """

    _instance: Optional[FileLogger] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> FileLogger:
        """Singleton pattern for logger instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the file logger."""
        if self._initialized:
            return

        self._initialized = True
        self._log_file = Path(LOG_FILE)
        self._callbacks: List[Callable[[str, str], None]] = []
        self._file_lock = threading.Lock()

        # Rotate log if too large
        self._rotate_if_needed()

        # Write startup marker
        self._write_to_file(f"\n{'='*60}\n")
        self._write_to_file(f"EPLAN Extractor v{VERSION} - Session Started\n")
        self._write_to_file(f"Timestamp: {datetime.now().isoformat()}\n")
        self._write_to_file(f"{'='*60}\n\n")

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds maximum size."""
        if not self._log_file.exists():
            return

        if self._log_file.stat().st_size > LOG_MAX_SIZE:
            # Rotate existing backups
            for i in range(LOG_BACKUP_COUNT - 1, 0, -1):
                old_backup = self._log_file.with_suffix(f".log.{i}")
                new_backup = self._log_file.with_suffix(f".log.{i + 1}")
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)

            # Move current log to first backup
            backup_path = self._log_file.with_suffix(".log.1")
            if backup_path.exists():
                backup_path.unlink()
            self._log_file.rename(backup_path)

    def _write_to_file(self, message: str) -> None:
        """Write a message to the log file (thread-safe)."""
        with self._file_lock:
            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(message)
            except IOError as e:
                print(f"Failed to write to log file: {e}")

    def add_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add a callback function to receive log messages."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, str], None]) -> None:
        """Remove a callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def log(self, message: str, level: str = LogLevel.INFO) -> None:
        """
        Log a message with timestamp and level.

        Args:
            message: The message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"

        # Write to file
        self._write_to_file(formatted + "\n")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(message, level)
            except Exception:
                pass  # Don't let callback errors break logging

    def debug(self, message: str) -> None:
        """Log a debug message."""
        if DEBUG:
            self.log(message, LogLevel.DEBUG)

    def info(self, message: str) -> None:
        """Log an info message."""
        self.log(message, LogLevel.INFO)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.log(message, LogLevel.WARNING)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.log(message, LogLevel.ERROR)

    def success(self, message: str) -> None:
        """Log a success message."""
        self.log(message, LogLevel.SUCCESS)


def get_logger() -> FileLogger:
    """Get the singleton logger instance."""
    return FileLogger()


# =============================================================================
# RETRY DECORATOR WITH EXPONENTIAL BACKOFF
# =============================================================================

def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    exceptions: Tuple[type, ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback called on each retry with (exception, attempt)

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = get_logger()
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}"
                        )

            raise last_exception  # type: ignore

        return wrapper
    return decorator


# =============================================================================
# CACHING SYSTEM
# =============================================================================

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


# =============================================================================
# CONFIGURATION MANAGER
# =============================================================================

@dataclass
class AppConfig:
    """Application configuration data class."""
    email: str = ""
    password_encrypted: str = ""
    project: str = ""
    headless: bool = True
    export_excel: bool = True
    export_csv: bool = False


class ConfigManager:
    """
    Manages application configuration with encrypted credential storage.

    Uses Fernet symmetric encryption for password storage.
    """

    CONFIG_FILE: str = "eplan_config.json"
    KEY_FILE: str = "fernet.key"

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._logger = get_logger()
        self._fernet: Optional[Fernet] = None
        self._config = AppConfig()
        self._setup_encryption()

    def _setup_encryption(self) -> None:
        """Set up Fernet encryption key."""
        key_path = Path(self.KEY_FILE)

        try:
            if key_path.exists():
                key = key_path.read_bytes()
            else:
                self._logger.info("Generating new encryption key...")
                key = Fernet.generate_key()
                key_path.write_bytes(key)

            self._fernet = Fernet(key)
        except Exception as e:
            self._logger.error(f"Failed to set up encryption: {e}")
            raise

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.

        Args:
            password: Plain text password

        Returns:
            Base64-encoded encrypted password
        """
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

        encrypted = self._fernet.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_password(self, encrypted: str) -> str:
        """
        Decrypt a password.

        Args:
            encrypted: Base64-encoded encrypted password

        Returns:
            Plain text password
        """
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

        try:
            encrypted_bytes = base64.b64decode(encrypted)
            return self._fernet.decrypt(encrypted_bytes).decode()
        except (InvalidToken, Exception) as e:
            self._logger.error(f"Failed to decrypt password: {e}")
            return ""

    def load(self) -> AppConfig:
        """
        Load configuration from file.

        Returns:
            Loaded configuration
        """
        config_path = Path(self.CONFIG_FILE)

        if not config_path.exists():
            self._logger.debug("No configuration file found")
            return self._config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._config = AppConfig(
                email=data.get("email", ""),
                password_encrypted=data.get("password", ""),
                project=data.get("project", ""),
                headless=data.get("headless", True),
                export_excel=data.get("export_excel", True),
                export_csv=data.get("export_csv", False)
            )

            self._logger.info("Configuration loaded successfully")
            return self._config

        except (json.JSONDecodeError, IOError) as e:
            self._logger.error(f"Failed to load configuration: {e}")
            return self._config

    def save(self, config: AppConfig) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration to save

        Returns:
            True if successful
        """
        try:
            data = {
                "email": config.email,
                "password": config.password_encrypted,
                "project": config.project,
                "headless": config.headless,
                "export_excel": config.export_excel,
                "export_csv": config.export_csv
            }

            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._config = config
            self._logger.info("Configuration saved successfully")
            return True

        except IOError as e:
            self._logger.error(f"Failed to save configuration: {e}")
            return False


# =============================================================================
# WEB EXTRACTOR
# =============================================================================

class SeleniumEPlanExtractor:
    """
    Handles web automation for extracting data from EPLAN eVIEW.

    Features:
    - Microsoft SSO authentication
    - Project navigation
    - PLC diagram variable extraction
    - Network error handling with retries
    - Caching support
    """

    # CSS/XPath selectors for various elements
    EMAIL_SELECTORS: List[str] = [
        "input[type='email']",
        "input[name='loginfmt']",
        "input[id='i0116']",
        "input[id='email']",
        "input[placeholder*='Email']",
        "input[placeholder*='E-Mail']",
        "input[name='username']",
    ]

    PASSWORD_SELECTORS: List[str] = [
        "input[type='password']",
        "input[name='passwd']",
        "input[id='i0118']",
        "input[id='passwordInput']",
        "input[placeholder*='Password']",
        "input[placeholder*='Passwort']",
    ]

    SUBMIT_SELECTORS: List[str] = [
        "input[type='submit']",
        "input[id='idSIButton9']",
        "button[type='submit']",
        "input[value='Next']",
        "input[value='Weiter']",
        "input[value='Sign in']",
        "input[value='Anmelden']",
        "input[value='Yes']",
        "input[value='Ja']",
        "button[id='idSIButton9']",
    ]

    ADDRESS_PATTERN: str = r"\b([IQ]W?\d+\.\d+|[IQ]W\d+)\b"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        project_number: str,
        headless: bool = True,
        cache_manager: Optional[CacheManager] = None
    ) -> None:
        """
        Initialize the extractor.

        Args:
            base_url: EPLAN eVIEW base URL
            username: Microsoft email
            password: Microsoft password
            project_number: Project number to extract
            headless: Run browser in headless mode
            cache_manager: Optional cache manager instance
        """
        self.base_url = base_url
        self.username = username
        self.password = password
        self.project_number = project_number
        self.headless = headless
        self.cache = cache_manager or CacheManager()

        self._logger = get_logger()
        self._driver: Optional[webdriver.Chrome] = None
        self._address_regex = re.compile(self.ADDRESS_PATTERN)
        self._stop_requested = False

    @property
    def driver(self) -> Optional[webdriver.Chrome]:
        """Get the WebDriver instance."""
        return self._driver

    def request_stop(self) -> None:
        """Request the extraction to stop."""
        self._stop_requested = True
        self._logger.warning("Stop requested")

    def _check_stop(self) -> bool:
        """Check if stop was requested."""
        return self._stop_requested

    @retry_with_backoff(
        max_retries=MAX_RETRIES,
        exceptions=(WebDriverException, TimeoutException)
    )
    def setup_driver(self) -> None:
        """Initialize the Chrome WebDriver with retry support."""
        self._logger.info("Initializing Chrome WebDriver...")

        options = Options()

        if self.headless:
            options.add_argument("--headless")
            self._logger.info("Headless mode activated")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")

        # Disable images for faster loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        self._driver = webdriver.Chrome(options=options)
        self._driver.set_page_load_timeout(60)
        self._logger.success("WebDriver started successfully")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._driver:
            try:
                self._driver.quit()
                self._logger.info("WebDriver closed")
            except Exception as e:
                self._logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self._driver = None

    def _find_element_with_selectors(
        self,
        selectors: List[str],
        by: By = By.CSS_SELECTOR,
        timeout: int = 15
    ) -> Optional[WebElement]:
        """
        Find an element using multiple selectors.

        Args:
            selectors: List of CSS selectors to try
            by: Selenium By locator type
            timeout: Maximum time to wait

        Returns:
            Found element or None
        """
        if not self._driver:
            return None

        for attempt in range(timeout):
            if self._check_stop():
                return None

            for selector in selectors:
                try:
                    element = self._driver.find_element(by, selector)
                    if element.is_displayed():
                        self._logger.debug(f"Element found with selector: {selector}")
                        return element
                except NoSuchElementException:
                    continue

            time.sleep(1)
            self._logger.debug(f"Waiting for element... [{attempt + 1}/{timeout}]")

        return None

    def _click_element_safely(self, element: WebElement) -> bool:
        """
        Safely click an element with error handling.

        Args:
            element: Element to click

        Returns:
            True if click successful
        """
        try:
            if element.is_displayed() and element.is_enabled():
                element.click()
                return True
        except ElementClickInterceptedException:
            # Try JavaScript click
            try:
                self._driver.execute_script("arguments[0].click();", element)  # type: ignore
                return True
            except Exception:
                pass
        except StaleElementReferenceException:
            self._logger.warning("Element became stale")
        except Exception as e:
            self._logger.debug(f"Click failed: {e}")

        return False

    @retry_with_backoff(
        max_retries=2,
        exceptions=(WebDriverException, TimeoutException)
    )
    def click_on_login_with_microsoft(self) -> bool:
        """
        Navigate to login page and click Microsoft login button.

        Returns:
            True if successful
        """
        if not self._driver:
            return False

        self._logger.info(f"Navigating to: {self.base_url}")
        self._driver.get(self.base_url)

        for attempt in range(15):
            if self._check_stop():
                return False

            self._logger.info(f"Looking for Microsoft button... [{attempt + 1}/15]")

            # Find elements containing "Microsoft"
            elements = self._driver.find_elements(
                By.XPATH,
                "//*[contains(text(), 'Microsoft') or contains(text(), 'microsoft') "
                "or contains(@title, 'Microsoft')]"
            )

            for elem in elements:
                try:
                    if self._click_element_safely(elem):
                        time.sleep(1)
                        if "login.microsoft" in self._driver.current_url:
                            self._logger.success("Microsoft login page reached")
                            return True
                except Exception:
                    continue

            time.sleep(1)

        return False

    def login(self) -> bool:
        """
        Perform Microsoft SSO login.

        Returns:
            True if login successful
        """
        if not self._driver:
            return False

        try:
            # Email input
            self._logger.info("Waiting for email field...")
            email_field = self._find_element_with_selectors(self.EMAIL_SELECTORS)

            if not email_field:
                raise Exception("Email field not found")

            self._logger.info("Entering email...")
            email_field.clear()
            email_field.send_keys(self.username)

            # Click Next
            self._logger.info("Looking for 'Next' button...")
            next_button = self._find_element_with_selectors(self.SUBMIT_SELECTORS[:6])

            if next_button:
                self._click_element_safely(next_button)
            else:
                email_field.send_keys(Keys.RETURN)

            time.sleep(3)

            if self._check_stop():
                return False

            # Password input
            self._logger.info("Looking for password field...")
            password_field = self._find_element_with_selectors(self.PASSWORD_SELECTORS)

            if password_field:
                self._logger.info("Entering password...")
                password_field.clear()
                password_field.send_keys(self.password)

                # Click Sign In
                self._logger.info("Looking for 'Sign-In' button...")
                signin_button = self._find_element_with_selectors(self.SUBMIT_SELECTORS)

                if signin_button:
                    self._click_element_safely(signin_button)
                else:
                    password_field.send_keys(Keys.RETURN)
            else:
                self._logger.warning("Password field not found - SSO may be active")

            time.sleep(3)

            if self._check_stop():
                return False

            # Handle "Stay signed in?" dialog
            self._logger.info("Handling 'Stay signed in' dialog...")
            for attempt in range(10):
                stay_button = self._find_element_with_selectors(
                    self.SUBMIT_SELECTORS[-4:],
                    timeout=1
                )
                if stay_button and self._click_element_safely(stay_button):
                    self._logger.debug("'Stay logged in' confirmed")
                    break
                time.sleep(1)

            time.sleep(5)

            # Verify login success
            current_url = self._driver.current_url
            if "login" not in current_url.lower() and (
                self.base_url in current_url or "eview" in current_url.lower()
            ):
                self._logger.success("Microsoft SSO login successful!")
                return True
            else:
                self._logger.warning(f"Login status unclear. URL: {current_url}")
                return True  # Continue anyway

        except Exception as e:
            self._logger.error(f"Login error: {e}")
            return False

    def open_project(self) -> bool:
        """
        Open the specified project.

        Returns:
            True if project opened successfully
        """
        if not self._driver:
            return False

        self._logger.info(f"Opening project: {self.project_number}")

        try:
            time.sleep(3)

            # Find project in list
            project_selectors = [
                f"//td[contains(text(), '{self.project_number}')]",
                f"//span[contains(text(), '{self.project_number}')]",
                f"//div[contains(text(), '{self.project_number}')]",
                f"//a[contains(text(), '{self.project_number}')]",
                f"//tr[contains(., '{self.project_number}')]",
                f"//*[text()='{self.project_number}']",
            ]

            project_element = None
            for xpath in project_selectors:
                try:
                    elements = self._driver.find_elements(By.XPATH, xpath)
                    if elements:
                        project_element = elements[0]
                        self._logger.success(f"Project found with: {xpath}")
                        break
                except Exception:
                    continue

            if not project_element:
                raise Exception(f"Project '{self.project_number}' not found")

            # Click on project
            self._click_element_safely(project_element)
            time.sleep(0.5)

            # Find and click Open button
            self._logger.info("Looking for 'Open' button...")
            buttons = self._driver.find_elements(By.TAG_NAME, "button")

            for btn in buttons:
                try:
                    btn_text = btn.text.strip().lower()
                    if "open" in btn_text or "öffnen" in btn_text:
                        if self._click_element_safely(btn):
                            self._logger.success("'Open' button clicked")
                            break
                except Exception:
                    continue

            time.sleep(5)

            self._logger.success(f"Project '{self.project_number}' opened")
            return True

        except Exception as e:
            self._logger.error(f"Error opening project: {e}")
            return False

    def switch_to_list_view(self) -> bool:
        """
        Switch from diagram view to list view.

        Returns:
            True if successful
        """
        if not self._driver:
            return False

        try:
            # Click three-dots menu button
            self._logger.info("Looking for menu button...")
            buttons = self._driver.find_elements(By.TAG_NAME, "eplan-icon-button")

            for btn in buttons:
                try:
                    if not btn.is_displayed():
                        continue
                    data_t = btn.get_attribute("data-t") or ""
                    if "ev-btn-page-more" in data_t:
                        if "fl-pop-up-open" not in (btn.get_attribute("class") or ""):
                            self._click_element_safely(btn)
                            self._logger.info("Menu button clicked")
                        break
                except Exception:
                    continue

            time.sleep(0.5)

            # Click "List" option
            dropdown_items = self._driver.find_elements(
                By.TAG_NAME, "eplan-dropdown-item"
            )

            for item in dropdown_items:
                try:
                    if not item.is_displayed():
                        continue
                    data_name = item.get_attribute("data-name") or ""
                    if "ev-page-list-view-btn" in data_name:
                        self._click_element_safely(item)
                        self._logger.success("Switched to list view")
                        return True
                except Exception:
                    continue

            return True

        except Exception as e:
            self._logger.error(f"Error switching to list view: {e}")
            return False

    def extract_current_plc_diagram_page(self) -> ExtractedData:
        """
        Extract variables from the current PLC diagram page.

        Returns:
            Dictionary of address -> variable name mappings
        """
        extracted: ExtractedData = {}

        if not self._driver:
            return extracted

        try:
            bodies = self._driver.find_elements(By.CLASS_NAME, "ev-svg-cad-content")

            for body in bodies:
                if body.get_attribute("id") != "page":
                    continue

                if not body.find_elements(By.TAG_NAME, "text"):
                    continue

                rows = body.find_elements(By.TAG_NAME, "g")

                for row in rows:
                    # Check if row contains an address
                    text_objects = row.find_elements(By.TAG_NAME, "text")
                    has_address = any(
                        self._address_regex.search(t.text)
                        for t in text_objects
                        if t.text
                    )

                    if not has_address:
                        continue

                    # Extract address and variable name
                    key: Optional[str] = None
                    value: Optional[str] = None

                    for text_obj in text_objects:
                        text = text_obj.text
                        if not text or text.startswith("=") or text.startswith(":"):
                            continue

                        if re.match(self.ADDRESS_PATTERN, text):
                            key = text
                        else:
                            value = text

                    if key and value and key not in extracted:
                        extracted[key] = value

            if extracted:
                self._logger.success(f"Extracted {len(extracted)} variables")

        except Exception as e:
            self._logger.error(f"Extraction error: {e}")

        return extracted

    def extract_variables(self) -> bool:
        """
        Extract variables from all PLC diagram pages.

        Returns:
            True if extraction successful
        """
        if not self._driver:
            return False

        try:
            scroll_container = self._driver.find_element(
                By.CSS_SELECTOR, "cdk-virtual-scroll-viewport"
            )
        except NoSuchElementException:
            self._logger.error("Scroll container not found")
            return False

        # Scroll to top
        self._driver.execute_script(
            "arguments[0].scrollTop = 0", scroll_container
        )
        time.sleep(0.5)

        all_extracted: List[ExtractedData] = []
        extracted_pages: List[str] = []
        last_height = -1

        while not self._check_stop():
            visible_pages = self._driver.find_elements(
                By.TAG_NAME, "pv-page-list-item"
            )

            for i in range(len(visible_pages)):
                if self._check_stop():
                    break

                try:
                    # Re-fetch to avoid stale references
                    page = self._driver.find_elements(
                        By.TAG_NAME, "pv-page-list-item"
                    )[i]

                    # Check if it's a PLC diagram
                    is_plc = any(
                        "PLC-Diagram" in div.text
                        for div in page.find_elements(By.TAG_NAME, "div")
                    )

                    if not is_plc:
                        continue

                    page_name = page.get_attribute("data-name")
                    if not page_name or page_name in extracted_pages:
                        continue

                    # Check cache first
                    cached_data = self.cache.get(self.project_number, page_name)
                    if cached_data:
                        self._logger.info(f"Using cached data for: {page_name}")
                        all_extracted.append(cached_data)
                        extracted_pages.append(page_name)
                        continue

                    self._logger.info(f"Extracting page: {page_name}")
                    extracted_pages.append(page_name)

                    time.sleep(0.5)
                    page.click()
                    time.sleep(0.5)

                    data = self.extract_current_plc_diagram_page()
                    all_extracted.append(data)

                    # Cache the data
                    if data:
                        self.cache.set(self.project_number, page_name, data)

                    self._logger.success(f"Extracted: {page_name}")

                except StaleElementReferenceException:
                    self._logger.warning("Element stale, continuing...")
                except ElementClickInterceptedException:
                    self._logger.warning("Click intercepted, skipping...")
                except Exception as e:
                    self._logger.debug(f"Error processing page: {e}")

            # Scroll down
            self._driver.execute_script(
                "arguments[0].scrollTop += 400", scroll_container
            )
            time.sleep(0.2)

            new_height = self._driver.execute_script(
                "return arguments[0].scrollTop", scroll_container
            )

            if new_height == last_height:
                break
            last_height = new_height

        # Export results
        self._logger.info(f"Total pages extracted: {len(extracted_pages)}")

        flat_data: List[List[str]] = []
        for data in all_extracted:
            for key, value in data.items():
                flat_data.append([key, value])

        flat_data.sort(key=lambda x: x[0])

        output_file = f"{self.project_number} IO-List.xlsx"
        df = pandas.DataFrame(flat_data, columns=["Address", "Variable"])
        df.to_excel(output_file, index=False)

        self._logger.success(f"Results saved to: {output_file}")
        return True

    def run_extraction(self) -> bool:
        """
        Run the complete extraction workflow.

        Returns:
            True if extraction completed successfully
        """
        self._stop_requested = False

        try:
            self.setup_driver()

            if self._check_stop():
                return False

            if not self.click_on_login_with_microsoft():
                raise Exception("Failed to click Microsoft login button")

            if self._check_stop():
                return False

            if not self.login():
                raise Exception("Failed to login")

            if self._check_stop():
                return False

            if not self.open_project():
                raise Exception("Failed to open project")

            if self._check_stop():
                return False

            if not self.switch_to_list_view():
                raise Exception("Failed to switch to list view")

            if self._check_stop():
                return False

            if not self.extract_variables():
                raise Exception("Failed to extract variables")

            return True

        except Exception as e:
            self._logger.error(f"Extraction failed: {e}")
            raise
        finally:
            self.cleanup()


# =============================================================================
# GUI APPLICATION
# =============================================================================

class EPlanExtractorGUI:
    """
    Tkinter GUI for the EPLAN eVIEW Text Extractor.

    Provides a user-friendly interface for:
    - Entering credentials
    - Configuring extraction options
    - Viewing extraction progress
    - Managing cache
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the GUI.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title(f"EPLAN eVIEW Text Extractor v{VERSION}")

        if DEBUG:
            self.root.geometry("900x700")
        else:
            self.root.geometry("500x350")

        self._logger = get_logger()
        self._config_manager = ConfigManager()
        self._cache_manager = CacheManager()
        self._extractor: Optional[SeleniumEPlanExtractor] = None
        self._is_running = False

        # Variables
        self._username_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._project_var = tk.StringVar()
        self._headless_var = tk.BooleanVar(value=True)
        self._export_excel_var = tk.BooleanVar(value=True)
        self._export_csv_var = tk.BooleanVar(value=False)
        self._status_var = tk.StringVar(value="Ready")

        self._setup_ui()
        self._load_config()

        # Register logger callback
        self._logger.add_callback(self._log_callback)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")

        # Configuration section
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)

        # Email
        ttk.Label(config_frame, text="Microsoft Email:").grid(
            row=0, column=0, sticky="w", padx=5, pady=2
        )
        ttk.Entry(
            config_frame, textvariable=self._username_var, width=50
        ).grid(row=0, column=1, padx=5, pady=2)

        # Password
        ttk.Label(config_frame, text="Microsoft Password:").grid(
            row=1, column=0, sticky="w", padx=5, pady=2
        )
        ttk.Entry(
            config_frame, textvariable=self._password_var, width=50, show="*"
        ).grid(row=1, column=1, padx=5, pady=2)

        # Project number
        ttk.Label(config_frame, text="Project Number:").grid(
            row=2, column=0, sticky="w", padx=5, pady=2
        )
        ttk.Entry(
            config_frame, textvariable=self._project_var, width=50
        ).grid(row=2, column=1, padx=5, pady=2)

        # Options section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Checkbutton(
            options_frame, text="Export to Excel", variable=self._export_excel_var
        ).grid(row=0, column=0, sticky="w")

        ttk.Checkbutton(
            options_frame, text="Export to CSV", variable=self._export_csv_var
        ).grid(row=1, column=0, sticky="w")

        if DEBUG:
            ttk.Checkbutton(
                options_frame, text="Browser in Background (Headless)",
                variable=self._headless_var
            ).grid(row=0, column=1, sticky="w", padx=20)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        self._start_button = ttk.Button(
            button_frame, text="Start Extraction", command=self._start_extraction
        )
        self._start_button.grid(row=0, column=0, padx=5)

        self._stop_button = ttk.Button(
            button_frame, text="Stop", command=self._stop_extraction, state="disabled"
        )
        self._stop_button.grid(row=0, column=1, padx=5)

        if DEBUG:
            ttk.Button(
                button_frame, text="Clear Log", command=self._clear_log
            ).grid(row=0, column=2, padx=5)

            ttk.Button(
                button_frame, text="Clear Cache", command=self._clear_cache
            ).grid(row=0, column=3, padx=5)

        # Log area (debug mode)
        if DEBUG:
            log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
            log_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=5)

            self._log_text = scrolledtext.ScrolledText(
                log_frame, height=20, width=100
            )
            self._log_text.grid(row=0, column=0, sticky="nsew")

            log_frame.columnconfigure(0, weight=1)
            log_frame.rowconfigure(0, weight=1)

        # Status bar
        ttk.Label(
            main_frame, textvariable=self._status_var, relief="sunken"
        ).grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _log_callback(self, message: str, level: str) -> None:
        """Callback for logger to update GUI log."""
        if not DEBUG:
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"

        try:
            self._log_text.insert("end", log_message)
            self._log_text.see("end")
            self.root.update_idletasks()
        except Exception:
            pass

    def _clear_log(self) -> None:
        """Clear the log display."""
        if DEBUG:
            self._log_text.delete("1.0", "end")

    def _clear_cache(self) -> None:
        """Clear the extraction cache."""
        count = self._cache_manager.clear()
        messagebox.showinfo("Cache Cleared", f"Cleared {count} cache entries")

    def _load_config(self) -> None:
        """Load saved configuration."""
        config = self._config_manager.load()

        self._username_var.set(config.email)
        self._project_var.set(config.project)
        self._headless_var.set(config.headless)
        self._export_excel_var.set(config.export_excel)
        self._export_csv_var.set(config.export_csv)

        # Decrypt password
        if config.password_encrypted:
            password = self._config_manager.decrypt_password(config.password_encrypted)
            self._password_var.set(password)

    def _save_config(self) -> None:
        """Save current configuration."""
        config = AppConfig(
            email=self._username_var.get(),
            password_encrypted=self._config_manager.encrypt_password(
                self._password_var.get()
            ),
            project=self._project_var.get(),
            headless=self._headless_var.get(),
            export_excel=self._export_excel_var.get(),
            export_csv=self._export_csv_var.get()
        )
        self._config_manager.save(config)

    def _start_extraction(self) -> None:
        """Start the extraction process."""
        if self._is_running:
            messagebox.showwarning("Warning", "Extraction is already running!")
            return

        # Validate input
        if not all([
            self._username_var.get(),
            self._password_var.get(),
            self._project_var.get()
        ]):
            messagebox.showerror("Error", "Please fill in all required fields.")
            return

        # Save configuration
        self._save_config()

        # Update UI
        self._start_button.config(state="disabled")
        self._stop_button.config(state="normal")
        self._status_var.set("Extraction running...")

        # Start extraction thread
        self._is_running = True
        thread = threading.Thread(target=self._run_extraction, daemon=True)
        thread.start()

    def _stop_extraction(self) -> None:
        """Stop the extraction process."""
        self._is_running = False
        self._status_var.set("Stopping...")

        if self._extractor:
            self._extractor.request_stop()

        self._start_button.config(state="normal")
        self._stop_button.config(state="disabled")
        self._status_var.set("Extraction stopped")

    def _run_extraction(self) -> None:
        """Run the extraction in a background thread."""
        try:
            self._logger.info("=" * 50)
            self._logger.info("Starting EPLAN eVIEW extraction")
            self._logger.info(f"Server: {BASE_URL}")
            self._logger.info(f"Project: {self._project_var.get()}")
            self._logger.info("=" * 50)

            self._extractor = SeleniumEPlanExtractor(
                base_url=BASE_URL,
                username=self._username_var.get(),
                password=self._password_var.get(),
                project_number=self._project_var.get(),
                headless=self._headless_var.get(),
                cache_manager=self._cache_manager
            )

            if self._extractor.run_extraction() and self._is_running:
                self._logger.success("Extraction completed successfully!")
                self._status_var.set("Extraction completed")
                messagebox.showinfo("Success", "Extraction completed successfully!")
            else:
                self._logger.warning("Extraction cancelled or failed")
                self._status_var.set("Extraction cancelled")

        except Exception as e:
            self._logger.error(f"Extraction error: {e}")
            self._status_var.set("Extraction failed")
            messagebox.showerror("Error", f"Extraction failed:\n{str(e)}")

        finally:
            self._is_running = False
            self._extractor = None
            self._start_button.config(state="normal")
            self._stop_button.config(state="disabled")


# =============================================================================
# UNIT TESTS
# =============================================================================

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


class TestConfigManager(unittest.TestCase):
    """Tests for the ConfigManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Backup existing files
        self.config_backup = None
        self.key_backup = None

        if Path(ConfigManager.CONFIG_FILE).exists():
            self.config_backup = Path(ConfigManager.CONFIG_FILE).read_text()
        if Path(ConfigManager.KEY_FILE).exists():
            self.key_backup = Path(ConfigManager.KEY_FILE).read_bytes()

    def tearDown(self) -> None:
        """Restore backed up files."""
        if self.config_backup:
            Path(ConfigManager.CONFIG_FILE).write_text(self.config_backup)
        if self.key_backup:
            Path(ConfigManager.KEY_FILE).write_bytes(self.key_backup)

    def test_encrypt_decrypt_password(self) -> None:
        """Test password encryption and decryption."""
        manager = ConfigManager()
        password = "TestPassword123!"

        encrypted = manager.encrypt_password(password)
        self.assertNotEqual(encrypted, password)

        decrypted = manager.decrypt_password(encrypted)
        self.assertEqual(decrypted, password)


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


def run_tests() -> bool:
    """
    Run all unit tests.

    Returns:
        True if all tests passed
    """
    print(f"\nEPLAN Extractor v{VERSION} - Running Unit Tests\n")
    print("=" * 60)

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


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def print_from_link(url: str) -> None:
    """
    Extract and print text content from a URL.

    Args:
        url: URL to fetch and parse
    """
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.extract()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)

    print(text)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main() -> None:
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description=f"EPLAN eVIEW Text Extractor v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python "TextExtractor 2.py"           Run the GUI application
  python "TextExtractor 2.py" --test    Run unit tests
  python "TextExtractor 2.py" --version Show version information
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
    global DEBUG
    if args.debug:
        DEBUG = True

    # Handle --test flag
    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    # Handle --clear-cache flag
    if args.clear_cache:
        cache = CacheManager()
        count = cache.clear()
        print(f"Cleared {count} cache entries")
        sys.exit(0)

    # Check for GUI availability
    if not GUI_AVAILABLE:
        print("Error: tkinter is not available.")
        print("Please install python3-tk or run with --test for unit tests.")
        sys.exit(1)

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Run GUI application
    root = tk.Tk()
    app = EPlanExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
