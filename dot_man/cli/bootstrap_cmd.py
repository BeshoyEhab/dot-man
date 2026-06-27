"""Bootstrap command for dot-man — install packages via system package managers."""

import logging
import shutil
import subprocess

import click

from .. import ui
from .common import require_init, success, warn
from .interface import cli as main

# Package manager detection: command → (install_cmd, update_cmd)
PACKAGE_MANAGERS = {
    "brew": {
        "install": "brew install {package}",
        "update": "brew update",
        "detect": "brew",
    },
    "apt": {
        "install": "sudo apt-get install -y {package}",
        "update": "sudo apt-get update",
        "detect": "apt-get",
    },
    "dnf": {
        "install": "sudo dnf install -y {package}",
        "update": "sudo dnf check-update",
        "detect": "dnf",
    },
    "pacman": {
        "install": "sudo pacman -S --noconfirm {package}",
        "update": "sudo pacman -Sy",
        "detect": "pacman",
    },
    "zypper": {
        "install": "sudo zypper install -y {package}",
        "update": "sudo zypper refresh",
        "detect": "zypper",
    },
    "nix-env": {
        "install": "nix-env -iA nixpkgs.{package}",
        "update": "nix-channel --update",
        "detect": "nix-env",
    },
    "xbps-install": {
        "install": "sudo xbps-install -y {package}",
        "update": "sudo xbps-install -Su",
        "detect": "xbps-install",
    },
    "pkg": {
        "install": "pkg install -y {package}",
        "update": "pkg update",
        "detect": "pkg",
    },
}


def _detect_package_manager() -> str | None:
    """Detect the available package manager on this system."""
    import platform

    os_name = platform.system().lower()

    # Preferred order by OS
    if os_name == "darwin":
        preferred = ["brew"]
    elif os_name == "linux":
        preferred = ["apt", "dnf", "pacman", "zypper", "xbps-install", "nix-env"]
    elif os_name == "freebsd":
        preferred = ["pkg"]
    else:
        preferred = list(PACKAGE_MANAGERS.keys())

    for pm in preferred:
        if shutil.which(PACKAGE_MANAGERS[pm]["detect"]):
            return pm

    return None


def _load_bootstrap_packages() -> dict[str, list[str]]:
    """Load packages from dot-man config or bootstrap.toml."""
    try:
        from ..config import DotManConfig

        config = DotManConfig()
        config.load()

        # Check for [bootstrap] section in config
        bootstrap = config._data.get("bootstrap", {})
        if bootstrap:
            packages = {}
            # Support both flat list and grouped format
            if isinstance(bootstrap, dict):
                for key, value in bootstrap.items():
                    if key == "packages" and isinstance(value, list):
                        packages["default"] = value
                    elif isinstance(value, list):
                        packages[key] = value
            return packages

    except Exception as e:
        logging.debug(f"Failed to load bootstrap config: {e}")

    return {}


def _run_with_pm(pm: str, command_template: str, package: str) -> bool:
    """Run a package manager command. Returns True on success."""
    cmd = command_template.format(package=package)
    ui.console.print(f"  [cyan]$ {cmd}[/cyan]")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return True
        else:
            warn(f"Failed to install {package} (exit code {result.returncode})")
            if result.stderr:
                for line in result.stderr.splitlines()[:3]:
                    ui.console.print(f"    [dim]{line}[/dim]")
            return False
    except subprocess.TimeoutExpired:
        warn(f"Timeout installing {package}")
        return False
    except Exception as e:
        warn(f"Error installing {package}: {e}")
        return False


@main.command("bootstrap")
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    help="List packages that would be installed without installing",
)
@click.option("--pm", help="Package manager to use (auto-detected if not specified)")
@click.option("--update", is_flag=True, help="Update package manager first")
@click.argument("packages", nargs=-1)
@require_init
def bootstrap(list_only: bool, pm: str | None, update: bool, packages: tuple[str, ...]):
    """Install system packages via package managers.

    Detects your system package manager (brew, apt, dnf, pacman, etc.)
    and installs the specified packages. Packages can also be defined
    in your dot-man config under [bootstrap].

    Examples:
        # Install specific packages
        dot-man bootstrap neovim tmux git

        # List what would be installed from config
        dot-man bootstrap --list

        # Use a specific package manager
        dot-man bootstrap --pm brew neovim

        # Update package manager first
        dot-man bootstrap --update neovim
    """
    # Detect package manager
    if not pm:
        pm = _detect_package_manager()
        if not pm:
            ui.console.print("[red]No supported package manager found.[/red]")
            ui.console.print(
                "Supported: brew, apt, dnf, pacman, zypper, nix-env, xbps-install, pkg"
            )
            ui.console.print("Use --pm to specify one manually.")
            raise SystemExit(1)

    if pm not in PACKAGE_MANAGERS:
        ui.console.print(f"[red]Unknown package manager: {pm}[/red]")
        raise SystemExit(1)

    pm_info = PACKAGE_MANAGERS[pm]
    ui.console.print(f"[bold]Using package manager:[/bold] [cyan]{pm}[/cyan]")

    # Collect packages from args and config
    all_packages: dict[str, list[str]] = {}

    if packages:
        all_packages["command-line"] = list(packages)

    config_packages = _load_bootstrap_packages()
    all_packages.update(config_packages)

    if not all_packages:
        ui.console.print("[yellow]No packages specified.[/yellow]")
        ui.console.print("Usage: dot-man bootstrap <package1> <package2> ...")
        ui.console.print("Or add [bootstrap] section to your dot-man.toml:")
        ui.console.print('  [bootstrap]\n  packages = ["neovim", "tmux", "git"]')
        return

    # List mode
    if list_only:
        ui.console.print()
        ui.console.print("[bold]Packages to install:[/bold]")
        for group, pkgs in all_packages.items():
            ui.console.print(f"  [cyan]{group}:[/cyan]")
            for pkg in pkgs:
                ui.console.print(f"    • {pkg}")
        ui.console.print()
        total = sum(len(pkgs) for pkgs in all_packages.values())
        ui.console.print(f"  [dim]{total} package(s) total[/dim]")
        return

    # Update package manager if requested
    if update:
        ui.console.print()
        ui.console.print("[bold]Updating package manager...[/bold]")
        _run_with_pm(pm, pm_info["update"], "")

    # Install packages
    installed = 0
    failed = 0

    for group, pkgs in all_packages.items():
        ui.console.print()
        ui.console.print(f"[bold]Installing {group}:[/bold]")
        for pkg in pkgs:
            ui.console.print(f"\n[bold]→ {pkg}[/bold]")
            result = _run_with_pm(pm, pm_info["install"], pkg)
            if result:
                installed += 1
            else:
                failed += 1

    # Summary
    ui.console.print()
    ui.console.print("[bold]Bootstrap complete:[/bold]")
    ui.console.print(f"  [green]✓ {installed} installed[/green]")
    if failed:
        ui.console.print(f"  [red]✗ {failed} failed[/red]")
    ui.console.print()

    if installed > 0:
        success(f"Installed {installed} package(s) via {pm}")
