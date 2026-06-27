"""Save command for dot-man CLI - save changes without switching branches."""

import click

from .. import ui
from ..constants import REPO_DIR
from ..exceptions import DotManError
from ..files import compare_files
from .common import (
    AliasedCommand,
    complete_sections,
    error,
    get_secret_handler,
    handle_exception,
    require_init,
    success,
    warn,
)
from .interface import cli as main


def _warn_symlinks(save_result: dict) -> None:
    """Warn user if any saved paths were symlinks."""
    from pathlib import Path

    symlinks: list = save_result.get("symlinks", [])
    for sym_path in symlinks:
        target = Path(sym_path).resolve()
        ui.console.print(f"  [yellow]! {sym_path} is a symlink -> {target}[/yellow]")
        ui.console.print(
            "  [dim]Edits affect the symlink target, not the dot-man repo.[/dim]"
        )


@main.command("save", cls=AliasedCommand, aliases=["sv"])
@click.option("--commit", "-c", is_flag=True, help="Commit changes after saving")
@click.option(
    "--message",
    "-m",
    "commit_message",
    type=str,
    default=None,
    help="Custom commit message (requires --commit)",
)
@click.option("--dry-run", "-n", is_flag=True, help="Show what would be saved")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--section",
    "-s",
    "section_filter",
    type=str,
    default=None,
    help="Save only a specific section",
    shell_complete=complete_sections,
)
@require_init
def save(
    commit: bool,
    commit_message: str | None,
    dry_run: bool,
    force: bool,
    section_filter: str | None,
):
    """Save current changes to the repository without switching branches.

    Saves all tracked file changes from local to the dot-man repository.
    Use --commit to also create a git commit.
    """
    try:
        from ..operations import get_operations

        ops = get_operations()

        branch = ops.current_branch
        ui.console.print(f"[bold]Saving changes on branch '{branch}'...[/bold]")
        ui.console.print()

        if dry_run:
            ui.console.print("[dim]Dry run - no changes will be made[/dim]")
            ui.console.print()

        # Get sections to save
        sections_to_save = ops.get_sections()
        if section_filter:
            if section_filter not in sections_to_save:
                error(f"Section '{section_filter}' not found", exit_code=1)
            sections_to_save = [section_filter]

        # Check for changes
        changed_sections = []
        for section_name in sections_to_save:
            section = ops.get_section(section_name)
            has_changes = False
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                if repo_path.exists():
                    if not local_path.exists() or not compare_files(
                        repo_path, local_path
                    ):
                        has_changes = True
                        break
                elif local_path.exists():
                    has_changes = True
                    break
            if has_changes:
                changed_sections.append(section_name)

        if not changed_sections:
            success("No changes detected - all files are in sync")
            return

        ui.console.print(
            f"  [cyan]{len(changed_sections)}[/cyan] section(s) with changes:"
        )
        for s in changed_sections:
            ui.console.print(f"    - {s}")
        ui.console.print()

        if dry_run:
            ui.console.print("[dim]Dry run complete - no files were saved[/dim]")
            return

        if not force:
            if not ui.confirm(f"Save changes to {len(changed_sections)} section(s)?"):
                ui.console.print("[dim]Aborted.[/dim]")
                return

        ui.console.print()
        ui.console.print("[bold]Phase 1:[/bold] Saving files...")

        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        _warn_symlinks(save_result)

        saved_count = save_result["saved"]
        secrets = save_result["secrets"]
        errors = save_result["errors"]

        if secrets:
            warn(f"{len(secrets)} secrets were redacted during save")

        if errors:
            ui.error(f"Encountered {len(errors)} errors during save:")
            for err in errors:
                ui.console.print(f"  [red]• {err}[/red]")

        ui.console.print(f"  Saved {saved_count} files")

        # Commit if requested
        if commit and saved_count > 0:
            ui.console.print()
            ui.console.print("[bold]Phase 2:[/bold] Committing changes...")

            if commit_message:
                msg = commit_message
            else:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                relevant = [
                    s for s in changed_sections if s not in ("defaults", "config")
                ]
                if relevant:
                    sections_str = ", ".join(relevant[:3])
                    if len(relevant) > 3:
                        sections_str += f" +{len(relevant) - 3} more"
                    msg = f"[dot-man] Save {saved_count} files | sections: {sections_str} [{timestamp}]"
                else:
                    msg = f"[dot-man] Save {saved_count} files [{timestamp}]"

            commit_sha = ops.git.commit(msg)
            if commit_sha:
                ui.console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")
            else:
                ui.console.print("  [dim]Nothing to commit[/dim]")
        elif commit and saved_count == 0:
            ui.console.print()
            ui.console.print("[dim]No files changed - nothing to commit[/dim]")

        ui.console.print()
        success(f"Saved {saved_count} files on branch '{branch}'")

    except DotManError as e:
        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Save")
