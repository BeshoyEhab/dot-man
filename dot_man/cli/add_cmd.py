"""Add command for dot-man CLI."""

# TODO: Move add command implementation here
# For now, this is a placeholder for the module structure.
# The actual command is still in the main cli.py

from pathlib import Path

import click

from .. import ui
from ..constants import REPO_DIR
from ..config import GlobalConfig, DotManConfig
from ..files import copy_file, copy_directory
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, warn, require_init, get_secret_handler


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--section", "-s", help="Section name (default: auto-generated from path)"
)
@click.option(
    "--repo-base", "-r", help="Base directory in repo (default: section name)"
)
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="Patterns to exclude (can be specified multiple times)",
)
@click.option(
    "--include",
    "-i",
    multiple=True,
    help="Patterns to include (can be specified multiple times)",
)
@click.option(
    "--inherits",
    "-t",
    multiple=True,
    help="Templates to inherit from (can be specified multiple times)",
)
@click.option("--post-deploy", help="Command to run after deploying")
@click.option("--pre-deploy", help="Command to run before deploying")
@require_init
def add(
    path: str,
    section: str | None,
    repo_base: str | None,
    exclude: tuple,
    include: tuple,
    inherits: tuple,
    post_deploy: str | None,
    pre_deploy: str | None,
):
    """Add a file or directory to be tracked.

    Adds the specified path to the dot-man.toml configuration and copies
    the content to the repository.

    Examples:
        dot-man add ~/.bashrc
        dot-man add ~/.config/fish --section fish --exclude "*.log"
        dot-man add ~/.config/hypr --inherits linux-gui --post-deploy "hyprctl reload"
    """
    try:
        local_path = Path(path).expanduser().resolve()

        # Auto-generate section name if not provided
        if not section:
            if local_path.is_dir() and str(local_path).startswith(
                str(Path.home() / ".config")
            ):
                section = local_path.name
            else:
                section = local_path.stem or local_path.name

        repo_base = repo_base or section

        # Load config
        global_config = GlobalConfig()
        global_config.load()

        dotman_config = DotManConfig(global_config=global_config)
        try:
            dotman_config.load()
        except (FileNotFoundError, DotManError):
            dotman_config.create_default()
            dotman_config.load()

        # Check for duplicates
        existing_sections = dotman_config.get_section_names()
        if section in existing_sections:
            error(
                f"Section '{section}' already exists. Use a different --section name."
            )

        # Convert to home-relative path for config
        path_str = str(local_path)
        home = str(Path.home())
        if path_str.startswith(home):
            path_str = path_str.replace(home, "~", 1)

        # Add section to config
        dotman_config.add_section(
            name=section,
            paths=[path_str],
            repo_base=repo_base,
            exclude=list(exclude) if exclude else None,
            include=list(include) if include else None,
            inherits=list(inherits) if inherits else None,
            post_deploy=post_deploy,
            pre_deploy=pre_deploy,
        )
        dotman_config.save()

        # Copy content to repo
        repo_dest = REPO_DIR / repo_base

        if local_path.is_file():
            repo_dest = repo_dest / local_path.name
            try:
                secret_handler = get_secret_handler()
                success_copy, secrets = copy_file(
                    local_path,
                    repo_dest,
                    filter_secrets_enabled=True,
                    secret_handler=secret_handler,
                )
                if success_copy:
                    success(f"Added file: {local_path}")
                    ui.console.print(f"  Section: [cyan][{section}][/cyan]")
                    ui.console.print(f"  Repo path: [dim]{repo_dest}[/dim]")
                    if secrets:
                        warn(f"{len(secrets)} secrets were redacted")
                else:
                    error(f"Failed to copy file: {local_path}")
            except (FileNotFoundError, OSError) as e:
                error(f"Failed to access file {local_path}: {e}")
            except Exception as e:
                error(f"Error copying file {local_path}: {e}")
        else:
            secret_handler = get_secret_handler()
            copied, failed, secrets = copy_directory(
                local_path,
                repo_dest,
                filter_secrets_enabled=True,
                exclude_patterns=list(exclude) if exclude else None,
                include_patterns=list(include) if include else None,
                secret_handler=secret_handler,
            )
            success(f"Added directory: {local_path}")
            ui.console.print(f"  Section: [cyan][{section}][/cyan]")
            ui.console.print(f"  Repo path: [dim]{repo_dest}[/dim]")
            ui.console.print(f"  Files: {copied} copied, {failed} failed")
            if secrets:
                warn(f"{len(secrets)} secrets were redacted")

        if inherits:
            ui.console.print(f"  Inherits: {', '.join(inherits)}")

        ui.console.print()
        ui.console.print("[dim]Run 'dot-man switch <branch>' to commit changes.[/dim]")

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to add: {e}")
