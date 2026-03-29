"""Doctor command for dot-man CLI - diagnostics and health checks."""

import os
import shutil
from pathlib import Path

import click

from .. import ui
from ..constants import DOT_MAN_DIR, REPO_DIR, DOT_MAN_TOML, GLOBAL_TOML
from .interface import cli as main
from .common import error, success, warn, require_init


@main.command("doctor")
@require_init
def doctor():
    """Run diagnostics and health checks.

    Checks the dot-man installation for common issues:
    git availability, repository integrity, configuration validity,
    file permissions, and remote connectivity.
    """
    from ..operations import get_operations

    checks_passed = 0
    checks_failed = 0
    checks_warned = 0

    def check_pass(label: str, detail: str = "") -> None:
        nonlocal checks_passed
        checks_passed += 1
        msg = f"[success]✓[/success] {label}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        ui.console.print(msg)

    def check_fail(label: str, detail: str = "") -> None:
        nonlocal checks_failed
        checks_failed += 1
        msg = f"[error]✗[/error] {label}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        ui.console.print(msg)

    def check_warn(label: str, detail: str = "") -> None:
        nonlocal checks_warned
        checks_warned += 1
        msg = f"[warning]⚠[/warning] {label}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        ui.console.print(msg)

    ui.console.print("[bold]dot-man doctor[/bold]")
    ui.console.print()

    # 1. Git availability
    ui.console.print("[bold]System[/bold]")
    git_path = shutil.which("git")
    if git_path:
        import subprocess

        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip() if result.returncode == 0 else "unknown"
        check_pass("Git installed", version)
    else:
        check_fail("Git not found", "Install git and ensure it's in PATH")

    # 2. Python version
    import sys

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        check_pass("Python version", py_version)
    else:
        check_fail("Python version too old", f"{py_version} (requires 3.9+)")

    ui.console.print()

    # 3. Repository checks
    ui.console.print("[bold]Repository[/bold]")
    if DOT_MAN_DIR.exists():
        check_pass("Config directory exists", str(DOT_MAN_DIR))
    else:
        check_fail("Config directory missing", f"Run 'dot-man init'")

    if REPO_DIR.exists():
        check_pass("Repository directory exists", str(REPO_DIR))
    else:
        check_fail("Repository directory missing", "Run 'dot-man init'")

    # Check .git directory
    git_dir = REPO_DIR / ".git"
    if git_dir.exists():
        check_pass("Git repository initialized")
    else:
        check_fail("No .git directory in repo", "Repository may be corrupted")

    # Check repo permissions
    if REPO_DIR.exists():
        if os.access(REPO_DIR, os.R_OK | os.W_OK):
            check_pass("Repository permissions", "read/write OK")
        else:
            check_fail("Repository permissions", "Cannot read/write to repo directory")

    ui.console.print()

    # 4. Configuration checks
    ui.console.print("[bold]Configuration[/bold]")

    if GLOBAL_TOML.exists():
        check_pass("Global config exists", str(GLOBAL_TOML))
    else:
        check_warn("No global config", "Will use defaults")

    if DOT_MAN_TOML.exists():
        check_pass("dot-man.toml exists", str(DOT_MAN_TOML))
        # Try to parse it
        try:
            ops = get_operations()
            sections = ops.get_sections()
            check_pass("Config is valid", f"{len(sections)} section(s)")
        except Exception as e:
            check_fail("Config parse error", str(e))
    else:
        check_warn("No dot-man.toml", "Run 'dot-man config create' or 'dot-man edit'")

    ui.console.print()

    # 5. Branch checks
    ui.console.print("[bold]Branches[/bold]")
    try:
        ops = get_operations()
        current = ops.current_branch
        check_pass("Current branch", current)

        branches = ops.git.list_branches()
        check_pass("Available branches", ", ".join(branches) if branches else "none")
    except Exception as e:
        check_fail("Branch check failed", str(e))

    ui.console.print()

    # 6. Remote checks
    ui.console.print("[bold]Remote[/bold]")
    try:
        ops = get_operations()
        remote_url = ops.global_config.remote_url
        if remote_url:
            check_pass("Remote configured", remote_url)
        else:
            check_warn("No remote configured", "Run 'dot-man setup' to configure")
    except Exception as e:
        check_warn("Could not check remote", str(e))

    ui.console.print()

    # 7. Tracked files check
    ui.console.print("[bold]Tracked Files[/bold]")
    try:
        ops = get_operations()
        missing_count = 0
        total_paths = 0
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for p in section.paths:
                total_paths += 1
                if not p.exists():
                    missing_count += 1
                    check_warn(f"Missing: {p}", f"section '{section_name}'")

        if missing_count == 0 and total_paths > 0:
            check_pass("All tracked paths exist", f"{total_paths} path(s)")
        elif total_paths == 0:
            check_warn("No paths tracked", "Add files with 'dot-man add'")
    except Exception as e:
        check_fail("File check failed", str(e))

    # 8. Orphaned files
    try:
        ops = get_operations()
        orphans = ops.get_orphaned_files()
        if orphans:
            check_warn(
                f"{len(orphans)} orphaned file(s) in repo",
                "Run 'dot-man clean --orphans' to remove",
            )
        else:
            check_pass("No orphaned files")
    except Exception as e:
        check_warn("Could not check orphans", str(e))

    # 9. Backup check
    try:
        ops = get_operations()
        backup_list = ops.backups.list_backups()
        if backup_list:
            check_pass("Backups available", f"{len(backup_list)} backup(s)")
        else:
            check_warn("No backups", "Backups are created automatically before destructive operations")
    except Exception as e:
        check_warn("Could not check backups", str(e))

    ui.console.print()

    # Summary
    ui.console.print("[bold]Summary[/bold]")
    total = checks_passed + checks_failed + checks_warned
    ui.console.print(
        f"  [success]{checks_passed}[/success] passed, "
        f"[warning]{checks_warned}[/warning] warnings, "
        f"[error]{checks_failed}[/error] failed "
        f"[dim]({total} checks)[/dim]"
    )

    if checks_failed == 0:
        ui.console.print()
        success("dot-man is healthy!")
    else:
        ui.console.print()
        error(
            f"{checks_failed} check(s) failed. See above for details.",
            exit_code=0,
        )
        raise SystemExit(1)
