"""Tag commands for dot-man CLI."""

import click

from .. import ui
from .interface import cli as main
from .common import error, success, warn, require_init, complete_tags


@main.group()
@require_init
def tag():
    """Manage tags for fast navigation.

    Tags are like bookmarks for specific commits, allowing you to
    quickly switch to important points in your dotfiles history.

    Examples:
        dot-man tag list
        dot-man tag create my-setup
        dot-man tag create v1 abc1234
        dot-man tag delete old-tag
        dot-man tag switch my-setup
    """
    pass


@tag.command("list")
def tag_list():
    """List all tags."""
    try:
        from ..operations import get_operations

        ops = get_operations()
        tags = ops.git.list_tags()

        if not tags:
            warn("No tags found")
            return

        ui.console.print("[bold]Tags:[/bold]")
        for t in sorted(tags):
            commit_sha = ops.git.get_tag_commit(t)
            if commit_sha:
                ui.console.print(f"  [cyan]{t}[/cyan] -> {commit_sha}")

    except Exception as e:
        error(str(e))


@tag.command("create")
@click.argument("name")
@click.argument("commit", required=False)
@click.option("-m", "--message", help="Tag message (for annotated tags)")
def tag_create(name: str, commit: str | None, message: str | None):
    """Create a tag at the current commit or a specific commit.

    NAME is the name for the tag.
    COMMIT is optional - if provided, tag that commit instead of current HEAD.

    Examples:
        dot-man tag create my-setup
        dot-man tag create v1 abc1234
        dot-man tag create backup-2024 -m "Backup before system change"
    """
    try:
        from ..operations import get_operations

        ops = get_operations()

        # Determine which commit to tag
        target_commit = commit if commit else "HEAD"

        # Validate the commit exists
        try:
            commit_obj = ops.git.repo.commit(target_commit)
            target_sha = commit_obj.hexsha
        except Exception:
            error(f"Invalid commit: {commit}", exit_code=1)

        # Create the tag
        ops.git.create_tag(name, ref=target_sha, message=message)

        if message:
            success(f"Created annotated tag '{name}'")
        else:
            success(f"Created lightweight tag '{name}'")

        ui.console.print(f"  Points to: [cyan]{target_sha[:7]}[/cyan]")

    except Exception as e:
        error(str(e))


@tag.command("delete")
@click.argument("name", shell_complete=complete_tags)
@click.option("-f", "--force", is_flag=True, help="Force delete without confirmation")
def tag_delete(name: str, force: bool):
    """Delete a tag.

    Examples:
        dot-man tag delete old-tag
        dot-man tag delete -f temp-tag
    """
    try:
        from ..operations import get_operations
        from ..core import GitOperationError

        ops = get_operations()

        # Check if tag exists
        if name not in ops.git.list_tags():
            error(f"Tag not found: {name}", exit_code=1)

        # Confirm deletion unless -f flag
        if not force:
            ui.console.print(f"Delete tag '[bold]{name}[/bold]'?")
            if not ui.ask("Confirm", choices=["y", "n"], default="n") == "y":
                warn("Cancelled")
                return

        # Delete the tag
        try:
            ops.git.delete_tag(name)
            success(f"Deleted tag '{name}'")
        except GitOperationError as e:
            error(str(e), e.exit_code)

    except Exception as e:
        error(str(e))


@tag.command("switch")
@click.argument("name", shell_complete=complete_tags)
def tag_switch(name: str):
    """Switch to a tag (checkout the tag).

    This is equivalent to: dot-man checkout <tag>

    Examples:
        dot-man tag switch my-setup
        dot-man tag switch v1
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        current_branch = ops.current_branch

        # Check if tag exists
        tag_commit = ops.git.get_tag_commit(name)
        if not tag_commit:
            error(f"Tag not found: {name}", exit_code=1)

        # Checkout the tag
        ops.git.checkout(name)

        success(f"Switched to tag '{name}'")
        ui.console.print(f"  Commit: [cyan]{tag_commit}[/cyan]")
        ui.console.print()
        ui.console.print("To return to a branch, run:")
        ui.console.print(f"  [cyan]dot-man switch <branch-name>[/cyan]")

    except Exception as e:
        error(str(e))