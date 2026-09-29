"""Add command for dot-man CLI."""

from pathlib import Path

import click

from .. import ui
from ..config import DotManConfig, GlobalConfig
from ..config_detector import get_auto_hooks_for_config
from ..constants import REPO_DIR
from ..exceptions import DotManError
from ..files import copy_directory, copy_file
from ..hooks import run_hook
from .common import (
    AliasedCommand,
    error,
    get_secret_handler,
    require_init,
    success,
    warn,
)
from .interface import cli as main


@main.command("add", cls=AliasedCommand, aliases=["add"])
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
        raw_path = Path(path).expanduser()

        # Warn if path is a symlink
        if raw_path.is_symlink():
            from ..interactive import prompt_symlink_action

            action = prompt_symlink_action(raw_path)
            if action in ("ignore", "all_ignore"):
                warn(f"Skipped symlink: {raw_path}")
                return

        local_path = raw_path.resolve()

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
        if not run_hook(
            "add", "pre", env={"DOTMAN_SECTION": section, "DOTMAN_PATH": path_str}
        ):
            warn("pre_add hook failed (continuing)")
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
        # Auto-apply detected hooks for gaps the user didn't specify,
        # mirroring the init wizard.
        auto_hooks = get_auto_hooks_for_config(section, [path_str])
        if auto_hooks:
            user_hooks = {"post_deploy": post_deploy, "pre_deploy": pre_deploy}
            detected = {
                kind: cmd
                for kind, cmd in auto_hooks.items()
                if cmd and not user_hooks.get(kind)
            }
            if detected:
                for hook_type, hook_cmd in detected.items():
                    ui.console.print(
                        f"  [dim]Auto-detected {hook_type} hook: {hook_cmd}[/dim]"
                    )
                dotman_config.update_section(section, **detected)
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

        if not run_hook(
            "add", "post", env={"DOTMAN_SECTION": section, "DOTMAN_PATH": path_str}
        ):
            warn("post_add hook failed (continuing)")

        ui.next_steps(
            [
                "Run [cyan]dot-man status[/cyan] to verify your tracked files",
                "Run [cyan]dot-man navigate work[/cyan] to start a work configuration",
            ]
        )

    except DotManError as e:
        error(str(e), e.exit_code)
    except Exception as e:
        error(f"Failed to add: {e}")
