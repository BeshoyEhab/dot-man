"""First-time onboarding and tutorial flow for dot-man.

This module is invoked automatically on the very first launch of dot-man
(detected by the absence of ~/.config/dot-man/ or the .onboarded sentinel).
It walks new users through:

  1. An Architecture section – how dot-man works internally.
  2. A Manual section     – practical usage with ASCII examples.

After the tutorial, it runs 'dot-man init' automatically and optionally
creates the user's first branch.
"""

from __future__ import annotations

import sys

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


def _confirm_next(prompt: str = "Ready for the next section?") -> bool:
    """Ask the user if they want to continue."""
    _console.print()
    return Confirm.ask(f"[bold]{prompt}[/bold]", default=True, console=_console)


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
            "We'll walk you through a short tutorial\n"
            "before setting everything up automatically.\n\n"
            "[dim]The tutorial has 2 sections and takes about 2 minutes.[/dim]",
            border_style="cyan",
            padding=(1, 4),
        )
    )
    _console.print()

    menu_text = (
        "  [bold cyan][1][/bold cyan]  Architecture  — how dot-man works internally\n"
        "  [bold cyan][2][/bold cyan]  Manual        — practical usage examples\n"
        "  [bold cyan][s][/bold cyan]  Skip tutorial and go straight to setup"
    )
    _console.print(
        Panel(
            menu_text,
            title="[bold]Tutorial Menu[/bold]",
            border_style="dim",
            padding=(0, 2),
        )
    )
    _console.print()


# ──────────────────────────────────────────────────────────────────────────────
# Section 1 — Architecture
# ──────────────────────────────────────────────────────────────────────────────

ARCH_OVERVIEW = """\
  Your Home Directory          dot-man Repo              Your System
  ───────────────────          ────────────              ───────────

  ~/.bashrc        ──save──►  branch: main  ──deploy──►  ~/.bashrc
  ~/.vimrc         ──save──►  branch: work  ──deploy──►  ~/.vimrc
  ~/.gitconfig     ──save──►  branch: home              ~/.gitconfig
  ~/.config/nvim/  ──save──►  branch: server

  Each branch stores a COMPLETE snapshot of your dotfiles.
  Switching branches swaps your entire configuration instantly."""

BRANCH_DIAGRAM = """\
  main ──┬── work      ← office: proxy settings, work aliases
         │
         ├── home      ← personal: gaming tweaks, personal aliases
         │
         ├── server    ← minimal: headless, no GUI tools
         │
         └── laptop    ← mobile: battery saving, HiDPI settings

  All branches share the same tracked files list.
  Each branch stores its own version of those files."""

INIT_FLOW = """\
  $ dot-man init
        │
        ├─► Create ~/.config/dot-man/           (config root)
        │         ├── repo/                     (git repository)
        │         │     └── dot-man.toml        (file mappings)
        │         ├── backups/                  (safety backups)
        │         └── global.toml              (global settings)
        │
        ├─► git init  inside repo/
        ├─► Initial commit "dot-man: Initial commit"
        └─► Setup wizard  (auto-detect common dotfiles)"""

COMPONENTS = """\
  ┌────────────────┬──────────────────────────────────────────┐
  │  Component     │  Role                                    │
  ├────────────────┼──────────────────────────────────────────┤
  │  GitManager    │  git branches, commits, checkout         │
  │  DotManConfig  │  which files go in which section         │
  │  GlobalConfig  │  current branch, remote URL, settings    │
  │  Operations    │  save files  →  repo, deploy  →  system  │
  │  SecretGuard   │  redact passwords/keys before committing │
  └────────────────┴──────────────────────────────────────────┘"""


def _section_architecture() -> None:
    _section_rule("Section 1 of 2 — Architecture")

    _console.print("[bold]What is dot-man?[/bold]")
    _console.print(
        "dot-man tracks your dotfiles inside a [bold cyan]git repository[/bold cyan] "
        "and uses [bold cyan]branches[/bold cyan] to store different\n"
        "configurations. Switching branches swaps your entire dotfile setup instantly.\n"
    )
    _ascii_panel("How Files Flow", ARCH_OVERVIEW)
    _pause()

    _console.print("[bold]The Branch System[/bold]")
    _console.print(
        "Think of branches as named [bold cyan]configuration profiles[/bold cyan]. "
        "You can have one for work,\none for home, one for a minimal server — "
        "all managed from a single tool.\n"
    )
    _ascii_panel("Branch Model", BRANCH_DIAGRAM)
    _pause()

    _console.print("[bold]Core Components[/bold]")
    _console.print(
        "dot-man is composed of a few focused components that work together:\n"
    )
    _ascii_panel("Components", COMPONENTS)
    _pause()

    _console.print("[bold]Initialization Flow[/bold]")
    _console.print(
        "When you run [bold cyan]dot-man init[/bold cyan] for the first time, "
        "this is what happens:\n"
    )
    _ascii_panel("dot-man init", INIT_FLOW)
    _pause()

    _console.print("[bold green]✓[/bold green]  Architecture section complete!\n")


# ──────────────────────────────────────────────────────────────────────────────
# Section 2 — Manual / How to Use
# ──────────────────────────────────────────────────────────────────────────────

SWITCH_FLOW = """\
  $ dot-man switch work
        │
        ├─► Phase 1: Save current branch state
        │     └─► copies ~/yourfiles  →  repo/ (commits them in git)
        │
        ├─► Phase 2: Switch git branch
        │     └─► git checkout work  (creates it if new)
        │
        └─► Phase 3: Deploy new branch files
              └─► copies repo/ files  →  ~/yourfiles"""

WORKFLOW_LOOP = """\
  ╔══════════════════════════════════════════════════════════╗
  ║              Typical dot-man Workflow                    ║
  ╠══════════════════════════════════════════════════════════╣
  ║                                                          ║
  ║  1.  dot-man init              ──►  set up the repo      ║
  ║  2.  dot-man add ~/.bashrc     ──►  start tracking       ║
  ║  3.  dot-man add ~/.config/nvim                          ║
  ║  4.  dot-man switch work       ──►  create work branch   ║
  ║      (edit ~/.bashrc, configs…)                          ║
  ║  5.  dot-man switch home       ──►  auto-saves + deploys ║
  ║  6.  dot-man status            ──►  see what changed     ║
  ║  7.  dot-man sync              ──►  push to GitHub       ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝"""

COMMANDS_TABLE = """\
  ┌────────────────────────────────┬──────────────────────────────────┐
  │  Command                       │  What it does                    │
  ├────────────────────────────────┼──────────────────────────────────┤
  │  dot-man init                  │  Initialize repository           │
  │  dot-man add <path>            │  Track a file or directory       │
  │  dot-man switch <branch>       │  Switch configuration branch     │
  │  dot-man status                │  Show tracked files & changes    │
  │  dot-man deploy                │  Deploy repo files to system     │
  │  dot-man sync                  │  Push/pull from remote           │
  │  dot-man log                   │  Show commit history             │
  │  dot-man diff                  │  Show uncommitted changes        │
  │  dot-man audit                 │  Scan for secrets / passwords    │
  │  dot-man backup                │  Create a manual backup          │
  │  dot-man --help                │  Full command reference          │
  └────────────────────────────────┴──────────────────────────────────┘"""


def _section_manual() -> None:
    _section_rule("Section 2 of 2 — Manual / How To Use")

    _console.print("[bold]Step 1 — Initialization[/bold]")
    _console.print("The first thing you do is initialize the repository:\n")
    _code_block("$ dot-man init")
    _console.print(
        "\nThe setup wizard will detect common dotfiles on your system\n"
        "and ask which ones you'd like to track.\n"
    )
    _pause()

    _console.print("[bold]Step 2 — Adding Files to Track[/bold]")
    _console.print("You can always add more files later:\n")
    _code_block(
        "$ dot-man add ~/.bashrc          # single file\n"
        "$ dot-man add ~/.config/nvim     # entire directory\n"
        "$ dot-man add ~/.gitconfig       # git settings\n"
        "$ dot-man add ~/.ssh/config      # SSH config"
    )
    _console.print(
        "\nFiles are [bold cyan]copied into the git repo[/bold cyan] and tracked per branch.\n"
    )
    _pause()

    _console.print("[bold]Step 3 — Branches (Profiles)[/bold]")
    _console.print(
        "Use branches to maintain separate configurations.\n"
        "[bold cyan]dot-man switch[/bold cyan] does three things automatically:\n"
    )
    _ascii_panel("How 'switch' Works", SWITCH_FLOW)
    _code_block(
        "$ dot-man switch work    # create + switch to 'work' branch\n"
        "$ dot-man switch home    # switch back to 'home' branch\n"
        "$ dot-man switch server  # minimal server configuration"
    )
    _pause()

    _console.print("[bold]Step 4 — Full Workflow[/bold]\n")
    _ascii_panel("Complete Workflow", WORKFLOW_LOOP)
    _pause()

    _console.print("[bold]Quick Reference — All Commands[/bold]\n")
    _ascii_panel("Commands", COMMANDS_TABLE)
    _pause()

    _console.print("[bold green]✓[/bold green]  Manual section complete!\n")


# ──────────────────────────────────────────────────────────────────────────────
# Post-tutorial: init + first branch
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
            "  [bold cyan]dot-man switch <branch-name>[/bold cyan]\n"
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
            f"[dim]Try manually: [bold]dot-man switch {branch_name}[/bold][/dim]"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────


def run_onboarding() -> None:
    """Run the full first-time onboarding flow.

    Order:
      1. Welcome banner
      2. Tutorial menu (user picks Architecture / Manual / Skip)
      3. dot-man init (always runs)
      4. Offer first branch creation
      5. Write sentinel so flow never repeats
    """
    interrupted = False
    try:
        _show_welcome()

        choice = Prompt.ask(
            "[bold]Choose an option[/bold]",
            choices=["1", "2", "s"],
            default="1",
            console=_console,
        )

        if choice == "1":
            _section_architecture()
            if _confirm_next("Continue to the Manual section?"):
                _section_manual()
        elif choice == "2":
            _section_manual()
            if _confirm_next("Go back and read the Architecture section?"):
                _section_architecture()
        # choice == "s" → skip tutorial

        _console.print()
        _console.print(
            Rule("[bold green]Tutorial Complete[/bold green]", style="green")
        )

        # Always run init (the real one, with interactive wizard)
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
                "  [cyan]dot-man switch <name>[/cyan]   — switch branch\n"
                "  [cyan]dot-man config defaults[/cyan] — view/change default settings\n"
                "  [cyan]dot-man --help[/cyan]          — full command list",
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
        sys.exit(0)
