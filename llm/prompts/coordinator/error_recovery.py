ERROR_RECOVERY_SECTION = """## CRITICAL: Overlay and Popup Handling

**Overlays block clicks and must be closed first!**

When you see an error like "intercepts pointer events" or "click blocked by overlay":

**Multi-step strategy:**
1. **Try clicking close button first**:
   - `button:has-text('Close')`, `button:has-text('×')`
   - `button:has-text('Skip')`, `button:has-text('Dismiss')`
   - `a[class*='close']`, `button[class*='close']`
   - `div[class*='overlay'] >> button`

2. **If close button not found**, try `press_key("Escape")`

3. **Wait briefly** (use wait_for_element or small delay) for overlay to disappear

4. **Retry your original action**

5. **If still blocked**, request_human_help

**Common overlays:** Cookie banners, newsletter popups, app install prompts, welcome modals, ads

**Recovery flow:** Try close button → If fails: press_key("Escape") → Wait → Retry original action"""
