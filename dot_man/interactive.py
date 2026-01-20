"""Interactive CLI wizards for dot-man."""

from pathlib import Path
import questionary
from questionary import Validator, ValidationError
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .config import DotManConfig, GlobalConfig, Section
from .ui import console, print_banner, success, error, warn


# ANSI Colors for Questionary choices
COLOR_EDIT = "\033[36m"   # Cyan
COLOR_TOGGLE = "\033[33m" # Yellow
COLOR_SAVE = "\033[32m"   # Green
COLOR_ADD = "\033[32m"    # Green
COLOR_CANCEL = "\033[31m" # Red
COLOR_DELETE = "\033[31m" # Red
COLOR_RESET = "\033[0m"


class PathValidator(Validator):
    def validate(self, document):
        if not document.text:
            return  # Empty allowed
        path = Path(document.text).expanduser()
        if not path.is_absolute():
            # We generally prefer absolute paths or at least valid ones
            pass # Relative paths are okay if intended
            
class UrlValidator(Validator):
    def validate(self, document):
        if not document.text:
            return
        if not (document.text.startswith("http://") or document.text.startswith("https://") or document.text.startswith("git@") or document.text.startswith("ssh://")):
             raise ValidationError(
                message="Please enter a valid URL (http/https/ssh/git)",
                cursor_position=len(document.text),
            )

def print_section_dashboard(section: Section):
    """Print a dashboard summary for the section."""
    table = Table(title=None, box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="cyan bold")
    table.add_column("Value")

    paths = ", ".join(str(p) for p in section.paths)
    inherits = ", ".join(section.inherits) if section.inherits else "[dim]None[/dim]"
    
    table.add_row("Paths", paths)
    table.add_row("Repo Base", section.repo_base)
    table.add_row("Update Strategy", section.update_strategy)
    table.add_row("Secrets Filter", "[green]Enabled[/green]" if section.secrets_filter else "[dim]Disabled[/dim]")
    table.add_row("InheritsFrom", inherits)
    table.add_row("Pre-deploy", section.pre_deploy or "[dim]None[/dim]")
    table.add_row("Post-deploy", section.post_deploy or "[dim]None[/dim]")

    console.print(Panel(
        table,
        title=f"[magenta bold]Editing Section: {section.name}[/magenta bold]",
        subtitle="[dim]Select a field below to edit[/dim]",
        border_style="cyan"
    ))

def run_section_wizard(config: DotManConfig, section_name: str):
    """Run interactive wizard to edit a section."""
    section = config.get_section(section_name)
    
    while True:
        console.clear()
        print_section_dashboard(section)
        console.print()
        
        choices = [
            questionary.Choice(f"{COLOR_EDIT}Edit Paths{COLOR_RESET}", value="paths"),
            questionary.Choice(f"{COLOR_EDIT}Edit Repo Base{COLOR_RESET}", value="repo_base"),
            questionary.Choice(f"{COLOR_EDIT}Edit Update Strategy{COLOR_RESET}", value="update_strategy"),
            questionary.Choice(f"{COLOR_TOGGLE}Toggle Secrets Filter{COLOR_RESET}", value="secrets_filter"),
            questionary.Choice(f"{COLOR_EDIT}Edit Inherits{COLOR_RESET}", value="inherits"),
            questionary.Choice(f"{COLOR_EDIT}Edit Pre-deploy Hook{COLOR_RESET}", value="pre_deploy"),
            questionary.Choice(f"{COLOR_EDIT}Edit Post-deploy Hook{COLOR_RESET}", value="post_deploy"),
            questionary.Separator(),
            questionary.Choice(f"{COLOR_SAVE}Save & Return{COLOR_RESET}", value="save", shortcut_key="s"),
            questionary.Choice(f"{COLOR_CANCEL}Cancel{COLOR_RESET}", value="cancel", shortcut_key="q"),
        ]
        
        field = questionary.select("Select action:", choices=choices).ask()
        
        if not field or field == "cancel":
            return
            
        if field == "save":
            try:
                # Fix paths to be relative if possible
                fixed_paths = []
                home = Path.home()
                for p in section.paths:
                    path_obj = Path(p)
                    if path_obj.is_absolute() and path_obj.is_relative_to(home):
                         # Convert absolute /home/user/.foo to .foo
                         # The config expects relative paths to imply relative to home (or repo checkout)
                         # Usually standard dotfiles are relative to home.
                         rel = path_obj.relative_to(home)
                         fixed_paths.append(str(rel))
                    else:
                         fixed_paths.append(str(p))

                # Re-add section to save changes (updates existing)
                config.add_section(
                    name=section_name,
                    paths=fixed_paths,
                    repo_base=section.repo_base,
                    update_strategy=section.update_strategy,
                    secrets_filter=section.secrets_filter,
                    pre_deploy=section.pre_deploy,
                    post_deploy=section.post_deploy,
                    include=section.include,
                    exclude=section.exclude,
                    inherits=section.inherits,
                    overwrite=True,
                )
                config.save()
                success(f"Section '{section_name}' updated.")
                return
            except Exception as e:
                error(f"Failed to save: {e}")
                input("Press Enter to continue...")
                continue
        
        # Field Editing
        if field == "paths":
            current = ", ".join(str(p) for p in section.paths)
            val = questionary.text("Paths (comma separated):", default=current, validate=PathValidator).ask()
            if val:
                section.paths = [Path(p.strip()) for p in val.split(",") if p.strip()]
        
        elif field == "repo_base":
            val = questionary.text("Repo Base Directory:", default=section.repo_base).ask()
            if val:
                section.repo_base = val
                
        elif field == "update_strategy":
            val = questionary.select(
                "Update Strategy:",
                choices=["replace", "rename_old", "ignore"],
                default=section.update_strategy
            ).ask()
            if val:
                section.update_strategy = val
                
        elif field == "secrets_filter":
            # Toggle logic since it's a checkbox essentially
            section.secrets_filter = not section.secrets_filter
            
        elif field == "inherits":
            current = ", ".join(section.inherits)
            val = questionary.text("Inherits templates (comma separated):", default=current).ask()
            if val is not None:
                section.inherits = [t.strip() for t in val.split(",") if t.strip()]
                
        elif field == "pre_deploy":
            val = questionary.text("Pre-deploy Hook:", default=section.pre_deploy or "").ask()
            section.pre_deploy = val if val else None
            
        elif field == "post_deploy":
            val = questionary.text("Post-deploy Hook:", default=section.post_deploy or "").ask()
            section.post_deploy = val if val else None

def print_global_dashboard(config: GlobalConfig):
    """Print global config dashboard."""
    table = Table(title=None, box=None, show_header=False, padding=(0, 2))
    table.add_column("Key", style="cyan bold")
    table.add_column("Value")

    table.add_row("Default Editor", config.editor or "[dim]System Default[/dim]")
    table.add_row("Remote URL", config.remote_url or "[dim]Not Set[/dim]")
    table.add_row("Default Secrets Filter", "[green]Enabled[/green]" if config.secrets_filter_enabled else "[dim]Disabled[/dim]")

    console.print(Panel(
        table,
        title="[magenta bold]Global Configuration[/magenta bold]",
        subtitle="[dim]Settings apply to all new sections/machines[/dim]",
        border_style="cyan"
    ))

def run_global_wizard(config: GlobalConfig):
    """Edit global configuration."""
    while True:
        console.clear()
        print_global_dashboard(config)
        console.print()
        
        choices = [
            questionary.Choice(f"{COLOR_EDIT}Edit Default Editor{COLOR_RESET}", value="editor"),
            questionary.Choice(f"{COLOR_EDIT}Edit Remote URL{COLOR_RESET}", value="remote_url"),
            questionary.Choice(f"{COLOR_TOGGLE}Toggle Default Secrets Filter{COLOR_RESET}", value="secrets_filter"),
            questionary.Separator(),
            questionary.Choice(f"{COLOR_SAVE}Save & Return{COLOR_RESET}", value="save", shortcut_key="s"),
            questionary.Choice(f"{COLOR_CANCEL}Cancel{COLOR_RESET}", value="cancel", shortcut_key="q"),
        ]
        
        field = questionary.select("Select action:", choices=choices).ask()
        
        if not field or field == "cancel":
            return
            
        if field == "save":
            config.save()
            success("Global config updated.")
            return

        if field == "editor":
            val = questionary.text("Editor Command:", default=config.editor or "").ask()
            config.editor = val if val else None
            
        elif field == "remote_url":
            val = questionary.text("Remote URL:", default=config.remote_url, validate=UrlValidator).ask()
            config.remote_url = val if val else ""
            
        elif field == "secrets_filter":
             current = config.secrets_filter_enabled
             # Toggle
             val = not current
             if "defaults" not in config._data:
                 config._data["defaults"] = {}
             config._data["defaults"]["secrets_filter"] = val

def run_templates_wizard(config: DotManConfig):
    """Add or edit templates."""
    while True:
        console.clear()
        print_banner("Templates Manager")
        
        templates = config.get_local_templates()
        if templates:
            table = Table(title="Available Templates", show_header=True)
            table.add_column("Name", style="green")
            table.add_column("Update Strategy")
            table.add_column("Hooks")
            
            for name in templates:
                tmpl = config._data["templates"][name]
                hooks = []
                if tmpl.get("pre_deploy"): hooks.append("Pre")
                if tmpl.get("post_deploy"): hooks.append("Post")
                
                table.add_row(
                    name,
                    tmpl.get("update_strategy", "default"),
                    ", ".join(hooks) if hooks else "-"
                )
            console.print(table)
            console.print()

        choices = []
        if templates:
            for name in templates:
                choices.append(questionary.Choice(f"{COLOR_EDIT}Edit {name}{COLOR_RESET}", value=name))
        
        choices.append(questionary.Separator())
        choices.append(questionary.Choice(f"{COLOR_ADD}Add New Template{COLOR_RESET}", value="add_new"))
        choices.append(questionary.Choice(f"{COLOR_CANCEL}Back{COLOR_RESET}", value="back", shortcut_key="q"))
        
        selection = questionary.select("Manage Templates:", choices=choices, use_shortcuts=True).ask()
        
        if not selection or selection == "back":
            return
            
        if selection == "add_new":
            name = questionary.text("Template Name:").ask()
            if name:
                if name in templates:
                    warn("Template already exists!")
                else:
                    if "templates" not in config._data:
                        config._data["templates"] = {}
                    config._data["templates"][name] = {}
                    edit_template(config, name)
        else:
            edit_template(config, selection)

def edit_template(config: DotManConfig, name: str):
    """Edit a specific template."""
    template = config._data["templates"][name]
    
    while True:
        console.clear()
        
        # Mini dashboard for template
        table = Table(title=None, box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="cyan bold")
        table.add_column("Value")
        
        table.add_row("Pre-deploy Hook", template.get("pre_deploy", "[dim]None[/dim]"))
        table.add_row("Post-deploy Hook", template.get("post_deploy", "[dim]None[/dim]"))
        table.add_row("Update Strategy", template.get("update_strategy", "Default"))
        
        console.print(Panel(
            table,
            title=f"[magenta bold]Template: {name}[/magenta bold]",
            border_style="cyan"
        ))
        console.print()
        
        choices = [
            questionary.Choice(f"{COLOR_EDIT}Edit Pre-deploy Hook{COLOR_RESET}", value="pre_deploy"),
            questionary.Choice(f"{COLOR_EDIT}Edit Post-deploy Hook{COLOR_RESET}", value="post_deploy"),
            questionary.Choice(f"{COLOR_EDIT}Edit Update Strategy{COLOR_RESET}", value="update_strategy"),
            questionary.Separator(),
            questionary.Choice(f"{COLOR_SAVE}Save & Return{COLOR_RESET}", value="save", shortcut_key="s"),
            questionary.Choice(f"{COLOR_DELETE}Delete Template{COLOR_RESET}", value="delete"),
        ]
        
        field = questionary.select("Edit Template Field:", choices=choices, use_shortcuts=True).ask()
        
        if not field or field == "save":
            config.save()
            return
            
        if field == "delete":
            if questionary.confirm(f"Delete template '{name}'?").ask():
                del config._data["templates"][name]
                config.save()
                return

        if field == "pre_deploy":
            val = questionary.text("Pre-deploy Hook:", default=template.get("pre_deploy", "")).ask()
            if val:
                template["pre_deploy"] = val
            elif "pre_deploy" in template:
                del template["pre_deploy"]

        elif field == "post_deploy":
            val = questionary.text("Post-deploy Hook:", default=template.get("post_deploy", "")).ask()
            if val:
                template["post_deploy"] = val
            elif "post_deploy" in template:
                del template["post_deploy"]

        elif field == "update_strategy":
            val = questionary.select(
                "Update Strategy:",
                choices=["replace", "rename_old", "ignore"],
                default=template.get("update_strategy", "replace")
            ).ask()
            if val:
                template["update_strategy"] = val
