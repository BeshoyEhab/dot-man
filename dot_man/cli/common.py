"""Common utilities for dot-man CLI commands."""

import logging
import re
from enum import IntEnum
from functools import wraps
from typing import Callable

import click

from .. import constants, ui
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


class ExitCode(IntEnum):
    """Canonical process exit codes for all dot-man commands.

    All error paths must exit via ``raise SystemExit(ExitCode.X)``,
    ``error(..., exit_code=...)``, or ``handle_exception()`` — never
    bare ``sys.exit()`` — so codes stay consistent and testable.
    """

    OK = 0
    ERROR = 1
    USAGE = 2
    CONFIG = 7
    AUDIT = 50
    INTERRUPTED = 130


HAPPY_PATH_COMMANDS = ("init", "add", "status", "navigate", "deploy", "doctor")
"""Commands shown by `dot-man help` and bare `--help`; everything else
lives in `dot-man help-all`. Aliases and deprecated shims are never
listed in the short view."""


def error(message: str, exit_code: int = ExitCode.ERROR) -> None:
    """Print error message and exit (callers must not rely on a return,
    except the exit_code=0 print-only path)."""
    ui.error(message, exit_code)


def success(message: str) -> None:
    """Print success message."""
    ui.success(message)


def warn(message: str) -> None:
    """Print warning message."""
    ui.warn(message)


def warn_if_dirty(ops, current_branch: str) -> None:
    """Warn that uncommitted changes will be left behind by a checkout.

    Shared by every command that moves HEAD (log checkout, tag switch),
    so uncommitted work is never abandoned silently.
    """
    if ops.git.is_dirty():
        ui.error_console.print(
            f"[yellow]Warning:[/yellow] You have uncommitted changes on branch "
            f"[bold]{current_branch}[/bold]"
        )
        ui.error_console.print("  These changes will NOT be saved.")
        ui.error_console.print()


def handle_exception(exc: BaseException, context: str = "Operation") -> None:
    """Handle exceptions with user-friendly diagnostics."""
    from ..exceptions import DotManError, ErrorDiagnostic

    if isinstance(exc, DotManError):
        error(str(exc), exc.exit_code)
        return

    if isinstance(exc, KeyboardInterrupt):
        ui.error_console.print()
        warn("Operation cancelled by user")
        raise SystemExit(ExitCode.INTERRUPTED)

    diagnostic = ErrorDiagnostic.from_exception(exc)
    ui.error_console.print()
    ui.error_console.print(f"[red bold]{diagnostic.title}[/red bold]")
    ui.error_console.print(f"[red]{diagnostic.details}[/red]")
    ui.error_console.print()
    ui.error_console.print(f"[dim]💡 {diagnostic.suggestion}[/dim]")
    raise SystemExit(ExitCode.ERROR)


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

        ctx.exit(ExitCode.USAGE)

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """List happy-path commands only.

        Aliases and deprecated shims stay hidden here; `help-all` shows
        the exhaustive listing via the base-class implementation.
        """
        rows = []
        for name in HAPPY_PATH_COMMANDS:
            cmd = self.get_command(ctx, name)
            if cmd is None or cmd.hidden:
                continue
            rows.append((name, cmd))

        if rows:
            limit = formatter.width - 6 - max(len(row[0]) for row in rows)
            with formatter.section("Commands"):
                formatter.write_dl(
                    [(name, cmd.get_short_help_str(limit)) for name, cmd in rows]
                )
        canonical = {cmd.name for cmd in self.commands.values()}
        formatter.write_text(
            f"  Run 'dot-man help-all' to see all {len(canonical)} commands."
        )

    def invoke(self, ctx):
        """Invoke a subcommand with centralized error handling.

        Any exception escaping a subcommand is routed through
        :func:`handle_exception` for consistent diagnostics and exit
        codes. Click control-flow exceptions (``ClickException``,
        ``Abort``, ``Exit``) and ``SystemExit`` pass through untouched
        so ``--help``, usage errors, and deliberate exits keep working.
        """
        try:
            return super().invoke(ctx)
        except (SystemExit, click.ClickException, click.Abort, click.exceptions.Exit):
            raise
        except KeyboardInterrupt as e:
            handle_exception(e)
        except Exception as e:
            handle_exception(e)


def sync_shared_sections(ops) -> None:
    """Propagate ``shared = true`` sections to non-overriding branches.

    Called after a commit was created on the current branch. Failures
    are reported but never abort the surrounding command.
    """
    try:
        from ..shared_sync import SharedSectionSync

        report = SharedSectionSync(ops).sync()
        if not report.shared_sections:
            return
        for branch, sections in report.propagated.items():
            ui.console.print(
                f"  [dim]↔ shared → '{branch}': {', '.join(sections)}[/dim]"
            )
        for branch, reason in report.errors.items():
            warn(f"Shared-section sync failed for '{branch}': {reason}")
    except Exception as e:
        logging.debug("Shared-section sync skipped: %s", e)


def require_init(func):
    """Decorator to require initialization before running command."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not constants.get_dot_man_dir().exists():
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
            raise SystemExit(ExitCode.ERROR)

        if (
            not constants.get_repo_dir().exists()
            or not (constants.get_repo_dir() / ".git").exists()
        ):
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
        ui.console.print(f"Line {match.line_number}: {match.masked_line[:80]}...")
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
