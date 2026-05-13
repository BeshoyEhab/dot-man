"""Hook system for dot-man commands."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .operations import DotManOperations

from .constants import DOT_MAN_DIR

HOOKS_DIR = DOT_MAN_DIR / "hooks"

HOOK_COMMANDS = [
    "init",
    "switch",
    "checkout",
    "deploy",
    "save",
    "add",
    "remove",
    "audit",
    "sync",
    "backup",
]

HOOK_PHASES = ["pre", "post"]


def ensure_hooks_dir() -> Path:
    """Ensure hooks directory exists."""
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    return HOOKS_DIR


def get_hook_path(command: str, phase: str) -> Path:
    """Get the path to a specific hook script.

    Args:
        command: Command name (e.g., "switch", "checkout")
        phase: Phase ("pre" or "post")

    Returns:
        Path to the hook script
    """
    return HOOKS_DIR / f"{phase}_{command}"


def run_hook(
    command: str,
    phase: str,
    env: dict | None = None,
    cwd: Path | None = None,
) -> bool:
    """Run a hook script for a command and phase.

    Args:
        command: Command name (e.g., "switch", "checkout")
        phase: Phase ("pre" or "post")
        env: Optional environment variables to pass to the hook
        cwd: Working directory for the hook

    Returns:
        True if hook succeeded (or didn't exist), False if hook failed
    """
    hook_path = get_hook_path(command, phase)

    if not hook_path.exists():
        return True

    if not os.access(hook_path, os.X_OK):
        hook_path.chmod(0o755)

    hook_env = {
        "DOTMAN_HOOK_COMMAND": command,
        "DOTMAN_HOOK_PHASE": phase,
        "DOTMAN_HOOK_DIR": str(DOT_MAN_DIR),
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "SHELL": os.environ.get("SHELL", "/bin/sh"),
    }

    if env:
        hook_env.update(env)

    try:
        result = subprocess.run(
            [str(hook_path)],
            env=hook_env,
            cwd=cwd or DOT_MAN_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                print(f"  {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                print(f"  [dim]{line}[/dim]")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("  [yellow]Hook timed out after 30 seconds[/yellow]")
        return False
    except Exception as e:
        print(f"  [red]Hook error: {e}[/red]")
        return False


def run_switch_hooks(
    phase: str,
    ops: DotManOperations,
    source: str,
    target: str,
) -> bool:
    """Run hooks for switch command with appropriate environment variables.

    Args:
        phase: "pre" or "post"
        ops: DotManOperations instance
        source: Source branch/commit
        target: Target branch/commit
        ops: DotManOperations

    Returns:
        True if hook succeeded
    """
    env = {
        "DOTMAN_SOURCE": source,
        "DOTMAN_TARGET": target,
        "DOTMAN_SOURCE_BRANCH": source,
        "DOTMAN_TARGET_BRANCH": target,
    }
    return run_hook("switch", phase, env=env)


def run_checkout_hooks(
    phase: str,
    target: str,
) -> bool:
    """Run hooks for checkout command with appropriate environment variables.

    Args:
        phase: "pre" or "post"
        target: Target commit/tag

    Returns:
        True if hook succeeded
    """
    env = {
        "DOTMAN_TARGET": target,
    }
    return run_hook("checkout", phase, env=env)


def list_hooks() -> list[dict]:
    """List all available hooks.

    Returns:
        List of dicts with: command, phase, path, exists
    """
    hooks = []
    for command in HOOK_COMMANDS:
        for phase in HOOK_PHASES:
            path = get_hook_path(command, phase)
            hooks.append(
                {
                    "command": command,
                    "phase": phase,
                    "path": path,
                    "exists": path.exists(),
                }
            )
    return hooks


def create_hook(command: str, phase: str) -> Path:
    """Create a new hook script.

    Args:
        command: Command name
        phase: Phase ("pre" or "post")

    Returns:
        Path to the created hook
    """
    hook_path = get_hook_path(command, phase)
    hook_path.parent.mkdir(parents=True, exist_ok=True)

    template = f"""#!/bin/bash
# dot-man {phase}_{command} hook
# Environment variables available:
#   DOTMAN_HOOK_COMMAND={command}
#   DOTMAN_HOOK_PHASE={phase}
#   DOTMAN_HOOK_DIR={DOT_MAN_DIR}

set -e

echo "{phase.capitalize()} {command} hook running..."

# Add your commands here

echo "{phase.capitalize()} {command} hook completed."
"""

    hook_path.write_text(template)
    hook_path.chmod(0o755)

    return hook_path


def delete_hook(command: str, phase: str) -> bool:
    """Delete a hook script.

    Args:
        command: Command name
        phase: Phase ("pre" or "post")

    Returns:
        True if hook was deleted, False if it didn't exist
    """
    hook_path = get_hook_path(command, phase)
    if hook_path.exists():
        hook_path.unlink()
        return True
    return False
