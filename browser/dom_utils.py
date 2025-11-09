from typing import Any, Dict, List, Optional

from playwright.sync_api import Page


class DOMExtractor:
    """Extracts and simplifies DOM information for the agent."""

    def __init__(self, page: Page):
        self.page = page

    def get_accessibility_tree(self) -> List[Dict[str, Any]]:
        """
        Get the accessibility tree of the page.
        This provides a semantic, concise representation of interactive elements.
        """
        snapshot = self.page.accessibility.snapshot()
        if not snapshot:
            return []

        elements = []
        self._extract_accessible_elements(snapshot, elements)
        return elements

    def _extract_accessible_elements(
        self, node: Dict[str, Any], elements: List[Dict[str, Any]], depth: int = 0
    ) -> None:
        """Recursively extract accessible elements from the tree."""
        if depth > 10:
            return

        role = node.get("role", "")
        name = node.get("name", "")
        value = node.get("value", "")

        interesting_roles = {
            "button",
            "link",
            "textbox",
            "searchbox",
            "combobox",
            "checkbox",
            "radio",
            "menuitem",
            "tab",
            "heading",
            "list",
            "listitem",
            "article",
            "navigation",
            "main",
            "form",
        }

        if role in interesting_roles and (name or value):
            elements.append(
                {
                    "role": role,
                    "name": name,
                    "value": value,
                    "depth": depth,
                }
            )

        for child in node.get("children", []):
            self._extract_accessible_elements(child, elements, depth + 1)

    def get_page_overview(self) -> str:
        """
        Get a concise overview of the page with CSS selectors.
        This is the primary context sent to the agent.
        """
        url = self.page.url
        title = self.page.title()

        elements_with_selectors = self._get_interactive_elements_with_attributes()

        overview_parts = [
            f"URL: {url}",
            f"Title: {title}",
            "",
            "Interactive Elements:",
        ]

        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for elem in elements_with_selectors:
            role = elem["role"]
            if role not in grouped:
                grouped[role] = []
            grouped[role].append(elem)

        for role, elements in grouped.items():
            overview_parts.append(f"\n{role.upper()}S:")
            for elem in elements[:10]:
                name = elem["name"]
                value = elem.get("value", "")

                selector_parts = []
                if elem.get("id"):
                    selector_parts.append(f"#{elem['id']}")
                if elem.get("classes"):
                    classes = elem['classes'].split()[:2]
                    selector_parts.append("." + ".".join(classes))

                selector_hint = f" ({elem['tag']}" + ("".join(selector_parts) if selector_parts else "") + ")"

                if value:
                    overview_parts.append(f"  - {name} (value: {value}){selector_hint}")
                else:
                    overview_parts.append(f"  - {name}{selector_hint}")

            if len(elements) > 10:
                overview_parts.append(f"  ... and {len(elements) - 10} more")

        return "\n".join(overview_parts)

    def _get_interactive_elements_with_attributes(self) -> List[Dict[str, Any]]:
        """
        Extract interactive elements with their CSS classes and IDs.
        Returns a list of elements with role, name, tag, classes, and id.
        """
        script = """
        () => {
            const elements = [];
            const interactiveSelectors = [
                'button', 'a', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[role="textbox"]',
                '[role="searchbox"]', '[role="combobox"]', '[role="checkbox"]',
                '[role="radio"]', '[role="menuitem"]', '[role="tab"]',
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
            ];

            const found = document.querySelectorAll(interactiveSelectors.join(', '));

            found.forEach(el => {
                // Get element text
                const text = el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || '';
                if (!text.trim()) return;

                // Check visibility
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                const isVisible = style.display !== 'none' &&
                                 style.visibility !== 'hidden' &&
                                 rect.width > 0 &&
                                 rect.height > 0;

                if (!isVisible) return;

                // Determine role
                let role = el.getAttribute('role') || el.tagName.toLowerCase();
                if (role === 'a') role = 'link';
                if (role === 'input') {
                    const type = el.getAttribute('type') || 'text';
                    if (type === 'checkbox') role = 'checkbox';
                    else if (type === 'radio') role = 'radio';
                    else role = 'textbox';
                }
                if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(role)) role = 'heading';

                elements.push({
                    role: role,
                    name: text.substring(0, 100).trim(),
                    value: el.value || '',
                    tag: el.tagName.toLowerCase(),
                    classes: el.className || '',
                    id: el.id || ''
                });
            });

            return elements;
        }
        """

        try:
            return self.page.evaluate(script)
        except Exception:
            return self.get_accessibility_tree()

    def get_element_details(self, selector: str, max_length: int = 2000) -> Optional[str]:
        """
        Get detailed HTML for a specific element.
        Used when the agent needs to drill down into a specific part of the page.

        Args:
            selector: CSS selector for the element
            max_length: Maximum length of returned HTML (default 2000 chars)

        Returns:
            Simplified HTML content, truncated if necessary
        """
        try:
            element = self.page.query_selector(selector)
            if not element:
                return None

            html = element.inner_html()

            simplified = self._simplify_html(html)

            if len(simplified) > max_length:
                truncated = simplified[:max_length]
                last_close = truncated.rfind(">")
                if last_close > max_length * 0.8:
                    truncated = truncated[:last_close + 1]

                return f"{truncated}\n\n... [TRUNCATED - content was {len(simplified)} chars, showing first {len(truncated)} chars]"

            return simplified
        except Exception as e:
            return f"Error getting element details: {str(e)}"

    def _simplify_html(self, html: str) -> str:
        """
        Aggressively simplify HTML by removing unnecessary elements.
        Removes scripts, styles, comments, and cleans up attributes.
        """
        import re

        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)

        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        html = re.sub(r'\s+style="[^"]*"', "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+style='[^']*'", "", html, flags=re.IGNORECASE)
        
        html = re.sub(r'\s+on\w+="[^"]*"', "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on\w+='[^']*'", "", html, flags=re.IGNORECASE)

        html = re.sub(r'\s+data-[\w-]+="[^"]*"', "", html, flags=re.IGNORECASE)

        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

        html = re.sub(r"\s+", " ", html)

        html = re.sub(r"\s+>", ">", html)

        html = re.sub(r"<\s+", "<", html)

        return html.strip()

    def get_visible_text(self) -> str:
        """Get all visible text on the page."""
        return self.page.inner_text("body")

    def find_elements_by_text(self, text: str, role: Optional[str] = None) -> List[dict]:
        """
        Find elements containing specific text.
        Returns a list of dicts with selector and context information.

        Each result contains:
        - selector: CSS selector to use for clicking/interacting
        - text: The actual text content of the element
        - tag: HTML tag name
        - role: ARIA role if available
        - context: Description of parent/container element
        - is_visible: Whether the element is visible
        - classes: CSS classes on the element
        - id: Element ID if present
        """
        escaped_text = text.replace("'", "\\'")

        script = f"""
        () => {{
            const results = [];
            const interactiveTags = ['button', 'a', 'input', 'select', 'textarea'];

            // Helper: calculate element priority (higher = better match)
            const getPriority = (node) => {{
                let priority = 0;
                const tag = node.tagName.toLowerCase();

                // Prefer interactive elements
                if (interactiveTags.includes(tag)) priority += 100;

                // Check if text is directly in this element (not just in children)
                const ownText = Array.from(node.childNodes)
                    .filter(n => n.nodeType === Node.TEXT_NODE)
                    .map(n => n.textContent.trim())
                    .join(' ');

                if (ownText.includes('{escaped_text}')) {{
                    priority += 50;  // Direct text match is better
                }}

                // CRITICAL: Penalize text-only elements inside interactive elements
                // If this is a span/div inside a button/link, heavily penalize it
                if (['span', 'div', 'p'].includes(tag)) {{
                    let parent = node.parentElement;
                    if (parent && interactiveTags.includes(parent.tagName.toLowerCase())) {{
                        priority -= 200;  // Heavy penalty - prefer the parent instead
                    }}
                }}

                // Penalize generic containers
                if (['div', 'span', 'body', 'html'].includes(tag)) priority -= 20;

                // Prefer elements with fewer characters (more specific)
                const textLength = node.textContent.length;
                priority -= Math.min(textLength / 100, 30);

                return priority;
            }};

            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_ELEMENT,
                null
            );

            let node;
            let idx = 0;
            const candidates = [];

            while (node = walker.nextNode()) {{
                if (node.textContent.includes('{escaped_text}')) {{
                    // Filter by role if specified
                    const nodeRole = node.getAttribute('role') || node.tagName.toLowerCase();
                    {f"if (nodeRole === '{role}' || node.tagName.toLowerCase() === '{role}') {{" if role else ""}

                    // Check visibility
                    const rect = node.getBoundingClientRect();
                    const style = window.getComputedStyle(node);
                    const isVisible = style.display !== 'none' &&
                                     style.visibility !== 'hidden' &&
                                     style.opacity !== '0' &&
                                     rect.width > 0 &&
                                     rect.height > 0;

                    if (!isVisible) continue;

                    // Get parent context
                    let parent = node.parentElement;
                    let contextDesc = '';
                    if (parent) {{
                        const parentTag = parent.tagName.toLowerCase();
                        const parentClass = parent.className ? '.' + parent.className.split(' ')[0] : '';
                        const parentId = parent.id ? '#' + parent.id : '';
                        const parentText = parent.textContent.substring(0, 50).trim();
                        contextDesc = `in <${{parentTag}}${{parentClass}}${{parentId}}>`;
                    }}

                    candidates.push({{
                        node: node,
                        priority: getPriority(node),
                        text: node.textContent.substring(0, 100).trim(),
                        tag: node.tagName.toLowerCase(),
                        role: node.getAttribute('role') || '',
                        context: contextDesc,
                        classes: node.className || '',
                        id: node.id || ''
                    }});

                    {f"}}" if role else ""}
                }}
            }}

            // Sort by priority (best matches first)
            candidates.sort((a, b) => b.priority - a.priority);

            // Take top 10 matches and assign selectors
            const topMatches = candidates.slice(0, 10);
            topMatches.forEach((item, idx) => {{
                item.node.setAttribute('data-autobrowser-find-id', idx);
                results.push({{
                    selector: '[data-autobrowser-find-id="' + idx + '"]',
                    text: item.text,
                    tag: item.tag,
                    role: item.role,
                    context: item.context,
                    is_visible: true,
                    classes: item.classes,
                    id: item.id,
                    index: idx
                }});
            }});

            return results;
        }}
        """

        try:
            results = self.page.evaluate(script)
            return results if results else []
        except Exception as e:
            return []
