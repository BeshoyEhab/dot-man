"""CLI Interface definition.

This module defines the main Click group to avoid circular imports
when subcommands need to decorate themselves with @main.command().
"""

import click
import logging
from .. import __version__
from .common import DotManGroup
from .. import ui
from ..constants import DOT_MAN_DIR


@click.group(cls=DotManGroup)
@click.version_option(version=__version__, prog_name="dot-man")
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.pass_context
def cli(ctx, debug: bool):
    """dot-man: The Dotfile Manager for Professionals."""
    # Ensure config dir exists for logs
    if not DOT_MAN_DIR.exists():
        try:
            DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass # Init command will handle main creation

    log_file = DOT_MAN_DIR / "dot-man.log"
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure logging
    logging.basicConfig(
        filename=str(log_file),
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode='a'
    )
    if debug:
         ui.console.print("[dim]Debug logging enabled[/dim]")
    
    # Store debug flag in context if needed
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
