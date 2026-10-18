"""Restore command for dot-man CLI.

DEPRECATED: thin wrapper around ``dot-man revert <file> --commit <sha>``.
Kept as a hidden, deprecated alias until v2.0.
"""

from pathlib import Path

import click

from .. import ui
from ..exceptions import DotManError
from .common import AliasedCommand, complete_commits, error, require_init
from .interface import cli as main


@main.command(
    "restore",
    cls=AliasedCommand,
    deprecated=True,
    hidden=True,
    help="⚠️ DEPRECATED: Use 'dot-man revert <file> --commit <sha>' instead",
)
@click.argument("file", type=click.Path(path_type=Path))
@click.argument("commit", shell_complete=complete_commits)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@require_init
def restore(file: Path, commit: str, force: bool):
    """Restore a file from history.

    ⚠️ DEPRECATED: Use ``dot-man revert <file> --commit <sha>`` instead.

    Examples:
        dot-man restore ~/.bashrc abc1234
    """
    ui.console.print(
        "[yellow bold]⚠️ WARNING:[/yellow bold]"
        " [yellow]'restore' is deprecated.[/yellow]\n"
        "  Use [cyan]dot-man revert <file> --commit <sha>[/cyan] instead.\n"
    )
    try:
        from ..operations import get_operations
        from .revert_cmd import restore_file_from_commit

        ops = get_operations()
        restore_file_from_commit(ops, file.expanduser().resolve(), commit, force)

    except DotManError as e:
        error(str(e), getattr(e, "exit_code", 1))
    except Exception as e:
        error(f"Unexpected error: {e}")
