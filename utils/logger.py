from typing import Optional

from rich.console import Console
from rich.panel import Panel
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
        args_str = ", ".join(f"{k}={v}" for k, v in args.items())
        action_text = f"[yellow]{tool}[/yellow]({args_str})"

        agent_emoji = {
            "Coordinator": "🤖",
            "Navigator": "🧭",
            "FormFiller": "📝",
            "DataReader": "📊",
        }
        emoji = agent_emoji.get(agent, "🔧")

        self.console.print(f"\n{emoji} [bold]{agent}[/bold]: {action_text}")

        if reasoning:
            self.console.print(f"  [dim]→ {reasoning}[/dim]")

    def result(self, result: str, success: bool = True) -> None:
        """Log an action result."""
        pass

    def _summarize_result(self, result: str) -> str:
        """Summarize verbose tool results for clean terminal output."""
        if len(result) <= 100:
            return result

        element_keywords = ["BUTTONS:", "LINKS:", "COMBOBOXS:", "TEXTBOXS:"]

        if "URL:" in result and any(kw in result for kw in element_keywords):
            return self._summarize_page_overview(result)

        if result.strip().startswith("<") and ">" in result[:50]:
            return self._summarize_html(result)

        if "TRUNCATED" in result and "showing first" in result:
            parts = result.split("showing first")
            return f"Content truncated: {parts[1].strip()}" if len(parts) > 1 else result[:100] + "..."

        return result[:100] + "..."

    def _summarize_page_overview(self, overview: str) -> str:
        """Summarize page overview to show element counts only."""
        lines = overview.split("\n")

        url, title = self._extract_page_metadata(lines)
        element_counts = self._count_elements_by_type(lines)

        parts = []
        if url:
            parts.append(f"URL: {url}")
        if title:
            parts.append(f"Title: {title}")

        if element_counts:
            counts_str = ", ".join(
                f"{count} {typ.lower()}{'s' if count != 1 else ''}"
                for typ, count in element_counts.items()
                if count > 0
            )
            if counts_str:
                parts.append(f"Elements: {counts_str}")

        return " | ".join(parts) if parts else "Page overview extracted"

    def _extract_page_metadata(self, lines: list) -> tuple:
        """Extract URL and title from overview lines."""
        url = title = ""

        for line in lines:
            if line.startswith("URL:"):
                url = line.replace("URL:", "").strip()
                url = url[:47] + "..." if len(url) > 50 else url
            elif line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
                title = title[:27] + "..." if len(title) > 30 else title

        return url, title

    def _count_elements_by_type(self, lines: list) -> dict:
        """Count elements by type from overview lines."""
        element_counts = {}
        current_type = None

        for line in lines:
            stripped = line.strip()
            if stripped.endswith("S:") and stripped.isupper():
                current_type = stripped.rstrip("S:")
                element_counts[current_type] = 0
            elif current_type:
                if "... and" in line and "more" in line:
                    try:
                        extra = int(line.split("... and")[1].split("more")[0].strip())
                        element_counts[current_type] += extra
                    except:
                        pass
                elif stripped.startswith("-"):
                    element_counts[current_type] = element_counts.get(current_type, 0) + 1

        return element_counts

    def _summarize_html(self, html: str) -> str:
        """Summarize HTML content."""
        if "[TRUNCATED" in html:
            try:
                truncate_msg = html.split("[TRUNCATED")[1].split("]")[0]
                return f"HTML extracted (truncated): {truncate_msg}"
            except:
                pass

        return f"HTML extracted: {len(html)} chars"

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

    def pause(self, message: str) -> None:
        """Log pause with action required."""
        panel = Panel(
            f"[bold yellow]⏸️  PAUSED - Human Action Required[/bold yellow]\n\n"
            f"➡️  {message}\n\n"
            f"[dim]👉 Please complete this action in the browser window,\n"
            f"   then press Enter to continue...[/dim]",
            border_style="yellow",
            box=box.ROUNDED,
        )
        self.console.print()
        self.console.print(panel)

    def confirm(self, message: str, risk_level: str) -> None:
        """Log confirmation request for destructive actions."""
        emoji_map = {"financial": "💰", "deletion": "🗑️", "irreversible": "⚠️"}
        emoji = emoji_map.get(risk_level, "⚠️")

        panel = Panel(
            f"[bold red]{emoji}  CONFIRMATION REQUIRED - {risk_level.upper()} ACTION[/bold red]\n\n"
            f"➡️  {message}\n\n"
            f"[bold]⚠️  This action may be irreversible![/bold]",
            border_style="red",
            box=box.ROUNDED,
        )
        self.console.print()
        self.console.print(panel)

    def prompt(self, message: str) -> None:
        """Log user prompt."""
        self.console.print(f"\n[bold cyan]{message}[/bold cyan]")

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


logger = AgentLogger()
