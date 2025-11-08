"""Rich terminal logging utilities."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box


class AgentLogger:
    """Pretty terminal logging for agent actions."""

    def __init__(self):
        self.console = Console()

    def header(self, text: str) -> None:
        """Print a header."""
        self.console.print()
        self.console.print(f"[bold cyan]{text}[/bold cyan]")
        self.console.print()

    def task(self, task: str) -> None:
        """Log the user's task."""
        panel = Panel(
            f"[bold white]{task}[/bold white]",
            title="📋 Task",
            border_style="blue",
            box=box.ROUNDED,
        )
        self.console.print(panel)

    def action(
        self, agent: str, tool: str, args: dict, reasoning: Optional[str] = None
    ) -> None:
        """Log an agent action."""
        # Format the action
        args_str = ", ".join(f"{k}={v}" for k, v in args.items())
        action_text = f"[yellow]{tool}[/yellow]({args_str})"

        # Agent prefix with emoji
        agent_emoji = {
            "Coordinator": "🤖",
            "Navigator": "🧭",
            "FormFiller": "📝",
            "DataReader": "📊",
        }
        emoji = agent_emoji.get(agent, "🔧")

        # Print action
        self.console.print(f"\n{emoji} [bold]{agent}[/bold]: {action_text}")

        # Print reasoning if provided
        if reasoning:
            self.console.print(f"  [dim]→ {reasoning}[/dim]")

    def result(self, result: str, success: bool = True) -> None:
        """Log an action result."""
        color = "green" if success else "red"
        symbol = "✓" if success else "✗"

        # Summarize verbose results for minimal terminal output
        summarized = self._summarize_result(result)
        self.console.print(f"  [{color}]{symbol} {summarized}[/{color}]")

    def _summarize_result(self, result: str) -> str:
        """Summarize verbose tool results for clean terminal output."""
        # If result is short, keep it as-is
        if len(result) <= 100:
            return result

        # Detect page overview (contains element type headers)
        if "URL:" in result and any(keyword in result for keyword in ["BUTTONS:", "LINKS:", "COMBOBOXS:", "TEXTBOXS:"]):
            return self._summarize_page_overview(result)

        # Detect HTML content (contains HTML tags)
        if result.strip().startswith("<") and ">" in result[:50]:
            return self._summarize_html(result)

        # Detect truncation message
        if "TRUNCATED" in result:
            # Extract just the truncation info
            if "showing first" in result:
                parts = result.split("showing first")
                if len(parts) > 1:
                    return f"Content truncated: {parts[1].strip()}"

        # For other long results, show first 100 chars
        return result[:100] + "..."

    def _summarize_page_overview(self, overview: str) -> str:
        """Summarize page overview to show element counts only."""
        lines = overview.split("\n")

        # Extract URL and title
        url = ""
        title = ""
        for line in lines:
            if line.startswith("URL:"):
                url = line.replace("URL:", "").strip()
                # Truncate long URLs
                if len(url) > 50:
                    url = url[:47] + "..."
            elif line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
                # Truncate long titles
                if len(title) > 30:
                    title = title[:27] + "..."

        # Count element types
        element_counts = {}
        current_type = None
        for line in lines:
            # Detect element type headers (e.g., "BUTTONS:", "LINKS:")
            if line.strip().endswith("S:") and line.strip().isupper():
                current_type = line.strip().rstrip("S:")
                element_counts[current_type] = 0
            elif current_type and "... and" in line and "more" in line:
                # Extract count from "... and X more"
                try:
                    extra = int(line.split("... and")[1].split("more")[0].strip())
                    element_counts[current_type] += extra
                except:
                    pass
            elif current_type and line.strip().startswith("-"):
                element_counts[current_type] = element_counts.get(current_type, 0) + 1

        # Build summary
        parts = []
        if url:
            parts.append(f"URL: {url}")
        if title:
            parts.append(f"Title: {title}")

        # Format element counts
        if element_counts:
            counts_str = ", ".join(f"{count} {typ.lower()}{'s' if count != 1 else ''}"
                                   for typ, count in element_counts.items() if count > 0)
            if counts_str:
                parts.append(f"Elements: {counts_str}")

        return " | ".join(parts) if parts else "Page overview extracted"

    def _summarize_html(self, html: str) -> str:
        """Summarize HTML content."""
        # Check for truncation message
        if "[TRUNCATED" in html:
            try:
                # Extract info from truncation message
                truncate_msg = html.split("[TRUNCATED")[1].split("]")[0]
                return f"HTML extracted (truncated): {truncate_msg}"
            except:
                pass

        # Count approximate size
        length = len(html)
        if length > 1000:
            return f"HTML extracted: {length} chars"
        else:
            return f"HTML extracted: {length} chars"

    def error(self, error: str) -> None:
        """Log an error."""
        self.console.print(f"  [bold red]❌ Error: {error}[/bold red]")

    def info(self, message: str) -> None:
        """Log an info message."""
        self.console.print(f"  [dim]ℹ {message}[/dim]")

    def success(self, summary: str) -> None:
        """Log successful task completion."""
        panel = Panel(
            f"[bold green]{summary}[/bold green]",
            title="✅ Task Complete",
            border_style="green",
            box=box.ROUNDED,
        )
        self.console.print()
        self.console.print(panel)

    def failure(self, reason: str) -> None:
        """Log task failure."""
        panel = Panel(
            f"[bold red]{reason}[/bold red]",
            title="❌ Task Failed",
            border_style="red",
            box=box.ROUNDED,
        )
        self.console.print()
        self.console.print(panel)

    def step(self, step_num: int, total: int, description: str) -> None:
        """Log a step in a multi-step process."""
        self.console.print(f"\n[bold]Step {step_num}/{total}:[/bold] {description}")

    def subagent_start(self, subagent: str, subtask: str) -> None:
        """Log sub-agent delegation."""
        self.console.print(f"\n[bold magenta]→ Delegating to {subagent}[/bold magenta]")
        self.console.print(f"  [dim]Subtask: {subtask}[/dim]")

    def subagent_complete(self, subagent: str, result: str) -> None:
        """Log sub-agent completion."""
        self.console.print(f"[bold magenta]← {subagent} completed[/bold magenta]")
        self.console.print(f"  [dim]Result: {result}[/dim]")

    def warning(self, message: str) -> None:
        """Log a warning."""
        self.console.print(f"  [yellow]⚠ {message}[/yellow]")

    def separator(self) -> None:
        """Print a separator line."""
        self.console.print("[dim]" + "─" * 80 + "[/dim]")


# Global logger instance
logger = AgentLogger()
