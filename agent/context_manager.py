"""Context management for the agent."""

import logging
from typing import Dict, Any

from browser.dom_utils import DOMExtractor
from browser.controller import BrowserController

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages page context extraction and simplification for the agent."""

    def __init__(self, browser: BrowserController, token_limit: int = 3000):
        self.browser = browser
        self.token_limit = token_limit
        self.extractor = DOMExtractor(browser.page)

    def get_current_context(self) -> Dict[str, Any]:
        """
        Get the current page context in a format suitable for the agent.
        Uses hybrid approach: accessibility tree + on-demand HTML.
        """
        # Get page overview using accessibility tree
        overview = self.extractor.get_page_overview()

        # Estimate token count (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(overview) // 4
        was_truncated = False

        # If overview is too long, truncate intelligently
        if estimated_tokens > self.token_limit:
            was_truncated = True
            original_token_count = estimated_tokens
            lines = overview.split("\n")
            truncated_lines = []
            current_tokens = 0

            for line in lines:
                line_tokens = len(line) // 4
                if current_tokens + line_tokens > self.token_limit:
                    truncated_lines.append(
                        f"... (truncated, {len(lines) - len(truncated_lines)} lines omitted)"
                    )
                    break
                truncated_lines.append(line)
                current_tokens += line_tokens

            overview = "\n".join(truncated_lines)
            logger.warning(
                f"Context truncated: {original_token_count} tokens → {len(overview) // 4} tokens"
            )

        return {
            "url": self.browser.get_current_url(),
            "title": self.browser.get_title(),
            "overview": overview,
            "estimated_tokens": len(overview) // 4,
            "was_truncated": was_truncated,
        }

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
