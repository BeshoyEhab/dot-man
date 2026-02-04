"""TUI command for dot-man CLI."""

import sys
import subprocess

import click

from .. import ui
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, require_init


@main.command()
@require_init
def tui():
    """Interactive TUI for managing dotfiles.

    Navigate with arrow keys, press Enter to switch branches.

    Keys:
        Enter - Switch to selected branch
        c     - Open command palette
        s     - Sync with remote
        d     - Deploy selected branch
        e     - Edit config file
        a     - Run security audit
        r     - Refresh
        ?     - Show help
        q     - Quit

    Requires: pip install dot-man[tui]
    """
    try:
        from ..tui import run_tui
    except ImportError:
        ui.console.print("[yellow]TUI requires the 'textual' package.[/yellow]")
        ui.console.print()
        ui.console.print("Install with:")
        ui.console.print("  [cyan]pipx inject dot-man textual[/cyan]")
        ui.console.print("  or")
        ui.console.print("  [cyan]pip install dot-man[tui][/cyan]")
        return

    try:
        result = run_tui()

        if result:
            action, data = result

            if action == "switch" and data:
                from .switch_cmd import switch
                ctx = click.Context(switch)
                ctx.invoke(switch, branch=data, dry_run=False, force=True)

            elif action == "sync":
                from .remote_cmd import sync
                ctx = click.Context(sync)
                ctx.invoke(sync, push_only=False, pull_only=False)

            elif action == "deploy" and data:
                from .deploy_cmd import deploy
                ctx = click.Context(deploy)
                ctx.invoke(deploy, branch=data, force=True, dry_run=False)

            elif action == "run" and data:
                subprocess.run(
                    [sys.executable, "-m", "dot_man.cli"] + data, check=False
                )

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"TUI error: {e}")
