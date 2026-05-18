"""Navigate command for dot-man - unified switch + checkout with diff preview."""

import os
import subprocess
from datetime import datetime

import click

from .. import ui
from ..constants import REPO_DIR
from ..core import GitManager
from ..files import compare_files
from ..hooks import run_checkout_hooks, run_switch_hooks
from .common import (
    AliasedCommand,
    complete_switch_args,
    error,
    get_secret_handler,
    parse_branch_arg,
    require_init,
    success,
    warn,
)
from .interface import cli as main


def generate_commit_message(
    source: str,
    target: str,
    target_type: str,
    saved_count: int = 0,
    sections: list[str] | None = None,
) -> str:
    """Generate a smart commit message based on context.

    Args:
        source: Source branch/commit
        target: Target branch/commit
        target_type: "branch", "tag", or "commit"
        saved_count: Number of files saved
        sections: List of section names that changed

    Returns:
        A descriptive commit message
    """
    from ..core import GitManager

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if target_type == "tag":
        action = f"switch to tag {target}"
    elif target_type == "commit":
        action = f"checkout commit {target[:7]}"
    else:
        action = f"switch to branch '{target}'"

    git = GitManager()

    msg = f"[dot-man] Save before {action}"

    details = []
    if saved_count > 0:
        details.append(f"{saved_count} files")

    if sections:
        relevant = [s for s in sections if s not in ("defaults", "config")]
        if relevant:
            shown = ", ".join(relevant[:3])
            if len(relevant) > 3:
                shown += f" +{len(relevant) - 3} more"
            details.append(f"sections: {shown}")

    changed_files = []
    try:
        if git.is_dirty():
            for diff in git.repo.index.diff(None):
                if diff.a_path:
                    changed_files.append(diff.a_path)
                if diff.b_path:
                    changed_files.append(diff.b_path)
        changed_files = list(set(changed_files))[:5]
        if changed_files:
            shown_files = ", ".join([f.split("/")[-1] for f in changed_files])
            if len(changed_files) > 5:
                shown_files += f" +{len(changed_files) - 5} more"
            details.append(f"files: {shown_files}")
    except Exception:
        pass

    if details:
        msg += f" | {' | '.join(details)}"

    msg += f" [{timestamp}]"

    return msg


def get_changed_sections(ops) -> list[str]:
    """Get list of sections that have pending changes."""
    try:
        sections = []
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                if repo_path.exists():
                    if not local_path.exists() or not compare_files(
                        repo_path, local_path
                    ):
                        if section_name not in sections:
                            sections.append(section_name)
        return sections
    except Exception:
        return []


def run_branch_hooks(ops, hook_type: str) -> None:
    """Run on_activate or on_deactivate hooks from sections.

    Args:
        ops: DotManOperations instance
        hook_type: "on_activate" or "on_deactivate"
    """
    commands: list[str] = []
    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        cmd = getattr(section, hook_type, None)
        if cmd:
            commands.append(cmd)

    commands = list(dict.fromkeys(commands))

    if commands:
        ui.console.print()
        ui.console.print(f"[bold]Running {hook_type} hooks...[/bold]")
        hook_failed = False
        for cmd in commands:
            ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
            try:
                shell = os.environ.get("SHELL", "/bin/sh")
                result = subprocess.run(
                    [shell, "-c", cmd], capture_output=True, text=True
                )
                if result.returncode != 0:
                    hook_failed = True
                    ui.console.print(
                        f"  [yellow]⚠ Hook failed (exit code {result.returncode})[/yellow]"
                    )
                    if result.stderr:
                        for line in result.stderr.splitlines()[:3]:
                            ui.console.print(f"    [dim]{line}[/dim]")
            except Exception as e:
                hook_failed = True
                warn(f"Failed to run command '{cmd}': {e}")
        if hook_failed:
            ui.console.print("[dim]  Some hooks failed - continuing anyway[/dim]")


class BranchParamType(click.ParamType):
    """Parameter type that accepts branch, branch@tag, or commit SHA."""

    name = "branch"

    def convert(self, value, param, ctx):
        if not value:
            return None
        parsed = parse_branch_arg(value)
        return parsed


BRANCH = BranchParamType()


@main.command("navigate", cls=AliasedCommand, aliases=["nav"])
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--save",
    "save_mode",
    flag_value="save",
    default=None,
    help="Save current changes before switching",
)
@click.option(
    "--no-save",
    "save_mode",
    flag_value="no-save",
    default=None,
    help="Discard current changes before switching",
)
@click.option(
    "--message",
    "-m",
    "commit_message",
    type=str,
    default="auto",
    help="Custom commit message for auto-save (default: auto-generated). Use -m 'auto' for smart messages, -m 'none' to disable, or provide your own message.",
)
@click.option(
    "--preview",
    "-p",
    is_flag=True,
    help="Preview changes between branches before switching",
)
@click.option(
    "--diff",
    "-d",
    is_flag=True,
    help="Show diff of changes when previewing",
)
@click.option(
    "--files-only",
    is_flag=True,
    help="Only show commits that affected tracked files",
)
@click.argument(
    "target", type=BRANCH, required=False, shell_complete=complete_switch_args
)
@require_init
def navigate(
    target, dry_run, force, save_mode, commit_message, preview, diff, files_only
):
    """Navigate to a branch, tag, or commit with optional diff preview.

    This is the unified command for switching between configurations.
    It supports all branch, tag, and commit targets with full preview
    and diff capabilities.

    Supports multiple formats:
        \b
        dot-man navigate work          # switch to branch
        dot-man navigate work@tag     # switch to branch at tag position
        dot-man navigate abc1234      # switch to specific commit
        dot-man navigate my-tag       # switch to tag

    Use --preview or -p to see changes before switching.
    Use --diff or -d to show actual diff when previewing.
    Use --files-only to only show commits that changed tracked files.
    Use -m to provide a custom commit message for auto-save.
    Use -m "auto" for auto-generated messages based on changes.

    Examples:
        dot-man navigate work                  # switch to branch
        dot-man navigate work --preview        # preview changes
        dot-man navigate work --preview --diff # show full diff
        dot-man navigate work --files-only     # only changed commits
    """
    try:
        from ..operations import get_operations

        if not target:
            error("No branch, tag, or commit specified", exit_code=1)

        parsed = target
        ops = get_operations()

        if save_mode is None:
            save_mode = ops.global_config.switch_default_behavior

        target_type = parsed["type"]
        target_name = parsed["target"]
        current_branch = ops.current_branch

        if target_type == "commit":
            _handle_commit_navigate(
                ops,
                current_branch,
                target_name,
                save_mode,
                dry_run,
                force,
                preview,
                diff,
                files_only,
                commit_message,
            )
        elif target_type == "tag":
            _handle_tag_navigate(
                ops,
                current_branch,
                parsed["base"],
                target_name,
                save_mode,
                dry_run,
                force,
                preview,
                diff,
                files_only,
                commit_message,
            )
        else:
            _handle_branch_navigate(
                ops,
                current_branch,
                target_name,
                save_mode,
                dry_run,
                force,
                preview,
                diff,
                files_only,
                commit_message,
            )

    except Exception as e:
        from ..exceptions import ErrorDiagnostic

        ui.console.print()
        ui.console.print(
            f"[red bold]{ErrorDiagnostic.from_exception(e).title}[/red bold]"
        )
        ui.console.print(f"[red]{ErrorDiagnostic.from_exception(e).details}[/red]")
        raise SystemExit(1)


def _show_branch_diff_preview(ops, source: str, target: str, show_diff: bool = False):
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


def _show_commit_diff(ops, commit_sha: str):
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


def _show_commits_list(ops, branch: str, files_only: bool = False, count: int = 20):
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
        commits = _get_commits_with_file_changes(ops, branch, count)
        if commits:
            for commit in commits:
                tags_str = ""
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


def _get_commits_with_file_changes(ops, branch: str, max_count: int = 20) -> list[dict]:
    """Get commits that changed tracked files.

    Args:
        ops: DotManOperations instance
        branch: Branch name
        max_count: Maximum number of commits to check

    Returns:
        List of dicts with: sha, message, author, date, files
    """
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


def _handle_commit_navigate(
    ops,
    current_branch,
    commit_sha,
    save_mode,
    dry_run,
    force,
    preview,
    show_diff,
    files_only,
    commit_message=None,
):
    """Handle navigating to a specific commit."""
    ui.console.print(f"[bold]Navigating to commit[/bold] [cyan]{commit_sha}[/cyan]...")

    if preview:
        ui.console.print("[bold]Preview mode - showing commit info[/bold]")
        _show_commit_diff(ops, commit_sha)
        ui.console.print("Run again without --preview to checkout this commit.")
        return

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        return

    if save_mode == "save":
        ui.console.print(f"[bold]Saving current branch '{current_branch}'...[/bold]")
        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        saved_count = save_result["saved"]
        sections = get_changed_sections(ops)

        if commit_message and commit_message.lower() != "none":
            if commit_message.lower() == "auto":
                commit_msg = generate_commit_message(
                    current_branch, commit_sha, "commit", saved_count, sections
                )
            else:
                commit_msg = commit_message

            ops.git.commit(commit_msg)
            ui.console.print(f"  Saved {saved_count} files")
            if commit_message.lower() != "auto":
                ui.console.print(f"  [dim]Commit: {commit_msg}[/dim]")
        else:
            ui.console.print(f"  Saved {saved_count} files (no commit)")

    run_checkout_hooks("pre", commit_sha)

    ops.git.checkout_commit(commit_sha)
    ui.console.print(f"  Checked out commit: [dim]{commit_sha}[/dim]")
    ui.console.print("[yellow]Note: You are in detached HEAD state[/yellow]")
    ui.console.print("  Use 'dot-man navigate <branch>' to return to a branch")

    run_checkout_hooks("post", commit_sha)


def _handle_tag_navigate(
    ops,
    current_branch,
    base_branch,
    tag_name,
    save_mode,
    dry_run,
    force,
    preview,
    show_diff,
    files_only,
    commit_message=None,
):
    """Handle navigating to a tag."""
    ui.console.print(f"[bold]Navigating to tag[/bold] [cyan]{tag_name}[/cyan]...")

    if preview:
        ui.console.print("[bold]Preview mode - showing tag info[/bold]")
        tag_commit = ops.git.get_tag_commit(tag_name)
        if tag_commit:
            _show_commit_diff(ops, tag_commit)
        ui.console.print("Run again without --preview to checkout this tag.")
        return

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        return

    tag_commit = ops.git.get_tag_commit(tag_name)
    if not tag_commit:
        error(f"Tag '{tag_name}' not found", exit_code=1)

    if save_mode == "save":
        ui.console.print(f"[bold]Saving current branch '{current_branch}'...[/bold]")
        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        saved_count = save_result["saved"]
        sections = get_changed_sections(ops)

        if commit_message and commit_message.lower() != "none":
            if commit_message.lower() == "auto":
                commit_msg = generate_commit_message(
                    current_branch, tag_name, "tag", saved_count, sections
                )
            else:
                commit_msg = commit_message

            ops.git.commit(commit_msg)
            ui.console.print(f"  Saved {saved_count} files")
            if commit_message.lower() != "auto":
                ui.console.print(f"  [dim]Commit: {commit_msg}[/dim]")
        else:
            ui.console.print(f"  Saved {saved_count} files (no commit)")

    if base_branch and base_branch != "HEAD" and ops.git.branch_exists(base_branch):
        ops.git.checkout(base_branch)
        ui.console.print(f"  Switched to branch: {base_branch}")

    run_switch_hooks("pre", ops, current_branch, tag_name)

    ops.git.checkout(tag_name)
    ui.console.print(f"  Checked out tag: [dim]{tag_name}[/dim]")

    success(f"Switched to tag '{tag_name}'")

    run_switch_hooks("post", ops, current_branch, tag_name)


def _handle_branch_navigate(
    ops,
    current_branch,
    target_branch,
    save_mode,
    dry_run,
    force,
    preview,
    show_diff,
    files_only,
    commit_message=None,
):
    """Handle navigating to a branch."""
    if current_branch == target_branch and not dry_run:
        ui.console.print(f"Already on branch '[bold]{target_branch}[/bold]'")

        if preview:
            _show_commits_list(ops, target_branch, files_only)
        return

    if preview:
        ui.console.print("[bold]Preview mode - showing branch info[/bold]")
        _show_branch_diff_preview(ops, current_branch, target_branch, show_diff)
        _show_commits_list(ops, target_branch, files_only)
        ui.console.print("Run again without --preview to switch to this branch.")
        return

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        ui.console.print()
        _show_branch_diff_preview(ops, current_branch, target_branch, show_diff)
        return

    ui.console.print(
        f"[bold]Navigating to branch[/bold] [cyan]{target_branch}[/cyan]..."
    )

    ui.console.print()
    ui.console.print(
        f"[bold]Phase 1:[/bold] {'Saving' if save_mode == 'save' else 'Discarding'} branch '{current_branch}'..."
    )

    if save_mode == "save":
        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        saved_count = save_result["saved"]
        secrets = save_result["secrets"]
        errors = save_result["errors"]
        sections = get_changed_sections(ops)

        if secrets:
            warn(f"{len(secrets)} secrets were redacted during save")

        if errors:
            ui.error(f"Encountered {len(errors)} errors during save:")
            for err in errors:
                ui.console.print(f"  [red]• {err}[/red]")

        if commit_message and commit_message.lower() != "none":
            if commit_message.lower() == "auto":
                commit_msg = generate_commit_message(
                    current_branch, target_branch, "branch", saved_count, sections
                )
            else:
                commit_msg = commit_message

            commit_sha = ops.git.commit(commit_msg)
            if commit_sha:
                ui.console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")
                if commit_message.lower() != "auto":
                    ui.console.print(f"  [dim]Commit: {commit_msg}[/dim]")
        else:
            commit_sha = None

        ui.console.print(f"  Saved {saved_count} files")
        if not commit_sha and saved_count > 0:
            ui.console.print("  [dim](no commit created)[/dim]")
    else:
        ui.console.print("  [dim]Discarded uncommitted changes[/dim]")

    ui.console.print()
    ui.console.print(f"[bold]Phase 2:[/bold] Switching to branch '{target_branch}'...")

    run_branch_hooks(ops, "on_deactivate")

    run_switch_hooks("pre", ops, current_branch, target_branch)

    branch_exists = ops.git.branch_exists(target_branch)
    if not branch_exists:
        if not force and not ui.confirm(
            f"Branch '{target_branch}' doesn't exist. Create it?"
        ):
            ui.console.print("[dim]Aborted.[/dim]")
            return
        ui.console.print(f"  Creating new branch: [cyan]{target_branch}[/cyan]")

    ops.git.checkout(target_branch, create=not branch_exists)
    if branch_exists:
        ui.console.print(f"  Switched to existing branch: [cyan]{target_branch}[/cyan]")
    else:
        ui.console.print(
            f"  Created and switched to new branch: [cyan]{target_branch}[/cyan]"
        )
    ops.reload_config()

    ui.console.print()
    ui.console.print(
        f"[bold]Phase 3:[/bold] Deploying '{target_branch}' configuration..."
    )

    deployed_count = 0
    pre_hooks = []
    post_hooks = []

    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        for local_path in section.paths:
            repo_path = section.get_repo_path(local_path, REPO_DIR)
            if repo_path.exists():
                will_change = not local_path.exists() or not compare_files(
                    repo_path, local_path
                )
                if will_change:
                    if section.pre_deploy:
                        pre_hooks.append(section.pre_deploy)
                    if section.post_deploy:
                        post_hooks.append(section.post_deploy)

    pre_hooks = list(dict.fromkeys(pre_hooks))
    post_hooks = list(dict.fromkeys(post_hooks))

    if pre_hooks:
        ui.console.print()
        ui.console.print("[bold]Running pre-deploy hooks...[/bold]")
        hook_failed = False
        for cmd in pre_hooks:
            ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
            try:
                shell = os.environ.get("SHELL", "/bin/sh")
                result = subprocess.run(
                    [shell, "-c", cmd], capture_output=True, text=True
                )
                if result.returncode != 0:
                    hook_failed = True
                    ui.console.print(
                        f"  [yellow]⚠ Hook failed (exit code {result.returncode})[/yellow]"
                    )
                    if result.stderr:
                        for line in result.stderr.splitlines()[:3]:
                            ui.console.print(f"    [dim]{line}[/dim]")
            except Exception as e:
                hook_failed = True
                warn(f"Failed to run command '{cmd}': {e}")
        if hook_failed:
            ui.console.print("[dim]  Some hooks failed - continuing anyway[/dim]")
        ui.console.print()

    deploy_result = ops.deploy_all()
    deployed_count = deploy_result["deployed"]
    errors = [e for e in deploy_result["errors"] if e and str(e).strip()]

    if errors:
        ui.error(f"Encountered {len(errors)} errors during deploy:")
        for err in errors:
            ui.console.print(f"  [red]• {err}[/red]")

    ui.console.print(f"  Deployed {deployed_count} files")

    if post_hooks:
        ui.console.print()
        ui.console.print("[bold]Running post-deploy hooks...[/bold]")
        hook_failed = False
        for cmd in post_hooks:
            ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
            try:
                shell = os.environ.get("SHELL", "/bin/sh")
                result = subprocess.run(
                    [shell, "-c", cmd], capture_output=True, text=True
                )
                if result.returncode != 0:
                    hook_failed = True
                    ui.console.print(
                        f"  [yellow]⚠ Hook failed (exit code {result.returncode})[/yellow]"
                    )
                    if result.stderr:
                        for line in result.stderr.splitlines()[:3]:
                            ui.console.print(f"    [dim]{line}[/dim]")
            except Exception as e:
                hook_failed = True
                warn(f"Failed to run command '{cmd}': {e}")
        if hook_failed:
            ui.console.print("[dim]  Some hooks failed - continuing anyway[/dim]")

    ops.global_config.current_branch = target_branch
    ops.global_config.save()

    run_switch_hooks("post", ops, current_branch, target_branch)

    run_branch_hooks(ops, "on_activate")

    ui.console.print()
    success(f"Switched to '{target_branch}'")
    ui.console.print()
    ui.console.print(f"  • Deployed {deployed_count} files for '{target_branch}'")
    ui.console.print()
    ui.next_steps(
        [
            "Run [cyan]dot-man status[/cyan] to verify deployment",
            "Run [cyan]dot-man log[/cyan] to see commit history",
            f"Edit files and run [cyan]dot-man navigate {current_branch}[/cyan] to save changes",
        ]
    )


@main.command("hooks", cls=AliasedCommand, aliases=["hks"])
@click.argument("command", type=click.Choice(["list", "create", "delete"]))
@click.argument("phase", type=click.Choice(["pre", "post"]), required=False)
@click.argument("name", type=str, required=False)
@require_init
def hooks(command: str, phase: str | None, name: str | None):
    """Manage dot-man hooks.

    Hooks allow you to run custom scripts before/after commands.

    Commands:
        list    List all available hooks (no additional args needed)
        create  Create a new hook script (requires: pre|post NAME)
        delete  Delete a hook script (requires: pre|post NAME)

    Hook naming: {phase}_{command} (e.g., pre_switch, post_deploy)

    Examples:
        dot-man hooks list
        dot-man hooks create pre switch
        dot-man hooks create post deploy
        dot-man hooks delete pre checkout
    """
    from ..hooks import (
        create_hook,
        delete_hook,
        list_hooks,
    )

    if command == "list":
        ui.console.print("[bold]Available Hooks:[/bold]")
        all_hooks = list_hooks()
        for h in all_hooks:
            status = "[green]✓[/green]" if h["exists"] else "[dim]-[/dim]"
            ui.console.print(f"  {status} {h['phase']}_{h['command']} -> {h['path']}")

    elif command == "create":
        if not phase or not name:
            error("'create' requires: pre|post NAME", exit_code=1)
        assert isinstance(name, str) and isinstance(phase, str)
        hook_path = create_hook(name, phase)
        ui.console.print(f"[green]Created hook:[/green] {hook_path}")
        ui.console.print("  Edit this file to add your custom script.")

    elif command == "delete":
        if not phase or not name:
            error("'delete' requires: pre|post NAME", exit_code=1)
        assert isinstance(name, str) and isinstance(phase, str)
        deleted = delete_hook(name, phase)
        if deleted:
            success(f"Deleted hook: {phase}_{name}")
        else:
            warn(f"Hook not found: {phase}_{name}")
