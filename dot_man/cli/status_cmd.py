"""Status command for dot-man CLI."""

import json
from itertools import groupby
from pathlib import Path

import click
from rich.panel import Panel
from rich.table import Table

from .. import constants, ui
from ..exceptions import DotManError
from ..secrets import get_custom_scanner
from .common import AliasedCommand, error, handle_exception, require_init, warn
from .interface import cli as main


def _status_summary(status_items: list[dict]) -> dict[str, int]:
    """Tally tracked-file statuses for the summary line."""
    summary = {"modified": 0, "new": 0, "deleted": 0, "identical": 0}
    for item in status_items:
        st = item["status"]
        if st == "MODIFIED":
            summary["modified"] += 1
        elif st == "NEW":
            summary["new"] += 1
        elif st == "DELETED":
            summary["deleted"] += 1
        else:
            summary["identical"] += 1
    return summary


def _render_repo_panel(branch: str, remote: str) -> None:
    """Print the repository info panel (human output only)."""
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="cyan")
    info_table.add_column()
    info_table.add_row("Current Branch:", f"[bold]{branch}[/bold]")
    info_table.add_row("Remote:", remote)
    info_table.add_row("Repository:", str(constants.get_repo_dir()))

    ui.console.print(
        Panel(
            info_table,
            title="[bold]Repository Status[/bold]",
            border_style="blue",
        )
    )
    ui.console.print()


def _render_status_json(
    branch: str, remote_url: str, summary: dict, status_items: list[dict]
) -> None:
    """Emit machine-readable status JSON (stdout stays pure JSON)."""
    sections_list: list[dict] = []
    output = {
        "branch": branch,
        "remote": remote_url,
        "repository": str(constants.get_repo_dir()),
        "sections": sections_list,
        "summary": summary,
    }

    for section_name, group in groupby(status_items, key=lambda x: x["section"]):
        items = list(group)
        section_data = {"name": section_name, "files": []}
        for item in items:
            section_data["files"].append(
                {
                    "path": str(item["local_path"]),
                    "status": item["status"],
                }
            )
        sections_list.append(section_data)

    click.echo(json.dumps(output, indent=2))


def _render_status_table(
    ops,
    status_items: list[dict],
    all_section_names: list[str],
    verbose: bool,
    secrets: bool,
) -> list:
    """Render the tracked-sections table; return any secrets found."""
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

    scanner = get_custom_scanner() if secrets else None
    secrets_found = []

    # Items are already sorted by section iteration order from get_detailed_status
    displayed_sections = 0

    for section_name, group in groupby(status_items, key=lambda x: x["section"]):
        if displayed_sections >= 10:
            file_table.add_row(
                f"[dim]... +{len(all_section_names) - 10} more sections[/dim]",
                "",
                "",
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

            # Shorten path, width-aware, and fall back to an ASCII icon
            # in --plain mode.
            icon = ui.icon(
                "📁" if local_path.is_dir() else "📄",
                "DIR" if local_path.is_dir() else "FILE",
            )
            display_path = str(local_path).replace(str(Path.home()), "~")
            display_path = ui.truncate_text(
                display_path, max(24, ui.console.width - 40)
            )

            details = ""
            if file_status == "MODIFIED" and verbose:
                details = "Content differs"

            # Check for secrets
            secret_indicator = ""
            if (
                secrets
                and scanner is not None
                and local_path.exists()
                and local_path.is_file()
            ):
                matches = list(scanner.scan_file(local_path))
                if matches:
                    secret_indicator = f" [red]{ui.icon('🔒', '[locked]')}[/red]"
                    secrets_found.extend(matches)

            file_table.add_row(
                f"  {icon} {display_path}{secret_indicator}",
                f"[{color}]{file_status}[/{color}]",
                details,
            )
            path_count += 1

        displayed_sections += 1

    ui.console.print(file_table)
    return secrets_found


@main.command("status", cls=AliasedCommand)
@click.option("-v", "--verbose", is_flag=True, help="Show detailed information")
@click.option("--secrets", is_flag=True, help="Highlight files with detected secrets")
@click.option(
    "--json", "json_output", is_flag=True, help="Output as JSON for scripting"
)
@require_init
def status(verbose: bool, secrets: bool, json_output: bool):
    """Display current repository status.

    Shows the current branch, tracked files, and any pending changes
    that would be saved on the next switch.
    """
    # Honour the root group's global --json as well as the local flag.
    json_output = json_output or ui.json_mode()
    try:
        from ..operations import get_operations

        ops = get_operations()

        branch = ops.current_branch

        # Human-readable repository info panel. Machine-readable (--json)
        # output must stay pure JSON on stdout, so it is skipped there.
        if not json_output:
            remote = ops.global_config.remote_url or "[dim]Not configured[/dim]"
            _render_repo_panel(branch, remote)

        # Get detailed status once (Optimized single pass)
        status_items = list(ops.get_detailed_status())
        summary = _status_summary(status_items)

        all_section_names = ops.get_sections()
        if not all_section_names:
            if json_output:
                click.echo(json.dumps({"sections": [], "summary": summary}))
            else:
                ui.console.print(
                    "[dim]No sections tracked. Run 'dot-man add <path>' to add files.[/dim]"
                )
            return

        if json_output:
            _render_status_json(
                branch, ops.global_config.remote_url or "", summary, status_items
            )
            return

        secrets_found = _render_status_table(
            ops, status_items, all_section_names, verbose, secrets
        )

        # Summary
        ui.console.print()
        ui.console.print(
            f"[dim]Summary: {summary['modified']} modified, {summary['new']} new, {summary['deleted']} deleted, {summary['identical']} identical[/dim]"
        )

        # Secrets warning
        if secrets_found:
            ui.console.print()
            warn(
                f"{len(secrets_found)} potential secrets detected. Run 'dot-man audit' for details."
            )

        # Git status
        if ops.git.is_dirty():
            ui.console.print()
            ui.console.print("[yellow]Repository has uncommitted changes.[/yellow]")

        # Next steps, only when there is something to act on
        pending = summary["modified"] + summary["new"] + summary["deleted"]
        if pending:
            ui.next_steps(
                [
                    'Run [cyan]dot-man save "message"[/cyan] to snapshot your changes',
                    "Run [cyan]dot-man navigate <branch>[/cyan] to save and switch",
                ]
            )

    except DotManError as e:
        error(str(e), e.exit_code)
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())
    except Exception as e:
        handle_exception(e, "Status check")
