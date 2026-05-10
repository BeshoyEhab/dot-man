"""Log command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from .common import complete_branches, complete_tags, error, require_init, success, warn
from .interface import cli as main


@main.command()
@click.option("-n", "--count", default=10, help="Number of commits to show")
@click.option("--diff", "-d", is_flag=True, help="Show diff for each commit")
@click.option("--stat", is_flag=True, help="Show file change statistics")
@require_init
def log(count: int, diff: bool, stat: bool):
    """Show commit history with optional diffs.

    Examples:
        dot-man log
        dot-man log -n 20
        dot-man log --diff
        dot-man log --diff --stat
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        commits = list(ops.git.get_commits(count=count))

        if not commits:
            warn("No commits found")
            return

        for i, commit in enumerate(commits):
            sha = commit["sha"]
            message = commit["message"]
            author = commit["author"]
            date = commit["date"]

            # Format date nicely
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(date)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = date

            # Print commit header
            ui.console.print()
            ui.console.print(f"[bold cyan]{sha}[/bold cyan] [dim]{date_str}[/dim]")
            ui.console.print(f"[bold]{message}[/bold]")
            ui.console.print(f"[dim]by {author}[/dim]")

            # Show stat if requested
            if stat:
                try:
                    commit_obj = ops.git.repo.commit(sha)
                    files_changed = len(commit_obj.stats.files)
                    insertions = commit_obj.stats.total.get("insertions", 0)
                    deletions = commit_obj.stats.total.get("deletions", 0)
                    ui.console.print(
                        f"  [green]+{insertions}[/green] [red]-{deletions}[/red] "
                        f"({files_changed} file{'s' if files_changed != 1 else ''})"
                    )
                except Exception:
                    pass

            # Show diff if requested
            if diff:
                try:
                    # Get parent commit for diff
                    commit_obj = ops.git.repo.commit(sha)
                    parent = commit_obj.parents[0] if commit_obj.parents else None

                    if parent:
                        diff_text = ops.git.repo.git.diff(
                            parent.hexsha, commit_obj.hexsha, patch=True
                        )
                        if diff_text:
                            ui.console.print()
                            # Use a fixed-width font for diff
                            ui.console.print(
                                f"[dim]{diff_text[:2000]}[/dim]"
                                + ("... [truncated]" if len(diff_text) > 2000 else "")
                            )
                    else:
                        # First commit - show all files
                        diff_text = ops.git.repo.git.show(commit_obj.hexsha, patch=True)
                        if diff_text:
                            ui.console.print()
                            ui.console.print(
                                f"[dim]{diff_text[:2000]}[/dim]"
                                + ("... [truncated]" if len(diff_text) > 2000 else "")
                            )
                except Exception as e:
                    ui.console.print(f"[dim]  (diff unavailable: {e})[/dim]")

        ui.console.print()

    except Exception as e:
        error(str(e))


@main.command("diff")
@click.argument("file", required=False, type=click.Path(path_type=Path))
@click.option("--branch", "-b", help="Compare with another branch", shell_complete=complete_branches)
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
        from ..operations import get_operations

        ops = get_operations()
        git = ops.git

        if staged:
            # Show staged changes
            staged_files = git.repo.index.diff("HEAD")
            if not staged_files:
                warn("No staged changes")
                return

            ui.console.print("[bold]Staged Changes:[/bold]")
            for f in staged_files:
                ui.console.print(f"  {f.a_path}")
            return

        if branch:
            # Compare current branch with another branch
            current = ops.current_branch
            ui.console.print(f"[bold]Comparing[/bold] [cyan]{current}[/cyan] [bold]vs[/bold] [cyan]{branch}[/cyan]")
            ui.console.print()

            diff_result = git.repo.git.diff(f"{branch}...{current}")
            if diff_result:
                ui.console.print(diff_result[:5000])
                if len(diff_result) > 5000:
                    ui.console.print(f"\n[dim]... {len(diff_result) - 5000} more lines[/dim]")
            else:
                success("No differences found")
        elif file:
            # Show diff for specific file
            target_file = file.expanduser().resolve()

            # Find which section this file belongs to
            from ..constants import REPO_DIR
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for tracked_path in section.paths:
                    if tracked_path.resolve() == target_file:
                        repo_path = section.get_repo_path(tracked_path, REPO_DIR)

                        # Compare local vs repo
                        if target_file.exists():
                            local_content = target_file.read_text()
                        else:
                            local_content = ""

                        if repo_path.exists():
                            repo_content = repo_path.read_text()
                        else:
                            repo_content = ""

                        if local_content == repo_content:
                            success("File is identical to repository version")
                        else:
                            ui.console.print(f"[bold]Changes for:[/bold] {target_file}")
                            diff_result = git.repo.git.diff(
                                repo_path, target_file, patch=True
                            )
                            ui.console.print(diff_result[:3000])
                        return

            error(f"File not tracked: {target_file}")
        else:
            # Show uncommitted changes (working tree vs staging)
            if not git.is_dirty():
                success("No uncommitted changes")
                return

            ui.console.print("[bold]Uncommitted Changes:[/bold]")
            diff_result = git.repo.git.diff(patch=True)
            ui.console.print(diff_result[:5000])
            if len(diff_result) > 5000:
                ui.console.print(f"\n[dim]... {len(diff_result) - 5000} more lines[/dim]")

    except Exception as e:
        error(str(e))


@main.command()
@click.argument("target", shell_complete=complete_tags)
@require_init
def checkout(target: str):
    """Checkout a specific commit or tag (creates detached HEAD).

    This allows you to view the state of your dotfiles at a specific
    commit or tag without switching branches.

    To return to a branch, use:
        dot-man switch <branch-name>

    Examples:
        dot-man checkout abc1234
        dot-man checkout my-tag
    """
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
    from .. import ui

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
    from .. import ui
    from .common import success

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
