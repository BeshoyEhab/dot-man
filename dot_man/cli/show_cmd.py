"""Show command for dot-man CLI.

DEPRECATED: thin wrapper around ``dot-man log --commit <sha>``.
Kept as a hidden, deprecated alias until v2.0.
"""

import click

from .. import ui
from .common import complete_commits, require_init
from .interface import cli as main


@main.command(
    "show",
    deprecated=True,
    hidden=True,
    help="⚠️ DEPRECATED: Use 'dot-man log --commit <sha>' instead",
)
@click.argument("commit", shell_complete=complete_commits)
@require_init
def show(commit: str):
    """View full diff for a specific commit.

    ⚠️ DEPRECATED: Use ``dot-man log --commit <sha>`` instead.

    Examples:
        dot-man show HEAD
        dot-man show abc1234
    """
    ui.console.print(
        "[yellow bold]⚠️ WARNING:[/yellow bold]"
        " [yellow]'show' is deprecated.[/yellow]\n"
        "  Use [cyan]dot-man log --commit <sha>[/cyan] instead.\n"
    )
    from .log_cmd import _log_impl

    _log_impl(
        file=None,
        count=None,
        show_diff=False,
        stat=False,
        interactive=False,
        commit=commit,
    )
