"""Remote and sync commands for dot-man CLI."""

from types import ModuleType

import click

from .. import ui
from ..config import GlobalConfig
from ..core import GitManager
from ..exceptions import DotManError
from .common import AliasedCommand, error, require_init, success, warn
from .interface import cli as main


@main.group("remote")
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


@remote.command("sync-branch")
@require_init
def sync_branch():
    """Synchronize local branch name with remote default branch.

    Detects the remote's default branch (e.g., 'master') and renames
    the local branch to match if they differ. Fixes push/pull failures
    caused by main vs master naming mismatch.

    Example: dot-man remote sync-branch
    """
    try:
        git = GitManager()

        if not git.has_remote():
            error("No remote configured. Use 'dot-man remote set <url>' first.")
            return

        # Fetch to ensure we have remote info
        ui.console.print("Fetching remote info...")
        git.fetch()

        # Get remote default branch via git remote show
        try:
            result = git.repo.git.remote("show", "origin")
            remote_default = None
            for line in result.split("\n"):
                if "HEAD branch:" in line:
                    remote_default = line.split(":")[1].strip()
                    break
        except Exception as e:
            error(f"Could not determine remote default branch: {e}")
            return

        if not remote_default:
            error("Could not detect remote default branch")
            return

        local_current = git.current_branch()

        ui.console.print(f"Remote default branch: [cyan]{remote_default}[/cyan]")
        ui.console.print(f"Local current branch:  [cyan]{local_current}[/cyan]")
        ui.console.print()

        if local_current == remote_default:
            success("Branch names already match!")
            return

        # Offer to rename
        ui.console.print("[yellow]Branch name mismatch detected![/yellow]")
        ui.console.print()

        if ui.confirm(f"Rename local '{local_current}' to '{remote_default}'?"):
            try:
                # Rename the branch
                git.repo.git.branch("-m", local_current, remote_default)

                # Update global config
                global_config = GlobalConfig()
                global_config.load()
                global_config.current_branch = remote_default
                global_config.save()

                success(f"Renamed local branch to '{remote_default}'")
                ui.console.print()
                ui.console.print("You can now sync with: [cyan]dot-man sync[/cyan]")

            except Exception as rename_err:
                error(f"Failed to rename branch: {rename_err}")
        else:
            ui.info("Keeping current branch name")
            ui.console.print()
            ui.console.print("Tip: You can also set upstream manually with:")
            ui.console.print(
                f"  [cyan]git push -u origin {local_current}:{remote_default}[/cyan]"
            )

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Sync branch failed: {e}")


@main.command("sync", cls=AliasedCommand, aliases=["syn"])
@click.option("--push-only", is_flag=True, help="Only push, don't pull")
@click.option("--pull-only", is_flag=True, help="Only pull, don't push")
@require_init
def sync(push_only: bool, pull_only: bool):
    """Sync with remote repository.

    Pulls changes from remote (with rebase), then pushes local changes.
    Use this to keep dotfiles in sync across multiple machines.

    Example: dot-man sync
    """
    from ..lock import FileLock
    from ..operations import LOCK_FILE

    try:
        with FileLock(LOCK_FILE):
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

    if _setup_should_abort_existing(git):
        return

    _setup_print_banner()

    gh_available = shutil.which("gh") is not None

    if gh_available:
        if _setup_run_gh_flow(git, subprocess, REPO_DIR):
            return

    if not gh_available:
        _setup_print_no_gh()

    _setup_run_manual_flow(git)


def _setup_should_abort_existing(git: GitManager) -> bool:
    """Check if remote already configured. Return True to abort setup."""
    if not git.has_remote():
        return False
    url = git.get_remote_url()
    ui.console.print(f"Remote already configured: [cyan]{url}[/cyan]")
    return not ui.confirm("Replace with a new remote?")


def _setup_print_banner() -> None:
    """Print the setup banner."""
    ui.console.print()
    ui.console.print("[bold]🔧 Remote Setup[/bold]")
    ui.console.print()


def _setup_print_no_gh() -> None:
    """Print message when GitHub CLI is not found."""
    ui.console.print(
        "[dim]GitHub CLI not found. Install with: https://cli.github.com[/dim]"
    )
    ui.console.print()


def _setup_run_gh_flow(git: GitManager, subprocess: ModuleType, repo_dir: str) -> bool:
    """Run GitHub CLI setup flow. Returns True if setup is complete."""
    ui.console.print("[green]✓[/green] GitHub CLI (gh) detected")
    ui.console.print()

    if not ui.confirm("Create a new private GitHub repository?"):
        return False

    repo_name = ui.ask("Repository name", default="dotfiles")
    return _setup_gh_create_or_fallback(git, subprocess, repo_dir, repo_name)


def _setup_gh_create_or_fallback(
    git: GitManager, subprocess: ModuleType, repo_dir: str, repo_name: str
) -> bool:
    """Try to create gh repo, handling errors. Returns True if complete."""
    try:
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
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
    except Exception as e:
        warn(f"Error running gh: {e}")
        return _setup_gh_fallback()

    if result.returncode == 0:
        return _setup_gh_created_success(git, repo_name)

    return _setup_gh_handle_error(git, subprocess, repo_name, result)


def _setup_gh_created_success(git: GitManager, repo_name: str) -> bool:
    """Handle successful repo creation. Returns True."""
    remote_url = git.get_remote_url()
    if remote_url:
        global_config = GlobalConfig()
        global_config.load()
        global_config.remote_url = remote_url
        global_config.save()

    success(f"Created and connected to GitHub repository: {repo_name}")
    ui.console.print()
    ui.console.print("You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!")
    return True


def _setup_gh_handle_error(
    git: GitManager, subprocess: ModuleType, repo_name: str, result
) -> bool:
    """Handle gh command errors. Returns True if setup complete."""
    stderr = result.stderr.lower()

    if "already exists" in stderr:
        return _setup_gh_already_exists(git, subprocess, repo_name)

    if "not logged in" in stderr or "auth" in stderr:
        return _setup_gh_auth_error()

    warn(f"gh command failed: {result.stderr}")
    return _setup_gh_fallback()


def _setup_gh_auth_error() -> bool:
    """Print auth error message. Returns True (setup aborted)."""
    ui.console.print()
    ui.console.print("[red]GitHub authentication required![/red]")
    ui.console.print()
    ui.console.print("Run: [cyan]gh auth login[/cyan]")
    ui.console.print("Then try again.")
    return True


def _setup_gh_fallback() -> bool:
    """Print fallback message. Returns False to continue to manual flow."""
    ui.console.print("Falling back to manual setup...")
    ui.console.print()
    return False


def _setup_gh_already_exists(
    git: GitManager, subprocess: ModuleType, repo_name: str
) -> bool:
    """Handle 'already exists' error. Returns True when complete."""
    ui.console.print()
    ui.console.print("[yellow]Repository already exists![/yellow]")
    ui.console.print()

    if not ui.confirm(f"Connect to existing repository '{repo_name}' instead?"):
        return _setup_gh_fallback()

    return _setup_gh_connect_existing(git, subprocess, repo_name)


def _setup_gh_connect_existing(
    git: GitManager, subprocess: ModuleType, repo_name: str
) -> bool:
    """Connect to existing repo. Returns True when complete."""
    url_result = subprocess.run(
        ["gh", "repo", "view", repo_name, "--json", "url", "-q", ".url"],
        capture_output=True,
        text=True,
    )

    if url_result.returncode != 0:
        return _setup_gh_fallback()

    existing_url = url_result.stdout.strip()
    if not existing_url:
        return _setup_gh_fallback()

    _setup_connect_to_url(git, existing_url)
    return _setup_handle_remote_action(git)


def _setup_connect_to_url(git: GitManager, url: str) -> None:
    """Set remote and save to global config."""
    git.set_remote(url)
    global_config = GlobalConfig()
    global_config.load()
    global_config.remote_url = url
    global_config.save()
    success(f"Connected to existing repository: {url}")


def _setup_handle_remote_action(git: GitManager) -> bool:
    """Offer push/pull/skip for existing repo. Returns True."""
    ui.console.print()
    action = ui.ask(
        "Remote may have existing content. What would you like to do?",
        choices=[
            "pull (fetch remote content)",
            "push (overwrite remote)",
            "skip",
        ],
        default="skip",
    )

    if action.startswith("push"):
        _setup_do_force_push(git)
    elif action.startswith("pull"):
        _setup_do_pull(git)

    return True


def _setup_do_force_push(git: GitManager) -> None:
    """Force push to remote with confirmation."""
    if ui.confirm("[red]This will OVERWRITE the remote repository![/red] Continue?"):
        try:
            git.repo.git.push("--force", "-u", "origin", git.current_branch())
            success("Force pushed to remote!")
        except Exception as push_error:
            error(f"Push failed: {push_error}")


def _setup_do_pull(git: GitManager) -> None:
    """Pull from remote."""
    try:
        git.fetch()
        git.pull()
        success("Pulled from remote!")
    except Exception as pull_error:
        error(f"Pull failed: {pull_error}")


def _setup_run_manual_flow(git: GitManager) -> None:
    """Run the manual setup flow."""
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

        global_config = GlobalConfig()
        global_config.load()
        global_config.remote_url = url
        global_config.save()

        success(f"Remote set to: {url}")

        if ui.confirm("Push current dotfiles to remote?"):
            _setup_do_push(git)
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to set remote: {e}")


def _setup_do_push(git: GitManager) -> None:
    """Push dotfiles to remote, handling rejections."""
    ui.console.print("Pushing...")
    try:
        git.push()
        success("Pushed to remote!")
        ui.console.print()
        ui.console.print(
            "You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!"
        )
    except Exception as push_error:
        _setup_handle_push_error(git, push_error)


def _setup_handle_push_error(git: GitManager, push_error: Exception) -> None:
    """Handle push errors, particularly rejections."""
    push_err_str = str(push_error).lower()

    if "rejected" not in push_err_str and "non-fast-forward" not in push_err_str:
        error(f"Push failed: {push_error}")
        return

    ui.console.print()
    ui.console.print("[yellow]Push rejected - remote has existing content![/yellow]")
    ui.console.print()

    action = ui.ask(
        "What would you like to do?",
        choices=[
            "force-push (overwrite remote)",
            "pull (fetch remote first)",
            "skip",
        ],
        default="skip",
    )

    if action.startswith("force"):
        _setup_do_manual_force_push(git)
    elif action.startswith("pull"):
        _setup_do_manual_pull_and_push(git)
    else:
        ui.console.print("Skipped. You can sync later with: [cyan]dot-man sync[/cyan]")


def _setup_do_manual_force_push(git: GitManager) -> None:
    """Force push from manual setup."""
    if ui.confirm(
        "[red]This will OVERWRITE the remote repository![/red] Are you sure?"
    ):
        try:
            git.repo.git.push("--force", "-u", "origin", git.current_branch())
            success("Force pushed to remote!")
        except Exception as force_error:
            error(f"Force push failed: {force_error}")


def _setup_do_manual_pull_and_push(git: GitManager) -> None:
    """Pull then push from manual setup."""
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
