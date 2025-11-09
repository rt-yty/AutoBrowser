ELEMENT_DISCOVERY_SECTION = """## Element Discovery Workflow

**ALWAYS discover selectors - NEVER guess them!**

### Correct workflow:
1. Use `get_page_overview()` to see available elements
2. Use `find_element_by_text("text")` to get the real selector
3. Extract selector from response (look for "Selector: ...")
4. Use the discovered selector with click() or type_text()

### Extracting selector from find_element_by_text:
The tool returns multi-line text. You MUST extract the selector string:
- Find the line starting with "Selector:"
- Copy everything after "Selector: "
- Use this EXACT string in your tool call

**CRITICAL**: NEVER use empty selector! Always extract selector before clicking.

### When to use find_element_by_text:
- ALWAYS before clicking buttons/links
- ALWAYS before typing into fields
- ALWAYS when interacting with elements from get_page_overview()

### Handling multiple matches:
If multiple results returned, look at parent context to choose:
- Prefer specific elements (button, a, input) over generic (div, span)
- Check parent matches your task context
- Avoid elements "in <body>" - too generic
- For buttons, choose actual button, not text inside it

### If action fails:

**Check for:**
1. **Empty selector** - Extract properly from find_element_by_text
2. **Hidden menu** - Button may be in dropdown (see below)
3. **Overlay blocking** - Try `press_key("Escape")` first
4. **Off-screen** - Try scrolling first
5. **Timing** - Try `wait_for_element()` first

### Working with dropdown menus:

If button found but click doesn't work, it may be in hidden menu.

**Look for menu triggers:**
- Try `find_element_by_text("⋯")` or `find_element_by_text("⋮")`
- Try `find_element_by_text("...")` or `find_element_by_text("More")`
- Check page overview for buttons with "menu" in name
- Use `get_element_details()` on container to find aria-label

**Recovery workflow:**
1. Find and click menu trigger to open dropdown
2. Wait for menu if needed: `wait_for_element()`
3. Find target button again (should be visible now)
4. Click target button

**Alternative checks:**
- Try `hover()` on container - some menus appear on hover
- Use `get_element_details()` to inspect container HTML
- Look for buttons with aria-expanded="false"

### Best practices:
- Use narrow selectors: combine container + button
- Three-dot menus usually near the item they affect
- After opening menu, wait briefly for it to render
- Some menus need hover before click"""
