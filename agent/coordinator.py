from typing import Dict, List, Optional

from anthropic.types import MessageParam

from agent.context_manager import ContextManager
from agent.tools import create_coordinator_tools
from browser.controller import BrowserController
from config import AgentConfig
from llm.claude_client import ClaudeClient
from llm.prompts import get_coordinator_prompt
from utils.logger import logger

MAX_NO_TOOL_RETRIES = 3
MAX_CONSECUTIVE_FAILURES = 3

CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED:"
HUMAN_INTERVENTION_REQUIRED = "HUMAN_INTERVENTION_REQUIRED:"
TASK_COMPLETE_PREFIX = "TASK_COMPLETE:"


class Coordinator:
    """Main coordinator agent that orchestrates task execution."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        browser: BrowserController,
        context_manager: ContextManager,
        subagents: Dict,
        config: AgentConfig,
    ):
        self.claude_client = claude_client
        self.browser = browser
        self.context_manager = context_manager
        self.subagents = subagents
        self.config = config

        self.tools = create_coordinator_tools(browser, context_manager, subagents)

        self.conversation: List[MessageParam] = []

        self.task_complete = False
        self.task_summary: Optional[str] = None

        self.consecutive_failures = 0

    def execute_task(self, task: str) -> str:
        """Execute a high-level task.

        Args:
            task: Natural language description of the task

        Returns:
            Summary of task completion
        """
        logger.task(task)
        self._initialize_conversation(task)

        iteration = 0
        no_tool_retry_count = 0

        while iteration < self.config.max_iterations and not self.task_complete:
            iteration += 1

            response, reasoning = self._get_agent_response()

            tool_calls = self.claude_client.extract_tool_calls(response)

            if not tool_calls:
                if self.conversation and self.conversation[-1]["role"] == "assistant":
                    self.conversation.pop()

                no_tool_retry_count = self._handle_no_tool_calls(no_tool_retry_count)
                if no_tool_retry_count >= MAX_NO_TOOL_RETRIES:
                    break
                continue

            no_tool_retry_count = 0

            if not self._execute_tool_calls(tool_calls, reasoning):
                break

        return self._finalize_task()

    def _initialize_conversation(self, task: str) -> None:
        """Initialize conversation with task and initial context."""
        initial_context = self.context_manager.get_current_context()
        self.conversation = [
            {
                "role": "user",
                "content": f"""Task: {task}

Current Page Context:
{initial_context['overview']}

Please help me accomplish this task. Start by analyzing what's needed and take appropriate actions.""",
            }
        ]

    def _get_agent_response(self) -> tuple:
        """Get response from Claude agent.

        Returns:
            Tuple of (response, reasoning)
        """
        response = self.claude_client.send_message(
            messages=self.conversation,
            system_prompt=get_coordinator_prompt(),
            tools=self.tools.get_anthropic_tools(),
        )

        self.conversation.append({"role": "assistant", "content": response.content})

        reasoning = self.claude_client.extract_text(response)
        if reasoning:
            logger.info(f"Reasoning: {reasoning}")

        return response, reasoning

    def _handle_no_tool_calls(self, retry_count: int) -> int:
        """Handle case when agent doesn't provide tool calls.

        Args:
            retry_count: Current retry count

        Returns:
            Updated retry count
        """
        retry_count += 1
        logger.warning(
            f"No tool calls in response. Agent may be stuck. "
            f"(Retry {retry_count}/{MAX_NO_TOOL_RETRIES})"
        )

        if retry_count >= MAX_NO_TOOL_RETRIES:
            logger.error("Agent failed to provide tool calls after multiple retries.")
            return retry_count

        hint_msg = self._get_retry_hint_message(retry_count)
        self.conversation.append({"role": "user", "content": hint_msg})
        logger.info("Sending retry hint to agent...")

        return retry_count

    def _execute_tool_calls(self, tool_calls: List, reasoning: str) -> bool:
        """Execute all tool calls from agent response.

        Args:
            tool_calls: List of tool calls to execute
            reasoning: Agent's reasoning text

        Returns:
            True to continue loop, False to break (task completed)
        """
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["input"]

            if tool_name == "task_complete":
                self.task_complete = True
                self.task_summary = tool_input.get("summary", "Task completed")
                logger.success(self.task_summary)
                return False

            logger.action("Coordinator", tool_name, tool_input, reasoning)
            result = self.tools.execute_tool(tool_name, **tool_input)

            result = self._handle_special_results(result)

            success = not result.startswith("Error") and not result.startswith("Failed")
            logger.result(result, success)

            tool_result_msg = self.claude_client.create_tool_result_message(
                tool_call["id"], result
            )
            self.conversation.append(tool_result_msg)

            self._track_failures(success)
            self._update_context_if_needed(tool_name, result)

        return True

    def _handle_special_results(self, result: str) -> str:
        """Handle special result types (confirmations, human intervention).

        Args:
            result: Tool execution result

        Returns:
            Processed result string
        """
        if result.startswith(CONFIRMATION_REQUIRED):
            return self._handle_confirmation_request(result)

        if result.startswith(HUMAN_INTERVENTION_REQUIRED):
            return self._handle_human_intervention(result)

        return result

    def _handle_confirmation_request(self, result: str) -> str:
        """Handle confirmation requests for destructive actions."""
        parts = result.split(":", 2)
        risk_level = parts[1] if len(parts) > 1 else "unknown"
        action_description = parts[2] if len(parts) > 2 else "Unknown action"

        confirmed = self._request_user_confirmation(action_description, risk_level)
        if confirmed:
            return "User confirmed the action. You may proceed with the next step."
        else:
            logger.warning(f"User declined destructive action: {action_description}")
            return "User DECLINED the action. Do NOT proceed. The task cannot be completed as requested."

    def _handle_human_intervention(self, result: str) -> str:
        """Handle human intervention requests."""
        description = result.replace(HUMAN_INTERVENTION_REQUIRED, "").strip()
        self._request_human_intervention(description)

        try:
            updated_context = self.context_manager.get_current_context()
            logger.info(f"Context updated: {self._format_context_summary(updated_context)}")

            return f"""Human intervention completed. User has manually handled the required action in the browser.

Updated page context:
{updated_context['overview']}

You can now continue with the task."""
        except Exception as e:
            logger.error(f"Failed to get updated context after intervention: {str(e)}")
            return "Human intervention completed. User has manually handled the required action in the browser."

    def _track_failures(self, success: bool) -> None:
        """Track consecutive failures and provide hints if needed."""
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            logger.info(
                f"Consecutive failures: {self.consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}"
            )

            if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.warning(
                    "Multiple consecutive failures detected. Consider requesting human assistance."
                )
                self._add_failure_recovery_hint()

    def _add_failure_recovery_hint(self) -> None:
        """Add hint message for failure recovery."""
        help_hint = {
            "role": "user",
            "content": """You've encountered multiple consecutive failures. If you're stuck or unable to proceed:
1. Try a different approach or tool
2. Use get_page_overview to reassess the situation
3. If the issue persists, consider using request_human_help to get assistance

What would you like to do?""",
        }
        self.conversation.append(help_hint)
        self.consecutive_failures = 0

    def _update_context_if_needed(self, tool_name: str, result: str) -> None:
        """Update page context if the action might have changed the page."""
        page_changing_tools = {"click", "navigate_to", "scroll", "type_text", "press_key"}

        if tool_name not in page_changing_tools:
            return

        try:
            updated_context = self.context_manager.get_current_context()
            context_msg = {
                "role": "user",
                "content": f"""Updated page context after {tool_name}:
{updated_context['overview']}""",
            }
            self.conversation.append(context_msg)
            logger.info(f"Context updated: {self._format_context_summary(updated_context)}")
        except Exception as e:
            logger.error(f"Failed to get updated context: {str(e)}")


    def _finalize_task(self) -> str:
        """Finalize task execution and return summary."""
        if not self.task_complete:
            failure_reason = f"Agent reached maximum iterations ({self.config.max_iterations}) without completing the task."
            logger.failure(failure_reason)
            return failure_reason

        return self.task_summary or "Task completed"

    def _format_context_summary(self, context: Dict) -> str:
        """Format context as a minimal summary for terminal logging."""
        url = context.get('url', 'Unknown')
        title = context.get('title', 'Unknown')

        url = url[:47] + "..." if len(url) > 50 else url
        title = title[:27] + "..." if len(title) > 30 else title

        overview = context.get('overview', '')
        element_counts = self._count_elements(overview)

        if element_counts:
            counts_str = ', '.join(
                f"{count} {typ.lower()}{'s' if count != 1 else ''}"
                for typ, count in element_counts.items() if count > 0
            )
            return f"{url} | {counts_str}"

        return f"{url} | {title}"

    def _count_elements(self, overview: str) -> Dict[str, int]:
        """Count elements by type from overview text."""
        element_counts = {}
        current_type = None

        for line in overview.split('\n'):
            if line.strip().endswith('S:') and line.strip().isupper():
                current_type = line.strip().rstrip('S:')
                element_counts[current_type] = 0
            elif current_type:
                if '... and' in line and 'more' in line:
                    try:
                        extra = int(line.split('... and')[1].split('more')[0].strip())
                        element_counts[current_type] += extra
                    except:
                        pass
                elif line.strip().startswith('-'):
                    element_counts[current_type] = element_counts.get(current_type, 0) + 1

        return element_counts

    def _get_retry_hint_message(self, retry_count: int) -> str:
        """Get hint message for retry attempts when agent provides no tool calls."""
        if retry_count == 1:
            return """You didn't provide any tool calls in your last response. To continue with the task, you MUST call one of the available tools.

Please analyze the current situation and choose the next action. What tool should you use to make progress on the task?"""

        elif retry_count == 2:
            tool_names = [tool.name for tool in self.tools.tools]
            tools_list = "\n".join(f"  - {name}" for name in tool_names)

            return f"""You still haven't provided any tool calls. You MUST use one of the available tools to continue.

Available tools:
{tools_list}

Based on the current page context and the task goal, which tool should you call next? Please make a decision and call a tool."""

        else:
            return """This is the final attempt. You MUST call a tool or use task_complete if the task is done.

If you cannot proceed due to:
- Missing information: Use get_page_overview or get_element_details to gather more info
- Uncertainty: Make your best guess based on available context
- Task completion: Use task_complete with a summary

Please call a tool now."""

    def _request_human_intervention(self, description: str) -> None:
        """Pause execution and request human intervention."""
        logger.warning("Human intervention required")
        logger.info(f"📋 {description}")
        logger.separator()
        print("\n⏸️  PAUSED - Human Action Required")
        print(f"➡️  {description}")
        print("\n👉 Please complete this action in the browser window, then press Enter to continue...")
        print()

        try:
            input("Press Enter when ready to continue: ")
        except KeyboardInterrupt:
            logger.info("\nTask cancelled by user during intervention.")
            raise

        logger.separator()
        logger.info("Resuming agent execution...")
        print()

    def _request_user_confirmation(self, action_description: str, risk_level: str) -> bool:
        """Request user confirmation for a destructive action."""
        risk_emoji = {
            "financial": "💰",
            "deletion": "🗑️",
            "irreversible": "⚠️",
        }
        emoji = risk_emoji.get(risk_level, "⚠️")

        logger.separator()
        logger.warning(f"Destructive action detected ({risk_level})")
        logger.info(f"{emoji} {action_description}")
        logger.separator()

        print(f"\n{emoji}  CONFIRMATION REQUIRED - {risk_level.upper()} ACTION")
        print(f"➡️  {action_description}")
        print("\n⚠️  This action may be irreversible!")
        print()

        while True:
            try:
                response = input("Do you want to proceed? (yes/no): ").strip().lower()
                if response in ["yes", "y"]:
                    logger.info("User confirmed action")
                    print()
                    return True
                elif response in ["no", "n"]:
                    logger.info("User declined action")
                    print()
                    return False
                else:
                    print("Please enter 'yes' or 'no'")
            except KeyboardInterrupt:
                logger.info("\nTask cancelled by user.")
                print()
                return False
