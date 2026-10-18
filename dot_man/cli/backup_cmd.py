"""Backup command for dot-man CLI."""

import click
from rich.table import Table

from .. import ui
from ..exceptions import DotManError
from .common import error, require_init, success
from .interface import cli as main


@main.group("backup")
def backup():
    """Manage local safety backups."""
    pass


@backup.command("create")
@click.argument("note", required=False, default="manual")
@require_init
def backup_create(note: str):
    """Create a manual backup snapshot.

    Backups all currently tracked files to a local snapshot.
    """
    try:
        from ..operations import get_operations

        ops = get_operations()

        # Collect all tracked files
        paths_to_backup = []
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            paths_to_backup.extend([p for p in section.paths if p.exists()])

        if not paths_to_backup:
            ui.warn("No tracked files found to backup.")
            return

        ui.console.print("[bold]Creating backup...[/bold]")
        backup_id = ops.backups.create_backup(paths_to_backup, note=note)

        if backup_id:
            success(f"Backup created: [cyan]{backup_id}[/cyan]")
        else:
            ui.warn("Backup created but empty (no files found).")

    except Exception as e:
        error(f"Failed to create backup: {e}")


@backup.command("list")
@require_init
def backup_list():
    """List available backups."""
    try:
        from ..operations import get_operations

        ops = get_operations()
        backups = ops.backups.list_backups()

        if not backups:
            ui.console.print("[dim]No backups found[/dim]")
            return

        table = Table(title="Local Backups")
        table.add_column("ID", style="cyan")
        table.add_column("Date")
        table.add_column("Note")

        for b in backups:
            table.add_row(b["id"], b["date"], b["note"])

        ui.console.print(table)

    except Exception as e:
        error(f"Failed to list backups: {e}")


@backup.command(
    "restore",
    deprecated=True,
    hidden=True,
    help="⚠️ DEPRECATED: Use 'dot-man rollback --backup <id>' instead",
)
@click.argument("backup_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
@require_init
def backup_restore(backup_id: str, force: bool):
    """Restore files from a backup snapshot.

    ⚠️ DEPRECATED: Use ``dot-man rollback --backup <id>`` instead.

    WARNING: This will overwrite current local files with the backup version.
    """
    ui.console.print(
        "[yellow bold]⚠️ WARNING:[/yellow bold]"
        " [yellow]'backup restore' is deprecated.[/yellow]\n"
        "  Use [cyan]dot-man rollback --backup <id>[/cyan] instead.\n"
    )
    try:
        from ..operations import get_operations
        from .rollback_cmd import _restore_backup

        ops = get_operations()
        _restore_backup(ops, backup_id, force)

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to restore backup: {e}")
