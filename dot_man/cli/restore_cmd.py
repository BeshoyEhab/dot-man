"""Restore command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from ..exceptions import DotManError
from .common import complete_commits, error, require_init, success
from .interface import cli as main


@main.command("restore")
@click.argument("file", type=click.Path(path_type=Path))
@click.argument("commit", shell_complete=complete_commits)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@require_init
def restore(file: Path, commit: str, force: bool):
    """Restore a file from history.

    This restores the file from a specific commit and overwrites your local
    working file.

    Examples:
        dot-man restore ~/.bashrc abc1234
    """
    try:
        from ..constants import REPO_DIR
        from ..operations import get_operations

        ops = get_operations()
        target_path = file.expanduser().resolve()

        # Ensure the file is tracked
        found = False
        repo_path = None
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for tracked_path in section.paths:
                if tracked_path.resolve() == target_path:
                    repo_path = section.get_repo_path(tracked_path, REPO_DIR)
                    found = True
                    break
            if found:
                break

        if not found or not repo_path:
            error(f"File not tracked: {target_path}")
            return

        ui.console.print(
            f"Restoring [cyan]{target_path}[/cyan] from commit [yellow]{commit}[/yellow]..."
        )

        try:
            # We use the relative path of the file inside the repo
            repo_rel_path = repo_path.relative_to(REPO_DIR)
            file_content = ops.git.repo.git.show(f"{commit}:{repo_rel_path}")

            if not force:
                if not ui.confirm(
                    f"Overwrite '{target_path}' with version from {commit}?"
                ):
                    return

            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(file_content)

            # Also update the repo working copy so that `dot-man status` doesn't show it as a pending overwrite from the repo (or we could wait for user to save).
            # It's better to update both to keep them in sync, or let deploy/save handle it. We will update repo path as well.
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            repo_path.write_text(file_content)

            success(f"Restored: {target_path} from {commit}")

        except Exception as e:
            error(f"Could not restore from commit: {e}")

    except DotManError as e:
        error(str(e), getattr(e, "exit_code", 1))
    except Exception as e:
        error(f"Unexpected error: {e}")
