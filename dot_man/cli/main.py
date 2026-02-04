"""Main entry point for dot-man CLI.

This module aggregates all subcommands and exposes the main entry point.
"""

# Import the shared CLI group (interface)
from .interface import cli

# Import all subcommands to register them with the CLI group
from . import (
    init_cmd,
    add_cmd,
    status_cmd,
    switch_cmd,
    deploy_cmd,
    edit_cmd,
    audit_cmd,
    backup_cmd,
    branch_cmd,
    remote_cmd,
    tui_cmd,
    config_cmd,
)

def main():
    """Main entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
