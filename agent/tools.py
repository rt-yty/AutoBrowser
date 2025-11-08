"""Tool definitions and registry for the agent."""

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


# Tool factory functions for common tools across agents


def create_navigation_tool(browser) -> Tool:
    """Create navigate_to tool."""
    return Tool(
        name="navigate_to",
        description="Navigate to a specific URL.",
        parameters={
            "url": {"type": "string", "description": "The URL to navigate to"}
        },
        handler=lambda url: navigate_to_handler(browser, url),
    )


def create_click_tool(browser, description_override: str = None) -> Tool:
    """Create click tool with optional description override."""
    desc = description_override or "Click on an element on the page."
    return Tool(
        name="click",
        description=desc,
        parameters={
            "selector": {
                "type": "string",
                "description": "Single valid Playwright selector for the element to click. Must be specific. NEVER use comma-separated selectors.",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of what element you're clicking",
            },
        },
        handler=lambda selector, description: click_handler(browser, selector, description),
    )


def create_type_text_tool(browser) -> Tool:
    """Create type_text tool."""
    return Tool(
        name="type_text",
        description="Type text into an input field.",
        parameters={
            "selector": {
                "type": "string",
                "description": "Single valid Playwright selector for the input field. Must be specific. NEVER use comma-separated selectors.",
            },
            "text": {
                "type": "string",
                "description": "Text to type",
            },
        },
        handler=lambda selector, text: type_text_handler(browser, selector, text),
    )


def create_scroll_tool(browser) -> Tool:
    """Create scroll tool."""
    return Tool(
        name="scroll",
        description="Scroll the page in a specific direction.",
        parameters={
            "direction": {
                "type": "string",
                "description": "Direction to scroll: 'down', 'up', 'page_down', 'page_up', 'bottom', 'top'",
            },
            "amount": {
                "type": "integer",
                "description": "Amount to scroll in pixels (for 'up' and 'down')",
            },
        },
        handler=lambda direction, amount=500: scroll_handler(browser, direction, amount),
    )


def create_wait_tool(browser) -> Tool:
    """Create wait_for_element tool."""
    return Tool(
        name="wait_for_element",
        description="Wait for an element to appear on the page.",
        parameters={
            "selector": {
                "type": "string",
                "description": "Single valid Playwright selector for the element to wait for. NEVER use comma-separated selectors.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in milliseconds (default 10000)",
            },
        },
        handler=lambda selector, timeout=10000: wait_for_element_handler(browser, selector, timeout),
    )


def create_page_overview_tool(context_manager) -> Tool:
    """Create get_page_overview tool."""
    return Tool(
        name="get_page_overview",
        description="Get a high-level overview of the current page using accessibility tree.",
        parameters={},
        handler=lambda: get_page_overview_handler(context_manager),
    )


def create_element_details_tool(context_manager) -> Tool:
    """Create get_element_details tool."""
    return Tool(
        name="get_element_details",
        description="Get detailed HTML for a specific element on the page. Use narrow selectors, NEVER 'body'.",
        parameters={
            "selector": {
                "type": "string",
                "description": "Single valid Playwright selector for a specific container. NEVER use 'body' or 'html'.",
            }
        },
        handler=lambda selector: get_element_details_handler(context_manager, selector),
    )


def create_coordinator_tools(browser, context_manager, subagents) -> ToolRegistry:
    """Create tools for the coordinator agent."""
    registry = ToolRegistry()

    # Navigation tool
    registry.register(
        Tool(
            name="navigate_to",
            description="Navigate to a specific URL.",
            parameters={
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to",
                }
            },
            handler=lambda url: navigate_to_handler(browser, url),
        )
    )

    # Click tool
    registry.register(
        Tool(
            name="click",
            description="Click on an element on the page.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Single valid Playwright selector for the element to click. Must be specific. Examples: \"button:has-text('Submit')\", \"a.nav-link:has-text('Jobs')\", \"input[type='checkbox'][name='agree']\". NEVER use comma-separated selectors like 'input, button' - use one specific selector.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what element you're clicking",
                },
            },
            handler=lambda selector, description: click_handler(
                browser, selector, description
            ),
        )
    )

    # Type text tool
    registry.register(
        Tool(
            name="type_text",
            description="Type text into an input field.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Single valid Playwright selector for the input field. Must be specific. Examples: \"input[placeholder='Search']\", \"input[name='email']\", \"textarea#message\". NEVER use comma-separated selectors - use one specific selector.",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type",
                },
            },
            handler=lambda selector, text: type_text_handler(browser, selector, text),
        )
    )

    # Scroll tool
    registry.register(
        Tool(
            name="scroll",
            description="Scroll the page in a specific direction.",
            parameters={
                "direction": {
                    "type": "string",
                    "description": "Direction to scroll: 'down', 'up', 'page_down', 'page_up', 'bottom', 'top'",
                },
                "amount": {
                    "type": "integer",
                    "description": "Amount to scroll in pixels (for 'up' and 'down')",
                },
            },
            handler=lambda direction, amount=500: scroll_handler(
                browser, direction, amount
            ),
        )
    )

    # Press key tool
    registry.register(
        Tool(
            name="press_key",
            description="Press a keyboard key. Use after typing in input fields (Enter to submit), to close modals (Escape), or to navigate forms (Tab).",
            parameters={
                "key": {
                    "type": "string",
                    "description": "Key to press. Options: 'Enter', 'Escape', 'Tab', 'Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'",
                }
            },
            handler=lambda key: press_key_handler(browser, key),
        )
    )

    # Wait for element tool
    registry.register(
        Tool(
            name="wait_for_element",
            description="Wait for an element to appear on the page.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Single valid Playwright selector for the element to wait for. Examples: \"div.results\", \"button:has-text('Load More')\", \"article.job-card\". NEVER use comma-separated selectors.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds (default 10000)",
                },
            },
            handler=lambda selector, timeout=10000: wait_for_element_handler(
                browser, selector, timeout
            ),
        )
    )

    # Get page overview tool
    registry.register(
        Tool(
            name="get_page_overview",
            description="Get a high-level overview of the current page using accessibility tree. Use this FIRST to understand page structure before building selectors.",
            parameters={},
            handler=lambda: get_page_overview_handler(context_manager),
        )
    )

    # Get element details tool
    registry.register(
        Tool(
            name="get_element_details",
            description="Get detailed HTML for a specific element on the page. Use narrow selectors like '.search-form' or '#main-content', NEVER broad selectors like 'body'.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Single valid Playwright selector for a specific container or element. Examples: \".search-form\", \"#product-card-123\", \"nav.main-menu\". NEVER use 'body' or 'html'.",
                }
            },
            handler=lambda selector: get_element_details_handler(
                context_manager, selector
            ),
        )
    )

    # Find element by text tool
    registry.register(
        Tool(
            name="find_element_by_text",
            description="Search for elements on the page by their visible text content and get their actual CSS selectors. ALWAYS use this tool BEFORE clicking/typing to discover the correct selector instead of guessing. Returns real selectors that you can use with click() or type_text().",
            parameters={
                "text": {
                    "type": "string",
                    "description": "Text content to search for. Can be partial text. Examples: 'Submit', 'Login', 'Add to cart', 'Это спам!'",
                },
                "role": {
                    "type": "string",
                    "description": "Optional: Filter by element role/type. Examples: 'button', 'link', 'textbox', 'menuitem'. Leave empty to search all element types.",
                }
            },
            handler=lambda text, role=None: find_element_by_text_handler(
                context_manager, text, role
            ),
        )
    )

    # Delegate to sub-agent tool
    registry.register(
        Tool(
            name="delegate_to_subagent",
            description="Delegate a specific subtask to a specialized sub-agent.",
            parameters={
                "subagent": {
                    "type": "string",
                    "description": "Name of sub-agent: 'navigator', 'form_filler', or 'data_reader'",
                },
                "subtask": {
                    "type": "string",
                    "description": "Description of the subtask for the sub-agent",
                },
            },
            handler=lambda subagent, subtask: delegate_handler(
                subagents, subagent, subtask
            ),
        )
    )

    # Request human help tool
    registry.register(
        Tool(
            name="request_human_help",
            description="Request human intervention for tasks that require manual action (CAPTCHA, login, 2FA, etc.). Use this when you detect security barriers that cannot be automated.",
            parameters={
                "description": {
                    "type": "string",
                    "description": "Clear, specific instructions for what the user needs to do manually (e.g., 'Please solve the CAPTCHA', 'Please log in with your credentials')",
                }
            },
            handler=lambda description: f"HUMAN_INTERVENTION_REQUIRED: {description}",
        )
    )

    # Request confirmation tool for destructive actions
    registry.register(
        Tool(
            name="request_confirmation",
            description=(
                "Request user confirmation before performing a destructive or financial action. "
                "ALWAYS use this before: purchasing/buying, deleting/removing, confirming payment, "
                "canceling subscriptions, sending messages/emails, or any irreversible action."
            ),
            parameters={
                "action_description": {
                    "type": "string",
                    "description": "Clear description of the destructive action you're about to perform (e.g., 'Complete purchase of MacBook Pro for $2,499', 'Delete email from John Smith', 'Cancel Premium subscription')",
                },
                "risk_level": {
                    "type": "string",
                    "description": "Risk level: 'financial' (costs money), 'deletion' (removes data), or 'irreversible' (cannot be undone)",
                },
            },
            handler=lambda action_description, risk_level: f"CONFIRMATION_REQUIRED:{risk_level}:{action_description}",
        )
    )

    # Task complete tool
    registry.register(
        Tool(
            name="task_complete",
            description="Mark the task as complete and provide a summary.",
            parameters={
                "summary": {
                    "type": "string",
                    "description": "Summary of what was accomplished",
                }
            },
            handler=lambda summary: f"TASK_COMPLETE: {summary}",
        )
    )

    return registry


# Tool handler implementations


def navigate_to_handler(browser, url: str) -> str:
    """Handle navigation to a URL."""
    try:
        browser.navigate_to(url)
        return f"Successfully navigated to {url}"
    except Exception as e:
        return f"Failed to navigate to {url}: {str(e)}"


def click_handler(browser, selector: str, description: str) -> str:
    """Handle clicking an element."""
    try:
        browser.click(selector)
        return f"Successfully clicked: {description}"
    except Exception as e:
        return f"Failed to click {description}: {str(e)}"


def type_text_handler(browser, selector: str, text: str) -> str:
    """Handle typing text."""
    try:
        browser.type_text(selector, text)
        return f"Successfully typed text into {selector}"
    except Exception as e:
        return f"Failed to type text: {str(e)}"


def scroll_handler(browser, direction: str, amount: int) -> str:
    """Handle scrolling."""
    try:
        browser.scroll(direction, amount)
        return f"Successfully scrolled {direction}"
    except Exception as e:
        return f"Failed to scroll: {str(e)}"


def wait_for_element_handler(browser, selector: str, timeout: int) -> str:
    """Handle waiting for an element."""
    success = browser.wait_for_selector(selector, timeout)
    if success:
        return f"Element {selector} appeared"
    else:
        return f"Element {selector} did not appear within timeout"


def get_page_overview_handler(context_manager) -> str:
    """Handle getting page overview."""
    context = context_manager.get_current_context()
    return context["overview"]


def get_element_details_handler(context_manager, selector: str) -> str:
    """Handle getting element details."""
    return context_manager.get_element_details(selector)


def find_element_by_text_handler(context_manager, text: str, role: str = None) -> str:
    """Handle finding elements by text content."""
    results = context_manager.find_elements_by_text(text, role)

    if not results:
        return f"No elements found containing text '{text}'" + (f" with role '{role}'" if role else "")

    if len(results) == 1:
        # Single match - return the selector directly
        elem = results[0]
        return f"Found 1 element: {elem['tag']} '{elem['text'][:50]}' {elem['context']}\nSelector: {elem['selector']}"

    # Multiple matches - return list with context
    response_parts = [f"Found {len(results)} elements containing '{text}':"]
    for i, elem in enumerate(results[:10], 1):  # Limit to first 10
        response_parts.append(
            f"{i}. {elem['tag']} '{elem['text'][:50]}' {elem['context']}\n   Selector: {elem['selector']}"
        )

    if len(results) > 10:
        response_parts.append(f"... and {len(results) - 10} more matches")

    response_parts.append("\nChoose the appropriate selector from the list above for your next action.")
    return "\n".join(response_parts)


def delegate_handler(subagents, subagent: str, subtask: str) -> str:
    """Handle delegation to sub-agent."""
    if subagent not in subagents:
        return f"Unknown sub-agent: {subagent}"

    agent = subagents[subagent]
    result = agent.execute(subtask)
    return result


def press_key_handler(browser, key: str) -> str:
    """Handle pressing a keyboard key."""
    try:
        browser.press_key(key)
        return f"Successfully pressed key: {key}"
    except Exception as e:
        return f"Failed to press key: {str(e)}"
