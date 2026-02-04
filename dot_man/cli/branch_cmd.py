"""Branch command for dot-man CLI."""

import click
from rich.table import Table

from .. import ui
from ..core import GitManager
from ..config import GlobalConfig
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, require_init, complete_branches, handle_exception


@main.group()
def branch():
    """Manage configuration branches."""
    pass


@branch.command("list")
@require_init
def branch_list():
    """List all configuration branches."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        current = global_config.current_branch
        branches = git.list_branches()

        if not branches:
            ui.console.print("[dim]No branches found[/dim]")
            return

        table = Table(title="Branches")
        table.add_column("Branch")
        table.add_column("Active")

        for b in branches:
            active = "[green]✓[/green]" if b == current else ""
            style = "bold" if b == current else ""
            table.add_row(f"[{style}]{b}[/{style}]" if style else b, active)

        ui.console.print(table)

    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Branch list")


@branch.command("delete")
@click.argument("name", shell_complete=complete_branches)
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
@require_init
def branch_delete(name: str, force: bool):
    """Delete a configuration branch."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        if name == global_config.current_branch:
            error("Cannot delete the active branch. Switch to another branch first.")

        if not git.branch_exists(name):
            error(f"Branch '{name}' not found")

        if not force:
            if not ui.confirm(f"Delete branch '{name}'? This cannot be undone"):
                ui.info("Aborted.")
                return

        git.delete_branch(name, force=force)
        success(f"Deleted branch '{name}'")

    except DotManError as e:
        from ..exceptions import BranchNotMergedError

        if isinstance(e, BranchNotMergedError):
            if ui.confirm(f"Branch '{name}' is not fully merged. Force delete?"):
                try:
                    git.delete_branch(name, force=True)  # type: ignore
                    success(f"Deleted branch '{name}'")
                    return
                except Exception as e2:
                    error(f"Failed to force delete: {e2}")
            else:
                ui.info("Aborted.")
                return

        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Branch delete")
