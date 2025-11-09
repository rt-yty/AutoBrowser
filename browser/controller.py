"""Browser controller using Playwright."""

from typing import Optional, Tuple

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    sync_playwright,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError,
)

from config import BrowserConfig


class BrowserController:
    """Controls browser automation using Playwright."""

    def __init__(self, config: BrowserConfig):
        self.config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_started: bool = False  # Track if browser is running
        self._current_frame_selector: Optional[str] = None  # Track iframe context

    @staticmethod
    def validate_selector(selector: str) -> Tuple[bool, str]:
        """
        Validate a Playwright selector before use.

        Args:
            selector: The selector string to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, "")
            If invalid: (False, "error description")
        """
        if not selector or not selector.strip():
            return False, "Selector cannot be empty"

        selector = selector.strip()

        # Check for comma-separated selectors (not valid as single selector)
        # Allow commas inside quotes or square brackets
        in_quotes = False
        in_brackets = 0
        quote_char = None

        for i, char in enumerate(selector):
            if char in ('"', "'") and (i == 0 or selector[i - 1] != "\\"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == "[" and not in_quotes:
                in_brackets += 1
            elif char == "]" and not in_quotes:
                in_brackets -= 1
            elif char == "," and not in_quotes and in_brackets == 0:
                return False, "Selector contains comma outside quotes/brackets - use a single specific selector instead of multiple fragments"

        # Check for double commas
        if ",," in selector:
            return False, "Selector contains double comma - invalid syntax"

        # Check for suspicious patterns
        if selector.count(">>") > 0 and selector.count(",") > 0:
            return False, "Selector mixes >> and comma syntax - use one style consistently"

        return True, ""

    def _kill_existing_browser_processes(self) -> None:
        """
        Kill any existing browser processes using the same user data directory.

        This ensures only one browser instance is running at a time.
        """
        import subprocess
        import platform
        from utils.logger import logger

        try:
            system = platform.system()
            user_data_path = str(self.config.user_data_dir)

            if system == "Darwin":  # macOS
                # Find and kill processes using the user data directory
                # Use pgrep to find PIDs first, then kill them
                try:
                    # Find WebKit processes with our user data path
                    result = subprocess.run(
                        ["pgrep", "-f", user_data_path],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split('\n')
                        logger.info(f"Found {len(pids)} existing browser processes to kill")
                        for pid in pids:
                            if pid:
                                try:
                                    subprocess.run(["kill", "-9", pid], timeout=2)
                                except Exception:
                                    pass
                except Exception as e:
                    logger.debug(f"Could not kill existing processes: {e}")

            elif system == "Linux":
                # Kill browser processes on Linux
                try:
                    result = subprocess.run(
                        ["pgrep", "-f", user_data_path],
                        capture_output=True,
                        timeout=5,
                        text=True
                    )
                    if result.stdout:
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid:
                                subprocess.run(["kill", "-9", pid], timeout=2)
                except Exception:
                    pass

            elif system == "Windows":
                # Kill browser processes on Windows
                subprocess.run(
                    ["taskkill", "/F", "/IM", "WebKitWebProcess.exe"],
                    capture_output=True,
                    timeout=5
                )
                subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    capture_output=True,
                    timeout=5
                )
        except Exception as e:
            # If killing processes fails, continue anyway
            # The new browser will handle conflicts
            logger.debug(f"Process cleanup completed with some errors: {e}")

    @staticmethod
    def _is_safe_url(url: str) -> bool:
        """
        Check if URL has a safe protocol.

        Args:
            url: URL to validate

        Returns:
            True if safe (http/https or no protocol), False otherwise
        """
        url_lower = url.lower().strip()

        # Allow URLs without protocol (will be prefixed with https://)
        if "://" not in url_lower:
            return True

        # Whitelist: only http and https
        safe_protocols = ["http://", "https://"]

        # Blacklist: dangerous protocols
        dangerous_protocols = [
            "javascript:",
            "data:",
            "file:",
            "ftp:",
            "about:",
            "blob:",
            "vbscript:",
        ]

        # Check blacklist first (more specific)
        for dangerous in dangerous_protocols:
            if url_lower.startswith(dangerous):
                return False

        # Check whitelist
        for safe in safe_protocols:
            if url_lower.startswith(safe):
                return True

        # Unknown protocol - reject
        return False

    def start(self) -> Page:
        """Start the browser with persistent context (saves cookies/sessions)."""
        from utils.logger import logger

        # Check if browser is already running using explicit flag
        if self._is_started and self._page is not None and self._context is not None:
            logger.info("Browser already running, reusing existing instance")
            return self._page

        logger.info("Starting new browser instance...")

        # Ensure user data directory exists
        self.config.user_data_dir.mkdir(parents=True, exist_ok=True)

        # Kill any existing browser processes to ensure clean start
        self._kill_existing_browser_processes()

        # Start Playwright (only if not already started)
        if self._playwright is None:
            self._playwright = sync_playwright().start()
            logger.info("Playwright engine started")

        # Launch browser with persistent context
        # This automatically saves cookies, localStorage, and session data
        # between browser restarts
        if self.config.browser_type == "webkit":
            self._context = self._playwright.webkit.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        elif self.config.browser_type == "chromium":
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        elif self.config.browser_type == "firefox":
            self._context = self._playwright.firefox.launch_persistent_context(
                user_data_dir=str(self.config.user_data_dir),
                headless=self.config.headless,
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
            )
        else:
            raise ValueError(f"Unknown browser type: {self.config.browser_type}")

        # Note: launch_persistent_context returns a context, not a browser
        # The browser is managed internally
        self._browser = None  # Not needed with persistent context

        # Get or create page
        if len(self._context.pages) > 0:
            # Reuse existing page from previous session (first page is active)
            self._page = self._context.pages[0]
        else:
            # Create new page
            self._page = self._context.new_page()

        # Mark browser as started
        self._is_started = True
        logger.info(f"Browser started successfully (PID: {self._context.pages[0] if self._context.pages else 'unknown'})")

        return self._page

    def stop(self) -> None:
        """Stop the browser and clean up resources (saves session state)."""
        from utils.logger import logger

        if not self._is_started:
            logger.info("Browser not running, nothing to stop")
            return

        logger.info("Stopping browser...")

        # Don't close page explicitly - let context handle it
        # This preserves the session state better
        if self._context:
            try:
                self._context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")

        # Note: self._browser is None when using persistent context
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")

        # Reset all state
        self._page = None
        self._context = None
        self._playwright = None
        self._is_started = False
        logger.info("Browser stopped successfully")

    @property
    def page(self) -> Page:
        """Get the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    def navigate_to(self, url: str, timeout: int = 30000) -> None:
        """
        Navigate to a URL with protocol validation.

        Raises:
            Exception: If URL has unsafe protocol or navigation fails
        """
        # Validate URL protocol before navigation
        if not self._is_safe_url(url):
            raise Exception(
                f"Unsafe URL protocol detected: {url}. "
                "Only http:// and https:// protocols are allowed."
            )

        # Add https:// if no protocol specified
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        try:
            self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            raise Exception(f"Navigation timeout: page took longer than {timeout}ms to load")
        except PlaywrightError as e:
            raise Exception(f"Navigation failed: {str(e)}")

    def click(self, selector: str, timeout: int = 10000) -> None:
        """
        Click an element with automatic fallback strategies.

        Tries multiple click methods in order:
        1. Normal Playwright click
        2. Force click (ignores actionability checks)
        3. JavaScript click (direct DOM manipulation)

        Args:
            selector: Single Playwright selector (e.g., "button:has-text('Submit')")
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or all click attempts fail
        """
        # Check for empty selector first
        if not selector or not selector.strip():
            raise Exception(
                "Empty selector provided! You MUST extract the selector from find_element_by_text response. "
                "Look for the line starting with 'Selector:' and copy the text after it. "
                "Example: If response says 'Selector: [data-autobrowser-find-id=\"5\"]', "
                "use click('[data-autobrowser-find-id=\"5\"]', description) - NOT click(selector=, description)!"
            )

        # Validate selector format
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        # Strategy 1: Try normal click first
        try:
            self.page.click(selector, timeout=timeout)
            return  # Success!
        except PlaywrightTimeoutError:
            # Element not found or not clickable - will try other methods
            pass
        except PlaywrightError as e:
            error_str = str(e)
            # Check if it's an interception error - will try force click
            if "intercepts pointer events" not in error_str and "intercepted" not in error_str:
                # Some other error - try other strategies
                pass

        # Strategy 2: Try force click (ignores overlays and visibility checks)
        try:
            # Wait for element to exist
            self.page.wait_for_selector(selector, state="attached", timeout=timeout)
            # Force click
            self.page.click(selector, force=True, timeout=timeout)
            return  # Success!
        except (PlaywrightTimeoutError, PlaywrightError):
            # Force click failed, try JavaScript
            pass

        # Strategy 3: Try JavaScript click (most aggressive)
        try:
            # Wait for element to exist
            self.page.wait_for_selector(selector, state="attached", timeout=timeout)
            # JavaScript click
            self.page.eval_on_selector(
                selector,
                "element => element.click()"
            )
            return  # Success!
        except PlaywrightTimeoutError:
            raise Exception(
                f"Click timeout: element '{selector}' not found within {timeout}ms. "
                "The element might not exist on the page. "
                "Try using find_element_by_text() first to discover the correct selector."
            )
        except PlaywrightError as e:
            error_str = str(e)
            raise Exception(
                f"Click failed on '{selector}' after trying all methods (normal, force, JavaScript). "
                f"The selector might be incorrect. Original error: {error_str}"
            )

    def type_text(self, selector: str, text: str, timeout: int = 10000) -> None:
        """
        Type text into an element.

        Args:
            selector: Single Playwright selector for input field
            text: Text to type
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or typing fails with detailed error
        """
        # Validate selector first
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            element = self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                element.fill(text)
            else:
                raise Exception(f"Element '{selector}' not found within {timeout}ms")
        except PlaywrightTimeoutError:
            raise Exception(
                f"Type timeout: input element '{selector}' not found or not visible within {timeout}ms. "
                "The element might not exist, might be hidden, or you might need a more specific selector."
            )
        except PlaywrightError as e:
            raise Exception(f"Type text failed on '{selector}': {str(e)}")

    def scroll(self, direction: str = "down", amount: int = 500) -> None:
        """
        Scroll the page.

        Args:
            direction: Direction to scroll ('down', 'up', 'page_down', 'page_up', 'bottom', 'top')
            amount: Amount in pixels for 'up' and 'down' directions

        Raises:
            Exception: If scroll fails
        """
        try:
            if direction == "down":
                self.page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                self.page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "page_down":
                self.page.keyboard.press("PageDown")
            elif direction == "page_up":
                self.page.keyboard.press("PageUp")
            elif direction == "bottom":
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                self.page.evaluate("window.scrollTo(0, 0)")
            else:
                raise Exception(f"Invalid scroll direction: {direction}")
        except PlaywrightError as e:
            raise Exception(f"Scroll failed: {str(e)}")

    def wait_for_selector(
        self, selector: str, timeout: int = 10000, state: str = "visible"
    ) -> bool:
        """
        Wait for an element to appear.

        Args:
            selector: Single Playwright selector
            timeout: Timeout in milliseconds
            state: Element state to wait for

        Returns:
            True if element appeared, False if timeout

        Raises:
            Exception: If selector is invalid
        """
        # Validate selector first
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            self.page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except PlaywrightTimeoutError:
            return False
        except PlaywrightError as e:
            raise Exception(f"Wait for selector failed: {str(e)}")

    def get_current_url(self) -> str:
        """Get the current page URL."""
        return self.page.url

    def get_title(self) -> str:
        """Get the page title."""
        return self.page.title()

    def take_screenshot(self, path: str) -> None:
        """Take a screenshot of the current page."""
        self.page.screenshot(path=path, full_page=True)

    def press_key(self, key: str) -> None:
        """
        Press a keyboard key.

        Args:
            key: The key to press. Supported keys:
                 'Enter', 'Escape', 'Tab', 'Space',
                 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'

        Raises:
            Exception: If key is invalid or press fails
        """
        # Validate key
        supported_keys = {
            "Enter",
            "Escape",
            "Tab",
            "Space",
            "ArrowUp",
            "ArrowDown",
            "ArrowLeft",
            "ArrowRight",
            "Backspace",
            "Delete",
            "Home",
            "End",
            "PageUp",
            "PageDown",
        }

        if key not in supported_keys:
            raise Exception(
                f"Invalid key: '{key}'. Supported keys: {', '.join(sorted(supported_keys))}"
            )

        try:
            self.page.keyboard.press(key)
        except PlaywrightError as e:
            raise Exception(f"Failed to press key '{key}': {str(e)}")

    def hover(self, selector: str, timeout: int = 10000) -> None:
        """
        Hover over an element to reveal dropdown menus, tooltips, or hidden content.

        Args:
            selector: Single Playwright selector for the element to hover over
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or hover fails
        """
        # Validate selector first
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            # Wait for element to be visible before hovering
            element = self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                element.hover(timeout=timeout)
            else:
                raise Exception(f"Element '{selector}' not found within {timeout}ms")
        except PlaywrightTimeoutError:
            raise Exception(
                f"Hover timeout: element '{selector}' not found or not visible within {timeout}ms. "
                "The element might not exist or might be hidden."
            )
        except PlaywrightError as e:
            raise Exception(f"Hover failed on '{selector}': {str(e)}")

    def list_tabs(self) -> list[dict]:
        """
        Get a list of all open tabs with their information.

        Returns:
            List of dicts with: index, title, url, is_active
        """
        tabs = []
        for i, page in enumerate(self._context.pages):
            tabs.append({
                "index": i,
                "title": page.title(),
                "url": page.url,
                "is_active": page == self._page
            })
        return tabs

    def switch_to_tab(self, tab_index: int) -> None:
        """
        Switch to a different tab by index.

        Args:
            tab_index: Zero-based index of the tab to switch to

        Raises:
            Exception: If tab index is invalid
        """
        pages = self._context.pages
        if tab_index < 0 or tab_index >= len(pages):
            raise Exception(
                f"Invalid tab index: {tab_index}. "
                f"Available tabs: 0-{len(pages)-1}"
            )

        self._page = pages[tab_index]
        # Bring the tab to front
        try:
            self._page.bring_to_front()
        except Exception:
            # If bring_to_front fails, still switch the internal reference
            pass

    def close_tab(self, tab_index: int) -> None:
        """
        Close a tab by index.

        Args:
            tab_index: Zero-based index of the tab to close

        Raises:
            Exception: If tab index is invalid or trying to close the only tab
        """
        pages = self._context.pages

        if len(pages) == 1:
            raise Exception(
                "Cannot close the only open tab. "
                "At least one tab must remain open."
            )

        if tab_index < 0 or tab_index >= len(pages):
            raise Exception(
                f"Invalid tab index: {tab_index}. "
                f"Available tabs: 0-{len(pages)-1}"
            )

        page_to_close = pages[tab_index]

        # If closing the active tab, switch to another tab first
        if page_to_close == self._page:
            # Switch to the next tab, or previous if this is the last tab
            new_index = tab_index + 1 if tab_index < len(pages) - 1 else tab_index - 1
            self._page = pages[new_index]
            try:
                self._page.bring_to_front()
            except Exception:
                pass

        # Close the tab
        try:
            page_to_close.close()
        except Exception as e:
            raise Exception(f"Failed to close tab {tab_index}: {str(e)}")

    def get_active_tab_index(self) -> int:
        """
        Get the index of the currently active tab.

        Returns:
            Zero-based index of the active tab, or -1 if not found
        """
        for i, page in enumerate(self._context.pages):
            if page == self._page:
                return i
        return -1

    def switch_to_frame(self, selector: str) -> None:
        """
        Switch context to an iframe on the page.

        After calling this, all subsequent actions (click, type, etc.) will operate
        within the iframe until switch_to_main_content() is called.

        Args:
            selector: CSS selector for the iframe element (e.g., "iframe#payment-form")

        Raises:
            Exception: If selector is invalid or iframe not found
        """
        # Validate selector
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        # Check if iframe exists
        try:
            self.page.wait_for_selector(selector, timeout=5000, state="attached")
        except PlaywrightTimeoutError:
            raise Exception(f"Iframe with selector '{selector}' not found on page")
        except PlaywrightError as e:
            raise Exception(f"Failed to find iframe: {str(e)}")

        # Store the frame selector for use in subsequent operations
        self._current_frame_selector = selector

    def switch_to_main_content(self) -> None:
        """
        Switch context back to the main page content (exit iframe context).

        After calling this, all subsequent actions will operate on the main page.
        """
        self._current_frame_selector = None

    def _get_frame_or_page(self):
        """
        Internal helper to get the current frame locator or page.

        Returns the appropriate context for operations based on whether
        we're currently in an iframe or the main page.
        """
        if self._current_frame_selector:
            # Return frame locator
            return self.page.frame_locator(self._current_frame_selector)
        else:
            # Return main page
            return self.page
