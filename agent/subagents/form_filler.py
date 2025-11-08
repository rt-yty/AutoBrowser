"""FormFiller sub-agent for form interaction tasks."""

from agent.subagents.base import SubAgent
from llm.claude_client import ClaudeClient
from llm.prompts import get_subagent_prompt
from agent.tools import ToolRegistry, Tool


class FormFiller(SubAgent):
    """Specialized sub-agent for form filling tasks."""

    def __init__(self, claude_client: ClaudeClient, browser, context_manager):
        # Create tool registry with form-specific tools
        tools = self._create_tools(browser, context_manager)

        super().__init__(
            name="FormFiller",
            system_prompt=get_subagent_prompt("form_filler"),
            claude_client=claude_client,
            tools=tools,
        )

    def _create_tools(self, browser, context_manager) -> ToolRegistry:
        """Create tools specific to form filling."""
        from agent.tools import (
            create_type_text_tool,
            create_click_tool,
            create_wait_tool,
            create_page_overview_tool,
            create_element_details_tool,
        )

        registry = ToolRegistry()

        # Use factory functions for common tools
        registry.register(create_type_text_tool(browser))
        registry.register(
            create_click_tool(
                browser,
                "Click on form elements (buttons, checkboxes, radio buttons, dropdowns)."
            )
        )
        registry.register(create_wait_tool(browser))
        registry.register(create_page_overview_tool(context_manager))
        registry.register(create_element_details_tool(context_manager))

        # FormFiller-specific tool: press_key for Enter and Tab
        registry.register(
            Tool(
                name="press_key",
                description="Press a keyboard key. Use Enter to submit forms, Tab to navigate between fields.",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "Key to press. Options: 'Enter' (submit form), 'Tab' (next field)",
                    }
                },
                handler=lambda key: self._press_key_handler(browser, key),
            )
        )

        return registry

    def _press_key_handler(self, browser, key: str) -> str:
        """Handle pressing a keyboard key with validation."""
        # FormFiller only needs Enter and Tab
        allowed_keys = {"Enter", "Tab"}
        if key not in allowed_keys:
            return f"FormFiller only supports keys: {', '.join(allowed_keys)}"
        try:
            browser.press_key(key)
            return f"Successfully pressed key: {key}"
        except Exception as e:
            return f"Failed to press key: {str(e)}"
