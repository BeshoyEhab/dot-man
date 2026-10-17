"""Export command for exporting dotfiles to portable formats."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click

from .. import ui
from ..constants import REPO_DIR
from .common import (
    AliasedCommand,
    complete_branches,
    error,
    require_init,
    success,
)
from .interface import cli as main


@main.command("export", cls=AliasedCommand, aliases=["exp"])
@click.argument("format", type=click.Choice(["tar", "zip", "json"]))
@click.argument("output", type=click.Path())
@click.option(
    "--branch",
    "-b",
    default=None,
    shell_complete=complete_branches,
    help="Export specific branch (default: current branch)",
)
@click.option(
    "--include-secrets",
    is_flag=True,
    help="Include decrypted secrets in export (WARNING: not secure)",
)
@require_init
def export_cmd(format: str, output: str, branch: str | None, include_secrets: bool):
    """Export dotfiles to a portable archive format.

    Supported formats:
      tar  - Tar archive (.tar.gz)
      zip  - Zip archive (.zip)
      json - JSON manifest with file contents

    Examples:
        dot-man export tar backup.tar.gz           # Export as tar.gz
        dot-man export zip dots.zip                # Export as zip
        dot-man export json manifest.json          # Export as JSON
        dot-man export tar archive.tar.gz --branch work  # Export specific branch
    """
    from ..operations import get_operations

    ops = get_operations()
    current_branch = branch or ops.current_branch

    ui.console.print(f"[dim]Exporting branch: {current_branch}[/dim]")

    if format == "tar":
        _export_archive(ops, current_branch, output, "tar.gz", include_secrets)
    elif format == "zip":
        _export_archive(ops, current_branch, output, "zip", include_secrets)
    elif format == "json":
        _export_json(ops, output, current_branch, include_secrets)


def _export_archive(
    ops, branch: str, output: str, fmt: str, include_secrets: bool
) -> None:
    """Export a branch's committed tree via `git archive`.

    Using ``git archive`` (rather than copying the working directory) means the
    requested ``--branch`` is honored even when it is not currently checked out,
    and only committed content is exported.
    """
    suffix = ".tar.gz" if fmt == "tar.gz" else ".zip"
    output_path = Path(output).expanduser().resolve()

    if not str(output_path).endswith(suffix):
        output_path = output_path.with_suffix(suffix)

    ui.console.print(
        f"[dim]Creating {fmt} archive of branch '{branch}': {output_path}[/dim]"
    )

    if include_secrets:
        ui.console.print(
            "[yellow]Warning: archives contain the branch tree as committed; "
            "encrypted secrets are not decrypted.[/yellow]"
        )

    try:
        ops.git.repo.git.archive(
            f"--format={fmt}",
            f"--output={output_path}",
            "--prefix=dotman-export/",
            branch,
        )
        success(f"Exported branch '{branch}' to {output_path}")
    except Exception as e:
        error(f"Export failed: {e}", exit_code=1)


def _export_json(ops, output: str, branch: str, include_secrets: bool) -> None:
    """Export a JSON manifest describing tracked files."""
    output_path = Path(output).expanduser().resolve()

    if not str(output_path).endswith(".json"):
        output_path = output_path.with_suffix(".json")

    ui.console.print(
        f"[dim]Creating JSON manifest of branch '{branch}': {output_path}[/dim]"
    )

    manifest: dict[str, Any] = {
        "version": "1.0",
        "branch": branch,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        for path_str in section.paths:
            path = Path(path_str).expanduser()
            if not path.exists():
                continue

            file_entry = {
                "section": section_name,
                "local_path": str(path),
                "repo_path": _repo_relative_path(section, path),
            }

            if include_secrets:
                try:
                    file_entry["content"] = path.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                except OSError as e:
                    logging.debug("Could not read %s for export: %s", path, e)

            manifest["files"].append(file_entry)

    try:
        output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if include_secrets:
            # Secret-bearing manifests must not be world-readable.
            output_path.chmod(0o600)
        success(f"Exported {len(manifest['files'])} files to {output_path}")
    except Exception as e:
        error(f"Export failed: {e}", exit_code=1)


def _repo_relative_path(section, path: Path) -> str:
    """Return the path a local file maps to inside the repository."""
    try:
        return str(section.get_repo_path(path, REPO_DIR).relative_to(REPO_DIR))
    except (AttributeError, ValueError):
        return str(path)
