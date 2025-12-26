"""Interactive TUI for dot-man using textual."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, ListView, ListItem, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding

from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from pathlib import Path

from .core import GitManager
from .config import GlobalConfig, DotManConfig
from .files import compare_files, get_file_status


class FilesPanel(Static):
    """Widget to display tracked files and their status."""
    
    def update_files(self, sections: list, config: DotManConfig, current_branch: str):
        table = Table(show_header=True, header_style="bold", expand=True, box=None)
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center", width=8)
        table.add_column("Hooks", style="dim", width=10)
        
        for section_name in sections[:8]:  # Limit for space
            try:
                section = config.get_section(section_name)
                local_path = section["local_path"]
                repo_path = section["repo_path"]
                
                # Determine status
                if not local_path.exists():
                    status = "[red]missing[/red]"
                elif not repo_path.exists():
                    status = "[yellow]new[/yellow]"
                elif compare_files(local_path, repo_path):
                    status = "[green]✓[/green]"
                else:
                    status = "[yellow]modified[/yellow]"
                
                # Hooks
                hooks = []
                if section.get("pre_deploy"):
                    hooks.append("pre")
                if section.get("post_deploy"):
                    hooks.append("post")
                
                # Shorten path for display
                display_path = str(local_path).replace(str(Path.home()), "~")
                if len(display_path) > 30:
                    display_path = "..." + display_path[-27:]
                
                table.add_row(display_path, status, ", ".join(hooks) or "-")
            except Exception:
                pass
        
        if len(sections) > 8:
            table.add_row(f"... +{len(sections) - 8} more", "", "")
        
        self.update(Panel(table, title=f"Files ({len(sections)})", border_style="magenta"))


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
        pre_hooks = sum(1 for s in sections if config.get_section(s).get("pre_deploy"))
        post_hooks = sum(1 for s in sections if config.get_section(s).get("post_deploy"))
        
        if pre_hooks or post_hooks:
            text.append("\nHooks:\n", style="bold")
            if pre_hooks:
                text.append(f"  • {pre_hooks} pre-deploy\n", style="cyan")
            if post_hooks:
                text.append(f"  • {post_hooks} post-deploy\n", style="cyan")
        
        text.append("\n[Press Enter to switch]", style="dim italic")
        
        self.update(Panel(text, title="Switch Preview", border_style="yellow"))


class SyncStatus(Static):
    """Widget to display sync status."""
    
    def update_status(self, status: dict):
        text = Text()
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
        self.update(Panel(text, title="Sync", border_style="green"))


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
        Binding("s", "sync", "Sync"),
        Binding("d", "deploy", "Deploy"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def __init__(self):
        super().__init__()
        self.git = GitManager()
        self.global_config = GlobalConfig()
        self.global_config.load()
        self.dotman_config = DotManConfig()
        self.dotman_config.load()
        self.current_branch = self.global_config.current_branch
        self.sections = self.dotman_config.get_sections()
        
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
        self.sub_title = f"Branch: {self.current_branch}"
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
    
    def _update_files(self) -> None:
        files_widget = self.query_one("#files-panel", FilesPanel)
        files_widget.update_files(self.sections, self.dotman_config, self.current_branch)
    
    def _update_sync_status(self) -> None:
        sync_widget = self.query_one("#sync-status", SyncStatus)
        try:
            status = self.git.get_sync_status()
            sync_widget.update_status(status)
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
        self.notify("Running sync...")
        self.exit(result=("sync", None))
    
    def action_deploy(self) -> None:
        table = self.query_one("#branch-table", DataTable)
        row_key = table.cursor_row
        if row_key is not None:
            branches = self.git.list_branches()
            if 0 <= row_key < len(branches):
                branch = branches[row_key]
                self.notify(f"Deploying {branch}...")
                self.exit(result=("deploy", branch))
    
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
