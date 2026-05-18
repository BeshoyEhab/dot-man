"""Rollback command for dot-man — revert to a previous deployment state."""

from pathlib import Path
from typing import cast

import click
from rich.table import Table

from .. import ui
from ..exceptions import DotManError
from .common import error, require_init, success, warn
from .interface import cli as main


@main.command("rollback")
@click.argument("target", required=False)
@click.option(
    "--list",
    "list_only",
    is_flag=True,
    help="List available rollback points without rolling back",
)
@click.option(
    "--steps",
    "-n",
    default=1,
    show_default=True,
    type=int,
    help="Number of commits to roll back (ignored if TARGET given)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
@require_init
def rollback(
    target: str | None,
    list_only: bool,
    steps: int,
    dry_run: bool,
    force: bool,
):
    """Roll back to a previous deployment state.

    dot-man creates an automatic commit before every branch switch. This
    command lets you undo those changes and restore your dotfiles to any
    previous state.

    TARGET can be:
      - A commit SHA   (e.g. abc1234)
      - A tag          (e.g. v1.0)
      - HEAD~N         (e.g. HEAD~2 = two commits ago)

    If TARGET is omitted, rolls back --steps commits (default: 1).

    Examples:
        dot-man rollback                  # undo last auto-save
        dot-man rollback -n 3             # undo last 3 auto-saves
        dot-man rollback abc1234          # go to specific commit
        dot-man rollback v1.0             # go to tag
        dot-man rollback --list           # see available rollback points
        dot-man rollback --dry-run        # preview without changes
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        git = ops.git

        # ── List mode ────────────────────────────────────────────────────────
        if list_only:
            _show_rollback_points(ops)
            return

        # ── Resolve target commit ─────────────────────────────────────────────
        if target:
            resolved_sha = _resolve_target(git, target)
            if not resolved_sha:
                error(f"Cannot resolve target '{target}'", exit_code=1)
            display_target = target
        else:
            if steps < 1:
                error("--steps must be at least 1", exit_code=1)
            resolved_sha = _resolve_target(git, f"HEAD~{steps}")
            if not resolved_sha:
                error(
                    f"Not enough history to go back {steps} commit(s). "
                    "Run 'dot-man rollback --list' to see available points.",
                    exit_code=1,
                )
            display_target = f"HEAD~{steps}"

        assert resolved_sha is not None

        # ── Show what we're rolling back to ───────────────────────────────────
        commit_obj = git.repo.commit(resolved_sha)
        msg_first_line = str(commit_obj.message).strip().split("\n")[0]

        ui.console.print()
        ui.console.print("[bold]Rollback Plan[/bold]")
        ui.console.print()
        ui.console.print(f"  [dim]Target:[/dim]  {display_target}")
        ui.console.print(
            f"  [dim]Commit:[/dim]  [cyan]{resolved_sha[:7]}[/cyan]  {msg_first_line}"
        )
        ui.console.print(
            f"  [dim]Author:[/dim]  {commit_obj.author.name}  "
            f"[dim]{commit_obj.committed_datetime.strftime('%Y-%m-%d %H:%M')}[/dim]"
        )
        ui.console.print()

        # Show which files would change
        try:
            diff_output = git.repo.git.diff(
                "--name-status", f"{resolved_sha}...HEAD"  # type: ignore[arg-type]
            )
            if diff_output.strip():
                ui.console.print("[bold]Files that will change:[/bold]")
                for line in diff_output.strip().splitlines()[:15]:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status_char, fname = parts
                        colour = {"M": "yellow", "A": "green", "D": "red"}.get(
                            status_char[0], "white"
                        )
                        label = {"M": "modified", "A": "added", "D": "deleted"}.get(
                            status_char[0], status_char
                        )
                        ui.console.print(f"  [{colour}]{label:8}[/{colour}]  {fname}")
                if diff_output.strip().count("\n") >= 15:
                    remaining = diff_output.strip().count("\n") - 14
                    ui.console.print(f"  [dim]… and {remaining} more[/dim]")
            else:
                ui.console.print("[dim]No file differences detected.[/dim]")
        except Exception:
            pass

        ui.console.print()

        if dry_run:
            ui.console.print("[dim]Dry run — no changes made.[/dim]")
            return

        # ── Confirm ───────────────────────────────────────────────────────────
        if not force:
            if not ui.confirm(
                "Roll back? This will overwrite your current local dotfiles.",
                default=False,
            ):
                ui.console.print("[dim]Aborted.[/dim]")
                return

        # ── Auto-backup current state ─────────────────────────────────────────
        ui.console.print("[bold]Creating safety backup of current state…[/bold]")
        try:
            paths_to_backup: list[Path] = []
            for section_name in ops.get_sections():
                section = ops.get_section(section_name)
                paths_to_backup.extend(p for p in section.paths if p.exists())

            if paths_to_backup:
                backup_id = ops.backups.create_backup(
                    paths_to_backup, note="pre-rollback"
                )
                if backup_id:
                    ui.console.print(f"  [green]✓[/green] Backup: {backup_id}")
        except Exception as exc:
            warn(f"Backup failed (continuing anyway): {exc}")

        # ── Checkout target commit (detached HEAD) ────────────────────────────
        ui.console.print(f"[bold]Checking out {resolved_sha[:7]}…[/bold]")
        git.checkout_commit(resolved_sha)
        ops.reload_config()

        # ── Deploy files from that commit ─────────────────────────────────────
        ui.console.print("[bold]Deploying rolled-back files…[/bold]")
        deploy_result = ops.deploy_all()
        deployed = deploy_result["deployed"]
        deploy_errors = deploy_result["errors"]

        if deploy_errors:
            for e in deploy_errors:
                if e and str(e).strip():
                    warn(f"  {e}")

        ui.console.print()
        success(f"Rolled back to {display_target} ({resolved_sha[:7]})")
        ui.console.print(f"  [dim]{deployed} file(s) deployed[/dim]")
        ui.console.print()
        ui.console.print(
            "[dim]You are in detached HEAD state. "
            "Run 'dot-man navigate <branch>' to return to a branch.[/dim]"
        )

    except DotManError as exc:
        error(str(exc), exc.exit_code)
    except Exception as exc:
        error(f"Rollback failed: {exc}")


def _show_rollback_points(ops) -> None:
    """Display the last N commits as rollback points."""
    commits = ops.git.get_commits_detailed(count=20)

    if not commits:
        ui.console.print("[dim]No commit history found.[/dim]")
        return

    table = Table(title="Available Rollback Points", show_header=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("SHA", style="cyan", width=8)
    table.add_column("Date", style="dim", width=16)
    table.add_column("Message")
    table.add_column("Files", style="dim", width=6)

    for i, commit in enumerate(commits):
        files_changed = len(commit.get("files", []))
        if commit.get("files_more"):
            files_changed += commit["files_more"]

        tags = commit.get("tags", [])
        msg = commit["message"]
        if tags:
            msg += f"  [green]🏷 {', '.join(tags)}[/green]"

        table.add_row(
            f"~{i}" if i > 0 else "HEAD",
            commit["sha"],
            commit.get("relative_date", commit.get("date", ""))[:15],
            msg[:60],
            str(files_changed) if files_changed else "—",
        )

    ui.console.print()
    ui.console.print(table)
    ui.console.print()
    ui.console.print(
        "[dim]Usage: dot-man rollback <sha>  or  dot-man rollback -n <steps>[/dim]"
    )


def _resolve_target(git, target: str) -> str | None:
    """Resolve a target string to a full commit SHA."""
    try:
        commit = git.repo.commit(target)
        return cast(str, commit.hexsha)
    except Exception:
        return None
