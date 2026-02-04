"""Revert command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, require_init

@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@require_init
def revert(path: Path, force: bool):
    """Revert a file to its repository version.

    This discards local changes and restores the file from the current branch's
    repository state.
    
    Example: dot-man revert ~/.bashrc
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        
        # Resolve to absolute path
        target_path = path.resolve()
        
        if not force:
            if not ui.confirm(f"Revert '{target_path}'? Local changes will be lost."):
                return

        ui.console.print(f"Reverting [cyan]{target_path}[/cyan]...")
        
        if ops.revert_file(target_path):
            success(f"Reverted: {target_path}")
        else:
            # ops.revert_file already logged a warning if it failed logic
            # verify exit code? if it returns false, it means something went wrong or wasn't tracked
            pass 

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Unexpected error: {e}")
