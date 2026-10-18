"""Doctor command for dot-man CLI - diagnostics and health checks."""

import os
import shutil
from pathlib import Path

from .. import constants, ui
from ..constants import DOT_MAN_TOML
from .common import AliasedCommand, error, require_init, success
from .interface import cli as main


class _DoctorReport:
    """Collects pass/fail/warn outcomes and prints each check line."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.warned = 0

    @staticmethod
    def _line(mark: str, style: str, label: str, detail: str) -> str:
        msg = f"[{style}]{mark}[/{style}] {label}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        return msg

    def check_pass(self, label: str, detail: str = "") -> None:
        self.passed += 1
        ui.console.print(self._line("✓", "success", label, detail))

    def check_fail(self, label: str, detail: str = "") -> None:
        self.failed += 1
        ui.console.print(self._line("✗", "error", label, detail))

    def check_warn(self, label: str, detail: str = "") -> None:
        self.warned += 1
        ui.console.print(self._line("⚠", "warning", label, detail))


@main.command("doctor", cls=AliasedCommand)
@require_init
def doctor():
    """Run diagnostics and health checks.

    Checks the dot-man installation for common issues:
    git availability, repository integrity, configuration validity,
    file permissions, and remote connectivity.
    """
    from ..operations import get_operations

    report = _DoctorReport()
    check_pass = report.check_pass
    check_fail = report.check_fail
    check_warn = report.check_warn

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

    py_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    if sys.version_info >= (3, 9):
        check_pass("Python version", py_version)
    else:
        check_fail("Python version too old", f"{py_version} (requires 3.9+)")

    ui.console.print()

    # 3. Repository checks
    ui.console.print("[bold]Repository[/bold]")
    if constants.get_dot_man_dir().exists():
        check_pass("Config directory exists", str(constants.get_dot_man_dir()))
    else:
        check_fail("Config directory missing", "Run 'dot-man init'")

    if constants.get_repo_dir().exists():
        check_pass("Repository directory exists", str(constants.get_repo_dir()))
    else:
        check_fail("Repository directory missing", "Run 'dot-man init'")

    # Check .git directory
    git_dir = constants.get_repo_dir() / ".git"
    if git_dir.exists():
        check_pass("Git repository initialized")
    else:
        check_fail("No .git directory in repo", "Repository may be corrupted")

    # Check repo permissions
    if constants.get_repo_dir().exists():
        if os.access(constants.get_repo_dir(), os.R_OK | os.W_OK):
            check_pass("Repository permissions", "read/write OK")
        else:
            check_fail("Repository permissions", "Cannot read/write to repo directory")

    ui.console.print()

    # 4. Configuration checks
    ui.console.print("[bold]Configuration[/bold]")

    if constants.get_global_toml().exists():
        check_pass("Global config exists", str(constants.get_global_toml()))
    else:
        check_warn("No global config", "Will use defaults")

    dot_man_toml_path = Path(DOT_MAN_TOML)
    if dot_man_toml_path.exists():
        check_pass("dot-man.toml exists", str(dot_man_toml_path))
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
            check_warn(
                "No backups",
                "Backups are created automatically before destructive operations",
            )
    except Exception as e:
        check_warn("Could not check backups", str(e))

    ui.console.print()

    # Summary
    ui.console.print("[bold]Summary[/bold]")
    total = report.passed + report.failed + report.warned
    ui.console.print(
        f"  [success]{report.passed}[/success] passed, "
        f"[warning]{report.warned}[/warning] warnings, "
        f"[error]{report.failed}[/error] failed "
        f"[dim]({total} checks)[/dim]"
    )

    if report.failed == 0:
        ui.console.print()
        success("dot-man is healthy!")
    else:
        ui.console.print()
        error(
            f"{report.failed} check(s) failed. See above for details.",
            exit_code=1,
        )
