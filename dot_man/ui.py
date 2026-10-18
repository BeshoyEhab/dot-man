"""Centralized UI module for dot-man using Rich."""

from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.theme import Theme

# Custom theme for consistent branding
theme = Theme(
    {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red bold",
        "highlight": "magenta bold",
        "dim": "dim",
        "key": "blue bold",
        "value": "white",
    }
)

console = Console(theme=theme)
error_console = Console(theme=theme, stderr=True)


def _build_consoles(no_color: bool = False) -> None:
    """(Re)create the module consoles so ``--no-color`` takes effect."""
    global console, error_console
    console = Console(theme=theme, no_color=no_color)
    error_console = Console(theme=theme, stderr=True, no_color=no_color)


# Process-wide global-flag state, set from the root CLI group.
_quiet = False
_assume_yes = False
_no_input = False
_json_mode = False


def configure(
    *,
    quiet: bool = False,
    yes: bool = False,
    no_input: bool = False,
    no_color: bool = False,
    json: bool = False,
) -> None:
    """Apply the root group's global flags to the shared UI state.

    Called by the root CLI callback (and by tests) so behaviour is
    process-wide and deterministic. Always resets every flag so a flag
    can never leak from one invocation to the next.
    """
    global _quiet, _assume_yes, _no_input, _json_mode
    _quiet = quiet
    _assume_yes = yes
    _no_input = no_input
    _json_mode = json
    _build_consoles(no_color)


def is_quiet() -> bool:
    """Return True when ``--quiet`` suppressed informational output."""
    return _quiet


def json_mode() -> bool:
    """Return True when ``--json`` requested machine-readable output."""
    return _json_mode


def assume_yes() -> bool:
    """Return True when ``--yes`` auto-confirms prompts."""
    return _assume_yes


def no_input_enabled() -> bool:
    """Return True when ``--no-input`` forbids interactive prompts."""
    return _no_input


def print_banner(title: str, subtitle: str = "") -> None:
    """Print a styled banner."""
    if _quiet:
        return
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
    if _quiet:
        return
    console.print(f"[info]ℹ[/info]  {message}")


def success(message: str) -> None:
    """Print a success message."""
    if _quiet:
        return
    console.print(f"[success]✓[/success] {message}")


def warn(message: str) -> None:
    """Print a warning message."""
    if _quiet:
        return
    console.print(f"[warning]⚠[/warning] {message}")


def error(message: str, exit_code: int = 1) -> None:
    """Print an error message and optionally exit.

    Errors are never suppressed by ``--quiet``.

    Exits via ``raise SystemExit`` (never ``sys.exit``) so exit codes
    stay consistent and testable across all commands.
    """
    error_console.print(f"[error]✗ Error:[/error] {message}")
    if exit_code != 0:
        raise SystemExit(exit_code)


def confirm(question: str, default: bool = False) -> bool:
    """Ask a yes/no question, honouring ``--yes`` and ``--no-input``."""
    if _assume_yes:
        return True
    if _no_input:
        from .cli.common import ExitCode

        error(
            "A confirmation prompt is required but --no-input was given.",
            exit_code=ExitCode.USAGE,
        )
        return False  # unreachable: error() exits
    return Confirm.ask(f"[bold]{question}[/bold]", default=default, console=console)


def ask(
    question: str,
    default: Any = None,
    choices: Optional[list[str]] = None,
    show_default: bool = True,
) -> Any:
    """Ask for user input, honouring ``--no-input``."""
    if _no_input:
        from .cli.common import ExitCode

        error(
            "Interactive input is required but --no-input was given.",
            exit_code=ExitCode.USAGE,
        )
        return default  # unreachable: error() exits
    return Prompt.ask(
        f"[bold]{question}[/bold]",
        default=default,
        choices=choices,
        show_default=show_default,
        console=console,
    )


def suggest_command(
    mistake: str, choices: list[str], cutoff: float = 0.6
) -> Optional[str]:
    """Suggest a command based on Levenshtein distance."""
    import difflib

    matches = difflib.get_close_matches(mistake, choices, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def hint(message: str) -> None:
    """Print a helpful hint or suggestion."""
    if _quiet:
        return
    console.print(f"[dim]💡 {message}[/dim]")


def next_steps(steps: list[str]) -> None:
    """Print 'what to do next' suggestions.

    Args:
        steps: List of suggested next actions with commands
    """
    if _quiet or not steps:
        return

    console.print()
    console.print("[bold]📋 Next Steps:[/bold]")
    for i, step in enumerate(steps, 1):
        console.print(f"  [cyan]{i}.[/cyan] {step}")


def section(title: str, content: str) -> None:
    """Print a titled section with content."""
    if _quiet:
        return
    console.print()
    width = max(len(title) + 4, 40)
    console.print(f"[bold cyan]┌{'─' * width}┐[/bold cyan]")
    console.print(
        f"[bold cyan]│[/bold cyan]  {title}{' ' * (width - len(title) - 2)}[bold cyan]│[/bold cyan]"
    )
    console.print(f"[bold cyan]└{'─' * width}┘[/bold cyan]")
    if content:
        console.print(f"  {content}")
