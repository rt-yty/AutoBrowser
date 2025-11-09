from typing import Tuple

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from browser.lifecycle import BrowserLifecycle


class BrowserInteractor:
    """Handles browser interactions with elements."""

    def __init__(self, lifecycle: BrowserLifecycle):
        self.lifecycle = lifecycle

    @staticmethod
    def validate_selector(selector: str) -> Tuple[bool, str]:
        """Validate a Playwright selector before use.

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

        error = BrowserInteractor._check_invalid_commas(selector)
        if error:
            return False, error

        if ",," in selector:
            return False, "Selector contains double comma - invalid syntax"

        if selector.count(">>") > 0 and selector.count(",") > 0:
            return False, "Selector mixes >> and comma syntax - use one style consistently"

        return True, ""

    @staticmethod
    def _check_invalid_commas(selector: str) -> str:
        """Check if selector has invalid commas (outside quotes/brackets).

        Args:
            selector: Selector to check

        Returns:
            Error message if invalid comma found, empty string otherwise
        """
        in_quotes = False
        in_brackets = 0
        quote_char = None

        for i, char in enumerate(selector):
            if BrowserInteractor._is_quote_char(char, i, selector, in_quotes, quote_char):
                in_quotes, quote_char = BrowserInteractor._toggle_quotes(
                    char, in_quotes, quote_char
                )
            elif char == "[" and not in_quotes:
                in_brackets += 1
            elif char == "]" and not in_quotes:
                in_brackets = max(0, in_brackets - 1)
            elif char == "," and not in_quotes and in_brackets == 0:
                return "Selector contains comma outside quotes/brackets - use a single specific selector instead of multiple fragments"

        return ""

    @staticmethod
    def _is_quote_char(
        char: str, index: int, selector: str, in_quotes: bool, quote_char: str
    ) -> bool:
        """Check if character is a quote that should toggle quote mode.

        Args:
            char: Current character
            index: Character index
            selector: Full selector string
            in_quotes: Whether currently in quotes
            quote_char: Current quote character if in quotes

        Returns:
            True if this is a quote toggle character
        """
        if char not in ('"', "'"):
            return False

        is_not_escaped = index == 0 or selector[index - 1] != "\\"

        return is_not_escaped and (not in_quotes or char == quote_char)

    @staticmethod
    def _toggle_quotes(char: str, in_quotes: bool, quote_char: str) -> Tuple[bool, str]:
        """Toggle quote tracking state.

        Args:
            char: Quote character
            in_quotes: Current quote state
            quote_char: Current quote character

        Returns:
            Tuple of (new_in_quotes, new_quote_char)
        """
        if not in_quotes:
            return True, char
        elif char == quote_char:
            return False, None
        return in_quotes, quote_char

    def click(self, selector: str, timeout: int = 10000) -> None:
        """Click an element with automatic fallback strategies.

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
        if not selector or not selector.strip():
            raise Exception(
                "Empty selector provided! You MUST extract the selector from find_element_by_text response. "
                "Look for the line starting with 'Selector:' and copy the text after it. "
                "Example: If response says 'Selector: [data-autobrowser-find-id=\"5\"]', "
                "use click('[data-autobrowser-find-id=\"5\"]', description) - NOT click(selector=, description)!"
            )

        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        page = self.lifecycle.page

        try:
            page.click(selector, timeout=timeout)
            return
        except (PlaywrightTimeoutError, PlaywrightError):
            pass

        try:
            page.wait_for_selector(selector, state="attached", timeout=timeout)
            page.click(selector, force=True, timeout=timeout)
            return
        except (PlaywrightTimeoutError, PlaywrightError):
            pass

        try:
            page.wait_for_selector(selector, state="attached", timeout=timeout)
            page.eval_on_selector(selector, "element => element.click()")
            return
        except PlaywrightTimeoutError:
            raise Exception(
                f"Click timeout: element '{selector}' not found within {timeout}ms. "
                "The element might not exist on the page. "
                "Try using find_element_by_text() first to discover the correct selector."
            )
        except PlaywrightError as e:
            raise Exception(
                f"Click failed on '{selector}' after trying all methods (normal, force, JavaScript). "
                f"The selector might be incorrect. Original error: {str(e)}"
            )

    def type_text(self, selector: str, text: str, timeout: int = 10000) -> None:
        """Type text into an element.

        Args:
            selector: Single Playwright selector for input field
            text: Text to type
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or typing fails
        """
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            element = self.lifecycle.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )
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
        """Scroll the page.

        Args:
            direction: Direction to scroll ('down', 'up', 'page_down', 'page_up', 'bottom', 'top')
            amount: Amount in pixels for 'up' and 'down' directions

        Raises:
            Exception: If scroll fails
        """
        try:
            page = self.lifecycle.page
            if direction == "down":
                page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "page_down":
                page.keyboard.press("PageDown")
            elif direction == "page_up":
                page.keyboard.press("PageUp")
            elif direction == "bottom":
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                page.evaluate("window.scrollTo(0, 0)")
            else:
                raise Exception(f"Invalid scroll direction: {direction}")
        except PlaywrightError as e:
            raise Exception(f"Scroll failed: {str(e)}")

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
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            self.lifecycle.page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except PlaywrightTimeoutError:
            return False
        except PlaywrightError as e:
            raise Exception(f"Wait for selector failed: {str(e)}")

    def press_key(self, key: str) -> None:
        """Press a keyboard key.

        Args:
            key: The key to press. Supported keys:
                 'Enter', 'Escape', 'Tab', 'Space',
                 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'

        Raises:
            Exception: If key is invalid or press fails
        """
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
            self.lifecycle.page.keyboard.press(key)
        except PlaywrightError as e:
            raise Exception(f"Failed to press key '{key}': {str(e)}")

    def hover(self, selector: str, timeout: int = 10000) -> None:
        """Hover over an element to reveal dropdown menus, tooltips, or hidden content.

        Args:
            selector: Single Playwright selector for the element to hover over
            timeout: Timeout in milliseconds

        Raises:
            Exception: If selector is invalid or hover fails
        """
        is_valid, error_msg = self.validate_selector(selector)
        if not is_valid:
            raise Exception(f"Invalid selector: {error_msg}")

        try:
            element = self.lifecycle.page.wait_for_selector(
                selector, timeout=timeout, state="visible"
            )
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

    def take_screenshot(self, path: str) -> None:
        """Take a screenshot of the current page.

        Args:
            path: File path to save screenshot
        """
        self.lifecycle.page.screenshot(path=path, full_page=True)
