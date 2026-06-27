"""Config command for dot-man CLI."""

import json

import click
from rich.table import Table

from .. import ui
from ..config import GlobalConfig
from ..exceptions import ConfigurationError
from .common import complete_config_keys, error, require_init, success
from .interface import cli as main


@main.group("config")
def config():
    """Manage global configuration."""
    pass


@config.command("defaults")
def config_defaults():
    """Show all configurable defaults with descriptions."""
    table = Table(title="Configurable Defaults", show_header=True)
    table.add_column("Setting", style="cyan", no_wrap=True)
    table.add_column("Default Value", style="green")
    table.add_column("Description")

    defaults = [
        (
            "switch.default_behavior",
            "save",
            "What to do with unsaved changes when switching (save/no-save)",
        ),
        (
            "remote.auto_sync",
            "false",
            "Auto push/pull when switching branches (true/false)",
        ),
        ("remote.url", "", "Remote repository URL for sync"),
        ("defaults.secrets_filter", "true", "Redact secrets when saving (true/false)"),
        (
            "defaults.update_strategy",
            "replace",
            "How to deploy: replace/rename_old/ignore",
        ),
        (
            "defaults.follow_symlinks",
            "false",
            "Follow symlinks when deploying (true/false)",
        ),
        (
            "security.strict_mode",
            "false",
            "Exit with error if secrets detected (true/false)",
        ),
        ("security.audit_on_commit", "true", "Run audit before commits (true/false)"),
        ("backup.max_count", "5", "Maximum number of backups to keep"),
    ]

    for key, default_val, desc in defaults:
        table.add_row(key, str(default_val), desc)

    ui.console.print(table)
    ui.console.print()
    ui.console.print("[bold]Section-level settings (in dot-man.toml):[/bold]")
    ui.console.print("  [cyan]paths[/cyan]           - List of files/dirs to track")
    ui.console.print("  [cyan]secrets_filter[/cyan]  - Enable secret detection")
    ui.console.print("  [cyan]update_strategy[/cyan] - How to handle existing files")
    ui.console.print("  [cyan]pre_deploy[/cyan]      - Command to run before deploying")
    ui.console.print("  [cyan]post_deploy[/cyan]     - Command to run after deploying")
    ui.console.print()
    ui.console.print("[bold]To change a setting:[/bold]")
    ui.console.print("  [cyan]dot-man config set <key> <value>[/cyan]")
    ui.console.print()
    ui.console.print("[dim]Examples:[/dim]")
    ui.console.print("  dot-man config set switch.default_behavior no-save")
    ui.console.print("  dot-man config set remote.auto_sync true")
    ui.console.print("  dot-man config set defaults.update_strategy rename_old")
    ui.console.print()


@config.command("list")
def config_list():
    """List all global configuration values."""
    try:
        cfg = GlobalConfig()
        cfg.load()

        def flatten(d, parent_key="", sep="."):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        flat_data = flatten(cfg._data)

        table = Table(title="Global Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        for k, v in sorted(flat_data.items()):
            table.add_row(k, str(v))

        ui.console.print(table)

    except Exception as e:
        error(f"Failed to list config: {e}")


@config.command("get")
@click.argument("key", shell_complete=complete_config_keys)
def config_get(key: str):
    """Get a configuration value.

    Example: dot-man config get dot-man.editor
    """
    try:
        cfg = GlobalConfig()
        cfg.load()

        parts = key.split(".")
        current = cfg._data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                ui.console.print(f"[red]Key not found:[/red] {key}")
                ui.hint("Run 'dot-man config list' to see all available keys")
                raise SystemExit(1)

        if isinstance(current, dict):
            ui.console.print(f"[dim]Section '{key}' contains:[/dim]")
            ui.console.print(json.dumps(current, indent=2))
        else:
            ui.console.print(str(current))

    except Exception as e:
        error(f"Failed to get config: {e}")


@config.command("set")
@click.argument("key", shell_complete=complete_config_keys)
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Example: dot-man config set dot-man.editor nvim
    """
    try:
        cfg = GlobalConfig()
        try:
            cfg.load()
        except (FileNotFoundError, ConfigurationError):
            cfg.create_default()

        val: bool | str
        if value.lower() == "true":
            val = True
        elif value.lower() == "false":
            val = False
        else:
            val = value

        parts = key.split(".")
        current = cfg._data

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
            if not isinstance(current, dict):
                error(
                    f"Key path conflict: '{'.'.join(parts[: i + 1])}' is not a section"
                )

        current[parts[-1]] = val
        cfg.save()

        success(f"Set '{key}' to '{val}'")
        ui.console.print(f"[dim]  Verified: {key} = {val}[/dim]")

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
    """Create or regenerate the dot-man.toml configuration file."""
    try:
        from ..config import DotManConfig
        from ..constants import DOT_MAN_TOML, REPO_DIR

        config_path = REPO_DIR / DOT_MAN_TOML

        if config_path.exists() and not force:
            if not ui.confirm(
                f"Config file already exists at {config_path}. Overwrite?"
            ):
                ui.console.print("Cancelled.")
                return

        dotman_config = DotManConfig()

        if minimal:
            dotman_config._data = {}
            dotman_config.save()
            ui.console.print(f"Created minimal config at {config_path}")
        else:
            dotman_config.create_default()
            ui.console.print(f"Created config with examples at {config_path}")

        ui.console.print("Tip: Use 'dot-man edit' to open the config in your editor")

    except Exception as e:
        error(f"Failed to create config: {e}")


# Register tutorial subcommand from config_tutorial module
from .config_tutorial import register as _register_tutorial  # noqa: E402

_register_tutorial(config)
