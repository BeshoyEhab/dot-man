"""Common utilities for dot-man CLI commands."""

import sys
from functools import wraps
from typing import Callable

import click

from .. import ui
from ..constants import DOT_MAN_DIR, REPO_DIR
from ..core import GitManager
from ..secrets import SecretGuard, SecretMatch, PermanentRedactGuard


def error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    ui.error(message, exit_code)


def success(message: str) -> None:
    """Print success message."""
    ui.success(message)


def warn(message: str) -> None:
    """Print warning message."""
    ui.warn(message)


class DotManGroup(click.Group):
    """Custom Click Group to provide suggestions for typos."""

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        matches = [cmd for cmd in self.list_commands(ctx)]
        suggestion = ui.suggest_command(cmd_name, matches)

        ui.error(f"Unknown command '{cmd_name}'", exit_code=0)
        if suggestion:
            ui.warn(f"Did you mean '{suggestion}'?")

        ctx.exit(2)


def require_init(func):
    """Decorator to require initialization before running command."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not DOT_MAN_DIR.exists() or not REPO_DIR.exists():
            error("Not initialized. Run 'dot-man init' first.", exit_code=1)
        return func(*args, **kwargs)

    return wrapper


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        git = GitManager()
        branches = git.list_branches()
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        return []


def get_secret_handler() -> Callable[[SecretMatch], str]:
    """Get a secret handler that prompts the user for action."""
    guard = SecretGuard()
    permanent_guard = PermanentRedactGuard()

    def handle_secret(match: SecretMatch) -> str:
        # Check if should be permanently redacted
        if permanent_guard.should_redact(
            match.file, match.line_content, match.pattern_name
        ):
            return "REDACT"

        # Check if already in skip list
        if guard.is_allowed(match.file, match.line_content, match.pattern_name):
            return "IGNORE"

        # Show the secret to user
        ui.console.print()
        ui.warn("Potential secret detected!")
        ui.console.print(f"File: [cyan]{match.file}[/cyan]")
        ui.console.print(f"Line {match.line_number}: {match.line_content[:80]}...")
        ui.console.print(
            f"Pattern: {match.pattern_name} (severity: {match.severity.value})"
        )
        ui.console.print()

        # Options
        ui.console.print("Choose how to handle this secret:")
        ui.console.print("  1. [dim]Ignore (skip it this time)[/dim]")
        ui.console.print(
            "  2. [yellow]Protect (replace with ***REDACTED*** this time)[/yellow]"
        )
        ui.console.print("  3. [blue]Add to skip list (skip this line every time)[/blue]")
        ui.console.print("  4. [red]Protect forever (always replace in repo)[/red]")
        ui.console.print()

        choices = ["1", "2", "3", "4"]
        choice = ui.ask("Enter choice", choices=choices, default="2")

        if choice == "1":
            return "IGNORE"
        elif choice == "2":
            return "REDACT"
        elif choice == "3":
            guard.add_allowed(
                match.file, match.line_content, match.pattern_name
            )
            ui.info("Added to skip list.")
            return "IGNORE"
        elif choice == "4":
            permanent_guard.add_permanent_redact(
                match.file, match.line_content, match.pattern_name
            )
            ui.warn("Will always redact this secret.")
            return "REDACT"
        return "REDACT"

    return handle_secret
