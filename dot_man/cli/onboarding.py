"""First-time onboarding flow for dot-man.

This module is invoked automatically on the very first launch of dot-man
(detected by the absence of ~/.config/dot-man/ or the .onboarded sentinel).
It welcomes the user, runs 'dot-man init' automatically (including the
interactive setup wizard), and optionally creates the user's first branch.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.text import Text

from ..constants import DOT_MAN_DIR

# ──────────────────────────────────────────────────────────────────────────────
# Sentinel / detection
# ──────────────────────────────────────────────────────────────────────────────

SENTINEL = DOT_MAN_DIR / ".onboarded"

_console = Console()


def is_first_run() -> bool:
    """Return True if this is the first time dot-man has ever been launched.

    A run is considered "first" when either:
      - ~/.config/dot-man/ doesn't exist yet, OR
      - the directory exists but the .onboarded sentinel is missing
        (e.g. the user deleted it to replay the tutorial).
    """
    if not DOT_MAN_DIR.exists():
        return True
    return not SENTINEL.exists()


def mark_onboarded() -> None:
    """Write the sentinel file so the tutorial never re-fires."""
    DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
    SENTINEL.touch()


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _pause(label: str = "Press [bold cyan]Enter[/bold cyan] to continue…") -> None:
    """Block until the user presses Enter."""
    _console.print()
    _console.print(f"  {label}")
    try:
        input()
    except EOFError:
        pass


def _section_rule(title: str) -> None:
    _console.print()
    _console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))
    _console.print()


def _code_block(code: str) -> None:
    """Render a fenced-style code block."""
    _console.print(
        Panel(
            Text(code, style="green"),
            border_style="dim",
            padding=(0, 2),
        )
    )


def _ascii_panel(title: str, art: str) -> None:
    """Render an ASCII diagram inside a named panel."""
    _console.print(
        Panel(
            Text(art, style="cyan", justify="left"),
            title=f"[bold]{title}[/bold]",
            border_style="cyan",
            padding=(1, 3),
        )
    )


# ──────────────────────────────────────────────────────────────────────────────
# Welcome banner
# ──────────────────────────────────────────────────────────────────────────────

WELCOME_ART = r"""
    ██████╗  ██████╗ ████████╗      ███╗   ███╗ █████╗ ███╗   ██╗
    ██╔══██╗██╔═══██╗╚══██╔══╝      ████╗ ████║██╔══██╗████╗  ██║
    ██║  ██║██║   ██║   ██║   █████╗██╔████╔██║███████║██╔██╗ ██║
    ██║  ██║██║   ██║   ██║   ╚════╝██║╚██╔╝██║██╔══██║██║╚██╗██║
    ██████╔╝╚██████╔╝   ██║         ██║ ╚═╝ ██║██║  ██║██║ ╚████║
    ╚═════╝  ╚═════╝    ╚═╝         ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
"""


def _show_welcome() -> None:
    _console.print()
    _console.print(Text(WELCOME_ART, style="bold cyan", justify="center"))
    _console.print(
        Panel(
            "[bold white]Welcome to dot-man![/bold white]\n"
            "[dim]The Dotfile Manager with Git-Powered Branching[/dim]\n\n"
            "This is your [bold cyan]first launch[/bold cyan]. "
            "We'll get your dotfiles tracked in about a minute.\n\n"
            "[dim]No reading required — just answer a few prompts.[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    _console.print()


# ──────────────────────────────────────────────────────────────────────────────
# Setup: init + first branch
# ──────────────────────────────────────────────────────────────────────────────


def _run_init_direct() -> bool:
    """Run init by importing and calling the underlying logic directly.

    This avoids the CliRunner output-capture issue and lets Rich render
    directly to the terminal so colours and prompts work properly.
    """
    _section_rule("Setting Up Your Repository")
    _console.print(
        "Now let's initialize your dot-man repository.\n"
        "Running [bold cyan]dot-man init[/bold cyan]…\n"
    )

    try:
        from .. import ui
        from ..config import DotManConfig, GlobalConfig
        from ..constants import BACKUPS_DIR, FILE_PERMISSIONS, REPO_DIR
        from ..core import GitManager
        from ..utils import is_git_installed

        if not is_git_installed():
            _console.print("[red]✗ Git not found. Please install git first.[/red]")
            return False

        # Create directories
        DOT_MAN_DIR.mkdir(parents=True, exist_ok=True)
        DOT_MAN_DIR.chmod(FILE_PERMISSIONS)
        REPO_DIR.mkdir(parents=True, exist_ok=True)
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        # Git init
        git = GitManager()
        git.init()

        # Create configs
        global_config = GlobalConfig()
        global_config.create_default()

        dotman_config = DotManConfig()
        dotman_config.create_default()

        # Initial commit
        git.commit("dot-man: Initial commit")

        ui.console.print()
        ui.print_banner("🎉 dot-man initialized successfully!")
        ui.console.print()

        # Run the interactive wizard
        from .init_cmd import run_setup_wizard

        run_setup_wizard(global_config, dotman_config, git)
        return True

    except Exception as exc:
        _console.print(f"[red]Initialization failed: {exc}[/red]")
        _console.print(
            "[dim]You can run [bold]dot-man init[/bold] manually to try again.[/dim]"
        )
        return False


def _offer_first_branch() -> None:
    """Ask the user if they want to create their first branch."""
    _console.print()
    _section_rule("Create Your First Branch")

    _console.print(
        "Branches let you keep separate configurations (work, home, server…).\n"
        "Would you like to create your first branch now?\n"
    )

    want = Confirm.ask(
        "[bold]Do you want to create your first branch?[/bold]",
        default=True,
        console=_console,
    )

    if not want:
        _console.print()
        _console.print(
            "[dim]No problem — you can create one later with:[/dim]\n"
            "  [bold cyan]dot-man navigate <branch-name>[/bold cyan]\n"
        )
        return

    _console.print()
    _console.print("[dim]Common names: work, home, laptop, server, minimal…[/dim]")
    branch_name = Prompt.ask(
        "[bold]Enter branch name[/bold]",
        default="main",
        console=_console,
    )

    branch_name = branch_name.strip()
    if not branch_name:
        _console.print("[yellow]⚠  Empty name — skipping branch creation.[/yellow]")
        return

    _console.print()
    _console.print(
        f"Creating and switching to branch [bold cyan]{branch_name!r}[/bold cyan]…\n"
    )

    try:
        from ..operations import get_operations

        ops = get_operations()
        branch_exists = ops.git.branch_exists(branch_name)
        ops.git.checkout(branch_name, create=not branch_exists)
        ops.global_config.current_branch = branch_name
        ops.global_config.save()

        _console.print(
            f"[bold green]✓[/bold green]  "
            f"Branch [bold cyan]{branch_name!r}[/bold cyan] created and set as active!"
        )
    except Exception as exc:
        _console.print(f"[red]Could not create branch: {exc}[/red]")
        _console.print(
            f"[dim]Try manually: [bold]dot-man navigate {branch_name}[/bold][/dim]"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────


def run_onboarding() -> None:
    """Run the full first-time onboarding flow.

    Order:
      1. Welcome banner
      2. dot-man init (always runs, with interactive wizard)
      3. Offer first branch creation
      4. Write sentinel so flow never repeats
    """
    interrupted = False
    try:
        _show_welcome()

        # Run init (the real one, with interactive wizard)
        init_ok = _run_init_direct()

        if init_ok:
            _offer_first_branch()

        _console.print()
        _console.print(
            Panel(
                "[bold green]🎉 All done![/bold green]\n\n"
                "You're ready to use dot-man. Some useful commands:\n\n"
                "  [cyan]dot-man status[/cyan]          — see tracked files\n"
                "  [cyan]dot-man add <path>[/cyan]      — track a new file\n"
                "  [cyan]dot-man navigate <name>[/cyan] — switch configuration\n"
                "  [cyan]dot-man config defaults[/cyan] — view/change default settings\n"
                "  [cyan]dot-man help-all[/cyan]        — full command list",
                border_style="green",
                padding=(1, 4),
            )
        )
        _console.print()

        # Mark onboarded only on clean completion
        mark_onboarded()

    except KeyboardInterrupt:
        interrupted = True
        _console.print()
        _console.print(
            "\n[yellow]⚠  Tutorial interrupted.[/yellow]\n"
            "[dim]Run [bold]dot-man init[/bold] when you're ready to set up.[/dim]\n"
        )
        # Leave sentinel un-written so they see the tutorial again next time

    if interrupted:
        raise SystemExit(0)
