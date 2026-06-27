"""Common utilities for dot-man CLI commands."""

import logging
import re
from functools import wraps
from typing import Callable

import click

from .. import ui
from ..constants import DOT_MAN_DIR, REPO_DIR
from ..core import GitManager
from ..secrets import PermanentRedactGuard, SecretGuard, SecretMatch
from .completions import (  # noqa: F401 — re-exports for backward compat
    _clear_all_caches,
    _clear_completion_cache,
    _set_git_runner,
    complete_branches,
    complete_commits,
    complete_config_keys,
    complete_profiles,
    complete_sections,
    complete_switch_args,
    complete_tags,
    complete_template_keys,
)


def error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    ui.error(message, exit_code)


def success(message: str) -> None:
    """Print success message."""
    ui.success(message)


def warn(message: str) -> None:
    """Print warning message."""
    ui.warn(message)


def handle_exception(exc: BaseException, context: str = "Operation") -> None:
    """Handle exceptions with user-friendly diagnostics."""
    from ..exceptions import DotManError, ErrorDiagnostic

    if isinstance(exc, DotManError):
        error(str(exc), exc.exit_code)
        return

    if isinstance(exc, KeyboardInterrupt):
        ui.console.print()
        warn("Operation cancelled by user")
        raise SystemExit(130)

    diagnostic = ErrorDiagnostic.from_exception(exc)  # type: ignore[arg-type]
    ui.console.print()
    ui.console.print(f"[red bold]{diagnostic.title}[/red bold]")
    ui.console.print(f"[red]{diagnostic.details}[/red]")
    ui.console.print()
    ui.console.print(f"[dim]💡 {diagnostic.suggestion}[/dim]")
    raise SystemExit(1)


class AliasedCommand(click.Command):
    """Custom Command class that supports aliases."""

    def __init__(self, *args, aliases=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._aliases = aliases or []

    @property
    def aliases(self):
        return self._aliases


def command(name=None, cls=None, aliases=None, **kwargs):
    """Decorator to create a command with optional aliases."""
    if cls is None:
        cls = AliasedCommand

    def decorator(f):
        return click.command(name=name, cls=cls, aliases=aliases, **kwargs)(f)

    return decorator


class DotManGroup(click.Group):
    """Custom Click Group to provide suggestions for typos."""

    def add_command(self, command, name=None):
        name = name or command.name
        super().add_command(command, name)
        if hasattr(command, "aliases") and command.aliases:
            for alias in command.aliases:
                super().add_command(command, alias)

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
        if not DOT_MAN_DIR.exists():
            ui.console.print()
            ui.print_banner("🎯 Welcome to dot-man!")
            ui.console.print()
            ui.console.print("[bold]The Dotfile Manager for Professionals[/bold]")
            ui.console.print()
            ui.console.print("[bold cyan]Coming from another tool?[/bold cyan]")
            ui.console.print(
                "  [cyan]dot-man import chezmoi[/cyan]    - Import from chezmoi"
            )
            ui.console.print(
                "  [cyan]dot-man import yadm[/cyan]       - Import from yadm"
            )
            ui.console.print(
                "  [cyan]dot-man import stow[/cyan]       - Import from GNU Stow"
            )
            ui.console.print(
                "  [cyan]dot-man import all[/cyan]        - Auto-detect and import"
            )
            ui.console.print()
            ui.console.print("[bold cyan]Get started:[/bold cyan]")
            ui.console.print(
                "  [cyan]dot-man init[/cyan]              - Initialize your dotfiles repository"
            )
            ui.console.print(
                "  [cyan]dot-man init --help[/cyan]       - See all init options"
            )
            ui.console.print()
            ui.console.print("[bold cyan]Quick overview:[/bold cyan]")
            ui.console.print(
                "  [cyan]dot-man add <path>[/cyan]         - Add files to track"
            )
            ui.console.print(
                "  [cyan]dot-man status[/cyan]            - View tracked files"
            )
            ui.console.print(
                "  [cyan]dot-man navigate <branch>[/cyan]  - Switch between configurations"
            )
            ui.console.print(
                "  [cyan]dot-man --help[/cyan]            - See all commands"
            )
            ui.console.print()
            ui.console.print("[dim]💡 Run 'dot-man init' to get started![/dim]")
            ui.console.print()
            raise SystemExit(1)

        if not REPO_DIR.exists() or not (REPO_DIR / ".git").exists():
            error("Repository not initialized. Run 'dot-man init' first.", exit_code=1)

        return func(*args, **kwargs)

    return wrapper


def parse_branch_arg(arg: str) -> dict:
    """Parse branch argument with @tag or commit SHA support."""
    match = re.match(r"^(.+)@(.+)$", arg)
    if match:
        base = match.group(1)
        target = match.group(2)

        if not base:
            base = "HEAD"

        if re.match(r"^[a-f0-9]{7,40}$", target):
            return {"type": "commit", "base": base, "target": target}

        return {"type": "tag", "base": base, "target": target}

    if re.match(r"^[a-f0-9]{7,40}$", arg):
        return {"type": "commit", "base": "HEAD", "target": arg}

    try:
        git = GitManager()
        if arg in git.list_tags():
            return {"type": "tag", "base": "HEAD", "target": arg}
    except Exception as e:
        logging.debug(f"Could not check tags: {e}")

    return {"type": "branch", "base": arg, "target": arg}


class BranchParamType(click.ParamType):
    """Parameter type that accepts branch, branch@tag, or commit SHA."""

    name = "branch"

    def convert(self, value, param, ctx):
        if not value:
            return None
        return parse_branch_arg(value)


BRANCH = BranchParamType()


def get_secret_handler() -> Callable[[SecretMatch], str]:
    """Get a secret handler that prompts the user for action."""
    guard = SecretGuard()
    permanent_guard = PermanentRedactGuard()

    def handle_secret(match: SecretMatch) -> str:
        if permanent_guard.should_redact(
            match.file, match.line_content, match.pattern_name
        ):
            return "REDACT"

        if guard.is_allowed(match.file, match.line_content, match.pattern_name):
            return "IGNORE"

        ui.console.print()
        ui.warn("Potential secret detected!")
        ui.console.print(f"File: [cyan]{match.file}[/cyan]")
        ui.console.print(f"Line {match.line_number}: {match.line_content[:80]}...")
        ui.console.print(
            f"Pattern: {match.pattern_name} (severity: {match.severity.value})"
        )
        ui.console.print()

        ui.console.print("Choose how to handle this secret:")
        ui.console.print("  1. [dim]Ignore (skip it this time)[/dim]")
        ui.console.print(
            "  2. [yellow]Protect (replace with ***REDACTED*** this time)[/yellow]"
        )
        ui.console.print(
            "  3. [blue]Add to skip list (skip this line every time)[/blue]"
        )
        ui.console.print("  4. [red]Protect forever (always replace in repo)[/red]")
        ui.console.print()

        choices = ["1", "2", "3", "4"]
        choice = ui.ask("Enter choice", choices=choices, default="2")

        if choice == "1":
            return "IGNORE"
        elif choice == "2":
            return "REDACT"
        elif choice == "3":
            guard.add_allowed(match.file, match.line_content, match.pattern_name)
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
