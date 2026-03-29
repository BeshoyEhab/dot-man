"""Verify command for dot-man CLI - validate repository integrity."""

import os
from pathlib import Path

import click

from .. import ui
from ..constants import REPO_DIR, DOT_MAN_TOML
from .interface import cli as main
from .common import error, success, warn, require_init


@main.command("verify")
@click.option("--fix", is_flag=True, help="Attempt to fix issues automatically")
@require_init
def verify(fix: bool):
    """Validate repository integrity and configuration.

    Checks for orphaned files, broken symlinks, permission issues,
    and configuration consistency.
    """
    from ..operations import get_operations

    issues: list[str] = []
    fixed: list[str] = []

    ui.console.print("[bold]Verifying repository integrity...[/bold]")
    ui.console.print()

    ops = get_operations()

    # 1. Check config file is valid TOML
    ui.console.print("[bold]Configuration[/bold]")
    if (REPO_DIR / DOT_MAN_TOML).exists():
        try:
            sections = ops.get_sections()
            ui.console.print(
                f"  [success]✓[/success] Config valid ({len(sections)} sections)"
            )
        except Exception as e:
            issues.append(f"Config parse error: {e}")
            ui.console.print(f"  [error]✗[/error] Config parse error: {e}")
    else:
        issues.append("dot-man.toml not found")
        ui.console.print("  [warning]⚠[/warning] No dot-man.toml found")

    # 2. Check each section's paths
    ui.console.print()
    ui.console.print("[bold]Tracked Paths[/bold]")
    try:
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for p in section.paths:
                if not p.exists():
                    issues.append(f"Missing path: {p} (section '{section_name}')")
                    ui.console.print(
                        f"  [warning]⚠[/warning] Missing: {p} "
                        f"[dim](section '{section_name}')[/dim]"
                    )
                elif p.is_symlink() and not p.resolve().exists():
                    issues.append(f"Broken symlink: {p} (section '{section_name}')")
                    ui.console.print(
                        f"  [error]✗[/error] Broken symlink: {p} "
                        f"[dim](section '{section_name}')[/dim]"
                    )
                elif not os.access(p, os.R_OK):
                    issues.append(f"Permission denied: {p} (section '{section_name}')")
                    ui.console.print(
                        f"  [error]✗[/error] Cannot read: {p} "
                        f"[dim](section '{section_name}')[/dim]"
                    )
                else:
                    ui.console.print(
                        f"  [success]✓[/success] {p} "
                        f"[dim](section '{section_name}')[/dim]"
                    )

                # Check corresponding repo path
                repo_path = section.get_repo_path(p, REPO_DIR)
                if not repo_path.exists():
                    ui.console.print(f"    [dim]↳ Not yet saved to repo[/dim]")
    except Exception as e:
        issues.append(f"Section check error: {e}")
        ui.console.print(f"  [error]✗[/error] Error checking sections: {e}")

    # 3. Check for orphaned files in repo
    ui.console.print()
    ui.console.print("[bold]Orphaned Files[/bold]")
    try:
        orphans = ops.get_orphaned_files()
        if orphans:
            ui.console.print(
                f"  [warning]⚠[/warning] {len(orphans)} orphaned file(s) found:"
            )
            for p in orphans[:10]:  # Show max 10
                try:
                    rel = p.relative_to(REPO_DIR)
                    ui.console.print(f"    - {rel}")
                except ValueError:
                    ui.console.print(f"    - {p.name}")
            if len(orphans) > 10:
                ui.console.print(f"    [dim]... and {len(orphans) - 10} more[/dim]")

            if fix:
                deleted = ops.clean_orphaned_files(dry_run=False)
                fixed.append(f"Deleted {len(deleted)} orphaned files")
                ui.console.print(
                    f"  [success]✓[/success] Deleted {len(deleted)} orphaned files"
                )
            else:
                issues.append(f"{len(orphans)} orphaned files in repo")
                ui.console.print(
                    "  [dim]Run with --fix or 'dot-man clean --orphans' to remove[/dim]"
                )
        else:
            ui.console.print("  [success]✓[/success] No orphaned files")
    except Exception as e:
        issues.append(f"Orphan check error: {e}")
        ui.console.print(f"  [error]✗[/error] Error checking orphans: {e}")

    # 4. Check git status
    ui.console.print()
    ui.console.print("[bold]Git Status[/bold]")
    try:
        repo = ops.git.repo
        if repo.is_dirty(untracked_files=True):
            uncommitted = len(repo.index.diff(None))
            untracked = len(repo.untracked_files)
            details = []
            if uncommitted:
                details.append(f"{uncommitted} uncommitted")
            if untracked:
                details.append(f"{untracked} untracked")
            ui.console.print(
                f"  [warning]⚠[/warning] Repo has uncommitted changes "
                f"[dim]({', '.join(details)})[/dim]"
            )
            issues.append(f"Uncommitted changes in repo ({', '.join(details)})")
        else:
            ui.console.print("  [success]✓[/success] Repository is clean")
    except Exception as e:
        issues.append(f"Git status check error: {e}")
        ui.console.print(f"  [error]✗[/error] Error checking git: {e}")

    # Summary
    ui.console.print()
    if not issues:
        success("Repository integrity verified — no issues found!")
    else:
        ui.console.print(f"[warning]Found {len(issues)} issue(s)[/warning]")
        if fixed:
            ui.console.print(f"[success]Fixed {len(fixed)} issue(s)[/success]")
        if not fix and any("orphaned" in i.lower() for i in issues):
            ui.console.print(
                "[dim]💡 Run 'dot-man verify --fix' to auto-fix some issues[/dim]"
            )
