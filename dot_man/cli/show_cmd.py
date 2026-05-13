"""Show command for dot-man CLI."""

import subprocess

import click

from ..constants import REPO_DIR
from .common import complete_commits, error, require_init
from .interface import cli as main


@main.command("show")
@click.argument("commit", shell_complete=complete_commits)
@require_init
def show(commit: str):
    """View full diff for a specific commit.

    This acts as a native wrapper for git show, providing full native output
    including colors and pagers.

    Examples:
        dot-man show HEAD
        dot-man show abc1234
    """
    try:
        git_args = ["git", "show", "--color=always", commit]
        subprocess.run(git_args, cwd=REPO_DIR)
    except Exception as e:
        error(str(e))
