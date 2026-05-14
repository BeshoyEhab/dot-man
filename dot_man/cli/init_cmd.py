"""Init command for dot-man CLI."""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from .. import ui
from ..config import DotManConfig, GlobalConfig
from ..config_detector import ConfigDetector, get_auto_hooks_for_config
from ..constants import BACKUPS_DIR, DOT_MAN_DIR, FILE_PERMISSIONS, REPO_DIR
from ..core import GitManager
from ..utils import is_git_installed
from .common import error, handle_exception, success, warn
from .interface import cli as main


@main.command()
@click.option("--force", is_flag=True, help="Reinitialize even if already exists")
@click.option("--no-wizard", is_flag=True, help="Skip interactive setup wizard")
@click.option(
    "--sandbox",
    "sandbox_dir",
    type=click.Path(),
    default=None,
    help="Test init in a temporary sandbox directory (for testing wizard)",
)
@click.option(
    "--import",
    "import_path",
    type=click.Path(exists=True),
    default=None,
    help="Import from an existing git repository",
)
def init(
    force: bool, no_wizard: bool, sandbox_dir: str | None, import_path: str | None
):
    """Initialize a new dot-man repository.

    By default, runs an interactive setup wizard to detect and add
    common dotfiles. Use --no-wizard for manual setup.

    Examples:
        dot-man init                    # Interactive wizard
        dot-man init --sandbox /tmp/test # Test wizard in sandbox
        dot-man init --no-wizard         # Manual setup only
        dot-man init --import ~/dotfiles # Import existing dotfiles repo
    """
    # Pre-checks
    if not is_git_installed():
        error("Git not found. Please install git first.", exit_code=2)

    if DOT_MAN_DIR.exists() and not force:
        if not ui.confirm(
            "Repository already initialized. Reinitialize? (This will DELETE all data)"
        ):
            ui.info("Aborted.")
            sys.exit(1)

        shutil.rmtree(DOT_MAN_DIR)

    try:
        # Create directory structure
        DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        DOT_MAN_DIR.chmod(FILE_PERMISSIONS)
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        # Handle import from existing repo
        if import_path:
            source_path: Path

            # Check if it's a GitHub URL
            github_url = _parse_github_url(import_path)
            if github_url:
                cloned_path = _clone_github_repo(github_url)
                if cloned_path is None:
                    error("Failed to clone GitHub repository.", exit_code=1)
                source_path = cloned_path  # type: ignore[assignment]
            else:
                # It's a local path
                source_path = Path(import_path).expanduser().resolve()
                if not source_path.exists():
                    error(f"Path '{source_path}' does not exist.", exit_code=1)
                if not (source_path / ".git").exists():
                    error(f"'{source_path}' is not a git repository.", exit_code=1)

            ui.console.print(f"[dim]Importing from {source_path}...[/dim]")

            # Get the current branch from source repo
            current_branch = "master"
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=source_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    current_branch = result.stdout.strip()
            except Exception:
                pass

            # Copy entire repo including .git
            shutil.copytree(source_path, REPO_DIR, dirs_exist_ok=True)

            # Initialize git to get the repo object
            git = GitManager()

            # Set the active branch to match source
            try:
                if current_branch in git.list_branches():
                    git.checkout(current_branch)
            except Exception:
                pass

            ui.success(f"Imported dotfiles from {source_path}")
        else:
            # Initialize git repository
            git = GitManager()
            git.init()

        # Verify git config exists (user.name and user.email)
        try:
            git.repo.config_reader().get_value("user", "name")
            git.repo.config_reader().get_value("user", "email")
        except Exception:
            ui.console.print()
            ui.warn("Git user configuration not found. Setting defaults...")
            with git.repo.config_writer() as config:
                config.set_value("user", "name", "dot-man-user")
                config.set_value("user", "email", "dot-man@localhost")
            ui.console.print("[dim]  Configured default git user.[/dim]")
            ui.console.print(
                "[dim]  Run 'git config --global user.name \"Your Name\"' to customize[/dim]"
            )
            ui.console.print(
                "[dim]  Run 'git config --global user.email \"you@example.com\"' to customize[/dim]"
            )
            ui.console.print()

        # Create global configuration
        global_config = GlobalConfig()
        global_config.create_default()

        # Create minimal dot-man.toml
        dotman_config = DotManConfig()
        dotman_config.create_default()

        # Initial commit
        git.commit("dot-man: Initial commit")

        # Success message
        ui.console.print()
        ui.print_banner("🎉 dot-man initialized successfully!")
        ui.console.print()

        # Run wizard by default (unless --no-wizard)
        if not no_wizard:
            run_setup_wizard(global_config, dotman_config, git)
        else:
            show_quick_start()

    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Initialization")


def run_setup_wizard(
    global_config: GlobalConfig, dotman_config: DotManConfig, git: GitManager
):
    """Interactive setup wizard for new users."""
    ui.print_banner("🧙 Setup Wizard")
    ui.console.print()
    ui.console.print(
        "Let's get your dotfiles set up! I'll detect common files automatically."
    )
    ui.console.print()

    # Detect common dotfiles
    ui.console.print("[bold]Detecting dotfiles...[/bold]")
    ui.console.print()

    # Detect quickshell configs using ConfigDetector
    qs_configs = ConfigDetector.detect_quickshell_configs()

    # Build common_files with quickshell detection
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

    # Add quickshell configs as separate entries
    for qs_config in qs_configs:
        common_files.append(
            (
                qs_config["paths"][0],
                qs_config["display_name"],
                qs_config["section_name"],
            )
        )

    files_to_add = []
    found_count = 0

    for path_str, desc, section_name in common_files:
        path = Path(path_str).expanduser()

        # Skip quickshell subdirs (detected separately by ConfigDetector)
        if section_name.startswith("qs-"):
            if path.exists():
                found_count += 1
                ui.console.print(
                    f"  [green]✓[/green] Found: [cyan]{path_str}[/cyan] ({desc})"
                )
                if ui.confirm("    Track this?", default=True):
                    files_to_add.append((path_str, section_name))
            continue

        # Special handling for Quickshell root ambiguity
        if section_name == "quickshell" and path.exists():
            subdirs = sorted(
                [
                    d
                    for d in path.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                ],
                key=lambda x: x.name,
            )
            if len(subdirs) > 1:
                found_count += 1
                ui.console.print(
                    f"  [green]✓[/green] Found: [cyan]{path_str}[/cyan] ({desc})"
                )
                ui.console.print(
                    "    [yellow]⚠️  Multiple configurations detected:[/yellow]"
                )

                # List options
                options = subdirs + [path]  # subdirs + root
                for i, opt in enumerate(options, 1):
                    if opt == path:
                        label = f"Track root directory ({path_str})"
                    else:
                        label = f"Track '{opt.name}'"
                    ui.console.print(f"      [bold]{i}.[/bold] {label}")

                # Ask user
                while True:
                    choice = ui.ask(
                        f"    Which one to track? (1-{len(options)})",
                        default=str(len(options)),
                    )
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(options):
                            selected_path = options[idx]

                            # Determine section name
                            if selected_path == path:
                                final_section = section_name
                                final_path_str = path_str
                            else:
                                final_section = selected_path.name
                                final_path_str = f"{path_str}/{selected_path.name}"

                            if ui.confirm(
                                f"    Track '{final_section}'?", default=True
                            ):
                                files_to_add.append((final_path_str, final_section))
                            break
                        else:
                            warn("Invalid selection")
                    except ValueError:
                        warn("Please enter a number")
                continue

        if path.exists():
            found_count += 1
            ui.console.print(
                f"  [green]✓[/green] Found: [cyan]{path_str}[/cyan] ({desc})"
            )
            if ui.confirm("    Track this?", default=True):
                files_to_add.append((path_str, section_name))

    if found_count == 0:
        ui.console.print(
            "  [dim]No common dotfiles detected in default locations[/dim]"
        )
        ui.console.print()
    else:
        ui.console.print()

    # Offer to add custom files
    if ui.confirm("Add custom files not in the list?", default=False):
        ui.console.print()
        while True:
            custom_path = ui.ask(
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

            section_name = ui.ask("Section name", default=default_section)
            files_to_add.append((custom_path, section_name))

    # Add files to config
    if files_to_add:
        ui.console.print()
        ui.console.print(f"[bold]Adding {len(files_to_add)} files...[/bold]")
        ui.console.print()

        for path_str, section_name in files_to_add:
            try:
                dotman_config.add_section(
                    name=section_name,
                    paths=[path_str],
                )
                # Auto-detect and suggest hooks for popular configs
                auto_hooks = get_auto_hooks_for_config(section_name, [path_str])
                if auto_hooks:
                    for hook_type, hook_cmd in auto_hooks.items():
                        # Map to actual config keys
                        if hook_type == "post_deploy":
                            dotman_config.update_section(
                                section_name, post_deploy=hook_cmd
                            )
                        elif hook_type == "pre_deploy":
                            dotman_config.update_section(
                                section_name, pre_deploy=hook_cmd
                            )
                        ui.console.print(
                            f"  [dim]Auto-detected {hook_type} hook for {section_name}[/dim]"
                        )
                ui.console.print(f"  [green]✓[/green] [{section_name}]: {path_str}")
            except Exception as e:
                warn(f"Could not add {path_str}: {e}")

        dotman_config.save()

        # Commit the initial config
        git.add_all()
        git.commit("Add initial dotfiles configuration")

        ui.console.print()
        success(f"Added {len(files_to_add)} files to configuration")
        ui.console.print()

        # Show what was configured
        ui.console.print("[bold]Your dotfiles are now tracked:[/bold]")
        for path_str, section_name in files_to_add[:5]:
            ui.console.print(f"  • [{section_name}] {path_str}")
        if len(files_to_add) > 5:
            ui.console.print(f"  ... and {len(files_to_add) - 5} more")

    ui.console.print()

    # Offer remote setup
    if ui.confirm("Set up remote repository for syncing? (optional)", default=False):
        ui.console.print()
        from .remote_cmd import setup

        ctx = click.Context(setup)
        ctx.invoke(setup)

    # Final instructions
    ui.console.print()
    ui.print_banner("🎉 Setup Complete!")
    ui.console.print()

    if files_to_add:
        ui.console.print("[bold]Next steps:[/bold]")
        ui.console.print(
            "  1. [cyan]dot-man status[/cyan]            - View your tracked files"
        )
        ui.console.print(
            "  2. [cyan]dot-man navigate work[/cyan]     - Create a work configuration branch"
        )
        ui.console.print(
            "  3. [cyan]dot-man add <path>[/cyan]       - Track more files"
        )
    else:
        ui.console.print("[bold]Get started:[/bold]")
        ui.console.print(
            "  [cyan]dot-man add ~/.bashrc[/cyan]        - Add files to track"
        )
        ui.console.print(
            "  [cyan]dot-man edit[/cyan]                 - Edit config file"
        )
        ui.console.print("  [cyan]dot-man status[/cyan]               - View status")

    ui.console.print()
    ui.console.print("[dim]💡 Run 'dot-man --help' to see all commands[/dim]")
    ui.console.print()


def show_quick_start():
    """Display quick start guide (for --no-wizard users)."""
    ui.console.print("[bold]📚 Quick Start Guide:[/bold]")
    ui.console.print()
    ui.console.print("[bold cyan]Adding files to track:[/bold cyan]")
    ui.console.print("  dot-man add ~/.bashrc              [dim]# Single file[/dim]")
    ui.console.print("  dot-man add ~/.config/nvim         [dim]# Directory[/dim]")
    ui.console.print(
        "  dot-man edit                       [dim]# Edit config manually[/dim]"
    )
    ui.console.print()
    ui.console.print("[bold cyan]Managing configurations:[/bold cyan]")
    ui.console.print(
        "  dot-man status                     [dim]# View tracked files[/dim]"
    )
    ui.console.print(
        "  dot-man navigate main              [dim]# Save & switch to main[/dim]"
    )
    ui.console.print(
        "  dot-man navigate work --preview    [dim]# Preview work branch[/dim]"
    )
    ui.console.print()
    ui.console.print(
        "[dim]💡 Tip: Config is at ~/.config/dot-man/repo/dot-man.toml[/dim]"
    )
    ui.console.print()


def _parse_github_url(url: str) -> str | None:
    """Parse GitHub URL and return repo URL if valid.

    Supports:
    - github.com/user/repo
    - https://github.com/user/repo
    - git@github.com:user/repo
    - https://github.com/user/repo.git

    Returns:
        Clone URL if valid GitHub repo, None otherwise
    """
    import re

    url = url.strip()

    # https://github.com/user/repo or https://github.com/user/repo.git
    match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if match:
        return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

    # git@github.com:user/repo
    match = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if match:
        return f"git@github.com:{match.group(1)}/{match.group(2)}.git"

    # github.com/user/repo (shorthand)
    match = re.match(r"^github\.com/([^/]+)/([^/]+)$", url)
    if match:
        return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

    return None


def _clone_github_repo(github_url: str) -> Path | None:
    """Clone a GitHub repo to a temporary directory.

    Args:
        github_url: GitHub clone URL

    Returns:
        Path to cloned repo, or None on failure
    """
    import tempfile

    ui.console.print(f"[dim]Cloning {github_url}...[/dim]")

    try:
        temp_dir = tempfile.mkdtemp(prefix="dotman_import_")
        result = subprocess.run(
            ["git", "clone", "--mirror", github_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            ui.error(f"Failed to clone: {result.stderr}")
            return None

        # Get the actual repo path (git clone --mirror creates a bare repo)
        # We need to convert it to a working repo
        # Clone again to get a working copy
        work_dir = tempfile.mkdtemp(prefix="dotman_working_")
        result = subprocess.run(
            ["git", "clone", temp_dir, work_dir],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            ui.error(f"Failed to clone working copy: {result.stderr}")
            return None

        return Path(work_dir)
    except subprocess.TimeoutExpired:
        ui.error("Clone timed out")
        return None
    except Exception as e:
        ui.error(f"Clone failed: {e}")
        return None
