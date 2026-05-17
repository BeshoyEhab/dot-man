"""Discover command for auto-detecting existing dotfiles."""

import click

from .. import ui
from ..config_detector import ConfigDetector
from .common import require_init
from .interface import cli as main


@main.command("discover")
@click.option(
    "--include-extended/--no-extended",
    default=True,
    help="Include extended configs (VS Code, Sublime, etc.)",
)
@click.option(
    "--add",
    is_flag=True,
    help="Automatically add detected configs to dot-man.toml",
)
@require_init
def discover_cmd(include_extended: bool, add: bool):
    """Auto-detect existing dotfiles on your system.

    Scans common locations for popular configuration files and directories,
    then offers to add them to dot-man for tracking.

    Examples:
        dot-man discover                  # Show all detected dotfiles
        dot-man discover --no-extended    # Only common configs
        dot-man discover --add            # Auto-add to config
    """
    ui.console.print("[bold]🔍 Scanning for dotfiles...[/bold]")
    ui.console.print()

    detected = ConfigDetector.detect_popular_configs(include_extended=include_extended)
    detected.extend(ConfigDetector.detect_quickshell_configs())

    if not detected:
        ui.console.print("[yellow]No dotfiles detected on this system.[/yellow]")
        return

    ui.console.print(f"[bold]Found {len(detected)} configurations:[/bold]")
    ui.console.print()

    for config in detected:
        exists = "✓" if config["paths"] else "?"
        hook = f" ({config['default_hook']})" if config["default_hook"] else ""
        ui.console.print(f"  [{exists}] {config['display_name']}")
        ui.console.print(f"       [{config['section_name']}]{hook}")
        for path in config["paths"]:
            ui.console.print(f"       {path}")

    if add:
        _add_detected_configs(detected)
    else:
        ui.console.print()
        ui.console.print(
            "[dim]Tip: Use --add to automatically add these to dot-man.toml[/dim]"
        )


def _add_detected_configs(detected: list):
    """Add detected configs to dot-man.toml."""
    from ..dotman_config import DotManConfig
    from ..operations import get_operations

    config = DotManConfig()
    ops = get_operations()
    added_count = 0

    for conf in detected:
        section_name = conf["section_name"]

        if section_name in ops.get_sections():
            continue

        try:
            config.add_section(
                name=section_name,
                paths=conf["paths"],
            )

            if conf["default_hook"]:
                config.update_section(
                    section_name,
                    post_deploy=conf["default_hook"],
                )

            added_count += 1
            ui.console.print(f"  [green]✓[/green] Added: {section_name}")
        except Exception as e:
            ui.console.print(f"  [red]✗[/red] Failed to add {section_name}: {e}")

    config.save()

    if added_count > 0:
        ui.console.print()
        ui.success(f"Added {added_count} sections to dot-man.toml")
        ui.console.print("[dim]Run 'dot-man status' to see your tracked files[/dim]")
    else:
        ui.console.print(
            "[dim]No new sections to add (already tracked or duplicates)[/dim]"
        )
