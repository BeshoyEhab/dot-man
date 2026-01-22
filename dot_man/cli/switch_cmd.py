"""Switch command for dot-man CLI."""

import os
import subprocess

import click

from .. import ui
from ..constants import REPO_DIR
from ..files import compare_files
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, warn, require_init, complete_branches, get_secret_handler


@main.command()
@click.argument("branch", shell_complete=complete_branches)
@click.option(
    "--dry-run", is_flag=True, help="Show what would happen without making changes"
)
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@require_init
def switch(branch: str, dry_run: bool, force: bool):
    """Switch to a different configuration branch.

    Saves current changes to the current branch, then deploys files
    from the target branch. Creates the branch if it doesn't exist.

    Example: dot-man switch work
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        current_branch = ops.current_branch

        # Check if already on target branch
        if current_branch == branch and not dry_run:
            ui.console.print(f"Already on branch '[bold]{branch}[/bold]'")
            return

        if dry_run:
            ui.console.print("[dim]Dry run - no changes will be made[/dim]")
            ui.console.print()

        # Phase 1: Save current branch state
        ui.console.print(
            f"[bold]Phase 1:[/bold] Saving current branch '{current_branch}'..."
        )

        if dry_run:
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for local_path, repo_path, status in ops.iter_section_paths(section):
                    if status != "IDENTICAL":
                        ui.console.print(f"  Would save: {local_path} [{status}]")
        else:
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
                f"Auto-save from '{current_branch}' before switch to '{branch}'"
            )
            commit_sha = ops.git.commit(commit_msg)
            if commit_sha:
                ui.console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")
            ui.console.print(f"  Saved {saved_count} files")

        # Phase 2: Switch branch
        ui.console.print()
        ui.console.print(f"[bold]Phase 2:[/bold] Switching to branch '{branch}'...")

        branch_exists = ops.git.branch_exists(branch)
        if dry_run:
            if branch_exists:
                ui.console.print(f"  Would checkout existing branch: {branch}")
            else:
                ui.console.print(f"  Would create new branch: {branch}")
        else:
            ops.git.checkout(branch, create=not branch_exists)
            if not branch_exists:
                ui.console.print(f"  Created new branch: [cyan]{branch}[/cyan]")
            ops.reload_config()

        # Phase 3: Deploy new branch files
        ui.console.print()
        ui.console.print(f"[bold]Phase 3:[/bold] Deploying '{branch}' configuration...")

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
            ops.global_config.current_branch = branch
            ops.global_config.save()

        # Summary
        ui.console.print()
        if dry_run:
            ui.console.print("[dim]Dry run complete. No changes were made.[/dim]")
        else:
            success(f"Switched to '{branch}'")
            ui.console.print()
            ui.console.print(f"  • Deployed {deployed_count} files for '{branch}'")
            ui.console.print()
            ui.console.print("Run [cyan]dot-man status[/cyan] to verify.")

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
