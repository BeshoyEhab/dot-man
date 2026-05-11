"""Common utilities for dot-man CLI commands."""

from functools import wraps
from typing import Callable

import click

from .. import ui
from ..constants import DOT_MAN_DIR, REPO_DIR
from ..core import GitManager
from ..secrets import PermanentRedactGuard, SecretGuard, SecretMatch


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
    """Handle exceptions with user-friendly diagnostics.

    Uses ErrorDiagnostic to categorize errors and provide helpful suggestions.
    This is the centralized exception handler for all CLI commands.
    """
    from ..exceptions import DotManError, ErrorDiagnostic

    if isinstance(exc, DotManError):
        error(str(exc), exc.exit_code)
        return

    if isinstance(exc, KeyboardInterrupt):
        ui.console.print()
        warn("Operation cancelled by user")
        raise SystemExit(130)

    # At this point exc is known to be an Exception (not KeyboardInterrupt)
    diagnostic = ErrorDiagnostic.from_exception(exc)  # type: ignore[arg-type]
    ui.console.print()
    ui.console.print(f"[red bold]{diagnostic.title}[/red bold]")
    ui.console.print(f"[red]{diagnostic.details}[/red]")
    ui.console.print()
    ui.console.print(f"[dim]💡 {diagnostic.suggestion}[/dim]")
    raise SystemExit(1)


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


import re


def parse_branch_arg(arg: str) -> dict:
    """Parse branch argument with @tag or commit SHA support.

    Args:
        arg: Branch string like "work", "work@tag", or "abc1234"

    Returns:
        dict with keys: type (branch|tag|commit), base, target
    """
    # Pattern: branch@tag
    match = re.match(r"^(.+)@(.+)$", arg)
    if match:
        base = match.group(1)
        target = match.group(2)

        if not base:
            base = "HEAD"

        # Check if target looks like a commit SHA (7+ hex chars)
        if re.match(r"^[a-f0-9]{7,40}$", target):
            return {"type": "commit", "base": base, "target": target}

        # Otherwise it's a tag
        return {"type": "tag", "base": base, "target": target}

    # Check if entire arg looks like a commit SHA
    if re.match(r"^[a-f0-9]{7,40}$", arg):
        return {"type": "commit", "base": "HEAD", "target": arg}

    # Check if arg is a tag (before checking if it's a branch)
    try:
        git = GitManager()
        if arg in git.list_tags():
            return {"type": "tag", "base": "HEAD", "target": arg}
    except Exception as e:
        import logging

        logging.debug(f"Could not check tags: {e}")

    # Plain branch name
    return {"type": "branch", "base": arg, "target": arg}


def complete_switch_args(ctx, param, incomplete):
    """Shell completion callback for switch (branches, tags, commits)."""
    try:
        git = GitManager()
        results = []

        # Add branches
        branches = git.list_branches()
        for b in branches:
            if b.startswith(incomplete):
                results.append(b)
            # Also add branch@tag suggestions for tags
            if "@" in incomplete:
                prefix = incomplete.split("@")[0]
                if b.startswith(prefix) and b != prefix:
                    for tag in git.list_tags():
                        if tag.startswith(
                            incomplete.split("@")[1]
                            if len(incomplete.split("@")) > 1
                            else ""
                        ):
                            results.append(f"{b}@{tag}")

        # Add tags
        tags = git.list_tags()
        for t in tags:
            if t.startswith(incomplete):
                results.append(t)
            if "@" in incomplete:
                prefix = incomplete.split("@")[0]
                if prefix and t.startswith(incomplete.split("@")[1]):
                    results.append(f"{prefix}@{t}")

        # Add recent commits (first 7 chars)
        for commit in git.get_commits(count=10):
            if commit["sha"].startswith(incomplete):
                results.append(commit["sha"])

        return list(set(results))
    except Exception as e:
        import logging

        logging.debug(f"Completion error: {e}")
        return []


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        git = GitManager()
        branches = git.list_branches()
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        return []


def complete_tags(ctx, param, incomplete):
    """Shell completion callback for tags."""
    try:
        git = GitManager()
        tags = git.list_tags()
        return [t for t in tags if t.startswith(incomplete)]
    except Exception:
        return []


def complete_commits(ctx, param, incomplete):
    """Shell completion callback for commits."""
    try:
        git = GitManager()
        commits = git.get_commits(count=50)
        return [c["sha"][:7] for c in commits if c["sha"].startswith(incomplete)]
    except Exception:
        return []


def complete_template_keys(ctx, param, incomplete):
    """Shell completion callback for template keys."""
    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        templates = gc.get_all_templates()
        return [k for k in templates.keys() if k.startswith(incomplete)]
    except Exception:
        return []


def complete_config_keys(ctx, param, incomplete):
    """Shell completion callback for config keys."""
    try:
        from ..global_config import GlobalConfig

        GlobalConfig()  # validate it loads
        keys = [
            "dot-man.current_branch",
            "remote.url",
            "security.strict_mode",
            "switch.default_behavior",
            "secrets_filter_enabled",
        ]
        return [k for k in keys if k.startswith(incomplete)]
    except Exception:
        return []


def complete_profiles(ctx, param, incomplete):
    """Shell completion callback for profiles."""
    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        profiles = gc._data.get("profiles", {})
        return [k for k in profiles.keys() if k.startswith(incomplete)]
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
