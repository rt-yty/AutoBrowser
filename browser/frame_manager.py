from typing import Optional

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from browser.lifecycle import BrowserLifecycle
from browser.interactor import BrowserInteractor


class FrameManager:
    """Handles iframe context switching."""

    def __init__(self, lifecycle: BrowserLifecycle, interactor: BrowserInteractor):
        self.lifecycle = lifecycle
        self.interactor = interactor
        self._current_frame_selector: Optional[str] = None

    def switch_to_frame(self, selector: str) -> None:
        """Switch context to an iframe on the page.

        After calling this, all subsequent actions (click, type, etc.) will operate
        within the iframe until switch_to_main_content() is called.

        Args:
            selector: CSS selector for the iframe element (e.g., "iframe#payment-form")

        Raises:
            Exception: If selector is invalid or iframe not found
        """
        is_valid, error_msg = self.interactor.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            self.lifecycle.page.wait_for_selector(selector, timeout=5000, state="attached")
        except PlaywrightTimeoutError:
            raise Exception(f"Iframe with selector '{selector}' not found on page")
        except PlaywrightError as e:
            raise Exception(f"Failed to find iframe: {str(e)}")

        self._current_frame_selector = selector

    def switch_to_main_content(self) -> None:
        """Switch context back to the main page content (exit iframe context).

        After calling this, all subsequent actions will operate on the main page.
        """
        self._current_frame_selector = None

    @property
    def current_frame_selector(self) -> Optional[str]:
        """Get the current frame selector, if any.

        Returns:
            Frame selector string, or None if on main content
        """
        return self._current_frame_selector
