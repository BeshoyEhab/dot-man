"""Completions command for dot-man CLI."""

import shutil
from pathlib import Path

import click

from .interface import cli as main


@main.command("completions")
@click.option(
    "--shell",
    type=click.Choice(["bash", "zsh", "fish", "all"]),
    default="all",
    help="Shell to install completions for",
)
@click.option(
    "--source-only",
    is_flag=True,
    help="Only print source command, don't install",
)
def completions(shell: str, source_only: bool):
    """Install or show shell completions for dot-man.

    Examples:
        dot-man completions                  # Install all completions
        dot-man completions --shell bash      # Install bash only
        dot-man completions --source-only     # Show source commands
    """
    home = Path.home()
    completions_dir = home / ".local" / "share" / "bash-completion" / "completions"
    zsh_compdir = home / ".local" / "share" / "zsh" / "site-functions"
    fish_compdir = home / ".config" / "fish" / "completions"

    try:
        from dot_man import completions as completions_pkg
    except ImportError:
        click.echo("Error: Completions not found. Is dot-man installed?", err=True)
        return

    completions_path = Path(completions_pkg.__file__).parent

    def do_bash():
        if shell not in ("bash", "all"):
            return
        bash_src = completions_path / "dot-man.bash"
        bash_dest = completions_dir / "dot-man"
        if source_only:
            click.echo("# Add to ~/.bashrc or ~/.profile:")
            click.echo(f"source {bash_src}")
        else:
            completions_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(bash_src, bash_dest)
            click.echo(f"✓ Installed bash completion to {bash_dest}")

    def do_zsh():
        if shell not in ("zsh", "all"):
            return
        zsh_src = completions_path / "_dot-man.zsh"
        zsh_dest = zsh_compdir / "_dot-man"
        if source_only:
            click.echo("# Add to ~/.zshrc:")
            click.echo(f"source {zsh_src}")
        else:
            zsh_compdir.mkdir(parents=True, exist_ok=True)
            shutil.copy(zsh_src, zsh_dest)
            click.echo(f"✓ Installed zsh completion to {zsh_dest}")

    def do_fish():
        if shell not in ("fish", "all"):
            return
        fish_src = completions_path / "dot-man.fish"
        fish_dest = fish_compdir / "dot-man.fish"
        if source_only:
            click.echo("# Add to ~/.config/fish/config.fish:")
            click.echo(f"source {fish_src}")
        else:
            fish_compdir.mkdir(parents=True, exist_ok=True)
            shutil.copy(fish_src, fish_dest)
            click.echo(f"✓ Installed fish completion to {fish_dest}")

    do_bash()
    do_zsh()
    do_fish()

    if not source_only:
        click.echo(
            "\nRestart your shell or source your shell config to enable completions."
        )


def run_install() -> None:
    """Entry point for pip install hook - silently installs completions."""
    try:
        from dot_man import completions as completions_pkg
    except ImportError:
        return

    home = Path.home()
    completions_path = Path(completions_pkg.__file__).parent

    # Bash
    bash_dest = (
        home / ".local" / "share" / "bash-completion" / "completions" / "dot-man"
    )
    if not bash_dest.exists():
        bash_src = completions_path / "dot-man.bash"
        if bash_src.exists():
            bash_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(bash_src, bash_dest)

    # Zsh
    zsh_dest = home / ".local" / "share" / "zsh" / "site-functions" / "_dot-man"
    if not zsh_dest.exists():
        zsh_src = completions_path / "_dot-man.zsh"
        if zsh_src.exists():
            zsh_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(zsh_src, zsh_dest)

    # Fish
    fish_dest = home / ".config" / "fish" / "completions" / "dot-man.fish"
    if not fish_dest.exists():
        fish_src = completions_path / "dot-man.fish"
        if fish_src.exists():
            fish_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(fish_src, fish_dest)
