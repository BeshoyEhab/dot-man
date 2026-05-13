"""TUI command for dot-man CLI."""

from .. import ui
from .common import require_init
from .interface import cli as main


@main.command(help="⚠️ TUI is under development. Use CLI commands instead.")
@require_init
def tui():
    """Interactive TUI for managing dotfiles.

    The TUI is currently under development. For now, use the CLI commands:

    Navigation:
      dot-man navigate <target>     # Switch configurations (recommended)
      dot-man status                 # Show current state

    Configuration:
      dot-man edit                   # Edit dot-man.toml
      dot-man config                 # Manage settings

    Files:
      dot-man add <path>             # Add file to tracking
      dot-man revert <file>          # Restore from branch

    Utilities:
      dot-man audit                  # Scan for secrets
      dot-man doctor                 # Diagnose issues

    Run [cyan]dot-man --help[/cyan] to see all commands.
    """
    ui.console.print()
    ui.console.print("[bold]📺 Interactive TUI[/bold]")
    ui.console.print()
    ui.console.print("[yellow]The TUI is under development.[/yellow]")
    ui.console.print()
    ui.console.print("[bold]Quick Navigation:[/bold]")
    ui.console.print("  [cyan]dot-man navigate --help[/cyan]  # Switch configurations")
    ui.console.print("  [cyan]dot-man status[/cyan]            # Show current state")
    ui.console.print()
    ui.console.print("[bold]Need help?[/bold]")
    ui.console.print("  [cyan]dot-man --help[/cyan]            # All commands")
    ui.console.print("  [cyan]dot-man doctor[/cyan]           # Diagnose issues")
