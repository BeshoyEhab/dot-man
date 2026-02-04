"""Status command for dot-man CLI."""

from pathlib import Path

import click
from rich.table import Table
from rich.panel import Panel

from .. import ui
from ..constants import REPO_DIR
from ..exceptions import DotManError
from ..secrets import SecretScanner
from .interface import cli as main
from .common import error, require_init, handle_exception


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
        from ..operations import get_operations

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

        ui.console.print(
            Panel(
                info_table, title="[bold]Repository Status[/bold]", border_style="blue"
            )
        )
        ui.console.print()

        # Get detailed status once (Optimized single pass)
        status_items = list(ops.get_detailed_status())

        # Calculate summary from items
        summary = {
            "modified": 0,
            "new": 0,
            "deleted": 0,
            "identical": 0
        }

        section_names_set = set()
        for item in status_items:
            section_names_set.add(item["section"])
            st = item["status"]
            if st == "MODIFIED":
                summary["modified"] += 1
            elif st == "NEW":
                summary["new"] += 1
            elif st == "DELETED":
                summary["deleted"] += 1
            else:
                summary["identical"] += 1

        all_section_names = ops.get_sections()
        if not all_section_names:
            ui.console.print(
                "[dim]No sections tracked. Run 'dot-man add <path>' to add files.[/dim]"
            )
            return

        file_table = Table(title=f"Tracked Sections ({len(all_section_names)})")
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

        from itertools import groupby

        # Items are already sorted by section iteration order from get_detailed_status
        displayed_sections = 0

        for section_name, group in groupby(status_items, key=lambda x: x["section"]):
            if displayed_sections >= 10:
                file_table.add_row(
                    f"[dim]... +{len(all_section_names) - 10} more sections[/dim]", "", ""
                )
                break

            items = list(group)
            # Retrieve section object for metadata like 'inherits'
            # Note: This is a fast lookup
            section = ops.get_section(section_name)

            # Section header
            file_table.add_row(
                f"[bold magenta][{section_name}][/bold magenta]",
                "",
                f"inherits: {', '.join(section.inherits)}" if section.inherits else "",
            )

            # Files under section
            path_count = 0
            for item in items:
                if path_count >= 5:  # Limit per section
                    file_table.add_row("  [dim]... more files[/dim]", "", "")
                    break

                local_path = item["local_path"]
                file_status = item["status"]

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

            displayed_sections += 1

        ui.console.print(file_table)

        # Summary
        ui.console.print()
        ui.console.print(
            f"[dim]Summary: {summary['modified']} modified, {summary['new']} new, {summary['deleted']} deleted, {summary['identical']} identical[/dim]"
        )

        # Secrets warning
        if secrets_found:
            ui.console.print()
            from .common import warn
            warn(
                f"{len(secrets_found)} potential secrets detected. Run 'dot-man audit' for details."
            )

        # Git status
        if ops.git.is_dirty():
            ui.console.print()
            ui.console.print("[yellow]Repository has uncommitted changes.[/yellow]")

    except DotManError as e:
        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Status check")
