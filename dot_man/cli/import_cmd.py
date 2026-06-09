"""Import command for migrating from other dotfile managers."""

import shutil
from pathlib import Path

import click

from .. import ui
from ..core import GitManager
from .common import AliasedCommand, error, require_init, warn
from .interface import cli as main


@main.command("import", cls=AliasedCommand, aliases=["imp"])
@click.argument("source", type=click.Choice(["chezmoi", "yadm", "stow", "all"]))
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=None,
    help="Custom source path (default: auto-detect)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be imported without importing",
)
@require_init
def import_cmd(source: str, path: str | None, dry_run: bool):
    """Import dotfiles from other dotfile managers.

    Supported sources:
      chezmoi   - Import from chezmoi managed dotfiles
      yadm      - Import from yadm managed dotfiles
      stow      - Import from GNU Stow packages
      all       - Auto-detect and import from any supported source

    Examples:
        dot-man import chezmoi           # Import from chezmoi
        dot-man import yadm              # Import from yadm
        dot-man import stow               # Import from Stow packages
        dot-man import all --dry-run      # Auto-detect and preview
    """
    git = GitManager()

    if source == "all":
        _import_all(path, dry_run, git)
    elif source == "chezmoi":
        _import_chezmoi(path, dry_run, git)
    elif source == "yadm":
        _import_yadm(path, dry_run, git)
    elif source == "stow":
        _import_stow(path, dry_run, git)


def _import_all(custom_path: str | None, dry_run: bool, git: GitManager):
    """Auto-detect and import from any supported source."""
    sources_found = []

    chezmoi_path = _detect_chezmoi()
    if chezmoi_path:
        sources_found.append(("chezmoi", chezmoi_path))

    yadm_path = _detect_yadm()
    if yadm_path:
        sources_found.append(("yadm", yadm_path))

    stow_path = _detect_stow()
    if stow_path:
        sources_found.append(("stow", stow_path))

    if not sources_found:
        error(
            "No dotfile manager sources detected. Use --path to specify a custom path.",
            exit_code=1,
        )

    ui.console.print("[bold]Detected dotfile sources:[/bold]")
    for src, src_path in sources_found:
        ui.console.print(f"  • {src}: {src_path}")

    if dry_run:
        ui.console.print("\n[dim]Dry-run mode - no changes will be made[/dim]")
        return

    for src, src_path in sources_found:
        ui.console.print(f"\n[bold]Importing from {src}...[/bold]")
        if src == "chezmoi":
            _import_chezmoi(src_path, False, git)
        elif src == "yadm":
            _import_yadm(src_path, False, git)
        elif src == "stow":
            _import_stow(src_path, False, git)


def _detect_chezmoi() -> str | None:
    """Detect chezmoi source directory."""
    home = Path.home()

    chezmoi_dirs = [
        home / ".local" / "share" / "chezmoi",
        home / ".config" / "chezmoi",
        home / "Library" / "Application Support" / "chezmoi",  # macOS
    ]

    for d in chezmoi_dirs:
        if d.exists() and (d / ".git").exists() or any(d.iterdir()):
            return str(d)

    return None


def _detect_yadm() -> str | None:
    """Detect yadm managed dotfiles."""
    home = Path.home()

    yadm_paths = [
        home / ".yadm.git",
        home / ".config" / "yadm" / "repo.git",
    ]

    for p in yadm_paths:
        if p.exists():
            return str(home / ".yadm")

    return None


def _detect_stow() -> str | None:
    """Detect GNU Stow packages in common locations."""
    home = Path.home()

    stow_locations = [
        home / "dotfiles",
        home / ".dotfiles",
        home / "dotfiles" / ".git",
        home / ".dotfiles" / ".git",
    ]

    for p in stow_locations:
        if p.exists():
            packages = [
                d for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]
            if packages:
                return str(p)

    return None


def _import_chezmoi(source_path: str | None, dry_run: bool, git: GitManager):
    """Import from chezmoi."""
    if source_path is None:
        source_path = _detect_chezmoi()
        if source_path is None:
            error(
                "chezmoi source not found. Install chezmoi first or use --path.",
                exit_code=1,
            )
            return
    if source_path is None:
        error("Source path is required", exit_code=1)
        return
    source = Path(source_path).expanduser().resolve()

    if not source.exists():
        error(f"Source path does not exist: {source}", exit_code=1)

    ui.console.print(f"[dim]Importing from chezmoi: {source}[/dim]")

    files_imported = 0

    for item in source.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(source)

            if rel_path.name.startswith("."):
                dest_path = Path.home() / f".{rel_path.name}"
            else:
                dest_path = Path.home() / ".config" / str(rel_path)

            if source.name == "chezmoi":
                src_path = item
            else:
                src_path = item

            if dry_run:
                ui.console.print(f"  [dim]Would import: {src_path} → {dest_path}[/dim]")
            else:
                try:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, dest_path)
                    files_imported += 1
                except Exception as e:
                    warn(f"Failed to import {src_path}: {e}")

    if dry_run:
        ui.success(f"Would import {files_imported} files from chezmoi")
    else:
        ui.success(f"Imported {files_imported} files from chezmoi")

        commit_msg = "Import dotfiles from chezmoi"
        git.add_all()
        git.commit(commit_msg)


def _import_yadm(source_path: str | None, dry_run: bool, git: GitManager):
    """Import from yadm."""
    if source_path is None:
        source_path = _detect_yadm()
        if source_path is None:
            error(
                "yadm source not found. Install yadm first or use --path.", exit_code=1
            )
            return
    if source_path is None:
        error("Source path is required", exit_code=1)
        return
    source = Path(source_path).expanduser().resolve()

    if not source.exists():
        error(f"Source path does not exist: {source}", exit_code=1)

    ui.console.print(f"[dim]Importing from yadm: {source}[/dim]")

    files_imported = 0

    for item in source.rglob("*"):
        if item.is_file() and not item.name.endswith(".git"):
            rel_path = item.relative_to(source)

            dest_path = Path.home() / rel_path.name
            if dest_path.exists():
                continue

            if dry_run:
                ui.console.print(f"  [dim]Would import: {item} → {dest_path}[/dim]")
            else:
                try:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    files_imported += 1
                except Exception as e:
                    warn(f"Failed to import {item}: {e}")

    if dry_run:
        ui.success(f"Would import {files_imported} files from yadm")
    else:
        ui.success(f"Imported {files_imported} files from yadm")

        commit_msg = "Import dotfiles from yadm"
        git.add_all()
        git.commit(commit_msg)


def _import_stow(source_path: str | None, dry_run: bool, git: GitManager):
    """Import from GNU Stow packages."""
    if source_path is None:
        source_path = _detect_stow()
        if source_path is None:
            error("Stow packages not found. Use --path to specify.", exit_code=1)
            return
    if source_path is None:
        error("Source path is required", exit_code=1)
        return
    source = Path(source_path).expanduser().resolve()

    if not source.exists():
        error(f"Source path does not exist: {source}", exit_code=1)

    ui.console.print(f"[dim]Importing from Stow: {source}[/dim]")

    packages = [
        d for d in source.iterdir() if d.is_dir() and not d.name.startswith(".")
    ]

    if not packages:
        error("No Stow packages found in source directory", exit_code=1)

    ui.console.print(
        f"[dim]Found {len(packages)} packages: {', '.join([p.name for p in packages])}[/dim]"
    )

    files_imported = 0

    for package in packages:
        for item in package.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(package)

                if rel_path.parts[0].startswith("."):
                    dest_path = Path.home() / "/".join(rel_path.parts)
                else:
                    dest_path = (
                        Path.home()
                        / f".{rel_path.parts[0]}"
                        / "/".join(rel_path.parts[1:])
                    )

                if dry_run:
                    ui.console.print(f"  [dim]Would import: {item} → {dest_path}[/dim]")
                else:
                    try:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)
                        files_imported += 1
                    except Exception as e:
                        warn(f"Failed to import {item}: {e}")

    if dry_run:
        ui.success(
            f"Would import {files_imported} files from {len(packages)} Stow packages"
        )
    else:
        ui.success(
            f"Imported {files_imported} files from {len(packages)} Stow packages"
        )

        commit_msg = f"Import dotfiles from {len(packages)} Stow packages"
        git.add_all()
        git.commit(commit_msg)
