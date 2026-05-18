"""Export command for exporting dotfiles to portable formats."""

import json
import os
import tarfile
import zipfile
from pathlib import Path

import click

from .. import ui
from ..constants import REPO_DIR
from .common import AliasedCommand, error, require_init, success
from .interface import cli as main


@main.command("export", cls=AliasedCommand, aliases=["exp"])
@click.argument("format", type=click.Choice(["tar", "zip", "json"]))
@click.argument("output", type=click.Path())
@click.option(
    "--branch",
    "-b",
    default=None,
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
        _export_tar(output, current_branch, include_secrets)
    elif format == "zip":
        _export_zip(output, current_branch, include_secrets)
    elif format == "json":
        _export_json(output, current_branch, include_secrets)


def _export_tar(output: str, branch: str, include_secrets: bool):
    """Export to tar.gz archive."""
    output_path = Path(output).expanduser().resolve()

    if not str(output_path).endswith((".tar.gz", ".tgz")):
        output_path = output_path.with_suffix(".tar.gz")

    ui.console.print(f"[dim]Creating tar archive: {output_path}[/dim]")

    try:
        with tarfile.open(output_path, "w:gz") as tar:
            tar.add(REPO_DIR, arcname="dotman-export")

        success(f"Exported to {output_path}")
    except Exception as e:
        error(f"Export failed: {e}", exit_code=1)


def _export_zip(output: str, branch: str, include_secrets: bool):
    """Export to zip archive."""
    output_path = Path(output).expanduser().resolve()

    if not str(output_path).endswith(".zip"):
        output_path = output_path.with_suffix(".zip")

    ui.console.print(f"[dim]Creating zip archive: {output_path}[/dim]")

    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(REPO_DIR):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(REPO_DIR)
                    zipf.write(file_path, arcname)

        success(f"Exported to {output_path}")
    except Exception as e:
        error(f"Export failed: {e}", exit_code=1)


def _export_json(output: str, branch: str, include_secrets: bool):
    """Export to JSON manifest."""
    output_path = Path(output).expanduser().resolve()

    if not str(output_path).endswith(".json"):
        output_path = output_path.with_suffix(".json")

    ui.console.print(f"[dim]Creating JSON manifest: {output_path}[/dim]")

    from ..operations import get_operations

    ops = get_operations()
    manifest: dict = {
        "version": "1.0",
        "branch": branch,
        "exported_at": str(Path().home()),
        "files": [],  # type: ignore[list-item]
    }

    for section_name in ops.get_sections():
        section = ops.get_section(section_name)
        for path_str in section.paths:
            path = Path(path_str).expanduser()
            if path.exists():
                file_entry = {
                    "section": section_name,
                    "local_path": str(path),
                    "repo_path": str(path_str),
                }

                if include_secrets:
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            file_entry["content"] = f.read()
                    except Exception:
                        pass

                manifest["files"].append(file_entry)

    try:
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        success(f"Exported {len(manifest['files'])} files to {output_path}")
    except Exception as e:
        error(f"Export failed: {e}", exit_code=1)
