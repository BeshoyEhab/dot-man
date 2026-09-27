"""Two-level help: `help` (happy path) and `help-all` (everything)."""

import shutil
from pathlib import Path

import click

from .common import error, success
from .interface import cli as main

__all__ = ["MAN_SOURCE"]

MAN_SOURCE = Path(__file__).resolve().parents[2] / "docs" / "man" / "dot-man.1"


@main.command("help")
@click.option(
    "--install-man",
    is_flag=True,
    help="Install the man page to ~/.local/share/man",
)
def help_cmd(install_man: bool):
    """Show the happy-path commands for everyday use.

    For the complete listing, see `dot-man help-all`.
    """
    if install_man:
        _install_man()
        return
    ctx = click.get_current_context()
    assert ctx.parent is not None
    click.echo(ctx.parent.get_help())


@main.command("help-all")
@click.pass_context
def help_all(ctx: click.Context):
    """Show every command, including aliases and deprecated shims."""
    group_ctx = ctx.parent
    assert group_ctx is not None
    group = group_ctx.command
    assert isinstance(group, click.Group)
    formatter = group_ctx.make_formatter()
    group.format_usage(group_ctx, formatter)
    group.format_help_text(group_ctx, formatter)
    group.format_options(group_ctx, formatter)
    # Explicit base-class call: the full listing, bypassing the
    # happy-path-only DotManGroup.format_commands override.
    click.Group.format_commands(group, group_ctx, formatter)
    group.format_epilog(group_ctx, formatter)
    click.echo(formatter.getvalue().rstrip("\n"))


def _install_man() -> None:
    """Copy the bundled man page into ~/.local/share/man."""
    if not MAN_SOURCE.is_file():
        error(f"Man page source not found: {MAN_SOURCE}")
        return
    dest = Path.home() / ".local" / "share" / "man" / "man1" / "dot-man.1"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(MAN_SOURCE, dest)
    success(f"Installed man page to {dest}")
