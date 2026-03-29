"""Clean command for dot-man CLI."""

import click

from .. import ui
from ..constants import REPO_DIR
from .interface import cli as main
from .common import error, success, require_init


@main.command("clean")
@click.option("--backups", is_flag=True, help="Clean old backups")
@click.option("--orphans", is_flag=True, help="Clean orphaned files from repo")
@click.option("--all", "clean_all", is_flag=True, help="Clean both backups and orphans")
@click.option("--keep", type=int, default=0, help="Number of backups to keep (default 0)")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option("--dry-run", is_flag=True, help="Preview what would be deleted")
@require_init
def clean(backups: bool, orphans: bool, clean_all: bool, keep: int, force: bool, dry_run: bool):
    """Clean stale backups and orphaned files.
    
    Removes old backups and files in the repository that are no longer tracked
    by any configuration section.
    """
    if not (backups or orphans or clean_all):
        ui.warn("Please specify what to clean: --backups, --orphans, or --all")
        return

    try:
        from ..operations import get_operations
        ops = get_operations()
        
        # 1. Clean Backups
        if backups or clean_all:
            ui.console.print("[bold]Checking backups...[/bold]")
            if dry_run:
                # Preview backups to delete
                all_backups = ops.backups.list_backups()
                if len(all_backups) > keep:
                    to_delete = all_backups[keep:]
                    ui.console.print(f"[bold]Backups to be deleted ({len(to_delete)}):[/bold]", style="red")
                    for b in to_delete:
                        ui.console.print(f"  - {b['id']} ({b['note']})")
                else:
                    ui.console.print("  No backups to clean.")
            else:
                current_backups_count = len(ops.backups.list_backups())
                if current_backups_count > keep:
                    if force or ui.confirm(f"Clean up backups (keeping {keep} newest)?"):
                        deleted = ops.backups.clean_backups(keep=keep)
                        if deleted > 0:
                            success(f"Deleted {deleted} old backups.")
                        else:
                            ui.console.print("No backups cleaned.")
                else:
                    ui.console.print("  No backups to clean.")

        # 2. Clean Orphans
        if orphans or clean_all:
            ui.console.print("[bold]Checking for orphaned files...[/bold]")
            orphaned_files = ops.get_orphaned_files()
            
            if not orphaned_files:
                ui.console.print("  No orphaned files found.")
                return

            if dry_run:
                ui.console.print(f"[bold]Orphaned files to be deleted ({len(orphaned_files)}):[/bold]", style="red")
                for p in orphaned_files:
                    # Show path relative to repo
                    try:
                        rel_path = p.relative_to(REPO_DIR)
                        ui.console.print(f"  - {rel_path}")
                    except ValueError:
                         ui.console.print(f"  - {p.name}")
            else:
                if force or ui.confirm(f"Found {len(orphaned_files)} orphaned files. Delete them?"):
                    deleted_files = ops.clean_orphaned_files(dry_run=False)
                    success(f"Deleted {len(deleted_files)} orphaned files.")
                    
    except Exception as e:
        error(f"Failed to clean: {e}")
