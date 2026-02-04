"""Centralized UI module for dot-man using Rich."""

import sys
from typing import Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.theme import Theme
from rich.style import Style

# Custom theme for consistent branding
theme = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "highlight": "magenta bold",
    "dim": "dim",
    "key": "blue bold",
    "value": "white",
})

console = Console(theme=theme)
error_console = Console(theme=theme, stderr=True)

def print_banner(title: str, subtitle: str = "") -> None:
    """Print a styled banner."""
    content = f"[bold]{title}[/bold]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"

    console.print(
        Panel(
            content,
            border_style="cyan",
            padding=(0, 2),
        )
    )

def info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]ℹ[/info]  {message}")

def success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓[/success] {message}")

def warn(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]⚠[/warning] {message}")

def error(message: str, exit_code: int = 1) -> None:
    """Print an error message and optionally exit."""
    error_console.print(f"[error]✗ Error:[/error] {message}")
    if exit_code != 0:
        sys.exit(exit_code)

def confirm(question: str, default: bool = False) -> bool:
    """Ask a yes/no question."""
    return Confirm.ask(f"[bold]{question}[/bold]", default=default, console=console)

def ask(question: str, default: Any = None, choices: Optional[list[str]] = None, show_default: bool = True) -> Any:
    """Ask for user input."""
    return Prompt.ask(
        f"[bold]{question}[/bold]",
        default=default,
        choices=choices,
        show_default=show_default,
        console=console
    )

def suggest_command(mistake: str, choices: list[str], cutoff: float = 0.6) -> Optional[str]:
    """Suggest a command based on Levenshtein distance."""
    import difflib
    matches = difflib.get_close_matches(mistake, choices, n=1, cutoff=cutoff)
    return matches[0] if matches else None
