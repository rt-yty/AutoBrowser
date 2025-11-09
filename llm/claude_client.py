import time
from typing import Any, Dict, List, Optional

import anthropic
from anthropic.types import MessageParam, ToolParam, ToolUseBlock, TextBlock


class ClaudeClient:
    """Client for interacting with Claude API with tool calling."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        timeout: float = 300.0,
    ):
        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.model = model
        self.max_retries = max_retries

    def send_message(
        self,
        messages: List[MessageParam],
        system_prompt: str,
        tools: Optional[List[ToolParam]] = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """
        Send a message to Claude and get a response with retry logic.

        Args:
            messages: Conversation history
            system_prompt: System prompt defining agent behavior
            tools: Available tools for the agent to use
            max_tokens: Maximum tokens in response

        Returns:
            Claude's response message

        Raises:
            anthropic.APIError: If all retries fail
        """
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(**kwargs)
                return response
            except (
                anthropic.APITimeoutError,
                anthropic.APIConnectionError,
            ) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"\n⚠️  Network error (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                    print(f"   Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"\n❌ All {self.max_retries} retry attempts failed.")
                    raise

        if last_error:
            raise last_error
        raise anthropic.APIError("Unknown error in send_message")

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
