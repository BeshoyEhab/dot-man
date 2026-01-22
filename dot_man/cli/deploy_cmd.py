"""Deploy command for dot-man CLI."""

import subprocess

import click
from rich.panel import Panel

from .. import ui
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, warn, require_init, complete_branches, handle_exception


@main.command()
@click.argument("branch", shell_complete=complete_branches)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Show what would be deployed")
@require_init
def deploy(branch: str, force: bool, dry_run: bool):
    """One-way deployment of a branch configuration.

    Deploys files from the specified branch to your home directory.
    Unlike 'switch', this does NOT save current local changes first.
    Typically used for setting up a new machine.

    Example: dot-man deploy main
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        git = ops.git

        # Check branch exists
        if not git.branch_exists(branch):
            available = ", ".join(git.list_branches())
            error(f"Branch '{branch}' not found. Available: {available}")

        if not force and not dry_run:
            ui.console.print(
                Panel(
                    "[yellow]WARNING: Deploy will OVERWRITE local files![/yellow]\n\n"
                    "This will:\n"
                    f"• Deploy '{branch}' configuration\n"
                    "• Overwrite existing dotfiles\n"
                    "• Local changes will be LOST\n\n"
                    "[dim]Typical use: Setting up a new machine[/dim]",
                    title="⚠️  Destructive Operation",
                    border_style="yellow",
                )
            )

            if not ui.confirm("Continue?"):
                ui.info("Aborted.")
                return

        # Checkout branch
        if not dry_run:
            git.checkout(branch)
            ops.reload_config()

        # Get sections
        section_names = ops.get_sections()
        if not section_names:
            warn("No files configured in this branch")
            return
            
        sections = [ops.get_section(name) for name in section_names]
        
        # Phase 1: Scan
        if not dry_run:
            ui.console.print("Scanning for changes...")
        
        plan = ops.scan_deployable_changes(sections)
        
        sections_to_process = plan["sections_to_deploy"]
        pre_hooks = list(dict.fromkeys(plan["pre_hooks"]))
        post_hooks = list(dict.fromkeys(plan["post_hooks"]))
        scan_errors = plan["errors"]
        
        for err in scan_errors:
            warn(err)

        if not sections_to_process:
            ui.console.print("[yellow]No changes detected.[/yellow]")
            return

        # Display Plan / Dry Run
        if dry_run:
            ui.console.print(f"\n[bold]Dry Run Summary - {len(sections_to_process)} files to deploy:[/bold]")
            for section, local_path, repo_path in sections_to_process:
                action = "OVERWRITE" if local_path.exists() else "CREATE"
                ui.console.print(f"  {action}: {local_path}")
            
            if pre_hooks:
                ui.console.print("\n[bold]Pre-Hooks:[/bold]")
                for cmd in pre_hooks:
                    ui.console.print(f"  [dim]{cmd}[/dim]")
            
            if post_hooks:
                ui.console.print("\n[bold]Post-Hooks:[/bold]")
                for cmd in post_hooks:
                    ui.console.print(f"  [dim]{cmd}[/dim]")
            return
        
        # Confirm
        ui.console.print(f"Found {len(sections_to_process)} files to deploy.")
        if not force:
            if not ui.confirm(f"Deploy {len(sections_to_process)} files?"):
                ui.info("Aborted.")
                return

        # Execute Pre-Hooks
        if pre_hooks:
            ui.console.print("\n[bold]Running pre-deploy hooks...[/bold]")
            for cmd in pre_hooks:
                ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
        
        # Phase 2: Execute Deployment (Parallel)
        ui.console.print("\n[bold]Deploying files...[/bold]")
        result = ops.execute_deployment_plan(plan)
        
        deployed = result["deployed"]
        exec_errors = result["errors"]
        
        if exec_errors:
            for err in exec_errors:
                ui.console.print(f"  [red]Error:[/red] {err}")
                import logging
                logging.error(f"Deployment error: {err}")
        
        ui.console.print(f"\nDeployed: {deployed}/{len(sections_to_process)} files.")

        # Execute Post-Hooks
        if post_hooks:
            ui.console.print("\n[bold]Running post-deploy hooks...[/bold]")
            for cmd in post_hooks:
                ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
        
        # Update global config
        ops.global_config.current_branch = branch
        ops.global_config.save()
        
        success(f"Deployment complete! ({deployed} files)")

    except DotManError as e:
        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Deployment")
