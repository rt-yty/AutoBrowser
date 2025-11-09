def validate_selector(selector: str, tool_name: str) -> str:
    """Validate selector format and return error if invalid.

    Args:
        selector: The selector to validate
        tool_name: Name of the tool for error messages

    Returns:
        Error message if invalid, empty string if valid
    """
    if not selector or not selector.strip():
        return f"Error: Empty selector provided to {tool_name}. Please provide a valid CSS selector."

    in_quotes = False
    in_brackets = 0
    quote_char = None

    for i, char in enumerate(selector):
        if char in ('"', "'") and (i == 0 or selector[i-1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
        elif char in ('[', '('):
            in_brackets += 1
        elif char in (']', ')'):
            in_brackets -= 1
        elif char == ',' and not in_quotes and in_brackets == 0:
            return f"Error: Invalid selector '{selector}' for {tool_name}. Contains comma-separated selectors. Use a single specific selector instead. Examples: 'button.submit', 'div.container >> a', 'input[name=\"email\"]'."

    stripped = selector.strip()
    if stripped in ('body', 'html', '*'):
        return f"Error: Invalid selector '{selector}' for {tool_name}. Selector is too broad. Use a more specific selector like '.container', '#main-content', 'nav.header'."

    return ""


def navigate_to_handler(browser, url: str) -> str:
    """Handle navigation to a URL."""
    try:
        browser.navigate_to(url)
        return f"Successfully navigated to {url}"
    except Exception as e:
        return f"Failed to navigate to {url}: {str(e)}"


def click_handler(browser, selector: str, description: str) -> str:
    """Handle clicking an element."""
    error = validate_selector(selector, "click")
    if error:
        return error

    try:
        browser.click(selector)
        return f"Successfully clicked: {description}"
    except Exception as e:
        return f"Failed to click {description}: {str(e)}"


def hover_handler(browser, selector: str, description: str) -> str:
    """Handle hovering over an element."""
    error = validate_selector(selector, "hover")
    if error:
        return error

    try:
        browser.hover(selector)
        return f"Successfully hovered over: {description}"
    except Exception as e:
        return f"Failed to hover over {description}: {str(e)}"


def type_text_handler(browser, selector: str, text: str) -> str:
    """Handle typing text."""
    error = validate_selector(selector, "type_text")
    if error:
        return error

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


def press_key_handler(browser, key: str) -> str:
    """Handle pressing a keyboard key."""
    try:
        browser.press_key(key)
        return f"Successfully pressed key: {key}"
    except Exception as e:
        return f"Failed to press key: {str(e)}"


def wait_for_element_handler(browser, selector: str, timeout: int) -> str:
    """Handle waiting for an element."""
    error = validate_selector(selector, "wait_for_element")
    if error:
        return error

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
    error = validate_selector(selector, "get_element_details")
    if error:
        return error

    return context_manager.get_element_details(selector)


def find_element_by_text_handler(context_manager, text: str, role: str = None) -> str:
    """Handle finding elements by text content."""
    results = context_manager.find_elements_by_text(text, role)

    if not results:
        return f"No elements found containing text '{text}'" + (f" with role '{role}'" if role else "")

    if len(results) == 1:
        elem = results[0]
        return f"Found 1 element: {elem['tag']} '{elem['text'][:50]}' {elem['context']}\nSelector: {elem['selector']}"

    response_parts = [f"Found {len(results)} elements containing '{text}':"]
    for i, elem in enumerate(results[:10], 1):
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


def list_tabs_handler(browser) -> str:
    """Handle listing all open tabs."""
    try:
        tabs = browser.list_tabs()
        if not tabs:
            return "No tabs open"

        lines = [f"Found {len(tabs)} open tab(s):"]
        for tab in tabs:
            active_marker = " [ACTIVE]" if tab["is_active"] else ""
            lines.append(
                f"{tab['index']}. {tab['title'][:50]} - {tab['url'][:60]}{active_marker}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Failed to list tabs: {str(e)}"


def switch_to_tab_handler(browser, tab_index: int) -> str:
    """Handle switching to a different tab."""
    try:
        browser.switch_to_tab(tab_index)
        tabs = browser.list_tabs()
        active_tab = tabs[tab_index]
        return f"Switched to tab {tab_index}: {active_tab['title'][:50]} - {active_tab['url'][:60]}"
    except Exception as e:
        return f"Failed to switch to tab: {str(e)}"


def close_tab_handler(browser, tab_index: int) -> str:
    """Handle closing a tab."""
    try:
        tabs = browser.list_tabs()
        if tab_index < len(tabs):
            tab_info = tabs[tab_index]
            browser.close_tab(tab_index)
            return f"Closed tab {tab_index}: {tab_info['title'][:50]}"
        else:
            return f"Invalid tab index: {tab_index}"
    except Exception as e:
        return f"Failed to close tab: {str(e)}"


def switch_to_frame_handler(browser, selector: str) -> str:
    """Handle switching to iframe context."""
    error = validate_selector(selector, "switch_to_frame")
    if error:
        return error

    try:
        browser.switch_to_frame(selector)
        return f"Switched to iframe: {selector}. You can now interact with elements inside the iframe using Playwright's >> syntax (e.g., '{selector} >> button')."
    except Exception as e:
        return f"Failed to switch to iframe: {str(e)}"


def switch_to_main_content_handler(browser) -> str:
    """Handle switching back to main content."""
    try:
        browser.switch_to_main_content()
        return "Switched back to main page content (exited iframe context)."
    except Exception as e:
        return f"Failed to switch to main content: {str(e)}"
