from agent.tools.registry import Tool, ToolRegistry
from agent.tools.handlers import (
    navigate_to_handler,
    click_handler,
    hover_handler,
    type_text_handler,
    scroll_handler,
    press_key_handler,
    wait_for_element_handler,
    get_page_overview_handler,
    get_element_details_handler,
    find_element_by_text_handler,
    delegate_handler,
    list_tabs_handler,
    switch_to_tab_handler,
    close_tab_handler,
    switch_to_frame_handler,
    switch_to_main_content_handler,
)


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


def create_hover_tool(browser, description_override: str = None) -> Tool:
    """Create hover tool with optional description override."""
    desc = description_override or "Hover over an element to reveal dropdown menus, tooltips, or hidden content."
    return Tool(
        name="hover",
        description=desc,
        parameters={
            "selector": {
                "type": "string",
                "description": "Single valid Playwright selector for the element to hover over. Must be specific. NEVER use comma-separated selectors.",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of what element you're hovering over",
            },
        },
        handler=lambda selector, description: hover_handler(browser, selector, description),
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

    registry.register(
        Tool(
            name="hover",
            description="Hover over an element to reveal dropdown menus, tooltips, or hidden content that appears on hover.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "Single valid Playwright selector for the element to hover over. Examples: \"nav a:has-text('Products')\", \".dropdown-trigger\", \"button.menu-toggle\". NEVER use comma-separated selectors.",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what element you're hovering over",
                },
            },
            handler=lambda selector, description: hover_handler(
                browser, selector, description
            ),
        )
    )

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

    registry.register(
        Tool(
            name="press_key",
            description="Press a keyboard key. Use for form submission (Enter), closing modals (Escape), navigation (Tab, arrows), editing (Backspace, Delete), or scrolling (PageUp, PageDown).",
            parameters={
                "key": {
                    "type": "string",
                    "description": "Key to press. Options: 'Enter', 'Escape', 'Tab', 'Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Backspace', 'Delete', 'Home', 'End', 'PageUp', 'PageDown'",
                }
            },
            handler=lambda key: press_key_handler(browser, key),
        )
    )

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

    registry.register(
        Tool(
            name="list_tabs",
            description="List all open browser tabs with their titles, URLs, and which one is currently active.",
            parameters={},
            handler=lambda: list_tabs_handler(browser),
        )
    )

    registry.register(
        Tool(
            name="switch_to_tab",
            description="Switch to a different browser tab by its index. Use list_tabs first to see available tabs.",
            parameters={
                "tab_index": {
                    "type": "integer",
                    "description": "Zero-based index of the tab to switch to (0 = first tab, 1 = second tab, etc.)",
                }
            },
            handler=lambda tab_index: switch_to_tab_handler(browser, tab_index),
        )
    )

    registry.register(
        Tool(
            name="close_tab",
            description="Close a browser tab by its index. Cannot close the only remaining tab.",
            parameters={
                "tab_index": {
                    "type": "integer",
                    "description": "Zero-based index of the tab to close (0 = first tab, 1 = second tab, etc.)",
                }
            },
            handler=lambda tab_index: close_tab_handler(browser, tab_index),
        )
    )

    registry.register(
        Tool(
            name="switch_to_frame",
            description="Switch context to an iframe/frame element. Use this when you need to interact with content inside an iframe (e.g., embedded forms, payment widgets, chat widgets). After switching, you can use Playwright's >> syntax: 'iframe#payment >> input[name=\"card\"]'.",
            parameters={
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the iframe element. Examples: 'iframe#payment-form', 'iframe[name=\"checkout\"]', 'iframe.embedded-widget'. NEVER use comma-separated selectors.",
                }
            },
            handler=lambda selector: switch_to_frame_handler(browser, selector),
        )
    )

    registry.register(
        Tool(
            name="switch_to_main_content",
            description="Switch context back to the main page content (exit iframe). Use this after you're done working with iframe content.",
            parameters={},
            handler=lambda: switch_to_main_content_handler(browser),
        )
    )

    registry.register(
        Tool(
            name="get_page_overview",
            description="Get a high-level overview of the current page using accessibility tree. Use this FIRST to understand page structure before building selectors.",
            parameters={},
            handler=lambda: get_page_overview_handler(context_manager),
        )
    )

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
