"""Edit command for dot-man CLI."""

from pathlib import Path

import click
import questionary

from .. import ui
from ..constants import REPO_DIR, DOT_MAN_TOML, GLOBAL_TOML
from ..config import GlobalConfig
from ..exceptions import DotManError
from .interface import cli as main
from .common import error, success, warn, require_init


@main.command()
@click.option("--editor", help="Editor to use (default: config or $VISUAL or $EDITOR)")
@click.option("--global", "edit_global", is_flag=True, help="Edit global configuration")
@click.option("--raw", is_flag=True, help="Use raw text editor instead of interactive TUI")
@require_init
def edit(editor: str | None, edit_global: bool, raw: bool):
    """Open the configuration file in your text editor.

    By default, opens the dot-man.toml file for the current branch.
    Use --global to edit the global configuration.
    """
    try:
        from ..interactive import run_section_wizard, run_global_wizard, run_templates_wizard, custom_style

        # Determine target file path
        if edit_global:
            target = GLOBAL_TOML
            desc = "global configuration"
        else:
            target = REPO_DIR / DOT_MAN_TOML
            desc = "dot-man.toml"

        # If --raw flag, skip interactive mode
        if raw:
            if not target.exists():
                error(f"Configuration file not found: {target}")
            _open_raw_editor(target, desc, editor)
            return

        # Interactive Mode
        from ..operations import get_operations
        
        try:
            ops = get_operations()
            
            while True:
                ops.reload_config()
                sections = ops.get_sections()
                
                choices = []
                choices.append(questionary.Choice("⚙️  Global Configuration", value="global"))
                
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

                selection = questionary.select(
                    "What would you like to configure?",
                    choices=choices,
                    use_shortcuts=True,
                    style=custom_style
                ).ask()

                if not selection or selection == "quit":
                    break
                
                if selection == "global":
                    run_global_wizard(ops.global_config)
                
                elif selection == "raw":
                    _open_raw_editor(target, desc, editor)
                    break
                
                elif selection == "add_new":
                    path_str = questionary.path("Path to file or directory:", style=custom_style).ask()
                    if path_str:
                        try:
                            path = Path(path_str).expanduser()
                            if not path.exists():
                                warn(f"Path does not exist: {path}")
                                continue
                            
                            section_name = questionary.text("Section Name:", default=path.stem, style=custom_style).ask()
                            if section_name:
                                from .add_cmd import add
                                ctx = click.get_current_context()
                                ctx.invoke(add, path=str(path), section=section_name, repo_base=None, 
                                          exclude=(), include=(), inherits=(), post_deploy=None, pre_deploy=None)
                                ui.console.print()
                                ui.console.print("Press Enter to continue...")
                                input()
                        except Exception as e:
                            warn(f"Error adding section: {e}")

                elif selection == "templates":
                    run_templates_wizard(ops.dotman_config)

                elif selection.startswith("section:"):
                    section_name = selection.split(":", 1)[1]
                    run_section_wizard(ops.dotman_config, section_name)

        except KeyboardInterrupt:
            return
        except Exception as e:
            warn(f"Interactive menu error: {e}")
            ui.console.print("Falling back to raw editor...")
            _open_raw_editor(target, desc, editor)

    except DotManError as e:
        error(str(e), e.exit_code)


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
