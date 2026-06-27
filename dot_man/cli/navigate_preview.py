"""Preview and diff display functions for navigate command."""

import subprocess

from .. import ui
from ..constants import REPO_DIR
from ..core import GitManager


def show_branch_diff_preview(ops, source: str, target: str, show_diff: bool = False):
    """Show diff preview between two branches."""
    ui.console.print()
    ui.console.print("[bold cyan]┌─────────────────────────────────────┐[/bold cyan]")
    ui.console.print(
        "[bold cyan]│[/bold cyan]  🔀 Branch Diff Preview              [bold cyan]│[/bold cyan]"
    )
    ui.console.print("[bold cyan]└─────────────────────────────────────┘[/bold cyan]")
    ui.console.print()
    ui.console.print(f"  [dim]From:[/dim] [cyan]{source}[/cyan]")
    ui.console.print(f"  [dim]To:[/dim]   [cyan]{target}[/cyan]")
    ui.console.print()

    git = GitManager()

    if git.branch_exists(source) and git.branch_exists(target):
        ui.console.print("[bold]📁 Changed files:[/bold]")
        try:
            result = git.repo.git.diff("--name-only", f"{source}...{target}")
            if result:
                for f in result.splitlines():
                    ui.console.print(f"     • [yellow]{f}[/yellow]")
            else:
                ui.console.print("     [dim](no differences)[/dim]")

            if show_diff:
                ui.console.print()
                ui.console.print("[bold]📄 Full Diff:[/bold]")
                subprocess.run(
                    ["git", "diff", "--color=always", f"{source}...{target}"],
                    cwd=REPO_DIR,
                )
        except Exception as e:
            ui.console.print(f"  [dim]Could not diff branches: {e}[/dim]")
    else:
        ui.console.print("  [dim](branch diff not available)[/dim]")


def show_commit_diff(ops, commit_sha: str):
    """Show what files changed in a specific commit."""
    git = GitManager()
    try:
        commit = git.repo.commit(commit_sha)
        ui.console.print()
        ui.console.print(
            "[bold cyan]┌─────────────────────────────────────┐[/bold cyan]"
        )
        ui.console.print(
            "[bold cyan]│[/bold cyan]  📌 Commit Details                      [bold cyan]│[/bold cyan]"
        )
        ui.console.print(
            "[bold cyan]└─────────────────────────────────────┘[/bold cyan]"
        )
        ui.console.print()
        ui.console.print(f"  [dim]Commit:[/dim]   [cyan]{commit_sha[:7]}[/cyan]")
        ui.console.print(
            f"  [dim]Message:[/dim] {str(commit.message).strip().split(chr(10))[0]}"
        )
        ui.console.print(
            f"  [dim]Author:[/dim]  {commit.author.name} <{commit.author.email}>"
        )
        ui.console.print()

        files_changed = []
        for parent in commit.parents:
            diff = parent.diff(commit)
            for d in diff:
                if d.a_path:
                    files_changed.append(f"[red]- {d.a_path}[/red]")
                if d.b_path:
                    files_changed.append(f"[green]+ {d.b_path}[/green]")

        if files_changed:
            ui.console.print("[bold]📁 Files changed:[/bold]")
            for f in files_changed[:10]:
                ui.console.print(f"     {f}")
            if len(files_changed) > 10:
                ui.console.print(
                    f"     [dim]... and {len(files_changed) - 10} more[/dim]"
                )
        ui.console.print()

        subprocess.run(
            ["git", "show", "--color=always", commit_sha, "--"], cwd=REPO_DIR
        )
    except Exception as e:
        ui.console.print(f"  [dim]Could not show commit diff: {e}[/dim]")


def show_commits_list(ops, branch: str, files_only: bool = False, count: int = 20):
    """Show commits for a branch with detailed information."""
    ui.console.print()
    ui.console.print("[bold cyan]┌─────────────────────────────────────┐[/bold cyan]")
    ui.console.print(
        "[bold cyan]│[/bold cyan]  📜 Commit History on [cyan]{}[/cyan]              [bold cyan]│[/bold cyan]".format(
            branch
        )
    )
    ui.console.print("[bold cyan]└─────────────────────────────────────┘[/bold cyan]")
    ui.console.print()

    git = GitManager()

    if files_only:
        commits = get_commits_with_file_changes(ops, branch, count)
        if commits:
            for commit in commits:
                ui.console.print(
                    f"[cyan]{commit['sha']}[/cyan] [dim]│[/dim] {commit['message']}"
                )
                ui.console.print(f"  [dim]{commit['date']}[/dim]")
                ui.console.print("  [dim]📁 Files:[/dim]")
                for f in commit["files"][:5]:
                    ui.console.print(f"     • [yellow]{f}[/yellow]")
                if commit.get("files_more"):
                    ui.console.print(
                        f"     [dim]... and {commit['files_more']} more[/dim]"
                    )
                ui.console.print()
            return
        else:
            ui.console.print("  [dim](no commits with tracked file changes)[/dim]")
            return

    commits = git.get_commits_detailed(count, branch)

    if not commits:
        ui.console.print("  [dim](no commits)[/dim]")
        return

    for commit in commits:
        tags_str = ""
        if commit["tags"]:
            tags_str = f" [dim]│[/dim] [green]🏷 {', '.join(commit['tags'])}[/green]"

        merge_icon = (
            " [dim]│[/dim] [yellow]⟷ merge[/yellow]" if commit["is_merge"] else ""
        )

        ui.console.print(
            f"[cyan]{commit['sha']}[/cyan]"
            f" [dim]│[/dim] {commit['message']}"
            f"{tags_str}{merge_icon}"
        )
        ui.console.print(
            f"  [dim]{commit['relative_date']}[/dim]"
            f" [dim]│[/dim] [dim]+{commit['insertions']}[/dim]"
            f" [dim]-{commit['deletions']}[/dim]"
        )

        if commit["files"]:
            ui.console.print("  [dim]📁 Files:[/dim]")
            for f in commit["files"]:
                ui.console.print(f"     • [yellow]{f}[/yellow]")
            if commit["files_more"]:
                ui.console.print(f"     [dim]... and {commit['files_more']} more[/dim]")

        ui.console.print()


def get_commits_with_file_changes(ops, branch: str, max_count: int = 20) -> list[dict]:
    """Get commits that changed tracked files."""
    git = GitManager()
    commits = git.get_commits_detailed(max_count, branch)

    result = []
    for commit in commits:
        if commit["files"]:
            result.append(
                {
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "author": commit["author"],
                    "date": commit["date"],
                    "files": commit["files"],
                    "files_more": commit["files_more"],
                }
            )

    return result
