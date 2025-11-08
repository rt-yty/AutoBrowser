"""Coordinator agent - main orchestrator."""

from typing import Dict, List, Optional

from anthropic.types import MessageParam

from agent.context_manager import ContextManager
from agent.tools import create_coordinator_tools
from browser.controller import BrowserController
from config import AgentConfig
from llm.claude_client import ClaudeClient
from llm.prompts import get_coordinator_prompt
from utils.logger import logger


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

        # Create tool registry
        self.tools = create_coordinator_tools(browser, context_manager, subagents)

        # Conversation history
        self.conversation: List[MessageParam] = []

        # Task status
        self.task_complete = False
        self.task_summary: Optional[str] = None

        # Retry tracking for stuck agent
        self.max_no_tool_retries = 3
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

    def execute_task(self, task: str) -> str:
        """
        Execute a high-level task.

        Args:
            task: Natural language description of the task

        Returns:
            Summary of task completion
        """
        logger.task(task)

        # Initialize conversation with task and initial context
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

        # Main agent loop
        iteration = 0
        no_tool_retry_count = 0

        while iteration < self.config.max_iterations and not self.task_complete:
            iteration += 1

            # Get response from Claude
            response = self.claude_client.send_message(
                messages=self.conversation,
                system_prompt=get_coordinator_prompt(),
                tools=self.tools.get_anthropic_tools(),
            )

            # Add assistant's response to conversation
            self.conversation.append({"role": "assistant", "content": response.content})

            # Extract text reasoning (if any)
            reasoning = self.claude_client.extract_text(response)
            if reasoning:
                logger.info(f"Reasoning: {reasoning}")

            # Extract and execute tool calls
            tool_calls = self.claude_client.extract_tool_calls(response)

            if not tool_calls:
                # No tool calls - agent might be done or stuck
                no_tool_retry_count += 1
                logger.warning(f"No tool calls in response. Agent may be stuck. (Retry {no_tool_retry_count}/{self.max_no_tool_retries})")

                if no_tool_retry_count >= self.max_no_tool_retries:
                    logger.error("Agent failed to provide tool calls after multiple retries.")
                    break

                # Send hint message based on retry attempt
                hint_msg = self._get_retry_hint_message(no_tool_retry_count)
                self.conversation.append({
                    "role": "user",
                    "content": hint_msg
                })
                logger.info(f"Sending retry hint to agent...")
                continue  # Retry with hint

            # Reset retry counter on successful tool call
            no_tool_retry_count = 0

            # Execute each tool call
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_input = tool_call["input"]

                # Check if task is complete
                if tool_name == "task_complete":
                    self.task_complete = True
                    self.task_summary = tool_input.get("summary", "Task completed")
                    logger.success(self.task_summary)
                    return self.task_summary

                # Log the action
                logger.action("Coordinator", tool_name, tool_input, reasoning)

                # Execute the tool
                result = self.tools.execute_tool(tool_name, **tool_input)

                # Check if confirmation is required for destructive actions
                if result.startswith("CONFIRMATION_REQUIRED:"):
                    # Parse: CONFIRMATION_REQUIRED:risk_level:description
                    parts = result.split(":", 2)
                    risk_level = parts[1] if len(parts) > 1 else "unknown"
                    action_description = parts[2] if len(parts) > 2 else "Unknown action"

                    # Request user confirmation
                    confirmed = self._request_user_confirmation(action_description, risk_level)

                    if confirmed:
                        result = "User confirmed the action. You may proceed with the next step."
                    else:
                        result = "User DECLINED the action. Do NOT proceed. The task cannot be completed as requested."
                        logger.warning(f"User declined destructive action: {action_description}")

                # Check if human intervention is required
                human_intervention_needed = result.startswith("HUMAN_INTERVENTION_REQUIRED:")
                if human_intervention_needed:
                    # Extract the description
                    description = result.replace("HUMAN_INTERVENTION_REQUIRED:", "").strip()

                    # Pause and request user action
                    self._request_human_intervention(description)

                    # Update result to reflect that intervention was completed
                    # This will be sent as the tool_result content
                    result = "Human intervention completed. User has manually handled the required action in the browser."

                # Check for success/failure
                success = not result.startswith("Error") and not result.startswith(
                    "Failed"
                )
                logger.result(result, success)

                # Add tool result to conversation
                # This MUST happen for every tool_use, including request_human_help
                tool_result_msg = self.claude_client.create_tool_result_message(
                    tool_call["id"], result
                )
                self.conversation.append(tool_result_msg)

                # Track consecutive failures for error recovery
                if success:
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                    logger.info(f"Consecutive failures: {self.consecutive_failures}/{self.max_consecutive_failures}")

                    if self.consecutive_failures >= self.max_consecutive_failures:
                        logger.warning("Multiple consecutive failures detected. Consider requesting human assistance.")
                        # Add hint to conversation to suggest using request_human_help
                        help_hint = {
                            "role": "user",
                            "content": """You've encountered multiple consecutive failures. If you're stuck or unable to proceed:
1. Try a different approach or tool
2. Use get_page_overview to reassess the situation
3. If the issue persists, consider using request_human_help to get assistance

What would you like to do?"""
                        }
                        self.conversation.append(help_hint)
                        # Reset counter to avoid spamming hints
                        self.consecutive_failures = 0

                # If human intervention occurred, add updated context as separate user message
                if human_intervention_needed:
                    try:
                        updated_context = self.context_manager.get_current_context()
                        context_msg = {
                            "role": "user",
                            "content": f"""Updated page context after human intervention:
{updated_context['overview']}

You can now continue with the task.""",
                        }
                        self.conversation.append(context_msg)

                        # Log minimal summary to terminal
                        logger.info(f"Context updated: {self._format_context_summary(updated_context)}")
                    except Exception as e:
                        logger.error(f"Failed to get updated context after intervention: {str(e)}")

                # After each action, provide updated context
                if tool_name in ["click", "navigate_to", "scroll", "type_text", "press_key"]:
                    # Page might have changed, provide fresh context
                    try:
                        updated_context = self.context_manager.get_current_context()
                        context_msg = {
                            "role": "user",
                            "content": f"""Updated page context after {tool_name}:
{updated_context['overview']}""",
                        }
                        self.conversation.append(context_msg)

                        # Log minimal summary to terminal (not full overview)
                        logger.info(f"Context updated: {self._format_context_summary(updated_context)}")
                    except Exception as e:
                        logger.error(f"Failed to get updated context: {str(e)}")

        # Max iterations reached without completion
        if not self.task_complete:
            failure_reason = f"Agent reached maximum iterations ({self.config.max_iterations}) without completing the task."
            logger.failure(failure_reason)
            return failure_reason

        return self.task_summary or "Task completed"

    def _format_context_summary(self, context: Dict) -> str:
        """
        Format context as a minimal summary for terminal logging.

        Args:
            context: Context dict from context_manager

        Returns:
            Concise summary string
        """
        url = context.get('url', 'Unknown')
        title = context.get('title', 'Unknown')

        # Truncate long URLs
        if len(url) > 50:
            url = url[:47] + "..."

        # Truncate long titles
        if len(title) > 30:
            title = title[:27] + "..."

        # Count element types from overview
        overview = context.get('overview', '')
        element_counts = {}

        lines = overview.split('\n')
        current_type = None

        for line in lines:
            # Detect element type headers
            if line.strip().endswith('S:') and line.strip().isupper():
                current_type = line.strip().rstrip('S:')
                element_counts[current_type] = 0
            elif current_type and '... and' in line and 'more' in line:
                try:
                    extra = int(line.split('... and')[1].split('more')[0].strip())
                    element_counts[current_type] += extra
                except:
                    pass
            elif current_type and line.strip().startswith('-'):
                element_counts[current_type] = element_counts.get(current_type, 0) + 1

        # Format counts
        if element_counts:
            counts_str = ', '.join(f"{count} {typ.lower()}{'s' if count != 1 else ''}"
                                   for typ, count in element_counts.items() if count > 0)
            return f"{url} | {counts_str}"
        else:
            return f"{url} | {title}"

    def _get_retry_hint_message(self, retry_count: int) -> str:
        """
        Get hint message for retry attempts when agent provides no tool calls.

        Args:
            retry_count: Current retry attempt number (1-based)

        Returns:
            Hint message to guide the agent
        """
        if retry_count == 1:
            return """You didn't provide any tool calls in your last response. To continue with the task, you MUST call one of the available tools.

Please analyze the current situation and choose the next action. What tool should you use to make progress on the task?"""

        elif retry_count == 2:
            # Get current available tools
            tool_names = [tool.name for tool in self.tools.tools]
            tools_list = "\n".join(f"  - {name}" for name in tool_names)

            return f"""You still haven't provided any tool calls. You MUST use one of the available tools to continue.

Available tools:
{tools_list}

Based on the current page context and the task goal, which tool should you call next? Please make a decision and call a tool."""

        else:  # retry_count >= 3
            return """This is the final attempt. You MUST call a tool or use task_complete if the task is done.

If you cannot proceed due to:
- Missing information: Use get_page_overview or get_element_details to gather more info
- Uncertainty: Make your best guess based on available context
- Task completion: Use task_complete with a summary

Please call a tool now."""

    def _request_human_intervention(self, description: str) -> None:
        """
        Pause execution and request human intervention.

        Args:
            description: Instructions for what the user needs to do
        """
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
        """
        Request user confirmation for a destructive action.

        Args:
            action_description: Description of the action
            risk_level: Risk level (financial, deletion, irreversible)

        Returns:
            True if user confirms, False if declines
        """
        # Map risk levels to emojis for clarity
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
