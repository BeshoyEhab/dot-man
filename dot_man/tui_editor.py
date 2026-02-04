"""Interactive Configuration Editor for dot-man."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    Input,
    Label,
    Button,
    Checkbox,
    Select,
    Static,
    ListView,
    ListItem,
    TabbedContent,
    TabPane,
)
from textual.containers import Vertical, Horizontal, VerticalScroll, Container
from typing import Any, Optional
from textual.binding import Binding
from textual.message import Message

from .config import DotManConfig, Section
from .operations import get_operations


class SectionForm(VerticalScroll):
    """Form to edit a specific configuration section."""

    class Submitted(Message):
        """Event sent when form is submitted."""
        def __init__(self, section_data: dict):
            self.section_data = section_data
            super().__init__()

    def __init__(self, section_name: str, config: DotManConfig):
        super().__init__()
        self.section_name = section_name
        self.config = config
        self.section = config.get_section(section_name)

    def compose(self) -> ComposeResult:
        with Vertical(classes="form-container"):
            yield Label(f"Editing: {self.section_name}", classes="form-title")
            
            # Paths
            yield Label("Paths (comma separated)", classes="field-label")
            paths_str = ", ".join(str(p) for p in self.section.paths)
            yield Input(value=paths_str, id="paths", placeholder="~/.bashrc, ~/.config/nvim")
            
            # Repo Base
            yield Label("Repo Directory Name", classes="field-label")
            yield Input(value=self.section.repo_base, id="repo_base", placeholder="bashrc")
            
            # Update Strategy
            yield Label("Update Strategy", classes="field-label")
            strategies = [("replace", "replace"), ("rename_old", "rename_old"), ("ignore", "ignore")]
            yield Select(strategies, value=self.section.update_strategy, id="update_strategy", allow_blank=False)
            
            # Secrets Filter
            yield Label("Security", classes="field-label")
            yield Checkbox("Filter Secrets (Redact)", value=self.section.secrets_filter, id="secrets_filter")
            
            # Hooks (Advanced)
            yield Label("Hooks (Advanced)", classes="section-header")
            
            yield Label("Pre-Deploy Command", classes="field-label")
            yield Input(value=self.section.pre_deploy or "", id="pre_deploy", placeholder="e.g. echo 'Starting...'")
            
            yield Label("Post-Deploy Command", classes="field-label")
            yield Input(value=self.section.post_deploy or "", id="post_deploy", placeholder="e.g. source ~/.bashrc")
            
            # Save Button
            yield Button("Save Changes", variant="primary", id="save-btn", classes="action-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save()

    def _save(self):
        # Gather data
        paths_val = self.query_one("#paths", Input).value
        paths = [p.strip() for p in paths_val.split(",") if p.strip()]
        
        repo_base = self.query_one("#repo_base", Input).value
        strategy = self.query_one("#update_strategy", Select).value
        secrets = self.query_one("#secrets_filter", Checkbox).value
        pre = self.query_one("#pre_deploy", Input).value
        post = self.query_one("#post_deploy", Input).value

        # Construct section data dict (matching config structure)
        data = {
            "paths": paths,
            "repo_base": repo_base,
            "update_strategy": strategy,
            "secrets_filter": secrets,
            "pre_deploy": pre if pre else None,
            "post_deploy": post if post else None,
        }
        
        self.post_message(self.Submitted(data))


class ConfigEditorScreen(Screen):
    """Main screen for interactive configuration editing."""

    CSS = """
    ConfigEditorScreen {
        layers: base overlay;
    }

    #sidebar {
        width: 30;
        dock: left;
        height: 100%;
        background: $surface;
        border-right: solid $primary;
    }

    #main-panel {
        height: 100%;
        padding: 1 2;
    }

    .form-title {
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 1;
        width: 100%;
        text-align: center;
        margin-bottom: 1;
    }

    .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    
    .section-header {
        color: $secondary;
        text-style: bold;
        margin-top: 2;
        border-bottom: solid $secondary;
    }

    .action-btn {
        margin-top: 2;
        width: 100%;
    }

    ListView {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+r", "toggle_raw", "Raw Mode"),
    ]

    def __init__(self):
        super().__init__()
        self.ops = get_operations()
        self.config = self.ops.dotman_config
        self.current_section = None

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            # Sidebar with sections
            with Vertical(id="sidebar"):
                yield Label("Sections", classes="form-title")
                yield ListView(id="section-list")
                yield Button("New Section", id="new-section-btn", variant="success")
            
            # Main Edit Area
            with Container(id="main-panel"):
                yield Label("Select a section to edit", id="placeholder-msg")

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_sections()

    def refresh_sections(self) -> None:
        list_view = self.query_one("#section-list", ListView)
        list_view.clear()
        
        params = self.config.get_section_names()
        for name in params:
            list_view.append(ListItem(Label(name), name=name))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item:
            section_name = event.item.name
            self.edit_section(section_name)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item:
            section_name = event.item.name
            self.edit_section(section_name)

    def edit_section(self, section_name: Optional[str]) -> None:
        if not section_name:
            return
        self.current_section = section_name
        container = self.query_one("#main-panel", Container)
        container.remove_children()
        container.mount(SectionForm(section_name, self.config))

    def on_section_form_submitted(self, event: SectionForm.Submitted) -> None:
        """Handle save from form."""
        if not self.current_section:
            return
            
        # Update config object directly (in-memory)
        # Note: We need a method in Config to update section data
        # For now, we manually update the dict and save
        try:
            # We are modifying private _data structure of config for simplicity in this task
            # A proper API update to Config class would be better but this works for now
            # as long as we validate.
            
            # Actually, let's just re-add the section with overwrite logic or update
            # The add_section raises error if exists.
            # We will manually update the internal dict.
            data = self.config._data[self.current_section]
            
            # Update fields
            data["paths"] = event.section_data["paths"]
            data["repo_base"] = event.section_data["repo_base"]
            data["update_strategy"] = event.section_data["update_strategy"]
            data["secrets_filter"] = event.section_data["secrets_filter"]
            
            if event.section_data["pre_deploy"]:
                data["pre_deploy"] = event.section_data["pre_deploy"]
            elif "pre_deploy" in data:
                del data["pre_deploy"]
                
            if event.section_data["post_deploy"]:
                data["post_deploy"] = event.section_data["post_deploy"]
            elif "post_deploy" in data:
                del data["post_deploy"]

            self.config.save()
            self.notify(f"Saved section: {self.current_section}")
            
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-section-btn":
            self.app.push_screen(AddSectionModal(), self.on_add_result)
    
    def on_add_result(self, result: Any) -> None:
        if result:
            self.refresh_sections()


class AddSectionModal(Screen):
    """Modal to add a new section."""
    
    CSS = """
    AddSectionModal {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }
    
    #modal-dialog {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $success;
        padding: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog"):
            yield Label("Add New Section", classes="form-title")
            yield Label("Section Name")
            yield Input(id="new-name", placeholder="e.g. nvim-config")
            yield Label("Path")
            yield Input(id="new-path", placeholder="~/.config/nvim")
            yield Horizontal(
                Button("Cancel", id="cancel", variant="error"),
                Button("Add", id="add", variant="success"),
                classes="action-row"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
        elif event.button.id == "add":
            self._add()

    def _add(self):
        name = self.query_one("#new-name", Input).value.strip()
        path = self.query_one("#new-path", Input).value.strip()
        
        if not name or not path:
            self.notify("Name and path are required", severity="error")
            return
            
        try:
            ops = get_operations()
            # Use CLI logic or Config add_section
            ops.dotman_config.add_section(name, [path])
            ops.dotman_config.save()
            ops.save_section(ops.dotman_config.get_section(name)) # Initial save/copy
            
            self.notify(f"Added section {name}")
            self.dismiss(True)
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

