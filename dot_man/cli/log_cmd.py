"""Log command for dot-man CLI."""

import logging
from pathlib import Path

import click

from .. import ui
from .common import (
    AliasedCommand,
    complete_branches,
    complete_tags,
    error,
    require_init,
    success,
)
from .interface import cli as main


@main.command("log", cls=AliasedCommand, aliases=["log"])
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


@main.command("diff", cls=AliasedCommand, aliases=["dif"])
@click.argument("file", required=False, type=click.Path(path_type=Path))
@click.option(
    "--branch",
    "-b",
    help="Compare with another branch",
    shell_complete=complete_branches,
)
@click.option("--staged", is_flag=True, help="Show staged changes")
@click.option(
    "--rich/--no-rich",
    default=True,
    help="Use rich for syntax-highlighted diff (default: enabled)",
)
@require_init
def diff(file: Path | None, branch: str | None, staged: bool, rich: bool):
    """Show changes between branches or files.

    Examples:
        dot-man diff                    # Show uncommitted changes
        dot-man diff --branch main      # Compare current branch with main
        dot-man diff .bashrc            # Show changes for specific file
        dot-man diff --no-rich          # Use plain git diff
    """
    try:
        import subprocess

        from ..constants import REPO_DIR

        if rich:
            _show_rich_diff(file, branch, staged)
        else:
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
                logging.debug("Target is not a valid commit, trying as tag")
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
        logging.debug("Invalid commit SHA: %s", commit_sha)
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
        logging.debug("Failed to get tag message for %s", tag_name)
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


def _show_rich_diff(file: Path | None, branch: str | None, staged: bool):
    """Show syntax-highlighted diff using rich."""
    try:
        import subprocess

        from rich.console import Console
        from rich.syntax import Syntax

        from ..constants import REPO_DIR

        console = Console()

        git_args = ["git", "diff", "--no-color"]

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

        result = subprocess.run(git_args, cwd=REPO_DIR, capture_output=True, text=True)

        if result.stdout:
            syntax = Syntax(result.stdout, "diff", theme="monokai", line_numbers=True)
            console.print(syntax)
        else:
            ui.console.print("[dim]No changes found[/dim]")

        if result.returncode == 1:
            pass
        elif result.returncode > 1:
            error(f"Git diff failed: {result.stderr}")

    except ImportError:
        ui.console.print(
            "[yellow]Rich not installed, falling back to git diff[/yellow]"
        )
        git_args = ["git", "diff", "--color=always"]
        if staged:
            git_args.append("--staged")
        if branch:
            from ..operations import get_operations

            ops = get_operations()
            git_args.append(f"{branch}...{ops.current_branch}")
        subprocess.run(git_args, cwd=REPO_DIR)
