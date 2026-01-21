"""Init command for dot-man CLI."""

import sys
import shutil
from pathlib import Path

import click

from .. import ui
from ..constants import DOT_MAN_DIR, REPO_DIR, BACKUPS_DIR, FILE_PERMISSIONS
from ..config import GlobalConfig, DotManConfig
from ..core import GitManager
from ..utils import is_git_installed
from .interface import cli as main
from .common import error, success, warn


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
        ui.console.print()
        ui.print_banner("🎉 dot-man initialized successfully!")
        ui.console.print()

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
    ui.print_banner("🧙 Setup Wizard")
    ui.console.print()
    ui.console.print(
        "Let's get your dotfiles set up! I'll detect common files automatically."
    )
    ui.console.print()

    # Detect common dotfiles
    ui.console.print("[bold]Detecting dotfiles...[/bold]")
    ui.console.print()

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
            ui.console.print(f"  [green]✓[/green] Found: [cyan]{path_str}[/cyan] ({desc})")
            if ui.confirm("    Track this?", default=True):
                files_to_add.append((path_str, section_name))

    if found_count == 0:
        ui.console.print("  [dim]No common dotfiles detected in default locations[/dim]")
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
            "  1. [cyan]dot-man status[/cyan]       - View your tracked files"
        )
        ui.console.print(
            "  2. [cyan]dot-man switch work[/cyan]  - Create a work configuration branch"
        )
        ui.console.print("  3. [cyan]dot-man add <path>[/cyan]   - Track more files")
    else:
        ui.console.print("[bold]Get started:[/bold]")
        ui.console.print("  [cyan]dot-man add ~/.bashrc[/cyan]   - Add files to track")
        ui.console.print("  [cyan]dot-man edit[/cyan]            - Edit config file")
        ui.console.print("  [cyan]dot-man status[/cyan]          - View status")

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
        "  dot-man switch main                [dim]# Save current state[/dim]"
    )
    ui.console.print(
        "  dot-man switch work                [dim]# Create work branch[/dim]"
    )
    ui.console.print()
    ui.console.print("[dim]💡 Tip: Config is at ~/.config/dot-man/repo/dot-man.toml[/dim]")
    ui.console.print()
