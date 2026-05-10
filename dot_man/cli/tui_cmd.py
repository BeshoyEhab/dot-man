"""TUI command for dot-man CLI."""

import click

from .. import ui
from .interface import cli as main
from .common import error, require_init


@main.command()
@require_init
def tui():
    """Interactive TUI for managing dotfiles.

    Note: The TUI is currently under redesign. The CLI provides all
    core functionality. Use commands like:
    
    - dot-man status      - Show current state
    - dot-man switch      - Switch branches  
    - dot-man edit        - Edit configuration
    - dot-man audit       - Scan for secrets
    - dot-man sync        - Sync with remote
    
    The TUI will return in a future version with improved design.
    """
    ui.console.print("[yellow]TUI is temporarily unavailable.[/yellow]")
    ui.console.print()
    ui.console.print("Use the CLI commands instead:")
    ui.console.print("  [cyan]dot-man --help[/cyan] to see all available commands")