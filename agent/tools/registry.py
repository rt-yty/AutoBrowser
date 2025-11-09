"""Tool registry - base classes for agent tools."""

from typing import Any, Callable, Dict, List

from anthropic.types import ToolParam


class Tool:
    """Represents a tool that the agent can use."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler

    def to_anthropic_tool(self) -> ToolParam:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": [
                    k for k, v in self.parameters.items() if v.get("required", False)
                ],
            },
        }


class ToolRegistry:
    """Registry of available tools for the agent."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name."""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name]

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())

    def get_anthropic_tools(self) -> List[ToolParam]:
        """Get all tools in Anthropic format."""
        return [tool.to_anthropic_tool() for tool in self.tools.values()]

    def execute_tool(self, name: str, **kwargs) -> str:
        """Execute a tool with given arguments."""
        tool = self.get_tool(name)
        try:
            result = tool.handler(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing tool {name}: {str(e)}"
