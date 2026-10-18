"""Revert command for dot-man CLI."""

from pathlib import Path

import click
from git import GitCommandError

from .. import constants, ui
from ..exceptions import DotManError
from .common import AliasedCommand, complete_commits, error, require_init, success
from .interface import cli as main


def restore_file_from_commit(ops, target_path: Path, commit: str, force: bool) -> bool:
    """Overwrite ``target_path`` (and the repo copy) with the ``commit`` version.

    Shared by ``revert --commit`` and the deprecated ``restore`` alias so the
    two can never drift.  Failures exit through ``error()``; a declined
    confirmation returns ``False`` without touching anything.
    """
    repo_rel: Path | None = None
    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        for tracked_path in section.paths:
            if tracked_path.resolve() == target_path:
                repo_rel = section.get_repo_path(
                    tracked_path, constants.get_repo_dir()
                ).relative_to(constants.get_repo_dir())
                break
        if repo_rel is not None:
            break

    if repo_rel is None:
        error(f"File not tracked: {target_path}")
        return False

    try:
        # Read the blob through the object API. ``git show`` (and any command
        # run through GitPython's stdout handling) strips the trailing
        # newline, which silently truncated dotfiles on every restore.
        blob = ops.git.repo.commit(commit).tree / str(repo_rel)
        content = blob.data_stream.read()
    except (GitCommandError, KeyError, ValueError, AttributeError) as e:
        error(f"Could not restore from commit: {e}")
        return False

    if not force:
        if not ui.confirm(f"Overwrite '{target_path}' with version from {commit}?"):
            return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(content)

    # Keep the repo working copy in sync so `dot-man status` stays clean.
    repo_path = constants.get_repo_dir() / repo_rel
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    repo_path.write_bytes(content)

    success(f"Restored: {target_path} from {commit}")
    return True


@main.command("revert", cls=AliasedCommand)
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
        from ..operations import get_operations

        ops = get_operations()

        # Resolve to absolute path
        target_path = path.expanduser().resolve()

        if commit:
            # Canonical single-file restore from a past commit.
            restore_file_from_commit(ops, target_path, commit, force)
            return

        # Default: revert to current branch version
        if not force:
            if not ui.confirm(f"Revert '{target_path}'? Local changes will be lost."):
                return

        ui.console.print(f"Reverting [cyan]{target_path}[/cyan]...")

        if ops.revert_file(target_path):
            success(f"Reverted: {target_path}")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Unexpected error: {e}")
