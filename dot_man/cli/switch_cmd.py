"""Switch command for dot-man CLI."""

import os
import subprocess

import click

from .. import ui
from ..constants import REPO_DIR
from ..exceptions import DotManError
from ..files import compare_files
from .common import (
    complete_switch_args,
    error,
    get_secret_handler,
    parse_branch_arg,
    require_init,
    success,
    warn,
)
from .interface import cli as main


class BranchParamType(click.ParamType):
    """Parameter type that accepts branch, branch@tag, or commit SHA."""

    name = "branch"

    def convert(self, value, param, ctx):
        if not value:
            return None
        parsed = parse_branch_arg(value)
        return parsed


BRANCH = BranchParamType()


@main.command()
@click.option(
    "--dry-run", "-n", is_flag=True, help="Show what would happen without making changes"
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
@click.argument("branch", type=BRANCH, required=False, shell_complete=complete_switch_args)
@require_init
def switch(branch, dry_run: bool, force: bool, save_mode):
    """Switch to a different configuration branch, tag, or commit.

    Supports multiple formats:
        \b
        dot-man switch work          # switch to branch
        dot-man switch work@tag     # switch to branch at tag position
        dot-man switch abc1234      # switch to specific commit
        dot-man switch my-tag       # switch to tag

    Use --save or --no-save to override the default behavior.
    Default behavior can be configured with:
        dot-man config set switch.default_behavior no-save

    Examples:
        dot-man switch work
        dot-man switch work --no-save
        dot-man switch --save work
        dot-man switch abc1234
    """
    try:
        from ..operations import get_operations

        if not branch:
            error("No branch, tag, or commit specified", exit_code=1)

        # branch is already a dict from BranchParamType
        parsed = branch

        # Determine save behavior
        ops = get_operations()
        if save_mode is None:
            save_mode = ops.global_config.switch_default_behavior
        target_type = parsed["type"]
        target_name = parsed["target"]

        current_branch = ops.current_branch

        # Handle commit checkout (detached HEAD)
        if target_type == "commit":
            _handle_commit_switch(
                ops, current_branch, target_name, save_mode, dry_run, force
            )
            return

        # Handle tag switch
        if target_type == "tag":
            _handle_tag_switch(
                ops, current_branch, parsed["base"], target_name, save_mode, dry_run, force
            )
            return

        # Regular branch switch
        _handle_branch_switch(
            ops, current_branch, target_name, save_mode, dry_run, force
        )

    except DotManError as e:
        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        ui.console.print()
        warn("Operation cancelled by user")
    except Exception as e:
        from ..exceptions import ErrorDiagnostic
        diagnostic = ErrorDiagnostic.from_exception(e)
        ui.console.print()
        ui.console.print(f"[red bold]{diagnostic.title}[/red bold]")
        ui.console.print(f"[red]{diagnostic.details}[/red]")
        ui.console.print()
        ui.console.print(f"[dim]💡 {diagnostic.suggestion}[/dim]")
        raise SystemExit(1)


def _handle_commit_switch(ops, current_branch, commit_sha, save_mode, dry_run, force):
    """Handle switching to a specific commit (detached HEAD)."""
    ui.console.print(f"[bold]Switching to commit[/bold] [cyan]{commit_sha}[/cyan]...")

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        return

    if save_mode == "save":
        ui.console.print(f"[bold]Saving current branch '{current_branch}'...[/bold]")
        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        commit_msg = f"Auto-save from '{current_branch}' before checkout {commit_sha}"
        ops.git.commit(commit_msg)
        ui.console.print(f"  Saved {save_result['saved']} files")

    # Checkout commit (detached HEAD)
    ops.git.checkout_commit(commit_sha)
    ui.console.print(f"  Checked out commit: [dim]{commit_sha}[/dim]")
    ui.console.print("[yellow]Note: You are in detached HEAD state[/yellow]")
    ui.console.print("  Use 'dot-man switch <branch>' to return to a branch")


def _handle_tag_switch(ops, current_branch, base_branch, tag_name, save_mode, dry_run, force):
    """Handle switching to a tag (optionally on a specific branch)."""
    ui.console.print(f"[bold]Switching to tag[/bold] [cyan]{tag_name}[/cyan]...")

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        return

    # Get the commit the tag points to
    tag_commit = ops.git.get_tag_commit(tag_name)
    if not tag_commit:
        error(f"Tag '{tag_name}' not found", exit_code=1)

    if save_mode == "save":
        ui.console.print(f"[bold]Saving current branch '{current_branch}'...[/bold]")
        secret_handler = get_secret_handler()
        save_result = ops.save_all(secret_handler)
        commit_msg = f"Auto-save from '{current_branch}' before switch to tag {tag_name}"
        ops.git.commit(commit_msg)
        ui.console.print(f"  Saved {save_result['saved']} files")

    # If base_branch is provided, try to switch to that branch first
    if base_branch and base_branch != "HEAD":
        branch_exists = ops.git.branch_exists(base_branch)
        if branch_exists:
            ops.git.checkout(base_branch)
            ui.console.print(f"  Switched to branch: {base_branch}")

    # Checkout the tag (creates detached HEAD or updates to tag)
    ops.git.checkout(tag_name)
    ui.console.print(f"  Checked out tag: [dim]{tag_name}[/dim]")

    success(f"Switched to tag '{tag_name}'")


def _handle_branch_switch(ops, current_branch, target_branch, save_mode, dry_run, force):
    """Handle switching to a regular branch."""

    # Check if already on target branch
    if current_branch == target_branch and not dry_run:
        ui.console.print(f"Already on branch '[bold]{target_branch}[/bold]'")
        return

    if dry_run:
        ui.console.print("[dim]Dry run - no changes will be made[/dim]")
        ui.console.print()

    # Phase 1: Save or discard current branch state
    ui.console.print(
        f"[bold]Phase 1:[/bold] {'Saving' if save_mode == 'save' else 'Discarding'} branch '{current_branch}'..."
    )

    if dry_run:
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for local_path, repo_path, status in ops.iter_section_paths(section):
                if status != "IDENTICAL":
                    ui.console.print(f"  Would {'save' if save_mode == 'save' else 'discard'}: {local_path} [{status}]")
    else:
        if save_mode == "save":
            secret_handler = get_secret_handler()
            save_result = ops.save_all(secret_handler)
            saved_count = save_result["saved"]
            secrets = save_result["secrets"]
            errors = save_result["errors"]

            if secrets:
                warn(f"{len(secrets)} secrets were redacted during save")

            if errors:
                ui.error(f"Encountered {len(errors)} errors during save:")
                for err in errors:
                    ui.console.print(f"  [red]• {err}[/red]")

            commit_msg = (
                f"Auto-save from '{current_branch}' before switch to '{target_branch}'"
            )
            commit_sha = ops.git.commit(commit_msg)
            if commit_sha:
                ui.console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")
            ui.console.print(f"  Saved {saved_count} files")
        else:
            ui.console.print("  [dim]Discarded uncommitted changes[/dim]")

    # Phase 2: Switch branch
    ui.console.print()
    ui.console.print(f"[bold]Phase 2:[/bold] Switching to branch '{target_branch}'...")

    branch_exists = ops.git.branch_exists(target_branch)
    if dry_run:
        if branch_exists:
            ui.console.print(f"  Would checkout existing branch: {target_branch}")
        else:
            ui.console.print(f"  Would create new branch: {target_branch}")
    else:
        ops.git.checkout(target_branch, create=not branch_exists)
        if not branch_exists:
            ui.console.print(f"  Created new branch: [cyan]{target_branch}[/cyan]")
        ops.reload_config()

    # Phase 3: Deploy new branch files
    ui.console.print()
    ui.console.print(f"[bold]Phase 3:[/bold] Deploying '{target_branch}' configuration...")

    deployed_count = 0
    if dry_run:
        for section_name in ops.get_sections():
            section = ops.get_section(section_name)
            for local_path, repo_path, _ in ops.iter_section_paths(section):
                if repo_path.exists():
                    will_change = not local_path.exists() or not compare_files(
                        repo_path, local_path
                    )
                    ui.console.print(f"  Would deploy: {local_path}")
                    if will_change:
                        if section.pre_deploy:
                            ui.console.print(f"    [dim]Pre-hook:[/dim] {section.pre_deploy}")
                        if section.post_deploy:
                            ui.console.print(f"    [dim]Post-hook:[/dim] {section.post_deploy}")
                    else:
                        ui.console.print("    [dim](No changes needed)[/dim]")
    else:
        # Collect hooks
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

        # Run pre-deploy hooks
        if pre_hooks:
            ui.console.print()
            ui.console.print("[bold]Running pre-deploy hooks...[/bold]")
            for cmd in pre_hooks:
                ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    shell = os.environ.get("SHELL", "/bin/sh")
                    subprocess.run([shell, "-c", cmd], check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
            ui.console.print()

        deploy_result = ops.deploy_all()
        deployed_count = deploy_result["deployed"]
        # Filter empty/whitespace-only errors
        errors = [e for e in deploy_result["errors"] if e and str(e).strip()]

        if errors:
            ui.error(f"Encountered {len(errors)} errors during deploy:")
            for err in errors:
                ui.console.print(f"  [red]• {err}[/red]")

        ui.console.print(f"  Deployed {deployed_count} files")

        # Run post-deploy hooks
        if post_hooks:
            ui.console.print()
            ui.console.print("[bold]Running post-deploy hooks...[/bold]")
            for cmd in post_hooks:
                ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    shell = os.environ.get("SHELL", "/bin/sh")
                    subprocess.run([shell, "-c", cmd], check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")

        # Update global config
        ops.global_config.current_branch = target_branch
        ops.global_config.save()

    # Summary
    ui.console.print()
    if dry_run:
        ui.console.print("[dim]Dry run complete. No changes were made.[/dim]")
    else:
        success(f"Switched to '{target_branch}'")
        ui.console.print()
        ui.console.print(f"  • Deployed {deployed_count} files for '{target_branch}'")
        ui.console.print()
        ui.console.print("Run [cyan]dot-man status[/cyan] to verify.")
