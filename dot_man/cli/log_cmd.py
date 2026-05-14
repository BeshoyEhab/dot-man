"""Log command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from .common import complete_branches, complete_tags, error, require_init, success
from .interface import cli as main


@main.command()
@click.argument("file", required=False, type=click.Path(path_type=Path))
@click.option("-n", "--count", type=int, help="Number of commits to show")
@click.option(
    "--diff", "-d", "show_diff", is_flag=True, help="Show diff for each commit"
)
@click.option("--stat", is_flag=True, help="Show file change statistics")
@click.option("--interactive", "-i", is_flag=True, help="Interactive log browser")
@require_init
def log(
    file: Path | None, count: int | None, show_diff: bool, stat: bool, interactive: bool
):
    """Show commit history.

    Examples:
        dot-man log
        dot-man log .bashrc
        dot-man log -n 20
        dot-man log --diff
        dot-man log --interactive
    """
    try:
        import subprocess

        from ..constants import REPO_DIR

        if interactive:
            from ..tui_log import LogViewerApp

            app = LogViewerApp()
            app.run()
            return

        git_args = ["git", "log", "--color=always"]
        if count:
            git_args.append(f"-n{count}")
        if show_diff:
            git_args.append("-p")
        if stat:
            git_args.append("--stat")

        if file:
            from ..operations import get_operations

            ops = get_operations()
            target_file = file.expanduser().resolve()
            found = False
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for tracked_path in section.paths:
                    if tracked_path.resolve() == target_file:
                        repo_path = section.get_repo_path(tracked_path, REPO_DIR)
                        git_args.extend(["--", str(repo_path.relative_to(REPO_DIR))])
                        found = True
                        break
                if found:
                    break

            if not found:
                error(f"File not tracked: {target_file}")
                return

        # Let git handle the pager and standard output natively
        subprocess.run(git_args, cwd=REPO_DIR)

    except Exception as e:
        error(str(e))


@main.command("diff")
@click.argument("file", required=False, type=click.Path(path_type=Path))
@click.option(
    "--branch",
    "-b",
    help="Compare with another branch",
    shell_complete=complete_branches,
)
@click.option("--staged", is_flag=True, help="Show staged changes")
@require_init
def diff(file: Path | None, branch: str | None, staged: bool):
    """Show changes between branches or files.

    Examples:
        dot-man diff                    # Show uncommitted changes
        dot-man diff --branch main      # Compare current branch with main
        dot-man diff .bashrc            # Show changes for specific file
    """
    try:
        import subprocess

        from ..constants import REPO_DIR

        git_args = ["git", "diff", "--color=always"]

        if staged:
            git_args.append("--staged")

        if branch:
            from ..operations import get_operations

            ops = get_operations()
            current = ops.current_branch
            git_args.append(f"{branch}...{current}")

        if file:
            from ..operations import get_operations

            ops = get_operations()
            target_file = file.expanduser().resolve()
            found = False
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for tracked_path in section.paths:
                    if tracked_path.resolve() == target_file:
                        repo_path = section.get_repo_path(tracked_path, REPO_DIR)
                        # Use git diff --no-index to compare the file in repo with the local file outside repo
                        git_args.extend(
                            ["--no-index", str(repo_path), str(target_file)]
                        )
                        found = True
                        break
                if found:
                    break

            if not found:
                error(f"File not tracked: {target_file}")
                return

        subprocess.run(git_args, cwd=REPO_DIR)

    except Exception as e:
        error(str(e))


@main.command(deprecated=True, help="⚠️ DEPRECATED: Use 'dot-man navigate' instead")
@click.argument("target", shell_complete=complete_tags)
@require_init
def checkout(target: str):
    """Checkout a specific commit or tag (creates detached HEAD).

    This allows you to view the state of your dotfiles at a specific
    commit or tag without switching branches.

    ⚠️ DEPRECATED: Use 'dot-man navigate' instead.

    To return to a branch, use:
        dot-man navigate <branch-name>

    Examples:
        dot-man checkout abc1234
        dot-man checkout my-tag
    """
    ui.console.print(
        "[yellow bold]⚠️ WARNING:[/yellow bold] [yellow]'checkout' is deprecated.[/yellow]\n"
        "  Use [cyan]dot-man navigate[/cyan] instead.\n"
        "  Run [cyan]dot-man navigate --help[/cyan] to see the new command.\n"
    )
    try:
        from ..operations import get_operations

        ops = get_operations()
        current_branch = ops.current_branch

        # Try to determine if target is a tag or commit
        from .common import parse_branch_arg

        parsed = parse_branch_arg(target)

        if parsed["type"] == "tag":
            _checkout_tag(ops, current_branch, parsed["target"])
        elif parsed["type"] == "commit":
            _checkout_commit(ops, current_branch, parsed["target"])
        else:
            # Check if it's a tag or commit by checking git
            # First try as commit
            try:
                ops.git.repo.commit(target)
                _checkout_commit(ops, current_branch, target)
            except Exception:
                # Try as tag
                tag_commit = ops.git.get_tag_commit(target)
                if tag_commit:
                    _checkout_tag(ops, current_branch, target)
                else:
                    error(f"Unknown commit or tag: {target}", exit_code=1)

    except Exception as e:
        error(str(e))


def _checkout_commit(ops, current_branch: str, commit_sha: str):
    """Checkout a specific commit."""

    # Check if it's a valid commit
    try:
        commit_obj = ops.git.repo.commit(commit_sha)
    except Exception:
        error(f"Invalid commit SHA: {commit_sha}", exit_code=1)

    # Save current changes if dirty
    if ops.git.is_dirty():
        ui.console.print(
            f"[yellow]Warning:[/yellow] You have uncommitted changes on branch "
            f"[bold]{current_branch}[/bold]"
        )
        ui.console.print("  These changes will NOT be saved.")
        ui.console.print()

    # Checkout the commit
    ops.git.checkout_commit(commit_sha)

    ui.console.print("Note: You are in [bold]detached HEAD[/bold] state")
    ui.console.print(f"  Commit: [cyan]{commit_sha}[/cyan]")
    ui.console.print(f"  Message: {commit_obj.message.strip().split(chr(10))[0][:60]}")
    ui.console.print()
    ui.console.print("To return to a branch, run:")
    ui.console.print("  [cyan]dot-man switch <branch-name>[/cyan]")


def _checkout_tag(ops, current_branch: str, tag_name: str):
    """Checkout a specific tag."""

    tag_commit = ops.git.get_tag_commit(tag_name)
    if not tag_commit:
        error(f"Tag not found: {tag_name}", exit_code=1)

    # Get tag info
    try:
        tag_obj = ops.git.repo.tags[tag_name]
        message = ""
        if tag_obj.tag:
            message = tag_obj.tag.message.strip().split("\n")[0]
    except Exception:
        message = ""

    # Checkout the tag
    ops.git.checkout(tag_name)

    success(f"Checked out tag '{tag_name}'")
    if message:
        ui.console.print(f"  Tag message: {message}")
    ui.console.print(f"  Commit: [cyan]{tag_commit}[/cyan]")
    ui.console.print()
    ui.console.print("To return to a branch, run:")
    ui.console.print("  [cyan]dot-man switch <branch-name>[/cyan]")
