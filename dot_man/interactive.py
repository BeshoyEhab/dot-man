"""Interactive CLI wizards for dot-man."""

from pathlib import Path
import questionary
from questionary import Validator, ValidationError

from .config import DotManConfig, GlobalConfig
from .ui import console, print_banner, confirm, warn, success, error


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

def run_section_wizard(config: DotManConfig, section_name: str):
    """Run interactive wizard to edit a section."""
    section = config.get_section(section_name)
    
    while True:
        console.clear()
        print_banner(f"Editing Section: {section_name}")
        console.print(f"Path: {', '.join(str(p) for p in section.paths)}")
        console.print()
        
        choices = [
            questionary.Choice(f"Paths ({', '.join(str(p) for p in section.paths)})", value="paths"),
            questionary.Choice(f"Repo Base ({section.repo_base})", value="repo_base"),
            questionary.Choice(f"Update Strategy ({section.update_strategy})", value="update_strategy"),
            questionary.Choice(f"Secrets Filter ({'Enabled' if section.secrets_filter else 'Disabled'})", value="secrets_filter"),
            questionary.Choice(f"Inherits ({', '.join(section.inherits) if section.inherits else 'None'})", value="inherits"),
            questionary.Choice(f"Pre-deploy Hook ({section.pre_deploy or 'None'})", value="pre_deploy"),
            questionary.Choice(f"Post-deploy Hook ({section.post_deploy or 'None'})", value="post_deploy"),
            questionary.Separator(),
            questionary.Choice("💾 Save & Return", value="save", shortcut_key="s"),
            questionary.Choice("🔙 Cancel", value="cancel", shortcut_key="q"),
        ]
        
        field = questionary.select("Select field to edit:", choices=choices).ask()
        
        if not field or field == "cancel":
            return
            
        if field == "save":
            try:
                # Re-add section to save changes (updates existing)
                config.add_section(
                    name=section_name,
                    paths=[str(p) for p in section.paths],
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
            val = questionary.confirm("Enable Secrets Filter?", default=section.secrets_filter).ask()
            section.secrets_filter = val
            
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

def run_global_wizard(config: GlobalConfig):
    """Edit global configuration."""
    while True:
        console.clear()
        print_banner("Global Configuration")
        console.print()
        
        choices = [
            questionary.Choice(f"Default Editor ({config.editor or 'System Default'})", value="editor"),
            questionary.Choice(f"Remote URL ({config.remote_url or 'Not Set'})", value="remote_url"),
            questionary.Choice(f"Default Secrets Filter ({'Enabled' if config.secrets_filter_enabled else 'Disabled'})", value="secrets_filter"),
            questionary.Separator(),
            questionary.Choice("💾 Save & Return", value="save", shortcut_key="s"),
            questionary.Choice("🔙 Cancel", value="cancel", shortcut_key="q"),
        ]
        
        field = questionary.select("Select setting to edit:", choices=choices).ask()
        
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
             # We need to update the deeply nested 'defaults' dict
             current = config.secrets_filter_enabled
             val = questionary.confirm("Enable Secrets Filter by default?", default=current).ask()
             if "defaults" not in config._data:
                 config._data["defaults"] = {}
             config._data["defaults"]["secrets_filter"] = val

def run_templates_wizard(config: DotManConfig):
    """Add or edit templates."""
    while True:
        templates = config.get_local_templates()
        
        choices = []
        if templates:
            for name in templates:
                choices.append(questionary.Choice(f"📝 {name}", value=name))
        
        choices.append(questionary.Separator())
        choices.append(questionary.Choice("➕ Add New Template", value="add_new"))
        choices.append(questionary.Choice("🔙 Back", value="back", shortcut_key="q"))
        
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
        print_banner(f"Template: {name}")
        
        current_pre = template.get("pre_deploy", "None")
        current_post = template.get("post_deploy", "None")
        current_strategy = template.get("update_strategy", "Default")
        
        choices = [
            questionary.Choice(f"Pre-deploy Hook ({current_pre})", value="pre_deploy"),
            questionary.Choice(f"Post-deploy Hook ({current_post})", value="post_deploy"),
            questionary.Choice(f"Update Strategy ({current_strategy})", value="update_strategy"),
            questionary.Separator(),
            questionary.Choice("💾 Save & Return", value="save", shortcut_key="s"),
            questionary.Choice("🗑️  Delete Template", value="delete"),
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
