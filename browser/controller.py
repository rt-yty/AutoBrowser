from typing import List, Dict, Tuple

from playwright.sync_api import Page

from config import BrowserConfig
from browser.lifecycle import BrowserLifecycle
from browser.navigator import BrowserNavigator
from browser.interactor import BrowserInteractor
from browser.tab_manager import TabManager
from browser.frame_manager import FrameManager


class BrowserController:
    """Controls browser automation using Playwright.

    This class serves as the main entry point for browser operations,
    delegating to specialized components for specific functionality.
    """

    def __init__(self, config: BrowserConfig):
        """Initialize browser controller with configuration.

        Args:
            config: Browser configuration
        """
        self.config = config

        self.lifecycle = BrowserLifecycle(config)
        self.navigator = BrowserNavigator(self.lifecycle)
        self.interactor = BrowserInteractor(self.lifecycle)
        self.tab_manager = TabManager(self.lifecycle)
        self.frame_manager = FrameManager(self.lifecycle, self.interactor)


    def start(self) -> Page:
        """Start the browser with persistent context (saves cookies/sessions).

        Returns:
            The active browser page
        """
        return self.lifecycle.start()

    def stop(self) -> None:
        """Stop the browser and clean up resources (saves session state)."""
        self.lifecycle.stop()

    @property
    def page(self) -> Page:
        """Get the current page.

        Returns:
            Current browser page

        Raises:
            RuntimeError: If browser not started
        """
        return self.lifecycle.page


    def navigate_to(self, url: str, timeout: int = 30000) -> None:
        """Navigate to a URL with protocol validation.

        Args:
            url: URL to navigate to
            timeout: Timeout in milliseconds (default 30000)

        Raises:
            Exception: If URL has unsafe protocol or navigation fails
        """
        self.navigator.navigate_to(url, timeout)

    def get_current_url(self) -> str:
        """Get the current page URL.

        Returns:
            Current URL as string
        """
        return self.navigator.get_current_url()

    def get_title(self) -> str:
        """Get the page title.

        Returns:
            Page title as string
        """
        return self.navigator.get_title()


    @staticmethod
    def validate_selector(selector: str) -> Tuple[bool, str]:
        """Validate a Playwright selector before use.

        Args:
            selector: The selector string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return BrowserInteractor.validate_selector(selector)

    def click(self, selector: str, timeout: int = 10000) -> None:
        """Click an element with automatic fallback strategies.

        Args:
            selector: Single Playwright selector
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or all click attempts fail
        """
        self.interactor.click(selector, timeout)

    def type_text(self, selector: str, text: str, timeout: int = 10000) -> None:
        """Type text into an element.

        Args:
            selector: Single Playwright selector for input field
            text: Text to type
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or typing fails
        """
        self.interactor.type_text(selector, text, timeout)

    def scroll(self, direction: str = "down", amount: int = 500) -> None:
        """Scroll the page.

        Args:
            direction: Direction to scroll
            amount: Amount in pixels for 'up' and 'down' directions

        Raises:
            Exception: If scroll fails
        """
        self.interactor.scroll(direction, amount)

    def wait_for_selector(
        self, selector: str, timeout: int = 10000, state: str = "visible"
    ) -> bool:
        """Wait for an element to appear.

        Args:
            selector: Single Playwright selector
            timeout: Timeout in milliseconds
            state: Element state to wait for

        Returns:
            True if element appeared, False if timeout

        Raises:
            Exception: If selector is invalid
        """
        return self.interactor.wait_for_selector(selector, timeout, state)

    def press_key(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: The key to press

        Raises:
            Exception: If key is invalid or press fails
        """
        self.interactor.press_key(key)

    def hover(self, selector: str, timeout: int = 10000) -> None:
        """Hover over an element to reveal dropdown menus, tooltips, or hidden content.

        Args:
            selector: Single Playwright selector for the element to hover over
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or hover fails
        """
        self.interactor.hover(selector, timeout)

    def take_screenshot(self, path: str) -> None:
        """Take a screenshot of the current page.

        Args:
            path: File path to save screenshot
        """
        self.interactor.take_screenshot(path)


    def list_tabs(self) -> List[Dict]:
        """Get a list of all open tabs with their information.

        Returns:
            List of dicts with: index, title, url, is_active
        """
        return self.tab_manager.list_tabs()

    def switch_to_tab(self, tab_index: int) -> None:
        """Switch to a different tab by index.

        Args:
            tab_index: Zero-based index of the tab to switch to

        Raises:
            Exception: If tab index is invalid
        """
        self.tab_manager.switch_to_tab(tab_index)

    def close_tab(self, tab_index: int) -> None:
        """Close a tab by index.

        Args:
            tab_index: Zero-based index of the tab to close

        Raises:
            Exception: If tab index is invalid or trying to close the only tab
        """
        self.tab_manager.close_tab(tab_index)

    def get_active_tab_index(self) -> int:
        """Get the index of the currently active tab.

        Returns:
            Zero-based index of the active tab, or -1 if not found
        """
        return self.tab_manager.get_active_tab_index()


    def switch_to_frame(self, selector: str) -> None:
        """Switch context to an iframe on the page.

        Args:
            selector: CSS selector for the iframe element

        Raises:
            Exception: If selector is invalid or iframe not found
        """
        self.frame_manager.switch_to_frame(selector)

    def switch_to_main_content(self) -> None:
        """Switch context back to the main page content (exit iframe context)."""
        self.frame_manager.switch_to_main_content()
