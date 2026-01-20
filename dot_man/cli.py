"""dot-man CLI: Dotfile manager with git-powered branching."""

import sys
import os
import subprocess
from functools import wraps
from pathlib import Path
from typing import Callable

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from . import __version__
from .constants import (
    DOT_MAN_DIR,
    REPO_DIR,
    BACKUPS_DIR,
    FILE_PERMISSIONS,
)
from .config import GlobalConfig, DotManConfig
from .core import GitManager
from .files import copy_file, backup_file, compare_files
from .secrets import SecretScanner
from .utils import get_editor, open_in_editor, is_git_installed, confirm
from .exceptions import (
    DotManError,
)
from .secrets import (
    SecretGuard,
    SecretMatch,
    PermanentRedactGuard,
)

console = Console()


def get_secret_handler() -> Callable[[SecretMatch], str]:
    """Get a secret handler that prompts the user for action."""
    guard = SecretGuard()
    permanent_guard = PermanentRedactGuard()

    def handle_secret(match: SecretMatch) -> str:
        # Check if should be permanently redacted
        if permanent_guard.should_redact(
            match.file, match.line_content, match.pattern_name
        ):
            return "REDACT"

        # Check if already in skip list
        if guard.is_allowed(match.file, match.line_content, match.pattern_name):
            return "IGNORE"

        # Show the secret to user
        console.print()
        console.print("[red]⚠️  Potential secret detected![/red]")
        console.print(f"File: [cyan]{match.file}[/cyan]")
        console.print(f"Line {match.line_number}: {match.line_content[:80]}...")
        console.print(
            f"Pattern: {match.pattern_name} (severity: {match.severity.value})"
        )
        console.print()

        # Options
        console.print("Choose how to handle this secret:")
        console.print("  1. [dim]Ignore (skip it this time)[/dim]")
        console.print(
            "  2. [yellow]Protect (replace with ***REDACTED*** this time)[/yellow]"
        )
        console.print("  3. [blue]Add to skip list (skip this line every time)[/blue]")
        console.print("  4. [red]Protect forever (always replace in repo)[/red]")
        console.print()

        while True:
            try:
                choice = click.prompt("Enter choice (1-4)", type=int, default=2)
                if choice not in (1, 2, 3, 4):
                    console.print("[red]Invalid choice. Please enter 1-4.[/red]")
                    continue

                if choice == 1:
                    return "IGNORE"
                elif choice == 2:
                    return "REDACT"
                elif choice == 3:
                    guard.add_allowed(
                        match.file, match.line_content, match.pattern_name
                    )
                    console.print("[blue]Added to skip list.[/blue]")
                    return "IGNORE"
                elif choice == 4:
                    permanent_guard.add_permanent_redact(
                        match.file, match.line_content, match.pattern_name
                    )
                    console.print("[red]Will always redact this secret.[/red]")
                    return "REDACT"
            except (ValueError, click.Abort):
                console.print("[red]Invalid input. Please enter a number 1-4.[/red]")

    return handle_secret


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        git = GitManager()
        branches = git.list_branches()
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        return []


def error(message: str, exit_code: int = 1) -> None:
    """Print error message and exit."""
    console.print(f"[red]✗ Error:[/red] {message}")
    sys.exit(exit_code)


def success(message: str) -> None:
    """Print success message."""
    console.print(f"[green]✓[/green] {message}")


def warn(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def require_init(func):
    """Decorator to require initialization before running command."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not DOT_MAN_DIR.exists() or not REPO_DIR.exists():
            error("Not initialized. Run 'dot-man init' first.", exit_code=1)
        return func(*args, **kwargs)

    return wrapper


# ============================================================================
# Main CLI Group
# ============================================================================


@click.group()
@click.version_option(version=__version__, prog_name="dot-man")
def main():
    """dot-man: Dotfile manager with git-powered branching.

    Manage your dotfiles across multiple machines using git branches.
    Each branch represents a different configuration (work, personal, minimal).
    """
    pass


# ============================================================================
# init Command
# ============================================================================


@main.command()
@click.option("--force", is_flag=True, help="Reinitialize even if already exists")
@click.option("--no-wizard", is_flag=True, help="Skip interactive setup wizard")
def init(force: bool, no_wizard: bool):
    """Initialize a new dot-man repository.

    By default, runs an interactive setup wizard to detect and add
    common dotfiles. Use --no-wizard for manual setup.
    """
    # Pre-checks
    if not is_git_installed():
        error("Git not found. Please install git first.", exit_code=2)

    if DOT_MAN_DIR.exists() and not force:
        if not confirm(
            "Repository already initialized. Reinitialize? (This will DELETE all data)"
        ):
            console.print("Aborted.")
            sys.exit(1)

        import shutil

        shutil.rmtree(DOT_MAN_DIR)

    try:
        # Create directory structure
        DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        DOT_MAN_DIR.chmod(FILE_PERMISSIONS)
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize git repository
        git = GitManager()
        git.init()

        # Create global configuration
        global_config = GlobalConfig()
        global_config.create_default()

        # Create minimal dot-man.toml
        dotman_config = DotManConfig()
        dotman_config.create_default()

        # Initial commit
        git.commit("dot-man: Initial commit")

        # Success message
        console.print()
        console.print(
            "╭─────────────────────────────────────────────────╮", style="green"
        )
        console.print(
            "│  🎉 dot-man initialized successfully!           │", style="green bold"
        )
        console.print(
            "╰─────────────────────────────────────────────────╯", style="green"
        )
        console.print()

        # Run wizard by default (unless --no-wizard)
        if not no_wizard:
            run_setup_wizard(global_config, dotman_config, git)
        else:
            show_quick_start()

    except Exception as e:
        error(f"Initialization failed: {e}")


def run_setup_wizard(
    global_config: GlobalConfig, dotman_config: DotManConfig, git: GitManager
):
    """Interactive setup wizard for new users."""
    console.print("[bold cyan]🧙 Setup Wizard[/bold cyan]")
    console.print()
    console.print(
        "Let's get your dotfiles set up! I'll detect common files automatically."
    )
    console.print()

    # Detect common dotfiles
    console.print("[bold]Detecting dotfiles...[/bold]")
    console.print()

    common_files = [
        ("~/.bashrc", "Bash shell", "bashrc"),
        ("~/.zshrc", "Zsh shell", "zshrc"),
        ("~/.gitconfig", "Git config", "gitconfig"),
        ("~/.vimrc", "Vim editor", "vimrc"),
        ("~/.config/nvim", "Neovim", "nvim"),
        ("~/.config/fish", "Fish shell", "fish"),
        ("~/.config/kitty", "Kitty terminal", "kitty"),
        ("~/.config/alacritty", "Alacritty terminal", "alacritty"),
        ("~/.config/hypr", "Hyprland WM", "hypr"),
        ("~/.config/i3", "i3 WM", "i3"),
        ("~/.tmux.conf", "tmux", "tmux"),
        ("~/.ssh/config", "SSH config", "ssh-config"),
    ]

    files_to_add = []
    found_count = 0

    for path_str, desc, section_name in common_files:
        path = Path(path_str).expanduser()
        if path.exists():
            found_count += 1
            console.print(f"  [green]✓[/green] Found: [cyan]{path_str}[/cyan] ({desc})")
            if confirm("    Track this?", default=True):
                files_to_add.append((path_str, section_name))

    if found_count == 0:
        console.print("  [dim]No common dotfiles detected in default locations[/dim]")
        console.print()
    else:
        console.print()

    # Offer to add custom files
    if confirm("Add custom files not in the list?", default=False):
        console.print()
        while True:
            custom_path = click.prompt(
                "Path to track (or press Enter to finish)",
                default="",
                show_default=False,
            )

            if not custom_path:
                break

            path = Path(custom_path).expanduser()
            if not path.exists():
                warn(f"Path doesn't exist: {custom_path}")
                continue

            # Auto-generate section name from path
            if path.name.startswith("."):
                default_section = path.name[1:] if path.suffix else path.name[1:]
            else:
                default_section = path.stem or path.name

            section_name = click.prompt("Section name", default=default_section)
            files_to_add.append((custom_path, section_name))

    # Add files to config
    if files_to_add:
        console.print()
        console.print(f"[bold]Adding {len(files_to_add)} files...[/bold]")
        console.print()

        for path_str, section_name in files_to_add:
            try:
                # Minimal config - only path needed!
                dotman_config.add_section(
                    name=section_name,
                    paths=[path_str],
                    # repo_base auto-generated
                    # secrets_filter uses default (true)
                )
                console.print(f"  [green]✓[/green] [{section_name}]: {path_str}")
            except Exception as e:
                warn(f"Could not add {path_str}: {e}")

        dotman_config.save()

        # Commit the initial config
        git.add_all()
        git.commit("Add initial dotfiles configuration")

        console.print()
        success(f"Added {len(files_to_add)} files to configuration")
        console.print()

        # Show what was configured
        console.print("[bold]Your dotfiles are now tracked:[/bold]")
        for path_str, section_name in files_to_add[:5]:
            console.print(f"  • [{section_name}] {path_str}")
        if len(files_to_add) > 5:
            console.print(f"  ... and {len(files_to_add) - 5} more")

    console.print()

    # Offer remote setup
    if confirm("Set up remote repository for syncing? (optional)", default=False):
        console.print()
        ctx = click.Context(setup)
        ctx.invoke(setup)

    # Final instructions
    console.print()
    console.print("╭─────────────────────────────────────────────────╮", style="cyan")
    console.print(
        "│            🎉 Setup Complete!                   │", style="cyan bold"
    )
    console.print("╰─────────────────────────────────────────────────╯", style="cyan")
    console.print()

    if files_to_add:
        console.print("[bold]Next steps:[/bold]")
        console.print(
            "  1. [cyan]dot-man status[/cyan]       - View your tracked files"
        )
        console.print(
            "  2. [cyan]dot-man switch work[/cyan]  - Create a work configuration branch"
        )
        console.print("  3. [cyan]dot-man add <path>[/cyan]   - Track more files")
    else:
        console.print("[bold]Get started:[/bold]")
        console.print("  [cyan]dot-man add ~/.bashrc[/cyan]   - Add files to track")
        console.print("  [cyan]dot-man edit[/cyan]            - Edit config file")
        console.print("  [cyan]dot-man status[/cyan]          - View status")

    console.print()
    console.print("[dim]💡 Run 'dot-man --help' to see all commands[/dim]")
    console.print()


def show_quick_start():
    """Display quick start guide (for --no-wizard users)."""
    console.print("[bold]📚 Quick Start Guide:[/bold]")
    console.print()
    console.print("[bold cyan]Adding files to track:[/bold cyan]")
    console.print("  dot-man add ~/.bashrc              [dim]# Single file[/dim]")
    console.print("  dot-man add ~/.config/nvim         [dim]# Directory[/dim]")
    console.print(
        "  dot-man edit                       [dim]# Edit config manually[/dim]"
    )
    console.print()
    console.print("[bold cyan]Managing configurations:[/bold cyan]")
    console.print(
        "  dot-man status                     [dim]# View tracked files[/dim]"
    )
    console.print(
        "  dot-man switch main                [dim]# Save current state[/dim]"
    )
    console.print(
        "  dot-man switch work                [dim]# Create work branch[/dim]"
    )
    console.print()
    console.print("[dim]💡 Tip: Config is at ~/.config/dot-man/repo/dot-man.toml[/dim]")
    console.print()


# ============================================================================
# add Command
# ============================================================================


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--section", "-s", help="Section name (default: auto-generated from path)"
)
@click.option(
    "--repo-base", "-r", help="Base directory in repo (default: section name)"
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Patterns to exclude (can be specified multiple times)",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    help="Patterns to include (can be specified multiple times)",
)
@click.option(
    "--inherits",
    "-t",
    multiple=True,
    help="Templates to inherit from (can be specified multiple times)",
)
@click.option("--post-deploy", help="Command to run after deploying")
@click.option("--pre-deploy", help="Command to run before deploying")
@require_init
def add(
    path: str,
    section: str | None,
    repo_base: str | None,
    exclude: tuple,
    include: tuple,
    inherits: tuple,
    post_deploy: str | None,
    pre_deploy: str | None,
):
    """Add a file or directory to be tracked.

    Adds the specified path to the dot-man.toml configuration and copies
    the content to the repository.

    Examples:
        dot-man add ~/.bashrc
        dot-man add ~/.config/fish --section fish --exclude "*.log"
        dot-man add ~/.config/hypr --inherits linux-gui --post-deploy "hyprctl reload"
    """
    try:
        from .files import copy_file, copy_directory

        local_path = Path(path).expanduser().resolve()

        # Auto-generate section name if not provided
        if not section:
            # Use parent dir name for config dirs, or filename for single files
            if local_path.is_dir() and str(local_path).startswith(
                str(Path.home() / ".config")
            ):
                section = local_path.name
            else:
                section = local_path.stem or local_path.name

        repo_base = repo_base or section

        # Load config
        global_config = GlobalConfig()
        global_config.load()

        dotman_config = DotManConfig(global_config=global_config)
        try:
            dotman_config.load()
        except (FileNotFoundError, DotManError):
            # Config might not exist yet, create it
            dotman_config.create_default()
            dotman_config.load()

        # Check for duplicates
        existing_sections = dotman_config.get_section_names()
        if section in existing_sections:
            error(
                f"Section '{section}' already exists. Use a different --section name."
            )

        # Convert to home-relative path for config
        path_str = str(local_path)
        home = str(Path.home())
        if path_str.startswith(home):
            path_str = path_str.replace(home, "~", 1)

        # Add section to config
        dotman_config.add_section(
            name=section,
            paths=[path_str],
            repo_base=repo_base,
            exclude=list(exclude) if exclude else None,
            include=list(include) if include else None,
            inherits=list(inherits) if inherits else None,
            post_deploy=post_deploy,
            pre_deploy=pre_deploy,
        )
        dotman_config.save()

        # Copy content to repo
        repo_dest = REPO_DIR / repo_base

        if local_path.is_file():
            repo_dest = repo_dest / local_path.name
            try:
                secret_handler = get_secret_handler()
                success_copy, secrets = copy_file(
                    local_path,
                    repo_dest,
                    filter_secrets_enabled=True,
                    secret_handler=secret_handler,
                )
                if success_copy:
                    success(f"Added file: {local_path}")
                    console.print(f"  Section: [cyan][{section}][/cyan]")
                    console.print(f"  Repo path: [dim]{repo_dest}[/dim]")
                    if secrets:
                        warn(f"{len(secrets)} secrets were redacted")
                else:
                    error(f"Failed to copy file: {local_path}")
            except (FileNotFoundError, OSError) as e:
                error(f"Failed to access file {local_path}: {e}")
            except Exception as e:
                error(f"Error copying file {local_path}: {e}")
        else:
            secret_handler = get_secret_handler()
            copied, failed, secrets = copy_directory(
                local_path,
                repo_dest,
                filter_secrets_enabled=True,
                exclude_patterns=list(exclude) if exclude else None,
                include_patterns=list(include) if include else None,
                secret_handler=secret_handler,
            )
            success(f"Added directory: {local_path}")
            console.print(f"  Section: [cyan][{section}][/cyan]")
            console.print(f"  Repo path: [dim]{repo_dest}[/dim]")
            console.print(f"  Files: {copied} copied, {failed} failed")
            if secrets:
                warn(f"{len(secrets)} secrets were redacted")

        # Show info about templates
        if inherits:
            console.print(f"  Inherits: {', '.join(inherits)}")

        console.print()
        console.print("[dim]Run 'dot-man switch <branch>' to commit changes.[/dim]")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to add: {e}")


# ============================================================================
# status Command
# ============================================================================


@main.command()
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
@click.option("--secrets", is_flag=True, help="Highlight files with detected secrets")
@require_init
def status(verbose: bool, secrets: bool):
    """Display current repository status.

    Shows the current branch, tracked files, and any pending changes
    that would be saved on the next switch.
    """
    try:
        from .operations import get_operations

        ops = get_operations()

        # Repository info panel
        branch = ops.current_branch
        remote = ops.global_config.remote_url or "[dim]Not configured[/dim]"

        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_column(style="cyan")
        info_table.add_column()
        info_table.add_row("Current Branch:", f"[bold]{branch}[/bold]")
        info_table.add_row("Remote:", remote)
        info_table.add_row("Repository:", str(REPO_DIR))

        console.print(
            Panel(
                info_table, title="[bold]Repository Status[/bold]", border_style="blue"
            )
        )
        console.print()

        # Get status summary
        summary = ops.get_status_summary()

        section_names = ops.get_sections()
        if not section_names:
            console.print(
                "[dim]No sections tracked. Run 'dot-man add <path>' to add files.[/dim]"
            )
            return

        file_table = Table(title=f"Tracked Sections ({len(section_names)})")
        file_table.add_column("Section / Path", style="cyan")
        file_table.add_column("Status")
        file_table.add_column("Details", style="dim")

        status_colors = {
            "NEW": "blue",
            "MODIFIED": "yellow",
            "DELETED": "red",
            "IDENTICAL": "green",
        }

        scanner = SecretScanner() if secrets else None
        secrets_found = []

        for section_name in section_names[:10]:  # Limit display
            section = ops.get_section(section_name)

            # Section header
            file_table.add_row(
                f"[bold magenta][{section_name}][/bold magenta]",
                "",
                f"inherits: {', '.join(section.inherits)}" if section.inherits else "",
            )

            # Files under section
            path_count = 0
            for local_path, repo_path, file_status in ops.iter_section_paths(section):
                if path_count >= 5:  # Limit per section
                    file_table.add_row("  [dim]... more files[/dim]", "", "")
                    break

                color = status_colors.get(file_status, "white")

                # Icon
                icon = "📁" if local_path.is_dir() else "📄"

                # Shorten path
                display_path = str(local_path).replace(str(Path.home()), "~")
                if len(display_path) > 35:
                    display_path = "..." + display_path[-32:]

                details = ""
                if file_status == "MODIFIED" and verbose:
                    details = "Content differs"

                # Check for secrets
                secret_indicator = ""
                if secrets and local_path.exists() and local_path.is_file():
                    matches = list(scanner.scan_file(local_path))  # type: ignore
                    if matches:
                        secret_indicator = " [red]🔒[/red]"
                        secrets_found.extend(matches)

                file_table.add_row(
                    f"  {icon} {display_path}{secret_indicator}",
                    f"[{color}]{file_status}[/{color}]",
                    details,
                )
                path_count += 1

        if len(section_names) > 10:
            file_table.add_row(
                f"[dim]... +{len(section_names) - 10} more sections[/dim]", "", ""
            )

        console.print(file_table)

        # Summary
        console.print()
        console.print(
            f"[dim]Summary: {summary['modified']} modified, {summary['new']} new, {summary['deleted']} deleted, {summary['identical']} identical[/dim]"
        )

        # Secrets warning
        if secrets_found:
            console.print()
            warn(
                f"{len(secrets_found)} potential secrets detected. Run 'dot-man audit' for details."
            )

        # Git status
        if ops.git.is_dirty():
            console.print()
            console.print("[yellow]Repository has uncommitted changes.[/yellow]")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Status check failed: {e}")


# ============================================================================
# switch Command
# ============================================================================


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
        from .operations import get_operations

        ops = get_operations()
        current_branch = ops.current_branch

        # Check if already on target branch
        if current_branch == branch and not dry_run:
            console.print(f"Already on branch '[bold]{branch}[/bold]'")
            return

        if dry_run:
            console.print("[dim]Dry run - no changes will be made[/dim]")
            console.print()

        # Phase 1: Save current branch state
        console.print(
            f"[bold]Phase 1:[/bold] Saving current branch '{current_branch}'..."
        )

        if dry_run:
            # Show what would be saved
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for local_path, repo_path, status in ops.iter_section_paths(section):
                    if status != "IDENTICAL":
                        console.print(f"  Would save: {local_path} [{status}]")
        else:
            secret_handler = get_secret_handler()
            saved_count, secrets = ops.save_all(secret_handler)
            if secrets:
                warn(f"{len(secrets)} secrets were redacted during save")

            # Commit
            commit_msg = (
                f"Auto-save from '{current_branch}' before switch to '{branch}'"
            )
            commit_sha = ops.git.commit(commit_msg)
            if commit_sha:
                console.print(f"  Committed: [dim]{commit_sha[:7]}[/dim]")
            console.print(f"  Saved {saved_count} files")

        # Phase 2: Switch branch
        console.print()
        console.print(f"[bold]Phase 2:[/bold] Switching to branch '{branch}'...")

        branch_exists = ops.git.branch_exists(branch)
        if dry_run:
            if branch_exists:
                console.print(f"  Would checkout existing branch: {branch}")
            else:
                console.print(f"  Would create new branch: {branch}")
        else:
            ops.git.checkout(branch, create=not branch_exists)

            if not branch_exists:
                console.print(f"  Created new branch: [cyan]{branch}[/cyan]")

            # Reload config for new branch (IMPORTANT for per-branch configs)
            ops.reload_config()

        # Phase 3: Deploy new branch files
        console.print()
        console.print(f"[bold]Phase 3:[/bold] Deploying '{branch}' configuration...")

        deployed_count = 0
        if dry_run:
            # Show what would be deployed
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                for local_path, repo_path, _ in ops.iter_section_paths(section):
                    if repo_path.exists():
                        will_change = not local_path.exists() or not compare_files(
                            repo_path, local_path
                        )
                        console.print(f"  Would deploy: {local_path}")
                        if will_change:
                            if section.pre_deploy:
                                console.print(
                                    f"    [dim]Pre-hook:[/dim] {section.pre_deploy}"
                                )
                            if section.post_deploy:
                                console.print(
                                    f"    [dim]Post-hook:[/dim] {section.post_deploy}"
                                )
                        else:
                            console.print("    [dim](No changes needed)[/dim]")
        else:
            # Collect hooks
            pre_hooks: list[str] = []
            post_hooks: list[str] = []

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

            # Run pre-deploy hooks
            pre_hooks = list(dict.fromkeys(pre_hooks))
            if pre_hooks:
                console.print()
                console.print("[bold]Running pre-deploy hooks...[/bold]")
                for cmd in pre_hooks:
                    console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                    try:
                        shell = os.environ.get("SHELL", "/bin/sh")
                        subprocess.run([shell, "-c", cmd], check=False)
                    except Exception as e:
                        warn(f"Failed to run command '{cmd}': {e}")
                console.print()

            # Deploy
            deployed_count, _, _ = ops.deploy_all()

            # Update global config
            ops.global_config.current_branch = branch
            ops.global_config.save()

            # Run post-deploy hooks
            post_hooks = list(dict.fromkeys(post_hooks))
            if post_hooks:
                console.print()
                console.print("[bold]Running post-deploy hooks...[/bold]")
                for cmd in post_hooks:
                    console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                    try:
                        shell = os.environ.get("SHELL", "/bin/sh")
                        subprocess.run([shell, "-c", cmd], check=False)
                    except Exception as e:
                        warn(f"Failed to run command '{cmd}': {e}")

        # Summary
        console.print()
        if dry_run:
            console.print("[dim]Dry run complete. No changes were made.[/dim]")
        else:
            success(f"Switched to '{branch}'")
            console.print()
            console.print(f"  • Deployed {deployed_count} files for '{branch}'")
            console.print()
            console.print("Run [cyan]dot-man status[/cyan] to verify.")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Switch failed: {e}")


# ============================================================================
# edit Command
# ============================================================================


@main.command()
@click.option("--editor", help="Editor to use (default: config or $VISUAL or $EDITOR)")
@click.option("--global", "edit_global", is_flag=True, help="Edit global configuration")
@require_init
def edit(editor: str | None, edit_global: bool):
    """Open the configuration file in your text editor.

    By default, opens the dot-man.toml file for the current branch.
    Use --global to edit the global configuration.
    """
    try:
        from .constants import GLOBAL_TOML, DOT_MAN_TOML

        if edit_global:
            target = GLOBAL_TOML
            desc = "global configuration"
        else:
            target = REPO_DIR / DOT_MAN_TOML
            desc = "dot-man.toml"

        if not target.exists():
            error(f"Configuration file not found: {target}")

        # Priority: CLI flag > global config > environment > fallback
        global_config = GlobalConfig()
        try:
            global_config.load()
            config_editor = global_config.editor
        except (FileNotFoundError, DotManError):
            config_editor = None

        editor_cmd = editor or config_editor or get_editor()
        console.print(f"Opening {desc} in [cyan]{editor_cmd}[/cyan]...")

        if not open_in_editor(target, editor_cmd):
            error(f"Editor '{editor_cmd}' exited with error")

        # Validate after edit
        if not edit_global:
            dotman_config = DotManConfig(global_config=global_config)
            try:
                dotman_config.load()
                warnings = dotman_config.validate()
                if warnings:
                    console.print()
                    warn("Configuration has warnings:")
                    for w in warnings:
                        console.print(f"  • {w}")
                else:
                    success("Configuration updated and validated")
            except Exception as e:
                warn(f"Configuration may have errors: {e}")
        else:
            success("Global configuration updated")

    except DotManError as e:
        error(str(e), e.exit_code)


# ============================================================================
# deploy Command
# ============================================================================


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
        from .operations import get_operations

        ops = get_operations()
        git = ops.git

        # Check branch exists
        if not git.branch_exists(branch):
            available = ", ".join(git.list_branches())
            error(f"Branch '{branch}' not found. Available: {available}")

        if not force and not dry_run:
            console.print(
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

            if not confirm("Continue?"):
                console.print("Aborted.")
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

        # Deploy files
        console.print(f"Deploying [bold]{branch}[/bold] configuration...")
        console.print()

        deployed = 0
        skipped = 0
        pre_hooks: list[str] = []
        post_hooks: list[str] = []
        sections_to_deploy = []

        # Pass 1: Collect hooks and potential changes
        for section_name in section_names:
            section = ops.get_section(section_name)

            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)

                if not repo_path.exists():
                    console.print(f"  [dim]Skip:[/dim] {repo_path} (missing)")
                    skipped += 1
                    continue

                # Check if file will change
                will_change = not local_path.exists() or not compare_files(
                    repo_path, local_path
                )

                if will_change:
                    if section.pre_deploy:
                        pre_hooks.append(section.pre_deploy)
                    if section.post_deploy:
                        post_hooks.append(section.post_deploy)

                sections_to_deploy.append((section, local_path, repo_path, will_change))

        # Run pre-deploy hooks
        pre_hooks = list(dict.fromkeys(pre_hooks))
        if not dry_run and pre_hooks:
            console.print()
            console.print("[bold]Running pre-deploy hooks...[/bold]")
            for cmd in pre_hooks:
                console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
            console.print()

        # Pass 2: Deploy files
        for section, local_path, repo_path, will_change in sections_to_deploy:
            if dry_run:
                action = "OVERWRITE" if local_path.exists() else "CREATE"
                console.print(f"  Would {action}: {local_path}")
                if will_change:
                    if section.pre_deploy:
                        console.print(f"    [dim]Pre-hook:[/dim]  {section.pre_deploy}")
                    if section.post_deploy:
                        console.print(
                            f"    [dim]Post-hook:[/dim] {section.post_deploy}"
                        )
                else:
                    console.print("    [dim](No changes needed)[/dim]")
            else:
                if not will_change:
                    # Optimization: Skip copy if identical
                    console.print(f"  [dim]-[/dim] {local_path} (unchanged)")
                    deployed += 1
                    continue

                if section.update_strategy == "rename_old" and local_path.exists():
                    backup_file(local_path)

                if section.update_strategy != "ignore":
                    success_copy, _ = copy_file(
                        repo_path, local_path, filter_secrets_enabled=False
                    )
                    if success_copy:
                        console.print(f"  [green]✓[/green] {local_path}")
                        deployed += 1
                    else:
                        console.print(f"  [red]✗[/red] {local_path}")

        # Run post-deploy hooks (only if not dry_run)
        post_hooks = list(dict.fromkeys(post_hooks))
        if not dry_run and post_hooks:
            console.print()
            console.print("[bold]Running post-deploy hooks...[/bold]")
            for cmd in post_hooks:
                console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")

        # Update global config
        if not dry_run:
            ops.global_config.current_branch = branch
            ops.global_config.save()

        console.print()
        if dry_run:
            console.print(
                f"[dim]Dry run: {len(sections_to_deploy)} files would be deployed[/dim]"
            )
        else:
            success(f"Deployed {deployed} files from '{branch}'")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Deployment failed: {e}")


# ============================================================================
# audit Command
# ============================================================================


@main.command()
@click.option(
    "--strict", is_flag=True, help="Exit with error if secrets found (for CI/CD)"
)
@click.option("--fix", is_flag=True, help="Automatically redact found secrets")
@require_init
def audit(strict: bool, fix: bool):
    """Scan repository for accidentally committed secrets.

    Scans all files in the repository for API keys, passwords,
    private keys, and other sensitive data.

    Use --strict in CI/CD pipelines to fail builds if secrets are found.
    """
    try:
        scanner = SecretScanner()
        guard = SecretGuard()
        permanent_guard = PermanentRedactGuard()

        console.print("🔒 [bold]Security Audit[/bold]")
        console.print()
        console.print(f"Scanning [cyan]{REPO_DIR}[/cyan]...")
        console.print()

        all_matches = list(scanner.scan_directory(REPO_DIR))

        # Filter out allowed or permanently redacted secrets
        matches = [
            match
            for match in all_matches
            if not guard.is_allowed(match.file, match.line_content, match.pattern_name)
            and not permanent_guard.should_redact(
                match.file, match.line_content, match.pattern_name
            )
        ]

        if not matches:
            success("No secrets detected. Repository is clean!")
            return

        # Group by severity
        by_severity = {}
        for match in matches:
            severity = match.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(match)

        # Display results
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        severity_colors = {
            "CRITICAL": "red",
            "HIGH": "yellow",
            "MEDIUM": "blue",
            "LOW": "dim",
        }

        for severity in severity_order:
            if severity not in by_severity:
                continue

            color = severity_colors[severity]
            items = by_severity[severity]

            console.print(f"[{color}]{severity}[/{color}] ({len(items)} findings)")
            console.print("─" * 50)

            for match in items:
                rel_path = match.file.relative_to(REPO_DIR)
                console.print(f"  File: [cyan]{rel_path}[/cyan]")
                console.print(
                    f"  Line {match.line_number}: {match.line_content[:60]}..."
                )
                console.print(f"  Pattern: {match.pattern_name}")
                console.print()

        # Summary
        console.print("─" * 50)
        console.print(
            f"[bold]Total:[/bold] {len(matches)} secrets in {len(set(m.file for m in matches))} files"
        )
        console.print()

        # Recommendations
        console.print("[bold]Recommendations:[/bold]")
        console.print(
            "  1. Enable [cyan]secrets_filter = true[/cyan] for affected files"
        )
        console.print("  2. Move credentials to environment variables")
        console.print("  3. Run [cyan]dot-man audit --fix[/cyan] to auto-redact")

        if fix:
            console.print()
            if not confirm("Auto-redact all detected secrets?"):
                console.print("Aborted.")
                return

            # Perform redaction
            fixed_files = set()
            for match in matches:
                if match.file in fixed_files:
                    continue

                content = match.file.read_text()
                redacted, count = scanner.redact_content(content)
                if count > 0:
                    match.file.write_text(redacted)
                    fixed_files.add(match.file)
                    console.print(
                        f"  [green]✓[/green] Redacted {count} secrets in {match.file.name}"
                    )

            # Commit changes
            git = GitManager()
            git.commit("Security: Auto-redacted secrets detected by audit")
            success(f"Redacted secrets in {len(fixed_files)} files")

        if strict:
            error("Secrets detected (strict mode)", exit_code=50)

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Audit failed: {e}")


# ============================================================================
# branch Commands
# ============================================================================


@main.group()
def branch():
    """Manage configuration branches."""
    pass


@branch.command("list")
@require_init
def branch_list():
    """List all configuration branches."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        current = global_config.current_branch
        branches = git.list_branches()

        if not branches:
            console.print("[dim]No branches found[/dim]")
            return

        table = Table(title="Branches")
        table.add_column("Branch")
        table.add_column("Active")

        for b in branches:
            active = "[green]✓[/green]" if b == current else ""
            style = "bold" if b == current else ""
            table.add_row(f"[{style}]{b}[/{style}]" if style else b, active)

        console.print(table)

    except Exception as e:
        error(f"Failed to list branches: {e}")


@branch.command("delete")
@click.argument("name", shell_complete=complete_branches)
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
@require_init
def branch_delete(name: str, force: bool):
    """Delete a configuration branch."""
    try:
        git = GitManager()
        global_config = GlobalConfig()
        global_config.load()

        if name == global_config.current_branch:
            error("Cannot delete the active branch. Switch to another branch first.")

        if not git.branch_exists(name):
            error(f"Branch '{name}' not found")

        if not force:
            if not confirm(f"Delete branch '{name}'? This cannot be undone"):
                console.print("Aborted.")
                return

        git.delete_branch(name, force=force)
        success(f"Deleted branch '{name}'")

    except DotManError as e:
        # Import locally to avoid circular import issues if placed at top
        from .exceptions import BranchNotMergedError

        if isinstance(e, BranchNotMergedError):
            if confirm(f"Branch '{name}' is not fully merged. Force delete?"):
                try:
                    git.delete_branch(name, force=True)  # type: ignore
                    success(f"Deleted branch '{name}'")
                    return
                except Exception as e2:
                    error(f"Failed to force delete: {e2}")
            else:
                console.print("Aborted.")
                return

        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to delete branch: {e}")


# ============================================================================
# remote Commands
# ============================================================================


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

        # Also save to global.conf
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
            console.print(f"Remote URL: [cyan]{url}[/cyan]")
        else:
            console.print("[dim]No remote configured[/dim]")
            console.print("Use: [cyan]dot-man remote set <url>[/cyan]")
    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to get remote: {e}")


# ============================================================================
# sync Command
# ============================================================================


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
        console.print(f"Syncing branch [bold]{current}[/bold] with remote...")
        console.print()

        # Pull first (unless push-only)
        if not push_only:
            console.print("[bold]Fetching...[/bold]")
            git.fetch()

            console.print("[bold]Pulling...[/bold]")
            pull_result = git.pull(rebase=True)
            console.print(f"  {pull_result}")
            console.print()

        # Push (unless pull-only)
        if not pull_only:
            console.print("[bold]Pushing...[/bold]")
            push_result = git.push()
            console.print(f"  {push_result}")
            console.print()

        success("Sync complete!")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Sync failed: {e}")


# ============================================================================
# tui Command
# ============================================================================


@main.command()
@require_init
def tui():
    """Interactive TUI for managing dotfiles.

    Navigate with arrow keys, press Enter to switch branches.

    Keys:
        Enter - Switch to selected branch
        c     - Open command palette
        s     - Sync with remote
        d     - Deploy selected branch
        e     - Edit config file
        a     - Run security audit
        r     - Refresh
        ?     - Show help
        q     - Quit

    Requires: pip install dot-man[tui]
    """
    try:
        from .tui import run_tui
    except ImportError:
        console.print("[yellow]TUI requires the 'textual' package.[/yellow]")
        console.print()
        console.print("Install with:")
        console.print("  [cyan]pipx inject dot-man textual[/cyan]")
        console.print("  or")
        console.print("  [cyan]pip install dot-man[tui][/cyan]")
        return

    try:
        result = run_tui()

        if result:
            action, data = result

            if action == "switch" and data:
                ctx = click.Context(switch)
                ctx.invoke(switch, branch=data, dry_run=False, force=True)

            elif action == "sync":
                ctx = click.Context(sync)
                ctx.invoke(sync, push_only=False, pull_only=False)

            elif action == "deploy" and data:
                ctx = click.Context(deploy)
                ctx.invoke(deploy, branch=data, force=True, dry_run=False)

            elif action == "run" and data:
                # Run arbitrary dot-man command
                subprocess.run(
                    [sys.executable, "-m", "dot_man.cli"] + data, check=False
                )

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"TUI error: {e}")


# ============================================================================
# setup Command
# ============================================================================


@main.command()
@require_init
def setup():
    """Set up remote repository for syncing.

    Guides you through creating a GitHub repository and connecting it.
    Supports GitHub CLI (gh) for automatic creation.
    """
    import shutil

    git = GitManager()

    # Check if remote already configured
    if git.has_remote():
        url = git.get_remote_url()
        console.print(f"Remote already configured: [cyan]{url}[/cyan]")
        if not confirm("Replace with a new remote?"):
            return

    console.print()
    console.print("[bold]🔧 Remote Setup[/bold]")
    console.print()

    # Check for GitHub CLI
    gh_available = shutil.which("gh") is not None

    if gh_available:
        console.print("[green]✓[/green] GitHub CLI (gh) detected")
        console.print()

        if confirm("Create a new private GitHub repository?"):
            repo_name = click.prompt("Repository name", default="dotfiles")

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
                    console.print()
                    console.print(
                        "You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!"
                    )
                    return
                else:
                    warn(f"gh command failed: {result.stderr}")
                    console.print("Falling back to manual setup...")
                    console.print()
            except Exception as e:
                warn(f"Error running gh: {e}")
                console.print("Falling back to manual setup...")
                console.print()
    else:
        console.print(
            "[dim]GitHub CLI not found. Install with: https://cli.github.com[/dim]"
        )
        console.print()

    # Manual setup instructions
    console.print("[bold]Manual Setup Steps:[/bold]")
    console.print()
    console.print("1. Create a new repository on GitHub:")
    console.print("   [cyan]https://github.com/new[/cyan]")
    console.print()
    console.print("2. Copy the repository URL (SSH or HTTPS)")
    console.print()

    url = click.prompt("Enter the repository URL (or 'skip' to exit)", default="skip")

    if url.lower() == "skip":
        console.print()
        console.print("You can set the remote later with:")
        console.print("  [cyan]dot-man remote set <url>[/cyan]")
        return

    try:
        git.set_remote(url)

        # Also save to global.conf
        global_config = GlobalConfig()
        global_config.load()
        global_config.remote_url = url
        global_config.save()

        success(f"Remote set to: {url}")

        if confirm("Push current dotfiles to remote?"):
            console.print("Pushing...")
            git.push()
            success("Pushed to remote!")
            console.print()
            console.print(
                "You can now use [cyan]dot-man sync[/cyan] to sync your dotfiles!"
            )
    except Exception as e:
        error(f"Failed to set remote: {e}")


# ============================================================================
# repo Command
# ============================================================================


@main.command()
@require_init
def repo():
    """Show the repository path for direct git access.

    Use this to run git commands directly in the dot-man repository.

    Example:
        cd $(dot-man repo)
        git remote add origin <url>
    """
    console.print(str(REPO_DIR))


@main.command()
@require_init
def shell():
    """Open a shell in the repository directory.

    Useful for running git commands directly.
    """
    import os

    console.print(f"Opening shell in [cyan]{REPO_DIR}[/cyan]")
    console.print("[dim]Type 'exit' to return[/dim]")
    console.print()

    # Get user's shell
    user_shell = os.environ.get("SHELL", "/bin/bash")

    # Change to repo dir and exec shell
    os.chdir(REPO_DIR)
    os.execlp(user_shell, user_shell)


# ============================================================================
# config Command
# ============================================================================


@main.group()
def config():
    """Manage global configuration."""
    pass


@config.command("list")
def config_list():
    """List all global configuration values."""
    try:
        config = GlobalConfig()
        config.load()

        # Flattener helper
        def flatten(d, parent_key="", sep="."):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        # Access private _data for full listing, or use specific properties?
        # Using _data is easiest to show everything.
        flat_data = flatten(config._data)

        table = Table(title="Global Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for k, v in sorted(flat_data.items()):
            table.add_row(k, str(v))

        console.print(table)

    except Exception as e:
        error(f"Failed to list config: {e}")


@config.command("get")
@click.argument("key")
def config_get(key: str):
    """Get a configuration value.

    Example: dot-man config get dot-man.editor
    """
    try:
        config = GlobalConfig()
        config.load()

        # Traverse keys
        parts = key.split(".")
        current = config._data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                error(f"Key not found: {key}")

        # If result is a dict, print it nicely? Or just error that it's a section?
        if isinstance(current, dict):
            console.print(f"[dim]Section '{key}' contains:[/dim]")
            import json

            console.print(json.dumps(current, indent=2))
        else:
            console.print(str(current))

    except Exception as e:
        error(f"Failed to get config: {e}")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Example: dot-man config set dot-man.editor nvim
    """
    try:
        config = GlobalConfig()
        try:
            config.load()
        except Exception:
            # If load fails (e.g. no file), we assume empty default or create new
            config.create_default()

        # Handle specific known keys via properties for safety/validation if needed
        # But generic access is more flexible.

        # Special handling for boolean values from CLI string
        if value.lower() == "true":
            val = True
        elif value.lower() == "false":
            val = False
        else:
            val = value

        # Set value
        parts = key.split(".")
        current = config._data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                error(
                    f"Key path conflict: '{'.'.join(parts[: i + 1])}' is not a section"
                )

        current[parts[-1]] = val
        config.save()

        success(f"Set '{key}' to '{val}'")

    except Exception as e:
        error(f"Failed to set config: {e}")


@config.command("create")
@click.option(
    "--examples",
    "with_examples",
    is_flag=True,
    default=True,
    help="Include commented examples in the config file (default: True)",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Create a minimal config file without examples or comments",
)
@click.option(
    "--force", is_flag=True, help="Overwrite existing config file without prompting"
)
@require_init
def config_create(with_examples: bool, minimal: bool, force: bool):
    """Create or regenerate the dot-man.toml configuration file.

    This command creates a new dot-man.toml file for the current branch.
    By default, it includes commented examples to help you get started.

    Examples:
        # Create config with examples (default)
        dot-man config create

        # Create minimal config without examples
        dot-man config create --minimal

        # Create config with examples, overwrite existing
        dot-man config create --examples --force

        # Create minimal config, overwrite existing
        dot-man config create --minimal --force
    """
    try:
        from .constants import DOT_MAN_TOML

        config_path = REPO_DIR / DOT_MAN_TOML

        # Check if file exists
        if config_path.exists() and not force:
            if not confirm(f"Config file already exists at {config_path}. Overwrite?"):
                console.print("Cancelled.")
                return

        # Create the config
        dotman_config = DotManConfig()

        if minimal:
            # Create minimal config without examples
            dotman_config._data = {}
            dotman_config.save()
            console.print(f"Created minimal config at {config_path}")
        else:
            # Create config with examples (default behavior)
            dotman_config.create_default()
            console.print(f"Created config with examples at {config_path}")

        console.print("Tip: Use 'dot-man edit' to open the config in your editor")

    except Exception as e:
        error(f"Failed to create config: {e}")


@config.command("tutorial")
@click.option("--section", help="Show examples for a specific section type")
@click.option("--interactive", "-i", is_flag=True, help="Interactive tutorial mode")
def config_tutorial(section: str | None, interactive: bool):
    """Interactive configuration tutorial with examples.

    Learn how to configure dot-man with practical examples and explanations.
    Similar to vimtutor, this guides you through configuration options.

    Examples:
        # Show all examples
        dot-man config tutorial

        # Show examples for a specific type
        dot-man config tutorial --section basic
        dot-man config tutorial --section advanced
        dot-man config tutorial --section hooks

        # Interactive mode (step by step)
        dot-man config tutorial --interactive
    """
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.prompt import Prompt, Confirm

    if interactive:
        _run_interactive_tutorial()
        return

    if section:
        _show_section_examples(section)
        return

    # Show interactive overview with all sections
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]dot-man Configuration Tutorial[/bold blue]\n\n"
            "This tutorial shows you how to configure dot-man to track your dotfiles.\n"
            "Choose from the options below or use --interactive for guided learning.",
            title="🎯 Tutorial Overview",
        )
    )

    console.print("\n[bold]What would you like to learn about?[/bold]")
    console.print()

    # Interactive menu options
    menu_options = [
        ("1", "Basic file tracking", "paths, sections, simple examples"),
        ("2", "Directory tracking", "include/exclude patterns, wildcards"),
        ("3", "Update strategies", "replace, rename_old, ignore strategies"),
        ("4", "Hooks & automation", "pre/post deploy commands, aliases"),
        ("5", "Templates & inheritance", "reusable configs, organization"),
        ("6", "Advanced features", "custom paths, overrides, limits"),
        ("7", "Security & secrets", "automatic filtering, best practices"),
        ("I", "Interactive tutorial", "step-by-step guided learning"),
        ("C", "Create config", "generate config file with examples"),
        ("Q", "Quit", "exit tutorial"),
    ]

    for key, title, desc in menu_options:
        if key in ["I", "C", "Q"]:
            console.print(f"  [yellow]{key}[/yellow] - [bold]{title}[/bold] - {desc}")
        else:
            console.print(f"  [cyan]{key}[/cyan] - [bold]{title}[/bold] - {desc}")

    console.print()

    # Get user choice
    choice = Prompt.ask(
        "Enter your choice",
        choices=["1", "2", "3", "4", "5", "6", "7", "I", "C", "Q"],
        default="I",
    ).upper()

    # Handle choice
    if choice == "1":
        _show_section_examples("basic")
    elif choice == "2":
        _show_section_examples("directories")
    elif choice == "3":
        _show_section_examples("hooks")  # Update strategies are in hooks section
    elif choice == "4":
        _show_section_examples("hooks")
    elif choice == "5":
        _show_section_examples("templates")
    elif choice == "6":
        _show_section_examples("advanced")
    elif choice == "7":
        _show_section_examples("secrets")
    elif choice == "I":
        _run_interactive_tutorial()
    elif choice == "C":
        console.print(
            "\n[dim]Tip: Run 'dot-man config create' to generate a config file with examples[/dim]"
        )
    elif choice == "Q":
        console.print(
            "\n[dim]Goodbye! Run 'dot-man config tutorial' anytime to return.[/dim]"
        )

    return
    console.print("[dim]Tip: Use --interactive for step-by-step guidance[/dim]")


def _show_section_examples(section: str):
    """Show examples for a specific section."""
    from rich.panel import Panel
    from rich.text import Text
    from rich.syntax import Syntax

    examples = {
        "basic": {
            "title": "Basic File Tracking",
            "description": "Track individual files with smart defaults",
            "examples": [
                {
                    "title": "Simple file tracking",
                    "config": """[bashrc]
paths = ["~/.bashrc"]""",
                    "explanation": "Tracks your bash configuration. dot-man automatically:\n"
                    "• Generates repo_base as 'bashrc'\n"
                    "• Uses 'replace' update_strategy\n"
                    "• Enables secrets_filter",
                },
                {
                    "title": "Multiple files in one section",
                    "config": """[shell-files]
paths = ["~/.bashrc", "~/.zshrc", "~/.profile"]""",
                    "explanation": "Group related files together. All files share the same settings.",
                },
                {
                    "title": "Custom repository name",
                    "config": """[my-config]
paths = ["~/.myapp/config"]
repo_base = "my-app-config" """,
                    "explanation": "Override the auto-generated repo_base with a custom name.",
                },
            ],
        },
        "directories": {
            "title": "Directory Tracking",
            "description": "Track entire directories with include/exclude patterns",
            "examples": [
                {
                    "title": "Basic directory tracking",
                    "config": """[nvim]
paths = ["~/.config/nvim"]""",
                    "explanation": "Tracks your entire Neovim config directory.",
                },
                {
                    "title": "Directory with exclusions",
                    "config": """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]""",
                    "explanation": "Exclude temporary files and compiled plugins from tracking.",
                },
                {
                    "title": "Include only specific files",
                    "config": """[dotfiles]
paths = ["~/dotfiles"]
include = ["*.conf", "*.sh", "README.md"]""",
                    "explanation": "Only track configuration files, scripts, and documentation.",
                },
            ],
        },
        "hooks": {
            "title": "Pre/Post Deploy Hooks",
            "description": "Run commands before or after file deployment",
            "examples": [
                {
                    "title": "Shell reload after config change",
                    "config": """[bashrc]
paths = ["~/.bashrc"]
post_deploy = "shell_reload" """,
                    "explanation": "Reloads your shell after deploying bash config.\n"
                    "'shell_reload' is an alias for: source ~/.bashrc || source ~/.zshrc",
                },
                {
                    "title": "Neovim plugin sync",
                    "config": """[nvim]
paths = ["~/.config/nvim"]
post_deploy = "nvim_sync" """,
                    "explanation": "Runs PackerSync after deploying Neovim config.\n"
                    "'nvim_sync' is an alias for: nvim --headless +PackerSync +qa",
                },
                {
                    "title": "Custom command",
                    "config": """[custom-app]
paths = ["~/.config/myapp"]
post_deploy = "systemctl --user restart myapp" """,
                    "explanation": "Restart a user service after config deployment.",
                },
                {
                    "title": "Pre-deploy backup",
                    "config": """[important-config]
paths = ["~/.important"]
pre_deploy = "cp ~/.important ~/.important.backup" """,
                    "explanation": "Create a backup before overwriting important files.",
                },
            ],
        },
        "templates": {
            "title": "Reusable Templates",
            "description": "Define shared settings that can be inherited",
            "examples": [
                {
                    "title": "Template definition",
                    "config": """[templates.linux-desktop]
post_deploy = "notify-send 'Config updated'"
update_strategy = "rename_old"

[templates.dev-tools]
secrets_filter = false
pre_deploy = "echo 'Deploying dev config'" """,
                    "explanation": "Define reusable templates with common settings.",
                },
                {
                    "title": "Template inheritance",
                    "config": """[hyprland]
paths = ["~/.config/hypr"]
inherits = ["linux-desktop"]

[git]
paths = ["~/.gitconfig"]
inherits = ["dev-tools"]""",
                    "explanation": "Inherit settings from templates. Child settings override parent settings.",
                },
            ],
        },
        "advanced": {
            "title": "Advanced Options",
            "description": "Fine-tune behavior with advanced configuration options",
            "examples": [
                {
                    "title": "Update strategies",
                    "config": """[careful-config]
paths = ["~/.important"]
update_strategy = "rename_old"

[aggressive-config]
paths = ["~/.cache/myapp"]
update_strategy = "replace"

[readonly-config]
paths = ["~/.readonly"]
update_strategy = "ignore" """,
                    "explanation": "• 'replace': Overwrite existing files (default)\n"
                    "• 'rename_old': Backup existing files\n"
                    "• 'ignore': Skip if file exists",
                },
                {
                    "title": "Explicit repository paths",
                    "config": """[special-file]
paths = ["~/.config/app/special.conf"]
repo_path = "configs/special-config.toml" """,
                    "explanation": "Override automatic repo path generation with explicit repo_path.",
                },
            ],
        },
        "secrets": {
            "title": "Secret Detection & Filtering",
            "description": "Automatically detect and handle sensitive information",
            "examples": [
                {
                    "title": "Automatic secret filtering",
                    "config": """[gitconfig]
paths = ["~/.gitconfig"]
# secrets_filter = true  (enabled by default)""",
                    "explanation": "Automatically redacts API keys, passwords, and tokens when saving.",
                },
                {
                    "title": "Disable filtering for trusted files",
                    "config": """[trusted-config]
paths = ["~/.config/trusted"]
secrets_filter = false""",
                    "explanation": "Disable secret filtering for files you know are safe.",
                },
                {
                    "title": "Check for secrets",
                    "command": "dot-man audit",
                    "explanation": "Scan your repository for secrets. Use --strict for CI/CD.",
                },
            ],
        },
    }

    if section not in examples:
        console.print(f"[red]Unknown section: {section}[/red]")
        console.print(f"Available sections: {', '.join(examples.keys())}")
        return

    data = examples[section]

    console.print()
    console.print(
        Panel.fit(
            f"[bold blue]{data['title']}[/bold blue]\n\n{data['description']}",
            title=f"📖 {data['title']}",
        )
    )

    for i, example in enumerate(data["examples"], 1):
        console.print(f"\n[bold cyan]Example {i}: {example['title']}[/bold cyan]")

        if "config" in example:
            console.print(
                Syntax(example["config"], "toml", theme="monokai", line_numbers=False)
            )
        elif "command" in example:
            console.print(f"[green]$ {example['command']}[/green]")

        console.print(f"\n[dim]{example['explanation']}[/dim]")

    console.print(
        f"\n[dim]💡 Run 'dot-man config create' to add these examples to your config file[/dim]"
    )


def _run_interactive_tutorial():
    """Run interactive step-by-step tutorial with detailed explanations."""
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns

    console.print()
    console.print(
        Panel.fit(
            "[bold green]🎓 Interactive dot-man Configuration Tutorial[/bold green]\n\n"
            "This interactive tutorial will guide you through configuring dot-man.\n"
            "You'll learn what each configuration option does as we build examples.",
            title="Welcome!",
        )
    )

    # Track user configurations for final summary
    user_configs = []

    # Step 1: Basic files
    console.print("\n[bold cyan]📁 Step 1: Basic File Tracking[/bold cyan]")
    console.print(
        "Every configuration section starts with [section-name] and defines what files to track."
    )

    console.print("\n[bold green]✅ Example: Shell Configuration[/bold green]")
    console.print()

    # Show the config with explanations
    config_text = """[shell-config]
paths = ["~/.bashrc", "~/.zshrc"]
post_deploy = "shell_reload" """

    console.print(Syntax(config_text, "toml", theme="monokai"))
    console.print()

    # Explain each part
    console.print(
        "[bold cyan]🔍 [shell-config][/bold cyan] - A unique name for this group of files"
    )
    console.print(
        "[bold cyan]📂 paths[/bold cyan] - List of files/directories to track (supports ~ expansion)"
    )
    console.print(
        "[bold cyan]🚀 post_deploy[/bold cyan] - Command to run AFTER files are deployed"
    )
    console.print(
        "[bold cyan]🔄 shell_reload[/bold cyan] - Built-in alias that reloads bash/zsh"
    )
    console.print("    [dim](runs: source ~/.bashrc || source ~/.zshrc)[/dim]")

    console.print(
        "\n[dim]💡 Smart defaults apply automatically - you only specify what's different![/dim]"
    )

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    console.print(
        "\n[bold green]✅ Git Config with Automatic Secret Protection:[/bold green]"
    )
    console.print()

    config_text = """[gitconfig]
paths = ["~/.gitconfig"]"""

    console.print(Syntax(config_text, "toml", theme="monokai"))
    console.print()

    console.print(
        "[bold cyan]🔒 Automatic security[/bold cyan] - Git configs get special protection:"
    )
    console.print(
        "  • [yellow]secrets_filter = true[/yellow] - Detects and redacts sensitive data"
    )
    console.print(
        "  • [yellow]API keys, passwords, tokens[/yellow] - Automatically removed when saving"
    )
    console.print(
        '  • [yellow]update_strategy = "replace"[/yellow] - Safe for most config files'
    )

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 2: Directories with patterns
    console.print(
        "\n[bold cyan]📂 Step 2: Directory Tracking with Patterns[/bold cyan]"
    )
    console.print("When tracking directories, you can include/exclude specific files.")

    console.print("\n[bold green]✅ Neovim Config with Smart Exclusions:[/bold green]")
    console.print()

    config_text = """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]
post_deploy = "nvim_sync" """

    console.print(Syntax(config_text, "toml", theme="monokai"))
    console.print()

    console.print(
        "[bold cyan]🎯 exclude[/bold cyan] - Patterns of files/directories to SKIP tracking"
    )
    console.print("  • [yellow]*.log[/yellow] - Any .log files")
    console.print(
        "  • [yellow]plugin/packer_compiled.lua[/yellow] - Compiled plugin cache"
    )
    console.print(
        "[bold cyan]📝 Pattern syntax[/bold cyan] - Wildcards (*, **, ?) and gitignore-style"
    )
    console.print(
        "[bold cyan]🔄 nvim_sync[/bold cyan] - Alias: nvim --headless +PackerSync +qa"
    )

    console.print(
        '\n[dim]💡 Use ** for recursive: "**/*.tmp" matches all .tmp files in subdirs[/dim]'
    )

    user_configs.append(
        (
            "nvim",
            """[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]
post_deploy = "nvim_sync" """,
        )
    )

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 3: Update strategies
    console.print(
        "\n[bold cyan]🔄 Step 3: Update Strategies - How Files Are Deployed[/bold cyan]"
    )
    console.print("Choose how dot-man handles existing files when deploying.")

    # Show update strategy information

    console.print("\n[bold green]📋 Update Strategy Options:[/bold green]")

    strategy_examples = {
        "Safe (rename_old)": {
            "config": 'update_strategy = "rename_old"',
            "explanation": "• Backs up existing file as filename.bak\n• Then overwrites with new version\n• Your original file is safe if something goes wrong",
        },
        "Direct (replace)": {
            "config": 'update_strategy = "replace"  # Default',
            "explanation": "• Directly overwrites existing files\n• No backup created\n• Fastest option",
        },
        "Conservative (ignore)": {
            "config": 'update_strategy = "ignore"',
            "explanation": "• Skips files that already exist\n• Never overwrites your changes\n• Good for one-time setup files",
        },
    }

    for name, details in strategy_examples.items():
        console.print(f"\n[yellow]{name}:[/yellow]")
        console.print(Syntax(details["config"], "toml", theme="monokai"))
        console.print(details["explanation"])

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 4: Pre-deploy hooks
    console.print(
        "\n[bold cyan]⚡ Step 4: Pre-Deploy Hooks - Actions Before Deployment[/bold cyan]"
    )
    console.print("Sometimes you need to prepare before deploying files.")

    console.print("\n[bold green]🔧 Pre-deploy Hook Examples:[/bold green]")
    console.print()

    examples = [
        {
            "title": "Backup important files",
            "config": """[important-config]
paths = ["~/.important/app.conf"]
pre_deploy = "cp ~/.important/app.conf ~/.important/app.conf.backup" """,
            "explanation": "Creates a backup before dot-man touches the file",
        },
        {
            "title": "Stop services before config change",
            "config": """[service-config]
paths = ["~/.config/my-service"]
pre_deploy = "systemctl --user stop my-service" """,
            "explanation": "Stops the service before updating its config files",
        },
    ]

    for example in examples:
        console.print(f"[cyan]{example['title']}:[/cyan]")
        console.print(Syntax(example["config"], "toml", theme="monokai"))
        console.print(f"  {example['explanation']}")
        console.print()

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 5: Templates
    console.print(
        "\n[bold cyan]📋 Step 5: Templates - Reusable Configuration[/bold cyan]"
    )
    console.print("Define shared settings that multiple sections can inherit.")

    console.print("\n[bold green]🎨 Template Example:[/bold green]")
    console.print()

    config_text = """# Define a template
[templates.desktop-apps]
post_deploy = "notify-send 'Config updated'"
update_strategy = "rename_old"

# Use the template
[hyprland]
paths = ["~/.config/hypr"]
inherits = ["desktop-apps"]

[waybar]
paths = ["~/.config/waybar"]
inherits = ["desktop-apps"]
# Override settings if needed
update_strategy = "replace" """

    console.print(Syntax(config_text, "toml", theme="monokai"))
    console.print()

    console.print(
        "[bold cyan]📋 Template definition[/bold cyan] - [templates.name] sections are reusable"
    )
    console.print(
        "[bold cyan]🔗 inherits[/bold cyan] - List of templates to inherit settings from"
    )
    console.print(
        "[bold cyan]⚡ Override behavior[/bold cyan] - Section settings override templates"
    )
    console.print(
        "[bold cyan]🎯 Use case[/bold cyan] - Share notifications, strategies, etc."
    )

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Step 6: Terminal
    console.print("\n[bold cyan]💻 Step 6: Terminal Configuration[/bold cyan]")

    console.print("\n[bold green]✅ Kitty Terminal Configuration:[/bold green]")
    console.print()

    config_text = """[kitty]
paths = ["~/.config/kitty"]
post_deploy = "kitty_reload" """

    console.print(Syntax(config_text, "toml", theme="monokai"))
    console.print()

    console.print(
        "[bold cyan]🖥️ Kitty[/bold cyan] - Fast, GPU-accelerated terminal emulator"
    )
    console.print("[bold cyan]📂 paths[/bold cyan] - Kitty configuration directory")
    console.print("[bold cyan]🚀 post_deploy[/bold cyan] - Reload command for Kitty")
    console.print(
        "[bold cyan]🔄 kitty_reload[/bold cyan] - Sends SIGUSR1 to reload running instances"
    )

    user_configs.append(
        (
            "kitty",
            """[kitty]
paths = ["~/.config/kitty"]
post_deploy = "kitty_reload" """,
        )
    )

    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    # Final summary
    console.print("\n[bold green]🎉 Tutorial Complete![/bold green]")
    console.print("\n[dim]You've learned about:[/dim]")
    console.print("  • 📁 Basic file and directory tracking")
    console.print("  • 🎯 Include/exclude patterns for selective tracking")
    console.print("  • 🔄 Update strategies (replace, rename_old, ignore)")
    console.print("  • ⚡ Pre/post deploy hooks for automation")
    console.print("  • 📋 Templates for reusable configuration")
    console.print("  • 🔒 Automatic secret detection and filtering")

    console.print("\n[dim]Next steps:[/dim]")
    console.print(
        "[green]$ dot-man config create[/green] [dim]- Generate config file with examples[/dim]"
    )
    console.print(
        "[green]$ dot-man edit[/green] [dim]- Customize your configuration[/dim]"
    )
    console.print(
        "[green]$ dot-man config tutorial --section advanced[/green] [dim]- Learn advanced features[/dim]"
    )


# ============================================================================
# Entry Point
# ============================================================================


if __name__ == "__main__":
    main()
