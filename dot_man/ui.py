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
_plain = False


def configure(
    *,
    quiet: bool = False,
    yes: bool = False,
    no_input: bool = False,
    no_color: bool = False,
    json: bool = False,
    plain: bool = False,
) -> None:
    """Apply the root group's global flags to the shared UI state.

    Called by the root CLI callback (and by tests) so behaviour is
    process-wide and deterministic. Always resets every flag so a flag
    can never leak from one invocation to the next. ``plain`` implies
    ``no_color`` (ASCII output should never carry ANSI codes).
    """
    global _quiet, _assume_yes, _no_input, _json_mode, _plain
    _quiet = quiet
    _assume_yes = yes
    _no_input = no_input
    _json_mode = json
    _plain = plain
    _build_consoles(no_color or plain)


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


def plain() -> bool:
    """Return True when ``--plain`` requested ASCII-only output."""
    return _plain


def icon(emoji: str, fallback: str) -> str:
    """Return ``emoji``, or a text ``fallback`` in ``--plain`` mode."""
    return fallback if _plain else emoji


def rule(title: str = "", char: str = "─") -> None:
    """Print a rule that spans the console width (Rich auto-fits it)."""
    if _quiet:
        return
    console.rule(title, characters=("-" if _plain else char))


def truncate_text(text: str, max_width: int) -> str:
    """Clip ``text`` to ``max_width`` terminal cells, adding an ellipsis.

    Cell-aware (unlike a raw slice), so wide/combining characters do not
    push a table column past the terminal edge.
    """
    from rich.text import Text

    if max_width < 1:
        return ""
    rich_text = Text(text)
    rich_text.truncate(max_width, overflow="ellipsis")
    return rich_text.plain


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
    marker = "[info]\\[i][/info]" if _plain else "[info]ℹ[/info]"
    console.print(f"{marker}  {message}")


def success(message: str) -> None:
    """Print a success message."""
    if _quiet:
        return
    marker = "[success]\\[ok][/success]" if _plain else "[success]✓[/success]"
    console.print(f"{marker} {message}")


def warn(message: str) -> None:
    """Print a warning message.

    Warnings are diagnostics, so they go to stderr — stdout stays
    reserved for data (and ``--json`` payloads).
    """
    if _quiet:
        return
    marker = "[warning]\\[!][/warning]" if _plain else "[warning]⚠[/warning]"
    error_console.print(f"{marker} {message}")


def error(message: str, exit_code: int = 1) -> None:
    """Print an error message and optionally exit.

    Errors are never suppressed by ``--quiet``.

    Exits via ``raise SystemExit`` (never ``sys.exit``) so exit codes
    stay consistent and testable across all commands.
    """
    marker = "[error]\\[x][/error]" if _plain else "[error]✗[/error]"
    error_console.print(f"{marker} Error: {message}")
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
    marker = "->" if _plain else "💡"
    console.print(f"[dim]{marker} {message}[/dim]")


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
    """Print a titled section with content, auto-fitted to the console."""
    if _quiet:
        return
    console.print()
    rule(title)
    if content:
        console.print(f"  {content}")
