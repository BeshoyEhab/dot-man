"""Main entry point for dot-man CLI.

This module aggregates all subcommands and exposes the main entry point.
"""

# Import the shared CLI group (interface)
from .interface import cli

# Import all subcommands to register them with the CLI group

def main():
    """Main entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
