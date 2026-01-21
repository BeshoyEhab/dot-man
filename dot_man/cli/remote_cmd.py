"""Remote and sync commands for dot-man CLI."""

import click

from .. import ui
from ..core import GitManager
from ..config import GlobalConfig
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, warn, require_init


@main.group()
def remote():
    """Manage remote repository connection."""
    pass


@remote.command("set")
@click.argument("url")
@require_init
def remote_set(url: str):
    """Set the remote repository URL.

    Example: dot-man remote set https://github.com/user/dotfiles.git
    """
    try:
        git = GitManager()
        git.set_remote(url)

        global_config = GlobalConfig()
        global_config.load()
        global_config.remote_url = url
        global_config.save()

        success(f"Remote set to: {url}")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to set remote: {e}")


@remote.command("get")
@require_init
def remote_get():
    """Show the current remote repository URL."""
    try:
        git = GitManager()
        url = git.get_remote_url()
        if url:
            ui.console.print(f"Remote URL: [cyan]{url}[/cyan]")
        else:
            ui.console.print("[dim]No remote configured[/dim]")
            ui.console.print("Use: [cyan]dot-man remote set <url>[/cyan]")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to get remote: {e}")


@main.command()
@click.option("--push-only", is_flag=True, help="Only push, don't pull")
@click.option("--pull-only", is_flag=True, help="Only pull, don't push")
@require_init
def sync(push_only: bool, pull_only: bool):
    """Sync with remote repository.

    Pulls changes from remote (with rebase), then pushes local changes.
    Use this to keep dotfiles in sync across multiple machines.

    Example: dot-man sync
    """
    try:
        git = GitManager()

        if not git.has_remote():
            error("No remote configured. Use 'dot-man remote set <url>' first.")

        current = git.current_branch()
        ui.console.print(f"Syncing branch [bold]{current}[/bold] with remote...")
        ui.console.print()

        # Pull first (unless push-only)
        if not push_only:
            ui.console.print("[bold]Fetching...[/bold]")
            git.fetch()

            ui.console.print("[bold]Pulling...[/bold]")
            pull_result = git.pull(rebase=True)
            ui.console.print(f"  {pull_result}")
            ui.console.print()

        # Push (unless pull-only)
        if not pull_only:
            from ..operations import get_operations
            ops = get_operations()
            if ops.pre_push_audit():
                ui.console.print("[bold]Pushing...[/bold]")
                push_result = git.push()
                ui.console.print(f"  {push_result}")
                ui.console.print()
                success("Sync complete!")
            else:
                warn("Push aborted.")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Sync failed: {e}")


@main.command()
@require_init
def setup():
    """Set up remote repository for syncing.

    Guides you through creating a GitHub repository and connecting it.
    Supports GitHub CLI (gh) for automatic creation.
    """
    import shutil
    import subprocess
    from ..constants import REPO_DIR

    git = GitManager()

    # Check if remote already configured
    if git.has_remote():
        url = git.get_remote_url()
        ui.console.print(f"Remote already configured: [cyan]{url}[/cyan]")
        if not ui.confirm("Replace with a new remote?"):
            return

    ui.console.print()
    ui.console.print("[bold]🔧 Remote Setup[/bold]")
    ui.console.print()

    # Check for GitHub CLI
    gh_available = shutil.which("gh") is not None

    if gh_available:
        ui.console.print("[green]✓[/green] GitHub CLI (gh) detected")
        ui.console.print()

        if ui.confirm("Create a new private GitHub repository?"):
            repo_name = ui.ask("Repository name", default="dotfiles")

            try:
                # Create repo with gh
                result = subprocess.run(
                    [
                        "gh",
                        "repo",
                        "create",
                        repo_name,
                        "--private",
                        "--source=.",
                        "--remote=origin",
                        "--push",
                    ],
                    cwd=REPO_DIR,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    # Get the remote URL that gh configured
                    remote_url = git.get_remote_url()
                    if remote_url:
                        # Save to global.conf
                        global_config = GlobalConfig()
                        global_config.load()
                        global_config.remote_url = remote_url
                        global_config.save()

                    success(f"Created and connected to GitHub repository: {repo_name}")
                    ui.console.print()
                    ui.console.print(
                        "You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!"
                    )
                    return
                else:
                    # Parse specific error cases
                    stderr = result.stderr.lower()
                    
                    if "already exists" in stderr:
                        ui.console.print()
                        ui.console.print("[yellow]Repository already exists![/yellow]")
                        ui.console.print()
                        if ui.confirm(f"Connect to existing repository '{repo_name}' instead?"):
                            # Get the repo URL using gh
                            url_result = subprocess.run(
                                ["gh", "repo", "view", repo_name, "--json", "url", "-q", ".url"],
                                capture_output=True,
                                text=True,
                            )
                            if url_result.returncode == 0:
                                existing_url = url_result.stdout.strip()
                                if existing_url:
                                    git.set_remote(existing_url)
                                    global_config = GlobalConfig()
                                    global_config.load()
                                    global_config.remote_url = existing_url
                                    global_config.save()
                                    success(f"Connected to existing repository: {existing_url}")
                                    
                                    # Offer to push or pull
                                    ui.console.print()
                                    action = ui.ask(
                                        "Remote may have existing content. What would you like to do?",
                                        choices=["pull (fetch remote content)", "push (overwrite remote)", "skip"],
                                        default="skip"
                                    )
                                    
                                    if action.startswith("push"):
                                        if ui.confirm("[red]This will OVERWRITE the remote repository![/red] Continue?"):
                                            try:
                                                git.repo.git.push("--force", "-u", "origin", git.current_branch())
                                                success("Force pushed to remote!")
                                            except Exception as push_error:
                                                error(f"Push failed: {push_error}")
                                    elif action.startswith("pull"):
                                        try:
                                            git.fetch()
                                            git.pull()
                                            success("Pulled from remote!")
                                        except Exception as pull_error:
                                            error(f"Pull failed: {pull_error}")
                                    return
                                    
                        ui.console.print("Falling back to manual setup...")
                        ui.console.print()
                    elif "not logged in" in stderr or "auth" in stderr:
                        ui.console.print()
                        ui.console.print("[red]GitHub authentication required![/red]")
                        ui.console.print()
                        ui.console.print("Run: [cyan]gh auth login[/cyan]")
                        ui.console.print("Then try again.")
                        return
                    else:
                        warn(f"gh command failed: {result.stderr}")
                        ui.console.print("Falling back to manual setup...")
                        ui.console.print()
            except Exception as e:
                warn(f"Error running gh: {e}")
                ui.console.print("Falling back to manual setup...")
                ui.console.print()

    else:
        ui.console.print(
            "[dim]GitHub CLI not found. Install with: https://cli.github.com[/dim]"
        )
        ui.console.print()

    # Manual setup instructions
    ui.console.print("[bold]Manual Setup Steps:[/bold]")
    ui.console.print()
    ui.console.print("1. Create a new repository on GitHub:")
    ui.console.print("   [cyan]https://github.com/new[/cyan]")
    ui.console.print()
    ui.console.print("2. Copy the repository URL (SSH or HTTPS)")
    ui.console.print()

    url = ui.ask("Enter the repository URL (or 'skip' to exit)", default="skip")

    if url.lower() == "skip":
        ui.console.print()
        ui.console.print("You can set the remote later with:")
        ui.console.print("  [cyan]dot-man remote set <url>[/cyan]")
        return

    try:
        git.set_remote(url)

        # Also save to global.conf
        global_config = GlobalConfig()
        global_config.load()
        global_config.remote_url = url
        global_config.save()

        success(f"Remote set to: {url}")

        if ui.confirm("Push current dotfiles to remote?"):
            ui.console.print("Pushing...")
            try:
                git.push()
                success("Pushed to remote!")
                ui.console.print()
                ui.console.print(
                    "You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!"
                )
            except Exception as push_error:
                push_err_str = str(push_error).lower()
                
                if "rejected" in push_err_str or "non-fast-forward" in push_err_str:
                    ui.console.print()
                    ui.console.print("[yellow]Push rejected - remote has existing content![/yellow]")
                    ui.console.print()
                    action = ui.ask(
                        "What would you like to do?",
                        choices=["force-push (overwrite remote)", "pull (fetch remote first)", "skip"],
                        default="skip"
                    )
                    
                    if action.startswith("force"):
                        if ui.confirm("[red]This will OVERWRITE the remote repository![/red] Are you sure?"):
                            try:
                                git.repo.git.push("--force", "-u", "origin", git.current_branch())
                                success("Force pushed to remote!")
                            except Exception as force_error:
                                error(f"Force push failed: {force_error}")
                    elif action.startswith("pull"):
                        try:
                            git.fetch()
                            result = git.pull()
                            ui.console.print(f"  {result}")
                            ui.console.print()
                            if ui.confirm("Now push local changes?"):
                                git.push()
                                success("Pushed to remote!")
                        except Exception as pull_error:
                            error(f"Pull failed: {pull_error}")
                    else:
                        ui.console.print("Skipped. You can sync later with: [cyan]dot-man sync[/cyan]")
                else:
                    error(f"Push failed: {push_error}")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to set remote: {e}")
