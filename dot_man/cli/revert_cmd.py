"""Revert command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from ..exceptions import DotManError
from .common import AliasedCommand, complete_commits, error, require_init, success
from .interface import cli as main


@main.command("revert", cls=AliasedCommand, aliases=["rev"])
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--commit",
    "-c",
    help="Restore from specific commit SHA",
    shell_complete=complete_commits,
)
@require_init
def revert(path: Path, force: bool, commit: str | None):
    """Revert a file to its repository version.

    This discards local changes and restores the file from the current branch's
    repository state, or from a specific commit.

    Examples:
        dot-man revert ~/.bashrc              # Revert to current branch version
        dot-man revert ~/.bashrc -c abc1234    # Restore from specific commit
    """
    try:
        from ..constants import REPO_DIR
        from ..operations import get_operations

        ops = get_operations()

        # Resolve to absolute path
        target_path = path.expanduser().resolve()

        if commit:
            # Restore from specific commit
            ui.console.print(
                f"Restoring [cyan]{target_path}[/cyan] from commit [yellow]{commit}[/yellow]..."
            )

            # Find the file in git history
            try:
                # Get the file content from the commit
                file_content = ops.git.repo.git.show(
                    f"{commit}:{target_path.relative_to(REPO_DIR.parent)}"
                )

                if not force:
                    if not ui.confirm(
                        f"Overwrite '{target_path}' with version from {commit}?"
                    ):
                        return

                # Write the content
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(file_content)

                success(f"Restored: {target_path} from {commit}")
                return

            except Exception as e:
                error(f"Could not restore from commit: {e}")

        # Default: revert to current branch version
        if not force:
            if not ui.confirm(f"Revert '{target_path}'? Local changes will be lost."):
                return

        ui.console.print(f"Reverting [cyan]{target_path}[/cyan]...")

        if ops.revert_file(target_path):
            success(f"Reverted: {target_path}")
        else:
            pass

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Unexpected error: {e}")
