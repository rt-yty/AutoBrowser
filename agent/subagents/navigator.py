from agent.subagents.base import SubAgent
from llm.claude_client import ClaudeClient
from llm.prompts import get_subagent_prompt
from agent.tools import ToolRegistry, Tool


class Navigator(SubAgent):
    """Specialized sub-agent for navigation tasks."""

    def __init__(self, claude_client: ClaudeClient, browser, context_manager):
        tools = self._create_tools(browser, context_manager)

        super().__init__(
            name="Navigator",
            system_prompt=get_subagent_prompt("navigator"),
            claude_client=claude_client,
            tools=tools,
        )

    def _create_tools(self, browser, context_manager) -> ToolRegistry:
        """Create tools specific to navigation."""
        from agent.tools import (
            create_navigation_tool,
            create_click_tool,
            create_hover_tool,
            create_scroll_tool,
            create_wait_tool,
            create_page_overview_tool,
            create_element_details_tool,
        )

        registry = ToolRegistry()

        registry.register(create_navigation_tool(browser))
        registry.register(
            create_click_tool(
                browser,
                "Click on a navigation element (link, button, menu item)."
            )
        )
        registry.register(
            create_hover_tool(
                browser,
                "Hover over navigation element to reveal dropdown menus."
            )
        )
        registry.register(create_scroll_tool(browser))
        registry.register(create_wait_tool(browser))
        registry.register(create_page_overview_tool(context_manager))
        registry.register(create_element_details_tool(context_manager))

        registry.register(
            Tool(
                name="press_key",
                description="Press Escape to close modals or overlays that block navigation.",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "Key to press. Only 'Escape' is supported for Navigator.",
                    }
                },
                handler=lambda key: self._press_key_handler(browser, key),
            )
        )

        return registry

    def _press_key_handler(self, browser, key: str) -> str:
        """Handle pressing a keyboard key with validation."""
        if key != "Escape":
            return "Navigator only supports 'Escape' key for closing modals/overlays"
        try:
            browser.press_key(key)
            return f"Successfully pressed key: {key}"
        except Exception as e:
            return f"Failed to press key: {str(e)}"
