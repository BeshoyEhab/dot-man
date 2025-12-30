"""Interactive TUI for dot-man using textual."""

import subprocess
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Input, Label, Button
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.binding import Binding
from textual.screen import ModalScreen
from textual import events

from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from .core import GitManager
from .config import GlobalConfig, DotManConfig
from .files import compare_files, get_file_status


# All available commands with (name, description, command_args, needs_input)
COMMANDS = [
    ("status", "Show current repository status", ["status"], False),
    ("status -v", "Show verbose status with file details", ["status", "-v"], False),
    ("status --secrets", "Show status and scan for secrets", ["status", "--secrets"], False),
    ("edit", "Open config in your editor", ["edit"], True),
    ("edit --global", "Open global config in editor", ["edit", "--global"], True),
    ("audit", "Scan all files for secrets", ["audit"], False),
    ("audit --strict", "Scan for secrets (fail on any)", ["audit", "--strict"], False),
    ("branch list", "List all configuration branches", ["branch", "list"], False),
    ("branch delete", "Delete a branch (prompts for name)", ["branch", "delete"], "branch"),
    ("remote get", "Show current remote URL", ["remote", "get"], False),
    ("remote set", "Set remote URL (prompts for URL)", ["remote", "set"], "url"),
    ("sync", "Sync with remote (pull + push)", ["sync"], False),
    ("sync --push-only", "Push to remote only", ["sync", "--push-only"], False),
    ("sync --pull-only", "Pull from remote only", ["sync", "--pull-only"], False),
    ("setup", "Interactive remote repository setup", ["setup"], True),
    ("repo", "Show repository path", ["repo"], False),
]


class OutputModal(ModalScreen):
    """Modal screen to display command output."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("enter", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]
    
    CSS = """
    OutputModal {
        align: center middle;
    }
    
    #output-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #output-title {
        dock: top;
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    #output-scroll {
        height: 1fr;
        border: solid $secondary;
        padding: 1;
    }
    
    #output-text {
        width: 100%;
    }
    
    #close-hint {
        dock: bottom;
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    """
    
    def __init__(self, title: str, output: str, is_error: bool = False):
        super().__init__()
        self.output_title = title
        self.output_text = output
        self.is_error = is_error
    
    def compose(self) -> ComposeResult:
        with Vertical(id="output-container"):
            yield Label(f"📋 {self.output_title}", id="output-title")
            with VerticalScroll(id="output-scroll"):
                style = "red" if self.is_error else ""
                yield Static(self.output_text, id="output-text")
            yield Label("[Escape/Enter/q to close]", id="close-hint")
    
    def action_dismiss(self) -> None:
        self.app.pop_screen()


class InputModal(ModalScreen):
    """Modal screen to get input from user."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    
    CSS = """
    InputModal {
        align: center middle;
    }
    
    #input-container {
        width: 60;
        height: 12;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    
    #input-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    #input-field {
        margin: 1 0;
    }
    
    #input-hint {
        height: 1;
        content-align: center middle;
        color: $text-muted;
    }
    """
    
    def __init__(self, title: str, prompt: str, callback):
        super().__init__()
        self.input_title = title
        self.prompt = prompt
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        with Vertical(id="input-container"):
            yield Label(f"📝 {self.input_title}", id="input-title")
            yield Label(self.prompt)
            yield Input(id="input-field", placeholder="Enter value...")
            yield Label("[Enter to submit, Escape to cancel]", id="input-hint")
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if value:
            self.app.pop_screen()
            self.callback(value)
    
    def action_cancel(self) -> None:
        self.app.pop_screen()


class CommandPalette(ModalScreen):
    """Command palette for executing any dot-man command."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "select", "Select"),
    ]
    
    CSS = """
    CommandPalette {
        align: center middle;
    }
    
    #palette-container {
        width: 70;
        height: 24;
        background: $surface;
        border: thick $accent;
        padding: 1;
    }
    
    #palette-title {
        height: 3;
        content-align: center middle;
        background: $accent;
        color: $text;
        text-style: bold;
    }
    
    #search-input {
        margin: 1 0;
    }
    
    #commands-scroll {
        height: 1fr;
        border: solid $secondary;
    }
    
    .command-item {
        height: 2;
        padding: 0 1;
    }
    
    .command-item:hover {
        background: $primary-lighten-2;
    }
    
    .command-item.selected {
        background: $accent;
        color: $text;
    }
    
    .command-name {
        text-style: bold;
    }
    
    .command-desc {
        color: $text-muted;
    }
    """
    
    def __init__(self, on_command):
        super().__init__()
        self.on_command = on_command
        self.filtered_commands = list(COMMANDS)
        self.selected_index = 0
    
    def compose(self) -> ComposeResult:
        with Vertical(id="palette-container"):
            yield Label("⌨ Command Palette", id="palette-title")
            yield Input(id="search-input", placeholder="Type to filter commands...")
            with VerticalScroll(id="commands-scroll"):
                for i, (name, desc, _, _) in enumerate(COMMANDS):
                    selected = "selected" if i == 0 else ""
                    yield Static(
                        f"[bold]{name}[/bold]\n[dim]{desc}[/dim]",
                        classes=f"command-item {selected}",
                        id=f"cmd-{i}"
                    )
    
    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower().strip()
        self.filtered_commands = [
            cmd for cmd in COMMANDS
            if query in cmd[0].lower() or query in cmd[1].lower()
        ]
        self._update_command_list()
        self.selected_index = 0
        self._update_selection()
    
    def _update_command_list(self) -> None:
        scroll = self.query_one("#commands-scroll", VerticalScroll)
        scroll.remove_children()
        for i, (name, desc, _, _) in enumerate(self.filtered_commands):
            selected = "selected" if i == self.selected_index else ""
            scroll.mount(Static(
                f"[bold]{name}[/bold]\n[dim]{desc}[/dim]",
                classes=f"command-item {selected}",
                id=f"cmd-{i}"
            ))
    
    def _update_selection(self) -> None:
        items = list(self.query(".command-item"))
        for i, item in enumerate(items):
            if i == self.selected_index:
                item.add_class("selected")
                # Scroll the selected item into view
                item.scroll_visible()
            else:
                item.remove_class("selected")
    
    def action_cursor_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()
    
    def action_cursor_down(self) -> None:
        if self.selected_index < len(self.filtered_commands) - 1:
            self.selected_index += 1
            self._update_selection()
    
    def action_select(self) -> None:
        if self.filtered_commands:
            cmd = self.filtered_commands[self.selected_index]
            self.app.pop_screen()
            self.on_command(cmd)
    
    def action_close(self) -> None:
        self.app.pop_screen()


class HelpScreen(ModalScreen):
    """Help screen showing all available keybindings."""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    CSS = """
    HelpScreen {
        align: center middle;
    }
    
    #help-container {
        width: 60;
        height: 22;
        background: $surface;
        border: thick $success;
        padding: 1 2;
    }
    
    #help-title {
        height: 3;
        content-align: center middle;
        background: $success;
        text-style: bold;
    }
    
    #help-content {
        height: 1fr;
        padding: 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        help_text = """
[bold cyan]Navigation[/bold cyan]
  ↑/↓        Navigate branches
  Enter      Switch to selected branch
  
[bold cyan]Quick Commands[/bold cyan]
  c          Open command palette
  s          Sync with remote
  d          Deploy selected branch
  e          Edit config file
  a          Run security audit
  r          Refresh display
  
[bold cyan]General[/bold cyan]
  ?          Show this help
  q          Quit
"""
        with Vertical(id="help-container"):
            yield Label("❓ Keyboard Shortcuts", id="help-title")
            yield Static(help_text.strip(), id="help-content")
    
    def action_close(self) -> None:
        self.app.pop_screen()


class FilesPanel(Static):
    """Widget to display tracked files and their status grouped by section."""
    
    def update_files(self, section_names: list, config: DotManConfig, current_branch: str):
        table = Table(show_header=True, header_style="bold", expand=True, box=None)
        table.add_column("Section / Path", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Hooks", style="dim", width=8)
        
        total_paths = 0
        shown_sections = 0
        max_sections = 6
        
        for section_name in section_names:
            if shown_sections >= max_sections:
                break
            
            try:
                section = config.get_section(section_name)
                paths = section.paths
                total_paths += len(paths)
                
                # Section header row
                hooks_str = ""
                if section.pre_deploy:
                    hooks_str += "pre "
                if section.post_deploy:
                    hooks_str += "post"
                
                table.add_row(
                    f"[bold magenta][{section_name}][/bold magenta]",
                    "",
                    hooks_str.strip() or "-"
                )
                
                # Show paths under section (limit to 3 per section)
                for i, local_path in enumerate(paths[:3]):
                    # Icon based on type
                    if local_path.is_dir():
                        icon = "📁"
                    elif local_path.is_file():
                        icon = "📄"
                    else:
                        icon = "❓"
                    
                    # Get repo path
                    repo_path = section.get_repo_path(local_path, config.repo_path)
                    
                    # Determine status
                    if not local_path.exists():
                        status = "[red]missing[/red]"
                    elif not repo_path.exists():
                        status = "[blue]new[/blue]"
                    elif compare_files(local_path, repo_path):
                        status = "[green]✓[/green]"
                    else:
                        status = "[yellow]modified[/yellow]"
                    
                    # Shorten path for display
                    display_path = str(local_path).replace(str(Path.home()), "~")
                    if len(display_path) > 28:
                        display_path = "..." + display_path[-25:]
                    
                    table.add_row(f"  {icon} {display_path}", status, "")
                
                if len(paths) > 3:
                    table.add_row(f"  [dim]... +{len(paths) - 3} more[/dim]", "", "")
                
                shown_sections += 1
                
            except Exception:
                pass
        
        remaining = len(section_names) - shown_sections
        if remaining > 0:
            table.add_row(f"[dim]... +{remaining} more sections[/dim]", "", "")
        
        title = f"Sections ({len(section_names)}) • Paths ({total_paths})"
        self.update(Panel(table, title=title, border_style="magenta"))


class SwitchPreview(Static):
    """Widget to show what will happen when switching."""
    
    def update_preview(self, from_branch: str, to_branch: str, sections: list, config: DotManConfig):
        text = Text()
        
        if from_branch == to_branch:
            text.append("Already on this branch", style="dim")
            self.update(Panel(text, title="Switch Preview", border_style="dim"))
            return
        
        text.append(f"Switch: ", style="bold")
        text.append(f"{from_branch}", style="yellow")
        text.append(" → ", style="dim")
        text.append(f"{to_branch}\n\n", style="green")
        
        text.append("Actions:\n", style="bold")
        text.append("  1. Save current files to ", style="dim")
        text.append(f"'{from_branch}'\n", style="yellow")
        text.append("  2. Deploy files from ", style="dim")
        text.append(f"'{to_branch}'\n", style="green")
        
        # Count hooks
        pre_hooks = sum(1 for s in sections if config.get_section(s).pre_deploy)
        post_hooks = sum(1 for s in sections if config.get_section(s).post_deploy)
        
        if pre_hooks or post_hooks:
            text.append("\nHooks:\n", style="bold")
            if pre_hooks:
                text.append(f"  • {pre_hooks} pre-deploy\n", style="cyan")
            if post_hooks:
                text.append(f"  • {post_hooks} post-deploy\n", style="cyan")
        
        text.append("\n[Press Enter to switch]", style="dim italic")
        
        self.update(Panel(text, title="Switch Preview", border_style="yellow"))


class SyncStatus(Static):
    """Widget to display sync status with optional audit badge."""
    
    def update_status(self, status: dict, audit_count: int = 0):
        text = Text()
        
        # Audit badge first if issues found
        if audit_count > 0:
            text.append(f"🔒 {audit_count} ", style="red bold")
        
        if not status.get("remote_configured"):
            text.append("⚠ No remote\n", style="yellow")
            text.append("Use: remote set <url>", style="dim")
        else:
            ahead = status.get("ahead", 0)
            behind = status.get("behind", 0)
            if ahead == 0 and behind == 0:
                text.append("✓ Synced", style="green bold")
            else:
                if ahead > 0:
                    text.append(f"↑ {ahead} ", style="green")
                if behind > 0:
                    text.append(f"↓ {behind}", style="yellow")
        
        title = "Sync" + (" • Audit" if audit_count > 0 else "")
        self.update(Panel(text, title=title, border_style="green" if audit_count == 0 else "red"))


class DotManApp(App):
    """Interactive TUI for dot-man."""
    
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #left-pane {
        width: auto;
        min-width: 25;
        max-width: 40;
        height: 100%;
    }
    
    #right-pane {
        width: 1fr;
        height: 100%;
    }
    
    #branch-table {
        height: 100%;
        border: solid blue;
    }
    
    DataTable {
        height: 100%;
    }
    
    DataTable > .datatable--cursor {
        background: $accent;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "switch_branch", "Switch"),
        Binding("c", "command_palette", "Commands"),
        Binding("s", "sync", "Sync"),
        Binding("d", "deploy", "Deploy"),
        Binding("e", "edit", "Edit"),
        Binding("a", "audit", "Audit"),
        Binding("r", "refresh", "Refresh"),
        Binding("question_mark", "help", "Help"),
    ]
    
    def __init__(self):
        super().__init__()
        self.git = GitManager()
        self.global_config = GlobalConfig()
        self.global_config.load()
        self.dotman_config = DotManConfig(global_config=self.global_config)
        self.dotman_config.load()
        self.current_branch = self.global_config.current_branch
        self.sections = self.dotman_config.get_section_names()
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-pane"):
                yield DataTable(id="branch-table")
            with Vertical(id="right-pane"):
                yield SwitchPreview(id="switch-preview")
                yield FilesPanel(id="files-panel")
                yield SyncStatus(id="sync-status")
        yield Footer()
    
    def on_mount(self) -> None:
        self.title = "dot-man"
        self.sub_title = f"Branch: {self.current_branch} | Press ? for help"
        self._load_branches()
        self._update_files()
        self._update_sync_status()
    
    def _load_branches(self) -> None:
        table = self.query_one("#branch-table", DataTable)
        table.clear(columns=True)
        table.add_columns("", "Branch", "Files", "Commits")
        table.cursor_type = "row"
        
        branches = self.git.list_branches()
        for branch in branches:
            stats = self.git.get_branch_stats(branch)
            marker = "✓" if branch == self.current_branch else ""
            style = "bold" if branch == self.current_branch else ""
            table.add_row(
                marker,
                Text(branch, style=style),
                str(stats["file_count"]),
                str(stats["commit_count"]),
                key=branch
            )
        
        # Select current branch
        if self.current_branch in branches:
            idx = branches.index(self.current_branch)
            table.move_cursor(row=idx)
            self._update_preview(self.current_branch)
    
    def _update_files(self, branch_name: str | None = None) -> None:
        """Update files panel, optionally for a specific branch."""
        files_widget = self.query_one("#files-panel", FilesPanel)
        
        # For the current branch, use loaded config
        if branch_name is None or branch_name == self.current_branch:
            files_widget.update_files(self.sections, self.dotman_config, self.current_branch)
        else:
            # For other branches, read the config using git show
            try:
                from .constants import DOT_MAN_TOML, DOT_MAN_INI
                
                # Try reading TOML config from the branch
                config_content = self.git.get_file_from_branch(branch_name, DOT_MAN_TOML)
                
                if config_content is None:
                    # Try old INI format
                    config_content = self.git.get_file_from_branch(branch_name, DOT_MAN_INI)
                    if config_content:
                        # Parse INI and show sections
                        import configparser
                        config = configparser.ConfigParser()
                        config.read_string(config_content)
                        sections = [s for s in config.sections() if s != "DEFAULT"]
                        
                        table = Table(show_header=True, header_style="bold", expand=True, box=None)
                        table.add_column("Section / Path", style="cyan", no_wrap=True)
                        table.add_column("Status", justify="center", width=10)
                        
                        for section in sections[:8]:
                            local_path = config.get(section, "local_path", fallback="")
                            display_path = local_path.replace("~/", "")
                            table.add_row(f"📁 {display_path}", "[dim]branch[/dim]")
                        
                        if len(sections) > 8:
                            table.add_row(f"[dim]... +{len(sections) - 8} more[/dim]", "")
                        
                        files_widget.update(Panel(table, title=f"Files ({branch_name})", border_style="blue"))
                        return
                
                if config_content:
                    # Parse TOML config
                    data = tomllib.loads(config_content)
                    sections = [k for k in data.keys() if k != "templates"]
                    
                    table = Table(show_header=True, header_style="bold", expand=True, box=None)
                    table.add_column("Section / Path", style="cyan", no_wrap=True)
                    table.add_column("Tracked", justify="center", width=10)
                    
                    for section_name in sections[:8]:
                        section_data = data.get(section_name, {})
                        paths = section_data.get("paths", [])
                        
                        # Section header
                        table.add_row(f"[bold magenta][{section_name}][/bold magenta]", f"{len(paths)} paths")
                        
                        # Show paths
                        for path in paths[:3]:
                            display = path.replace("~/.config/", "").replace("~/", "")
                            table.add_row(f"  📁 {display}", "")
                        
                        if len(paths) > 3:
                            table.add_row(f"  [dim]... +{len(paths) - 3} more[/dim]", "")
                    
                    if len(sections) > 8:
                        table.add_row(f"[dim]... +{len(sections) - 8} more sections[/dim]", "")
                    
                    files_widget.update(Panel(table, title=f"Sections ({branch_name})", border_style="blue"))
                else:
                    files_widget.update(Panel(
                        Text("No config file in this branch", style="dim"),
                        title=f"Files ({branch_name})",
                        border_style="dim"
                    ))
            except Exception as e:
                files_widget.update(Panel(
                    Text(f"Could not load branch config: {e}", style="red"),
                    title="Files",
                    border_style="red"
                ))
    
    def _update_sync_status(self) -> None:
        sync_widget = self.query_one("#sync-status", SyncStatus)
        try:
            status = self.git.get_sync_status()
            # Get audit count for badge
            audit_count = 0
            try:
                from .operations import get_operations
                ops = get_operations()
                audit_results = ops.audit()
                audit_count = sum(len(matches) for _, matches in audit_results)
            except Exception:
                pass
            sync_widget.update_status(status, audit_count)
        except Exception:
            sync_widget.update_status({"remote_configured": False})
    
    def _update_preview(self, selected_branch: str) -> None:
        preview_widget = self.query_one("#switch-preview", SwitchPreview)
        preview_widget.update_preview(
            self.current_branch, 
            selected_branch, 
            self.sections, 
            self.dotman_config
        )
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            branch_name = str(event.row_key.value)
            self._update_preview(branch_name)
            # Update files panel to show that we can't preview other branch files
            self._update_files(branch_name)
    
    def _run_command(self, args: list, title: str = "Command Output") -> None:
        """Run a dot-man command and show output in modal."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "dot_man.cli"] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            output = result.stdout or result.stderr or "(no output)"
            is_error = result.returncode != 0
            self.push_screen(OutputModal(title, output.strip(), is_error))
        except subprocess.TimeoutExpired:
            self.push_screen(OutputModal(title, "Command timed out", True))
        except Exception as e:
            self.push_screen(OutputModal(title, f"Error: {e}", True))
    
    def _handle_command(self, cmd: tuple) -> None:
        """Handle a command from the palette."""
        name, desc, args, needs_input = cmd
        
        if needs_input == True:
            # Interactive command - exit TUI and run
            self.notify(f"Running {name} (interactive)...")
            self.exit(result=("run", args))
        elif needs_input:
            # Needs specific input - show input modal
            def on_input(value):
                full_args = args + [value]
                self._run_command(full_args, name)
            self.push_screen(InputModal(name, f"Enter {needs_input}:", on_input))
        else:
            # Run directly
            self._run_command(args, name)
    
    def action_command_palette(self) -> None:
        self.push_screen(CommandPalette(self._handle_command))
    
    def action_help(self) -> None:
        self.push_screen(HelpScreen())
    
    def action_switch_branch(self) -> None:
        table = self.query_one("#branch-table", DataTable)
        row_key = table.cursor_row
        if row_key is not None:
            branches = self.git.list_branches()
            if 0 <= row_key < len(branches):
                branch = branches[row_key]
                if branch != self.current_branch:
                    self.notify(f"Switching to {branch}...")
                    self.exit(result=("switch", branch))
    
    def action_sync(self) -> None:
        self._run_command(["sync"], "Sync")
    
    def action_deploy(self) -> None:
        table = self.query_one("#branch-table", DataTable)
        row_key = table.cursor_row
        if row_key is not None:
            branches = self.git.list_branches()
            if 0 <= row_key < len(branches):
                branch = branches[row_key]
                self.notify(f"Deploying {branch}...")
                self.exit(result=("deploy", branch))
    
    def action_edit(self) -> None:
        self.notify("Opening config in editor...")
        self.exit(result=("run", ["edit"]))
    
    def action_audit(self) -> None:
        self._run_command(["audit"], "Security Audit")
    
    def action_refresh(self) -> None:
        self._load_branches()
        self._update_files()
        self._update_sync_status()
        self.notify("Refreshed")


def run_tui():
    """Run the TUI and handle the result."""
    app = DotManApp()
    result = app.run()
    return result
