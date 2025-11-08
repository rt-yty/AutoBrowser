"""Claude API client with tool calling support."""

from typing import Any, Dict, List, Optional

import anthropic
from anthropic.types import MessageParam, ToolParam, ToolUseBlock, TextBlock


class ClaudeClient:
    """Client for interacting with Claude API with tool calling."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def send_message(
        self,
        messages: List[MessageParam],
        system_prompt: str,
        tools: Optional[List[ToolParam]] = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """
        Send a message to Claude and get a response.

        Args:
            messages: Conversation history
            system_prompt: System prompt defining agent behavior
            tools: Available tools for the agent to use
            max_tokens: Maximum tokens in response

        Returns:
            Claude's response message
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)
        return response

    def extract_tool_calls(
        self, response: anthropic.types.Message
    ) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Claude's response.

        Returns:
            List of tool calls with name and input
        """
        tool_calls = []

        for block in response.content:
            if isinstance(block, ToolUseBlock):
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return tool_calls

    def extract_text(self, response: anthropic.types.Message) -> str:
        """Extract text content from Claude's response."""
        text_parts = []

        for block in response.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)

        return "\n".join(text_parts)

    def create_tool_result_message(
        self, tool_use_id: str, tool_result: str
    ) -> Dict[str, Any]:
        """Create a message containing tool results to send back to Claude."""
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": tool_result,
                }
            ],
        }
