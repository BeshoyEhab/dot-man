"""Template variables command for dot-man CLI."""

import os
import platform
import socket
from pathlib import Path

import click

from .. import ui
from .common import complete_template_keys, error, success, warn
from .interface import cli as main

# System variables that can be auto-detected
SYSTEM_VARS = {
    "HOSTNAME": lambda: socket.gethostname(),
    "USER": lambda: os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
    "HOME": lambda: str(Path.home()),
    "OS": lambda: platform.system(),
    "OS_VERSION": lambda: platform.version(),
    "ARCH": lambda: platform.machine(),
    "SHELL": lambda: os.environ.get("SHELL", "/bin/sh"),
    "EDITOR": lambda: os.environ.get("EDITOR", os.environ.get("VISUAL", "vim")),
    "EMAIL": lambda: None,  # Requires git config
    "DOMAIN": lambda: socket.getfqdn(),
}


@main.group()
def template():
    """Manage template variables for dynamic configuration.

    Template variables allow you to use placeholders in your dotfiles
    that get replaced with actual values when deploying.

    Examples:
        dot-man template set HOSTNAME $(hostname)
        dot-man template list
        dot-man template system    # Show auto-detected system variables
    """
    pass


@template.command("set")
@click.argument("key", shell_complete=complete_template_keys)
@click.argument("value", required=False)
@click.option("--from-env", help="Get value from environment variable")
def template_set(key: str, value: str | None, from_env: str | None):
    """Set a template variable.

    Examples:
        dot-man template set MACHINE work-laptop
        dot-man template set EMAIL user@example.com
        dot-man template set KEY --from-env MY_API_KEY
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        # Determine the value
        if from_env:
            actual_value = os.environ.get(from_env)
            if not actual_value:
                error(f"Environment variable '{from_env}' is not set", exit_code=1)
            value = actual_value
        elif value is None:
            error("Value or --from-env required", exit_code=1)

        # Get current templates or initialize
        templates = getattr(global_config, "_data", {}).get("templates", {})
        if not isinstance(templates, dict):
            templates = {}

        templates[key] = value
        global_config._data["templates"] = templates
        global_config.save()

        success(f"Template '{key}' = '{value}'")
        ui.hint(
            f"Use [cyan]{{{{{key}}}}}[/cyan] in your dotfiles to reference this value"
        )

    except Exception as e:
        error(str(e))


@template.command("get")
@click.argument("key", shell_complete=complete_template_keys)
def template_get(key: str):
    """Get a template variable value.

    Example:
        dot-man template get HOSTNAME
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        templates = getattr(global_config, "_data", {}).get("templates", {})

        if key in templates:
            ui.console.print(f"{key} = {templates[key]}")
        else:
            warn(f"Template '{key}' not found")

    except Exception as e:
        error(str(e))


@template.command("list")
def template_list():
    """List all template variables.

    Shows both user-defined templates and available system variables.
    """
    try:
        from rich.table import Table

        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config

        # Get user templates
        templates = getattr(global_config, "_data", {}).get("templates", {})

        table = Table(title="User-Defined Templates")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")

        if templates:
            for key, value in sorted(templates.items()):
                table.add_row(key, str(value))
        else:
            table.add_row(
                "[dim]No templates defined[/dim]",
                "[dim]Use 'dot-man template set'[/dim]",
            )

        ui.console.print(table)
        ui.console.print()
        ui.console.print("[bold]System Variables (auto-detected):[/bold]")
        ui.console.print("[dim]Use {{VARIABLE_NAME}} in your dotfiles[/dim]")
        ui.console.print()

        # Show system variables
        sys_table = Table()
        sys_table.add_column("Variable", style="cyan")
        sys_table.add_column("Current Value", style="green")

        for var_name in sorted(SYSTEM_VARS.keys()):
            try:
                val = SYSTEM_VARS[var_name]()
                display = str(val) if val else "[not set]"
            except Exception:
                display = "[error]"
            sys_table.add_row(f"{{{{{var_name}}}}}", display)

        ui.console.print(sys_table)

    except Exception as e:
        error(str(e))


@template.command("system")
def template_system():
    """Show auto-detected system variables.

    These variables are available automatically and can be used
    with the {{VARIABLE_NAME}} syntax in your dotfiles.
    """
    try:
        from rich.table import Table

        table = Table(title="System Variables")
        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Source", style="dim")

        for var_name in sorted(SYSTEM_VARS.keys()):
            source = "auto-detected"
            try:
                val = SYSTEM_VARS[var_name]()
                if val is None:
                    value = "[not set]"
                    source = "requires config"
                else:
                    value = str(val)
            except Exception as e:
                value = f"[error: {e}]"
                source = "failed"

            table.add_row(f"{{{{{var_name}}}}}", value, source)

        ui.console.print(table)
        ui.console.print()
        ui.console.print(
            "[dim]Tip: Use {{HOSTNAME}}, {{USER}}, {{SHELL}} etc. in your dotfiles[/dim]"
        )

    except Exception as e:
        error(str(e))


@template.command("substitute")
@click.argument("content")
def template_substitute(content: str):
    """Test template substitution.

    Example:
        dot-man template substitute "My shell is {{SHELL}} on {{HOSTNAME}}"
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        global_config = ops.global_config
        templates = getattr(global_config, "_data", {}).get("templates", {})

        result = content

        # Replace user-defined templates
        for key, value in templates.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

        # Replace system variables
        for var_name, getter in SYSTEM_VARS.items():
            placeholder = f"{{{{{var_name}}}}}"
            try:
                val = getter()
                if val:
                    result = result.replace(placeholder, str(val))
            except Exception:
                pass

        ui.console.print(result)

    except Exception as e:
        error(str(e))
