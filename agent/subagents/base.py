from typing import List, Dict, Any

from anthropic.types import MessageParam

from llm.claude_client import ClaudeClient
from agent.tools import ToolRegistry
from utils.logger import logger


class SubAgent:
    """Base class for specialized sub-agents."""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        claude_client: ClaudeClient,
        tools: ToolRegistry,
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.claude_client = claude_client
        self.tools = tools
        self.conversation: List[MessageParam] = []

    def execute(self, subtask: str, max_steps: int = 10) -> str:
        """
        Execute a subtask using the sub-agent's specialized capabilities.

        Args:
            subtask: Description of the subtask to accomplish
            max_steps: Maximum number of steps to take

        Returns:
            Result summary from the sub-agent
        """
        logger.subagent_start(self.name, subtask)

        self.conversation = [
            {
                "role": "user",
                "content": f"Subtask: {subtask}\n\nPlease accomplish this subtask using your specialized capabilities.",
            }
        ]

        for step in range(max_steps):
            response = self.claude_client.send_message(
                messages=self.conversation,
                system_prompt=self.system_prompt,
                tools=self.tools.get_anthropic_tools(),
            )

            self.conversation.append({"role": "assistant", "content": response.content})

            tool_calls = self.claude_client.extract_tool_calls(response)

            if not tool_calls:
                text = self.claude_client.extract_text(response)
                logger.subagent_complete(self.name, text)
                return text

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]

                logger.action(self.name, tool_name, tool_input)

                result = self.tools.execute_tool(tool_name, **tool_input)
                logger.result(result)

                tool_result_msg = self.claude_client.create_tool_result_message(
                    tool_call["id"], result
                )
                self.conversation.append(tool_result_msg)

        logger.warning(f"{self.name} reached max steps ({max_steps})")
        return f"Sub-agent {self.name} reached maximum steps without completing the subtask."
