"""Edit command for dot-man CLI."""

from pathlib import Path

import click
import questionary

from .. import ui
from ..config import GlobalConfig
from ..constants import DOT_MAN_TOML, GLOBAL_TOML, REPO_DIR
from ..exceptions import DotManError
from .common import AliasedCommand, error, require_init, success, warn
from .interface import cli as main


@main.command("edit", cls=AliasedCommand, aliases=["edt"])
@click.option("--editor", help="Editor to use (default: config or $VISUAL or $EDITOR)")
@click.option("--global", "edit_global", is_flag=True, help="Edit global configuration")
@click.option(
    "--raw", is_flag=True, help="Use raw text editor instead of interactive TUI"
)
@require_init
def edit(editor: str | None, edit_global: bool, raw: bool):
    """Open the configuration file in your text editor.

    By default, opens the dot-man.toml file for the current branch.
    Use --global to edit the global configuration.
    """
    try:
        target, desc = _edit_resolve_target(edit_global)

        if raw:
            if not target.exists():
                error(f"Configuration file not found: {target}")
            _open_raw_editor(target, desc, editor)
            return

        _edit_run_interactive(target, desc, editor)

    except DotManError as e:
        error(str(e), e.exit_code)


def _edit_resolve_target(edit_global: bool):
    """Resolve target file path and description."""
    if edit_global:
        return GLOBAL_TOML, "global configuration"
    return REPO_DIR / DOT_MAN_TOML, "dot-man.toml"


def _edit_run_interactive(target: Path, desc: str, editor: str | None):
    """Run the interactive TUI configuration editor."""
    from ..operations import get_operations

    try:
        ops = get_operations()
        _edit_interactive_loop(ops, target, desc, editor)
    except KeyboardInterrupt:
        return
    except Exception as e:
        warn(f"Interactive menu error: {e}")
        ui.console.print("Falling back to raw editor...")
        _open_raw_editor(target, desc, editor)


def _edit_interactive_loop(ops, target: Path, desc: str, editor: str | None):
    """Main interactive selection loop."""
    from ..interactive import custom_style

    while True:
        ops.reload_config()
        choices = _edit_build_menu(ops)
        selection = questionary.select(
            "What would you like to configure?",
            choices=choices,
            use_shortcuts=True,
            style=custom_style,
        ).ask()

        if not selection or selection == "quit":
            break

        if _edit_handle_selection(ops, target, desc, editor, selection):
            break


def _edit_build_menu(ops):
    """Build interactive menu choices."""
    sections = ops.get_sections()
    choices = [questionary.Choice("⚙️  Global Configuration", value="global")]
    if sections:
        choices.append(questionary.Separator("--- Sections ---"))
        for name in sections:
            choices.append(questionary.Choice(f"📄 {name}", value=f"section:{name}"))
    else:
        choices.append(questionary.Separator("--- No Sections ---"))
    choices.append(questionary.Separator("--- Actions ---"))
    choices.append(questionary.Choice("➕ Add New Section", value="add_new"))
    choices.append(questionary.Choice("📝 Edit Templates", value="templates"))
    choices.append(questionary.Choice("📝 Open Raw File (Advanced)", value="raw"))
    choices.append(questionary.Choice("🚪 Quit", value="quit", shortcut_key="q"))
    return choices


def _edit_handle_selection(
    ops, target: Path, desc: str, editor: str | None, selection: str
) -> bool:
    """Handle a menu selection. Returns True to break the outer loop."""
    from ..interactive import (
        run_global_wizard,
        run_section_wizard,
        run_templates_wizard,
    )

    if selection == "global":
        run_global_wizard(ops.global_config)
    elif selection == "raw":
        _open_raw_editor(target, desc, editor)
        return True
    elif selection == "add_new":
        _edit_handle_add_new()
    elif selection == "templates":
        run_templates_wizard(ops.dotman_config)
    elif selection.startswith("section:"):
        section_name = selection.split(":", 1)[1]
        run_section_wizard(ops.dotman_config, section_name)
    return False


def _edit_handle_add_new():
    """Handle the 'Add New Section' flow."""
    from ..interactive import custom_style

    path_str = questionary.path("Path to file or directory:", style=custom_style).ask()
    if not path_str:
        return
    try:
        path = Path(path_str).expanduser()
        if not path.exists():
            warn(f"Path does not exist: {path}")
            return
        section_name = questionary.text(
            "Section Name:", default=path.stem, style=custom_style
        ).ask()
        if not section_name:
            return
        from .add_cmd import add

        ctx = click.get_current_context()
        ctx.invoke(
            add,
            path=str(path),
            section=section_name,
            repo_base=None,
            exclude=(),
            include=(),
            inherits=(),
            post_deploy=None,
            pre_deploy=None,
        )
        ui.console.print()
        ui.console.print("Press Enter to continue...")
        input()
    except Exception as e:
        warn(f"Error adding section: {e}")


def _open_raw_editor(target: Path, desc: str, editor: str | None = None):
    """Helper to open raw editor."""
    from ..utils import get_editor, open_in_editor

    global_config = GlobalConfig()
    try:
        global_config.load()
        config_editor = global_config.editor
    except (FileNotFoundError, DotManError):
        config_editor = None

    editor_cmd = editor or config_editor or get_editor()
    ui.console.print(f"Opening {desc} in [cyan]{editor_cmd}[/cyan]...")

    if not open_in_editor(target, editor_cmd):
        error(f"Editor '{editor_cmd}' exited with error")

    success(f"Edited {desc}")
