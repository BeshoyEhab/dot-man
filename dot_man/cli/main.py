"""Main entry point for dot-man CLI.

This module aggregates all subcommands and exposes the main entry point.
"""

import logging
import sys

# Import the shared CLI group (interface)
from .interface import cli

# Import all subcommands to register them with the CLI group


def _should_auto_onboard(argv: list[str]) -> bool:
    """Decide whether first-run onboarding should run for this invocation.

    Onboarding must never hijack ``--help``/``--version`` or a non-interactive
    (piped/CI) invocation, which would break scripts and hide the version.
    It runs only for a bare ``dot-man`` or ``dot-man init``.
    """
    if "--no-onboarding" in argv:
        return False
    if any(flag in argv for flag in ("--help", "-h", "--version", "-V")):
        return False
    try:
        if not sys.stdout.isatty():
            return False
    except (AttributeError, ValueError):
        return False

    command = next((arg for arg in argv if not arg.startswith("-")), None)
    return command in (None, "init")


def main() -> None:
    """Main entry point for the CLI.

    On the very first launch the onboarding tutorial runs automatically, but
    only for an interactive bare invocation or ``dot-man init`` (see
    ``_should_auto_onboard``); every other command proceeds normally.
    """
    from .completion_engine import maybe_run_completion
    from .onboarding import is_first_run, run_onboarding

    argv = sys.argv[1:]
    maybe_run_completion()

    if is_first_run() and _should_auto_onboard(argv):
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
