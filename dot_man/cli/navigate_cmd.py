"""Navigate command for dot-man - unified switch + checkout with diff preview."""

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

import click

from .. import ui
from ..constants import REPO_DIR
from ..core import GitManager
from ..files import compare_files
from ..hooks import run_checkout_hooks, run_switch_hooks
from .common import (
    BRANCH,
    AliasedCommand,
    complete_switch_args,
    error,
    get_secret_handler,
    require_init,
    success,
    warn,
)
from .interface import cli as main
from .navigate_preview import (
    show_branch_diff_preview,
    show_commit_diff,
    show_commits_list,
)


def generate_commit_message(
    source: str,
    target: str,
    target_type: str,
    saved_count: int = 0,
    sections: list[str] | None = None,
) -> str:
    """Generate a smart commit message based on context."""

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
        logging.debug("Failed to gather changed files for commit message")

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
        logging.debug("Failed to get changed sections")
        return []


def _warn_symlinks(save_result: dict) -> None:
    """Warn user if any saved paths were symlinks."""
    symlinks: list = save_result.get("symlinks", [])
    for sym_path in symlinks:
        target = Path(sym_path).resolve()
        ui.console.print(f"  [yellow]⚠ {sym_path} is a symlink → {target}[/yellow]")
        ui.console.print(
            "  [dim]Edits affect the symlink target, not the dot-man repo.[/dim]"
        )


def _run_shell_hooks(commands: list[str], label: str) -> bool:
    """Run a list of shell commands as hooks. Returns True if any failed."""
    if not commands:
        return False
    ui.console.print()
    ui.console.print(f"[bold]{label}...[/bold]")
    hook_failed = False
    for cmd in commands:
        ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
        try:
            shell = os.environ.get("SHELL", "/bin/sh")
            result = subprocess.run([shell, "-c", cmd], capture_output=True, text=True)
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
    return hook_failed


def _prompt_for_symlinks(ops) -> set[Path]:
    """Scan sections for symlinks and prompt user how to handle each."""
    from ..interactive import prompt_symlink_action

    symlink_ignore: set[Path] = set()
    ignore_all = False

    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        for path in section.paths:
            if not path.is_symlink():
                continue
            if ignore_all:
                symlink_ignore.add(path)
                continue
            if path in symlink_ignore:
                continue
            action = prompt_symlink_action(path)
            if action == "ignore":
                symlink_ignore.add(path)
            elif action == "all_ignore":
                symlink_ignore.add(path)
                ignore_all = True

    return symlink_ignore


def run_branch_hooks(ops, hook_type: str) -> None:
    """Run on_activate or on_deactivate hooks from sections."""
    commands: list[str] = []
    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        cmd = getattr(section, hook_type, None)
        if cmd:
            commands.append(cmd)

    commands = list(dict.fromkeys(commands))
    _run_shell_hooks(commands, f"Running {hook_type} hooks")


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
    """Navigate to a branch, tag, or commit with optional diff preview."""
    _navigate_impl(
        target, dry_run, force, save_mode, commit_message, preview, diff, files_only
    )


def _navigate_impl(
    target, dry_run, force, save_mode, commit_message, preview, diff, files_only
):
    """Core implementation shared between navigate and switch commands."""
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
        show_commit_diff(ops, commit_sha)
        ui.console.print("Run again without --preview to checkout this commit.")
        return

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        return

    if save_mode == "save":
        ui.console.print(f"[bold]Saving current branch '{current_branch}'...[/bold]")
        secret_handler = get_secret_handler()
        symlink_ignore = _prompt_for_symlinks(ops)
        save_result = ops.save_all(secret_handler, symlink_ignore=symlink_ignore)
        _warn_symlinks(save_result)
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
            show_commit_diff(ops, tag_commit)
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
        symlink_ignore = _prompt_for_symlinks(ops)
        save_result = ops.save_all(secret_handler, symlink_ignore=symlink_ignore)
        _warn_symlinks(save_result)
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
            show_commits_list(ops, target_branch, files_only)
        return

    if preview:
        ui.console.print("[bold]Preview mode - showing branch info[/bold]")
        show_branch_diff_preview(ops, current_branch, target_branch, show_diff)
        show_commits_list(ops, target_branch, files_only)
        ui.console.print("Run again without --preview to switch to this branch.")
        return

    if dry_run:
        ui.console.print(
            f"[bold]Dry Run:[/bold] Navigate [cyan]{current_branch}[/cyan] → [cyan]{target_branch}[/cyan]"
        )
        ui.console.print()

        # Phase 1: What would be saved
        sections = get_changed_sections(ops)
        if sections:
            ui.console.print(
                f"[bold]Phase 1:[/bold] Would save {len(sections)} section(s): {', '.join(sections)}"
            )
        else:
            ui.console.print("[bold]Phase 1:[/bold] No changes to save")
        ui.console.print()

        # Phase 2: Branch switch
        branch_exists = ops.git.branch_exists(target_branch)
        if branch_exists:
            ui.console.print(
                f"[bold]Phase 2:[/bold] Would checkout existing branch: [cyan]{target_branch}[/cyan]"
            )
        else:
            ui.console.print(
                f"[bold]Phase 2:[/bold] Would create and checkout new branch: [cyan]{target_branch}[/cyan]"
            )
        ui.console.print()

        # Phase 3: What would be deployed
        ui.console.print("[bold]Phase 3:[/bold] Would deploy configuration...")
        pre_hooks, post_hooks = [], []
        deploy_items = []
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            if section.pre_deploy:
                pre_hooks.append(section.pre_deploy)
            if section.post_deploy:
                post_hooks.append(section.post_deploy)
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                if repo_path.exists():
                    if not local_path.exists() or not compare_files(
                        repo_path, local_path
                    ):
                        method = (
                            f" [dim]({section.deploy_method})[/dim]"
                            if section.deploy_method == "symlink"
                            else ""
                        )
                        deploy_items.append((local_path, method))

        pre_hooks = list(dict.fromkeys(pre_hooks))
        post_hooks = list(dict.fromkeys(post_hooks))

        if deploy_items:
            for local, method in deploy_items:
                ui.console.print(f"  [yellow]{local}[/yellow]{method}")
        else:
            ui.console.print("  [dim]No files would change[/dim]")

        if pre_hooks:
            ui.console.print(f"  pre_deploy: {', '.join(pre_hooks)}")
        if post_hooks:
            ui.console.print(f"  post_deploy: {', '.join(post_hooks)}")

        ui.console.print()
        ui.console.print(
            f"[bold]Phase 4:[/bold] Would update current_branch → {target_branch}"
        )
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
        symlink_ignore = _prompt_for_symlinks(ops)
        save_result = ops.save_all(secret_handler, symlink_ignore=symlink_ignore)
        _warn_symlinks(save_result)
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

    _run_shell_hooks(pre_hooks, "Running pre-deploy hooks")

    deploy_result = ops.deploy_all()
    deployed_count = deploy_result["deployed"]
    errors = [e for e in deploy_result["errors"] if e and str(e).strip()]

    if errors:
        ui.error(f"Encountered {len(errors)} errors during deploy:")
        for err in errors:
            ui.console.print(f"  [red]• {err}[/red]")

    ui.console.print(f"  Deployed {deployed_count} files")

    _run_shell_hooks(post_hooks, "Running post-deploy hooks")

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
