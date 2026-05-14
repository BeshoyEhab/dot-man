"""Common utilities for dot-man CLI commands."""

import json
import os
import re
import subprocess
import time
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
        if not DOT_MAN_DIR.exists():
            ui.console.print()
            ui.print_banner("🎯 Welcome to dot-man!")
            ui.console.print()
            ui.console.print("[bold]The Dotfile Manager for Professionals[/bold]")
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


_COMPLETION_CACHE_TTL = 10
_COMPLETION_CACHE_FILE = REPO_DIR / ".dotman" / "completion_cache.json"

_git_runner = None
_memory_cache: dict | None = None
_memory_cache_time: float = 0
_template_cache: list[str] | None = None
_config_keys_cache: list[str] | None = None
_profiles_cache: list[str] | None = None


def _set_git_runner(runner):
    """Set custom git runner for testing."""
    global _git_runner
    _git_runner = runner


def _run_git(args, cwd=REPO_DIR, timeout=2):
    """Run git command, using custom runner if set."""
    if _git_runner is not None:
        return _git_runner(args, cwd, timeout)
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def _get_completion_cache() -> dict:
    """Load completion cache from memory or file."""
    global _memory_cache, _memory_cache_time

    if (
        _memory_cache is not None
        and time.time() - _memory_cache_time < _COMPLETION_CACHE_TTL
    ):
        return _memory_cache

    try:
        if not REPO_DIR.exists():
            _memory_cache = {}
            _memory_cache_time = time.time()
            return _memory_cache
        if _COMPLETION_CACHE_FILE.exists():
            mtime = os.path.getmtime(_COMPLETION_CACHE_FILE)
            if time.time() - mtime < _COMPLETION_CACHE_TTL:
                _memory_cache = json.loads(_COMPLETION_CACHE_FILE.read_text())
                _memory_cache_time = time.time()
                return _memory_cache
    except Exception:
        pass

    _memory_cache = {}
    _memory_cache_time = time.time()
    return _memory_cache


def _save_completion_cache(data: dict) -> None:
    """Save completion cache to memory and file."""
    global _memory_cache, _memory_cache_time
    _memory_cache = data
    _memory_cache_time = time.time()

    try:
        if not REPO_DIR.exists():
            return
        _COMPLETION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _COMPLETION_CACHE_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def _clear_completion_cache() -> None:
    """Clear completion cache for testing."""
    global _memory_cache, _memory_cache_time
    _memory_cache = None
    _memory_cache_time = 0

    try:
        if _COMPLETION_CACHE_FILE.exists():
            _COMPLETION_CACHE_FILE.unlink()
    except Exception:
        pass


def _clear_all_caches() -> None:
    """Clear all completion caches including in-memory."""
    global _memory_cache, _memory_cache_time
    global _template_cache, _config_keys_cache, _profiles_cache

    _memory_cache = None
    _memory_cache_time = 0
    _template_cache = None
    _config_keys_cache = None
    _profiles_cache = None

    try:
        if _COMPLETION_CACHE_FILE.exists():
            _COMPLETION_CACHE_FILE.unlink()
    except Exception:
        pass


def parse_branch_arg(arg: str) -> dict:
    """Parse branch argument with @tag or commit SHA support.

    Args:
        arg: Branch string like "work", "work@tag", or "abc1234"

    Returns:
        dict with keys: type (branch|tag|commit), base, target
    """
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
        import logging

        logging.debug(f"Could not check tags: {e}")

    return {"type": "branch", "base": arg, "target": arg}


def complete_switch_args(ctx, param, incomplete):
    """Shell completion callback for switch (branches, tags, commits).

    Returns tuples (value, description) for shell completion.
    Order: branches first, then tags, then commits (git checkout style).
    """
    try:
        return _complete_navigate_items(incomplete)
    except Exception as e:
        import logging

        logging.debug(f"Completion error: {e}")
        return []


def _complete_navigate_items(
    incomplete: str,
) -> "list[click.shell_completion.CompletionItem]":
    """Get completion items for navigate command with context.

    Uses cache and lightweight git commands for performance.
    Order: branches -> tags -> commits (like git checkout)
    """
    from click.shell_completion import CompletionItem

    try:
        cache = _get_completion_cache()
        items: list[CompletionItem] = []

        if "branches" not in cache or "current_branch" not in cache:
            result = _run_git(["git", "branch", "--list", "--format=%(refname:short)"])
            branches = [
                b.strip() for b in result.stdout.strip().split("\n") if b.strip()
            ]

            result = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            current_branch = result.stdout.strip() or "HEAD"

            cache["branches"] = branches
            cache["current_branch"] = current_branch
        else:
            branches = cache["branches"]
            current_branch = cache["current_branch"]

        branch_items: list[CompletionItem] = []
        other_branches: list[CompletionItem] = []
        for b in branches:
            if b.startswith(incomplete):
                if b == current_branch:
                    branch_items.append(CompletionItem(b, help="current branch"))
                else:
                    other_branches.append(CompletionItem(b, help="branch"))

        other_branches.sort(key=lambda x: x.value.lower())
        items.extend(branch_items)
        items.extend(other_branches)

        if "tags" not in cache:
            result = _run_git(["git", "tag", "-l"])
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
            cache["tags"] = tags
        else:
            tags = cache["tags"]

        tag_items: list[CompletionItem] = []
        for t in tags:
            if t.startswith(incomplete):
                result = _run_git(["git", "rev-parse", f"{t}^{{commit}}"])
                commit_hash = (
                    result.stdout.strip()[:7] if result.returncode == 0 else ""
                )
                tag_items.append(CompletionItem(t, help=f"tag → {commit_hash}"))

        tag_items.sort(key=lambda x: x.value.lower())
        items.extend(tag_items)

        if "commits" not in cache:
            result = _run_git(
                ["git", "log", "--oneline", "-n", "20", "--format=%H %s"], timeout=3
            )
            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({"sha": parts[0][:7], "message": parts[1][:30]})
            cache["commits"] = commits
        else:
            commits = cache["commits"]

        commit_items: list[CompletionItem] = []
        for c in commits:
            if c["sha"].startswith(incomplete):
                commit_items.append(CompletionItem(c["sha"], help=f"{c['message']}..."))

        items.extend(commit_items)

        if "@" in incomplete:
            parts = incomplete.split("@", 1)
            if parts[0] in branches:
                for t in tags:
                    if t.startswith(parts[1] if len(parts) > 1 else ""):
                        result = _run_git(["git", "rev-parse", f"{t}^{{commit}}"])
                        commit_hash = (
                            result.stdout.strip()[:7] if result.returncode == 0 else ""
                        )
                        items.append(
                            CompletionItem(
                                f"{parts[0]}@{t}", help=f"tag at {commit_hash}"
                            )
                        )

        _save_completion_cache(cache)
        return items
    except Exception:
        return []


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        cache = _get_completion_cache()
        if "branches" not in cache:
            result = _run_git(["git", "branch", "--list", "--format=%(refname:short)"])
            branches = [
                b.strip() for b in result.stdout.strip().split("\n") if b.strip()
            ]
            cache["branches"] = branches
            _save_completion_cache(cache)
        else:
            branches = cache["branches"]
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        return []


def complete_tags(ctx, param, incomplete):
    """Shell completion callback for tags."""
    try:
        cache = _get_completion_cache()
        if "tags" not in cache:
            result = _run_git(["git", "tag", "-l"])
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
            cache["tags"] = tags
            _save_completion_cache(cache)
        else:
            tags = cache["tags"]
        return [t for t in tags if t.startswith(incomplete)]
    except Exception:
        return []


def complete_commits(ctx, param, incomplete):
    """Shell completion callback for commits."""
    try:
        cache = _get_completion_cache()
        if "commits_all" not in cache:
            result = _run_git(
                ["git", "log", "--oneline", "-n", "50", "--format=%h"], timeout=3
            )
            commits = [
                c.strip() for c in result.stdout.strip().split("\n") if c.strip()
            ]
            cache["commits_all"] = commits
            _save_completion_cache(cache)
        else:
            commits = cache["commits_all"]
        return [c for c in commits if c.startswith(incomplete)]
    except Exception:
        return []


def complete_template_keys(ctx, param, incomplete):
    """Shell completion callback for template keys."""
    global _template_cache

    if _template_cache is not None:
        return [k for k in _template_cache if k.startswith(incomplete)]

    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        templates = gc.get_all_templates()
        _template_cache = list(templates.keys())
        return [k for k in _template_cache if k.startswith(incomplete)]
    except Exception:
        return []


def complete_config_keys(ctx, param, incomplete):
    """Shell completion callback for config keys."""
    global _config_keys_cache

    if _config_keys_cache is not None:
        return [k for k in _config_keys_cache if k.startswith(incomplete)]

    try:
        keys = [
            "dot-man.current_branch",
            "remote.url",
            "security.strict_mode",
            "switch.default_behavior",
            "secrets_filter_enabled",
        ]
        _config_keys_cache = keys
        return [k for k in keys if k.startswith(incomplete)]
    except Exception:
        return []


def complete_profiles(ctx, param, incomplete):
    """Shell completion callback for profiles."""
    global _profiles_cache

    if _profiles_cache is not None:
        return [k for k in _profiles_cache if k.startswith(incomplete)]

    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        profiles = gc._data.get("profiles", {})
        _profiles_cache = list(profiles.keys())
        return [k for k in _profiles_cache if k.startswith(incomplete)]
    except Exception:
        return []


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
