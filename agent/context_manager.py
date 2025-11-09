import logging
from typing import Any, Dict, List

from browser.controller import BrowserController
from browser.dom_utils import DOMExtractor

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4


class ContextManager:
    """Manages page context extraction and simplification for the agent."""

    def __init__(self, browser: BrowserController, token_limit: int = 3000):
        self.browser = browser
        self.token_limit = token_limit
        self.extractor = DOMExtractor(browser.page)

    def get_current_context(self) -> Dict[str, Any]:
        """Get the current page context in a format suitable for the agent.

        Uses hybrid approach: accessibility tree + on-demand HTML.

        Returns:
            Dict with url, title, overview, estimated_tokens, was_truncated
        """
        overview = self.extractor.get_page_overview()

        estimated_tokens = len(overview) // CHARS_PER_TOKEN
        was_truncated = False

        if estimated_tokens > self.token_limit:
            overview, was_truncated = self._truncate_overview(overview)
            new_tokens = len(overview) // CHARS_PER_TOKEN
            logger.warning(
                f"Context truncated: {estimated_tokens} tokens → {new_tokens} tokens"
            )
            estimated_tokens = new_tokens

        return {
            "url": self.browser.get_current_url(),
            "title": self.browser.get_title(),
            "overview": overview,
            "estimated_tokens": estimated_tokens,
            "was_truncated": was_truncated,
        }

    def _truncate_overview(self, overview: str) -> tuple[str, bool]:
        """Truncate overview to fit within token limit.

        Args:
            overview: Original overview text

        Returns:
            Tuple of (truncated_overview, was_truncated)
        """
        lines = overview.split("\n")
        truncated_lines = []
        current_tokens = 0

        for line in lines:
            line_tokens = len(line) // CHARS_PER_TOKEN
            if current_tokens + line_tokens > self.token_limit:
                truncated_lines.append(
                    f"... (truncated, {len(lines) - len(truncated_lines)} lines omitted)"
                )
                break
            truncated_lines.append(line)
            current_tokens += line_tokens

        return "\n".join(truncated_lines), True

    def get_element_details(self, selector: str) -> str:
        """Get detailed information about a specific element."""
        details = self.extractor.get_element_details(selector)
        return details or "Element not found or error occurred"

    def find_elements_by_text(self, text: str, role: str = None) -> list[dict]:
        """
        Find elements containing specific text.

        Returns a list of dicts, each containing:
        - selector: CSS selector to use for clicking
        - text: Element text content
        - tag: HTML tag name
        - context: Parent element context
        - is_visible: Whether element is visible
        """
        return self.extractor.find_elements_by_text(text, role)
