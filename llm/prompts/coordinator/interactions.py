INTERACTIONS_SECTION = """## CRITICAL: Keyboard Interaction

**Use keyboard keys for common interactions:**

**After typing in input fields:**
- Always use `press_key("Enter")` after typing in search boxes or text inputs
- This submits forms and triggers search actions
- Example: type_text(selector, text) → press_key("Enter")

**For form navigation:**
- Use `press_key("Tab")` to move between form fields
- Use `press_key("Enter")` when on the last field or submit button

**For closing modals/overlays:**
- Use `press_key("Escape")` to close modal dialogs and overlays
- Try Escape before requesting human help

**Available keys:**
- `Enter`: Submit forms, activate buttons, trigger search
- `Escape`: Close modals, dismiss popups, cancel actions
- `Tab`: Navigate between form fields
- `Space`: Activate buttons, toggle checkboxes
- `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`: Navigate lists and menus
- `Backspace`: Clear text, delete characters
- `Delete`: Delete characters forward
- `Home`, `End`: Navigate to start/end of input field
- `PageUp`, `PageDown`: Scroll page up/down (alternative to scroll tool)

**Best practice flow:**
1. Type text into field: `type_text(selector, text)`
2. Submit: `press_key("Enter")`
3. If modal appears blocking interaction: `press_key("Escape")`

## Hover Interactions

**Use hover to reveal hidden content:**
- Dropdown menus, tooltips, additional options appear on hover
- If element not found, try hovering over parent first
- Common: navigation menus, profile menus, image previews

**When to use:**
- Navigation dropdown menus
- Tooltips or help text
- Hidden buttons/actions
- Image zoom features

**Workflow:** hover → wait briefly → click revealed element

## Multi-Tab Management

**Tools:** `list_tabs()`, `switch_to_tab(index)`, `close_tab(index)`

- Links with target="_blank" open in new tabs
- Work with multiple tabs simultaneously

**When to use:**
- Link opens in new tab and you need the content
- Comparing information across pages
- Keeping reference pages open

**Workflow:** click link → list_tabs() → switch_to_tab(N) → work → close_tab(N) or switch back

**Notes:**
- Tab indices are zero-based (0 = first, 1 = second)
- Cannot close only remaining tab
- Active tab marked [ACTIVE]

## Iframe Interactions

**Use when content is in iframes:**
- Payment forms, embedded widgets, third-party forms, video players

**Methods:**

1. **>> syntax (RECOMMENDED):** `iframe#id >> selector` - Direct targeting, simpler
2. **switch_to_frame:** Change context to work inside iframe

**Workflow (>> syntax):**
- Use: `click(selector="iframe#id >> button", description="...")`
- Or: `type_text(selector="iframe#id >> input", text="...")`

**Workflow (switch_to_frame):**
1. `switch_to_frame(selector="iframe#id")`
2. Interact with elements inside
3. `switch_to_main_content()` to exit

**Notes:**
- Check for iframes if interaction fails
- Prefer >> syntax for simplicity
- Exit iframe context with switch_to_main_content when done"""
