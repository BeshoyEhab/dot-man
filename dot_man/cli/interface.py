"""CLI Interface definition.

This module defines the main Click group to avoid circular imports
when subcommands need to decorate themselves with @main.command().
"""

import logging

import click

from .. import __version__, ui
from ..constants import DOT_MAN_DIR
from .common import DotManGroup


@click.group(cls=DotManGroup)
@click.version_option(version=__version__, prog_name="dot-man")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output on console")
@click.option("--debug", is_flag=True, help="Enable debug logging to file")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--yes", "-y", is_flag=True, help="Assume yes for all prompts")
@click.option(
    "--no-input",
    "no_input",
    is_flag=True,
    help="Never prompt; fail when input would be required",
)
@click.option("--no-color", "no_color", is_flag=True, help="Disable coloured output")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Emit machine-readable JSON where supported",
)
@click.option(
    "--no-onboarding",
    is_flag=True,
    help="Skip the first-run onboarding tutorial",
)
@click.pass_context
def cli(
    ctx,
    verbose: bool,
    debug: bool,
    quiet: bool,
    yes: bool,
    no_input: bool,
    no_color: bool,
    json_output: bool,
    no_onboarding: bool,
):
    """dot-man: The Dotfile Manager for Professionals.

    Git-powered branching for your dotfiles. Switch between configurations
    (work, personal, minimal, server) on the fly — each branch is a
    complete dotfile environment.

    Supports deploy_method = "symlink" for edit-in-place workflows,
    auto-detected post-deploy hooks, and import from chezmoi, yadm,
    and GNU Stow.
    """
    # Ensure config dir exists for logs
    if not DOT_MAN_DIR.exists():
        try:
            DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Init command will handle main creation

    log_file = DOT_MAN_DIR / "dot-man.log"
    level = logging.DEBUG if (debug or verbose) else logging.INFO

    # Configure file logging
    logging.basicConfig(
        filename=str(log_file),
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filemode="a",
    )

    # If verbose, also log to console
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter("[dim]%(levelname)s:[/dim] %(message)s")
        )
        logging.getLogger().addHandler(console_handler)
        ui.console.print("[dim]Verbose mode enabled[/dim]")
    elif debug:
        ui.console.print("[dim]Debug logging enabled (see dot-man.log)[/dim]")

    # Store flags in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["QUIET"] = quiet
    ctx.obj["YES"] = yes
    ctx.obj["NO_INPUT"] = no_input
    ctx.obj["NO_COLOR"] = no_color
    ctx.obj["JSON"] = json_output

    # Apply the global output/confirmation flags process-wide.
    ui.configure(
        quiet=quiet,
        yes=yes,
        no_input=no_input,
        no_color=no_color,
        json=json_output,
    )
