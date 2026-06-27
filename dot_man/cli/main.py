"""Main entry point for dot-man CLI.

This module aggregates all subcommands and exposes the main entry point.
"""

import logging

# Import the shared CLI group (interface)
from .interface import cli

# Import all subcommands to register them with the CLI group


def main() -> None:
    """Main entry point for the CLI.

    On the very first launch (no ~/.config/dot-man/ or sentinel missing),
    the onboarding tutorial runs automatically before anything else.
    """
    from .onboarding import is_first_run, run_onboarding

    if is_first_run():
        run_onboarding()
        return

    # Try to install completions if not already installed
    try:
        from .completions_cmd import run_install

        run_install()
    except Exception as e:
        logging.debug("Shell completion installation skipped: %s", e)

    cli()


if __name__ == "__main__":
    main()
