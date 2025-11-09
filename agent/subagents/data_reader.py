from agent.subagents.base import SubAgent
from llm.claude_client import ClaudeClient
from llm.prompts import get_subagent_prompt
from agent.tools import ToolRegistry, Tool


class DataReader(SubAgent):
    """Specialized sub-agent for data reading and extraction tasks."""

    def __init__(self, claude_client: ClaudeClient, browser, context_manager):
        tools = self._create_tools(browser, context_manager)

        super().__init__(
            name="DataReader",
            system_prompt=get_subagent_prompt("data_reader"),
            claude_client=claude_client,
            tools=tools,
        )

    def _create_tools(self, browser, context_manager) -> ToolRegistry:
        """Create tools specific to data reading."""
        from agent.tools import (
            create_scroll_tool,
            create_wait_tool,
            create_page_overview_tool,
            create_element_details_tool,
        )

        registry = ToolRegistry()

        registry.register(create_page_overview_tool(context_manager))
        registry.register(create_element_details_tool(context_manager))
        registry.register(create_scroll_tool(browser))
        registry.register(create_wait_tool(browser))

        return registry
