"""Profile command for dot-man CLI - Multi-machine configuration profiles."""

from typing import Any

import click

from .. import ui
from .common import complete_profiles, error, require_init, success, warn
from .interface import cli as main


@main.group("profile")
def profile():
    """Manage machine-specific profiles.

    Profiles allow you to have different configurations for different machines.
    Each profile can inherit from a base profile and override specific settings.

    Examples:
        dot-man profile list              # List all profiles
        dot-man profile create work       # Create new profile
        dot-man profile switch personal   # Switch to profile
        dot-man profile detect            # Auto-detect profile by hostname
    """
    pass


@profile.command("list")
def profile_list():
    """List all available profiles."""
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        profiles = global_config.profiles if hasattr(global_config, "profiles") else {}
        current = (
            global_config.current_profile
            if hasattr(global_config, "current_profile")
            else None
        )

        from rich.table import Table

        table = Table(title="Available Profiles")
        table.add_column("Profile", style="cyan")
        table.add_column("Inherits", style="dim")
        table.add_column("Hostnames", style="green")
        table.add_column("Status", style="yellow")

        if profiles:
            for name, data in sorted(profiles.items()):
                inherits = data.get("inherits", "")
                hostnames = ", ".join(data.get("hostnames", []))
                status = "current" if name == current else ""
                table.add_row(name, inherits or "-", hostnames or "-", status)
        else:
            table.add_row("[dim]No profiles defined[/dim]", "-", "-", "-")

        ui.console.print(table)

        # Show auto-detected profile
        detected = _detect_profile(global_config)
        if detected and detected != current:
            ui.console.print(f"\n[dim]Auto-detected profile: {detected}[/dim]")

    except Exception as e:
        error(str(e))


@profile.command("create")
@click.argument("name")
@click.option("--inherits", "-i", help="Profile to inherit from")
@click.option(
    "--hostname", "-h", multiple=True, help="Hostnames that match this profile"
)
def profile_create(name: str, inherits: str | None, hostname: tuple):
    """Create a new profile.

    Examples:
        dot-man profile create work
        dot-man profile create work -i minimal
        dot-man profile create work -h laptop -h desktop
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        # Get existing profiles
        profiles = getattr(global_config, "_data", {}).get("profiles", {})

        if name in profiles:
            error(f"Profile '{name}' already exists", exit_code=1)

        # Validate inherits
        if inherits and inherits not in profiles:
            error(f"Profile '{inherits}' does not exist", exit_code=1)

        # Create new profile
        profile_data: dict[str, Any] = {
            "hostnames": list(hostname) if hostname else [],
        }
        if inherits:
            profile_data["inherits"] = inherits
        profiles[name] = profile_data

        # Save
        if "profiles" not in global_config._data:
            global_config._data["profiles"] = {}
        global_config._data["profiles"] = profiles
        global_config.save()

        success(f"Profile '{name}' created")
        if inherits:
            ui.console.print(f"  Inherits from: {inherits}")
        if hostname:
            ui.console.print(f"  Hostnames: {', '.join(hostname)}")

        ui.hint(f"Run 'dot-man profile set-branch {name} <branch>' to link a branch")
        ui.hint("Or run 'dot-man profile detect' to auto-detect this profile")

    except Exception as e:
        error(str(e))


@profile.command("delete")
@click.argument("name", shell_complete=complete_profiles)
@click.option("--force", is_flag=True, help="Skip confirmation")
def profile_delete(name: str, force: bool):
    """Delete a profile.

    Example:
        dot-man profile delete old-machine
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        profiles = getattr(global_config, "_data", {}).get("profiles", {})

        if name not in profiles:
            error(f"Profile '{name}' does not exist", exit_code=1)

        if not force:
            if not ui.confirm(f"Delete profile '{name}'?"):
                return

        del profiles[name]
        global_config._data["profiles"] = profiles
        global_config.save()

        success(f"Profile '{name}' deleted")

    except Exception as e:
        error(str(e))


@profile.command("switch")
@click.argument("name", shell_complete=complete_profiles)
@require_init
def profile_switch(name: str):
    """Switch to a profile.

    This changes the current branch to match the profile and updates
    any profile-specific configuration.

    Examples:
        dot-man profile switch work
        dot-man profile switch server
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        profiles = getattr(global_config, "_data", {}).get("profiles", {})

        if name not in profiles:
            error(f"Profile '{name}' does not exist", exit_code=1)

        profile_data = profiles[name]
        inherits = profile_data.get("inherits")

        # Get branch to switch to (inherits branch from parent profile if specified)
        branch = None
        if inherits and inherits in profiles:
            branch = profiles[inherits].get("branch")
        if not branch:
            branch = name

        # Switch to the branch
        ui.console.print(f"Switching to profile '{name}'...")

        # Update current profile
        global_config._data["dot-man"] = global_config._data.get("dot-man", {})
        global_config._data["dot-man"]["current_profile"] = name
        global_config.save()

        # Try to switch to branch (if it exists)
        if branch in ops.git.list_branches():
            from .common import parse_branch_arg
            from .switch_cmd import switch

            parsed_branch = parse_branch_arg(branch)
            ctx = click.Context(switch)
            ctx.invoke(switch, branch=parsed_branch, dry_run=False, force=True)
        else:
            ui.console.print(
                f"[yellow]Branch '{branch}' does not exist - profile saved but no branch switched[/yellow]"
            )

        success(f"Switched to profile '{name}'")

    except Exception as e:
        error(str(e))


@profile.command("detect")
def profile_detect():
    """Auto-detect the best profile based on hostname.

    Looks at all profiles and finds one with matching hostname.
    If no match found, uses the default branch.
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        detected = _detect_profile(global_config)

        if detected:
            current = (
                global_config.current_profile
                if hasattr(global_config, "current_profile")
                else None
            )

            if detected == current:
                ui.console.print(
                    f"[green]Already on matching profile: {detected}[/green]"
                )
            else:
                ui.console.print(f"[yellow]Detected profile: {detected}[/yellow]")
                ui.console.print(
                    f"  Run 'dot-man profile switch {detected}' to activate"
                )
        else:
            warn("No matching profile found")

        # Show all profiles with their hostnames
        ui.console.print()
        ui.console.print("[bold]Profiles and their hostnames:[/bold]")

        profiles = getattr(global_config, "_data", {}).get("profiles", {})
        for name, data in sorted(profiles.items()):
            hostnames = data.get("hostnames", [])
            if hostnames:
                ui.console.print(f"  {name}: {', '.join(hostnames)}")

    except Exception as e:
        error(str(e))


@profile.command("set-branch")
@click.argument("name")
@click.argument("branch")
def profile_set_branch(name: str, branch: str):
    """Set the branch for a profile.

    Example:
        dot-man profile set-branch work work-main
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        profiles = global_config._data.get("profiles", {})

        if name not in profiles:
            error(f"Profile '{name}' does not exist", exit_code=1)

        profiles[name]["branch"] = branch
        global_config._data["profiles"] = profiles
        global_config.save()

        success(f"Profile '{name}' now uses branch '{branch}'")

    except Exception as e:
        error(str(e))


def _detect_profile(global_config) -> str | None:
    """Detect which profile matches the current hostname."""
    import socket

    hostname = socket.gethostname()
    profiles: dict = global_config._data.get("profiles", {})

    for name, data in profiles.items():
        hostnames = data.get("hostnames", [])
        if hostname in hostnames:
            return str(name)

        # Also check for partial matches (e.g., "laptop" matches "work-laptop")
        for h in hostnames:
            if h in hostname or hostname in h:
                return str(name)

    return None
