"""
Web automation for extracting data from EPLAN eVIEW.
"""

from __future__ import annotations

import re
import time
from typing import List, Optional

import pandas
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

from ..constants import ExtractedData, MAX_RETRIES
from ..utils.logging import get_logger
from ..utils.retry import retry_with_backoff
from .cache import CacheManager


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
