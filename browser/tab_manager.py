from typing import List, Dict

from browser.lifecycle import BrowserLifecycle


class TabManager:
    """Handles browser tab management."""

    def __init__(self, lifecycle: BrowserLifecycle):
        self.lifecycle = lifecycle

    def list_tabs(self) -> List[Dict]:
        """Get a list of all open tabs with their information.

        Returns:
            List of dicts with: index, title, url, is_active
        """
        tabs = []
        context = self.lifecycle.context
        current_page = self.lifecycle.page

        for i, page in enumerate(context.pages):
            tabs.append(
                {
                    "index": i,
                    "title": page.title(),
                    "url": page.url,
                    "is_active": page == current_page,
                }
            )
        return tabs

    def switch_to_tab(self, tab_index: int) -> None:
        """Switch to a different tab by index.

        Args:
            tab_index: Zero-based index of the tab to switch to

        Raises:
            Exception: If tab index is invalid
        """
        context = self.lifecycle.context
        pages = context.pages

        if tab_index < 0 or tab_index >= len(pages):
            raise Exception(
                f"Invalid tab index: {tab_index}. " f"Available tabs: 0-{len(pages)-1}"
            )

        self.lifecycle._page = pages[tab_index]

        try:
            self.lifecycle._page.bring_to_front()
        except Exception:
            pass

    def close_tab(self, tab_index: int) -> None:
        """Close a tab by index.

        Args:
            tab_index: Zero-based index of the tab to close

        Raises:
            Exception: If tab index is invalid or trying to close the only tab
        """
        context = self.lifecycle.context
        pages = context.pages

        if len(pages) == 1:
            raise Exception(
                "Cannot close the only open tab. " "At least one tab must remain open."
            )

        if tab_index < 0 or tab_index >= len(pages):
            raise Exception(
                f"Invalid tab index: {tab_index}. " f"Available tabs: 0-{len(pages)-1}"
            )

        page_to_close = pages[tab_index]

        if page_to_close == self.lifecycle.page:
            new_index = tab_index + 1 if tab_index < len(pages) - 1 else tab_index - 1
            self.lifecycle._page = pages[new_index]
            try:
                self.lifecycle._page.bring_to_front()
            except Exception:
                pass

        try:
            page_to_close.close()
        except Exception as e:
            raise Exception(f"Failed to close tab {tab_index}: {str(e)}")

    def get_active_tab_index(self) -> int:
        """Get the index of the currently active tab.

        Returns:
            Zero-based index of the active tab, or -1 if not found
        """
        context = self.lifecycle.context
        current_page = self.lifecycle.page

        for i, page in enumerate(context.pages):
            if page == current_page:
                return i
        return -1
