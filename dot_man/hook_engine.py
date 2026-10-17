"""Unified hook resolution and execution (the executable hook schema)."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import constants, ui
from .constants import DOT_MAN_DIR, REPO_DIR
from .exceptions import ConfigurationError

HOOKS_DIR = DOT_MAN_DIR / "hooks"

HOOK_FILE_PATTERN = re.compile(r"(?<![\w/:\\])file:([^\s;|&\"']+)")
HOOK_FILE_ESCAPE_PATTERN = re.compile(r"\\(file:[^\s;|&\"']+)")


@dataclass(frozen=True)
class HookContext:
    """Values available to hook placeholder resolution."""

    section_name: str = ""
    config_name: str = ""
    config_root: str = ""
    paths: tuple[str, ...] = field(default_factory=tuple)
    branch: str = ""

    def placeholders(self) -> dict[str, str]:
        """Canonical vocabulary, shell-quoted to neutralize injection.

        Hook strings come from repo config and are run through ``sh -c``. Raw
        interpolation of a branch/path value (e.g. a branch named
        ``main; touch /tmp/pwned``) let a crafted value run arbitrary commands,
        so every value is passed through ``shlex.quote`` — normally safe values
        are left untouched. ``{qs_config}`` is the deprecated ``{config_name}``.
        """

        def q(value: str) -> str:
            return shlex.quote(value) if value else ""

        return {
            "section_name": q(self.section_name),
            "config_name": q(self.config_name),
            "config_root": q(self.config_root),
            "paths": " ".join(q(p) for p in self.paths),
            "branch": q(self.branch),
            "qs_config": q(self.config_name),
        }


def find_hook_script(name: str) -> Path | None:
    """Find a hook script: `<repo>/hooks/` first, global dir fallback.

    Names escaping the hooks directory never match.
    """
    for hooks_dir in (REPO_DIR / "hooks", HOOKS_DIR):
        if not hooks_dir.is_dir():
            continue
        candidate = hooks_dir / name
        try:
            inside = candidate.resolve().is_relative_to(hooks_dir.resolve())
        except (OSError, RuntimeError):
            continue
        if inside and candidate.is_file():
            return candidate
    return None


def resolve_hook(hook: str | None, context: HookContext) -> str | None:
    """Resolve one hook string: alias, then `{x}`, then `file:` tokens."""
    if not hook:
        return None
    resolved = constants.HOOK_ALIASES.get(hook, hook)
    for name, value in context.placeholders().items():
        if value:
            resolved = resolved.replace("{" + name + "}", value)
    searched = [REPO_DIR / "hooks", HOOKS_DIR]

    def _replace(match: re.Match[str]) -> str:
        script = match.group(1)
        path = find_hook_script(script)
        if path is None:
            dirs = ", ".join(f"'{d}'" for d in searched)
            raise ConfigurationError(
                f"Hook script '{script}' not found. Searched: {dirs}."
            )
        if not os.access(path, os.X_OK):
            path.chmod(0o755)
        return shlex.quote(str(path))

    resolved = HOOK_FILE_PATTERN.sub(_replace, resolved)
    return HOOK_FILE_ESCAPE_PATTERN.sub(r"\1", resolved)


def run_hooks(
    commands: list[str],
    label: str,
    context: HookContext,
    env: dict[str, str] | None = None,
) -> bool:
    """Run shell hook commands; warn and continue on failure.

    context: reserved for future use; execution is context-free.
    Returns True if any hook failed (matches legacy contract).
    """
    if not commands:
        return False
    ui.console.print()
    ui.console.print(f"[bold]{label}...[/bold]")
    hook_failed = False
    for cmd in commands:
        ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
        try:
            shell = os.environ.get("SHELL", "/bin/sh")
            result = subprocess.run(
                [shell, "-c", cmd],
                capture_output=True,
                text=True,
                env={**os.environ, **(env or {})},
            )
            if result.returncode != 0:
                hook_failed = True
                ui.console.print(
                    f"  [yellow]⚠ Hook failed (exit code {result.returncode})[/yellow]"
                )
                if result.stderr:
                    for line in result.stderr.splitlines()[:3]:
                        ui.console.print(f"    [dim]{line}[/dim]")
        except Exception as e:
            hook_failed = True
            ui.console.print(f"  [yellow]⚠ Failed to run command '{cmd}': {e}[/yellow]")
    if hook_failed:
        ui.console.print("[dim]  Some hooks failed - continuing anyway[/dim]")
    return hook_failed
