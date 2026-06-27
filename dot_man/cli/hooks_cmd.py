"""Hooks management CLI command."""

import click

from .. import ui
from .common import AliasedCommand, error, require_init, success, warn
from .interface import cli as main


@main.command("hooks", cls=AliasedCommand, aliases=["hks"])
@click.argument("command", type=click.Choice(["list", "create", "delete"]))
@click.argument("phase", type=click.Choice(["pre", "post"]), required=False)
@click.argument("name", type=str, required=False)
@require_init
def hooks(command: str, phase: str | None, name: str | None):
    """Manage dot-man hooks.

    Hooks allow you to run custom scripts before/after commands.

    Commands:
        list    List all available hooks (no additional args needed)
        create  Create a new hook script (requires: pre|post NAME)
        delete  Delete a hook script (requires: pre|post NAME)

    Hook naming: {phase}_{command} (e.g., pre_switch, post_deploy)

    Examples:
        dot-man hooks list
        dot-man hooks create pre switch
        dot-man hooks create post deploy
        dot-man hooks delete pre checkout
    """
    from ..hooks import (
        create_hook,
        delete_hook,
        list_hooks,
    )

    if command == "list":
        ui.console.print("[bold]Available Hooks:[/bold]")
        all_hooks = list_hooks()
        for h in all_hooks:
            status = "[green]✓[/green]" if h["exists"] else "[dim]-[/dim]"
            ui.console.print(f"  {status} {h['phase']}_{h['command']} -> {h['path']}")

    elif command == "create":
        if not phase or not name:
            error("'create' requires: pre|post NAME", exit_code=1)
            return
        if not isinstance(name, str) or not isinstance(phase, str):
            error("Hook name and phase must be strings", exit_code=1)
            return
        hook_path = create_hook(name, phase)
        ui.console.print(f"[green]Created hook:[/green] {hook_path}")
        ui.console.print("  Edit this file to add your custom script.")

    elif command == "delete":
        if not phase or not name:
            error("'delete' requires: pre|post NAME", exit_code=1)
        if not isinstance(name, str) or not isinstance(phase, str):
            raise click.ClickException("Hook name and phase must be strings")
        deleted = delete_hook(name, phase)
        if deleted:
            success(f"Deleted hook: {phase}_{name}")
        else:
            warn(f"Hook not found: {phase}_{name}")
