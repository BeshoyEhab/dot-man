"""Switch command for dot-man CLI.

DEPRECATED: Thin wrapper around 'navigate' command.
"""

import click

from .. import ui
from .common import (
    BRANCH,
    complete_switch_args,
    error,
    require_init,
)
from .interface import cli as main


@main.command(deprecated=True, help="⚠️ DEPRECATED: Use 'dot-man navigate' instead")
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--save",
    "save_mode",
    flag_value="save",
    default=None,
    help="Save current changes before switching",
)
@click.option(
    "--no-save",
    "save_mode",
    flag_value="no-save",
    default=None,
    help="Discard current changes before switching",
)
@click.argument(
    "branch", type=BRANCH, required=False, shell_complete=complete_switch_args
)
@require_init
def switch(branch, dry_run: bool, force: bool, save_mode):
    """Switch to a different configuration branch, tag, or commit.

    ⚠️ DEPRECATED: Use 'dot-man navigate' instead.
    """
    ui.console.print(
        "[yellow bold]⚠️ WARNING:[/yellow bold]"
        " [yellow]'switch' is deprecated.[/yellow]\n"
        "  Use [cyan]dot-man navigate[/cyan] instead.\n"
    )
    if not branch:
        error("No branch, tag, or commit specified", exit_code=1)

    from .navigate_cmd import _navigate_impl

    _navigate_impl(
        target=branch,
        dry_run=dry_run,
        force=force,
        save_mode=save_mode,
        commit_message=None,
        preview=False,
        diff=False,
        files_only=False,
    )
