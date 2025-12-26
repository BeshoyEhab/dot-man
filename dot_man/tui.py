"""Interactive TUI for dot-man using textual."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual import events

from rich.text import Text
from rich.panel import Panel

from .core import GitManager
from .config import GlobalConfig, DotManConfig


class BranchInfo(Static):
    """Widget to display branch information."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._branch = None
        
    def set_branch(self, branch_name: str, stats: dict):
        self._branch = branch_name
        info = Text()
        info.append(f"Branch: ", style="bold")
        info.append(f"{branch_name}\n\n", style="cyan")
        info.append(f"Files: ", style="bold")
        info.append(f"{stats['file_count']}\n", style="green")
        info.append(f"Commits: ", style="bold")
        info.append(f"{stats['commit_count']}\n", style="yellow")
        info.append(f"Last: ", style="bold")
        info.append(f"{stats['last_commit_date']}\n", style="dim")
        info.append(f"\n{stats['last_commit_msg']}", style="italic dim")
        self.update(Panel(info, title="Details", border_style="blue"))


class SyncStatus(Static):
    """Widget to display sync status."""
    
    def update_status(self, status: dict):
        text = Text()
        if not status.get("remote_configured"):
            text.append("⚠️ No remote\n", style="yellow")
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
        layout: grid;
        grid-size: 2;
        grid-columns: 2fr 1fr;
    }
    
    #left-pane {
        height: 100%;
    }
    
    #right-pane {
        height: 100%;
    }
    
    #branch-table {
        height: 1fr;
    }
    
    #branch-info {
        height: auto;
        min-height: 10;
    }
    
    #sync-status {
        height: auto;
        min-height: 5;
    }
    
    DataTable {
        height: 100%;
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
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left-pane"):
                yield DataTable(id="branch-table")
            with Vertical(id="right-pane"):
                yield BranchInfo(id="branch-info")
                yield SyncStatus(id="sync-status")
        yield Footer()
    
    def on_mount(self) -> None:
        self.title = "dot-man"
        self.sub_title = f"Branch: {self.current_branch}"
        self._load_branches()
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
    
    def _update_sync_status(self) -> None:
        sync_widget = self.query_one("#sync-status", SyncStatus)
        try:
            status = self.git.get_sync_status()
            sync_widget.update_status(status)
        except Exception:
            sync_widget.update_status({"remote_configured": False})
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key:
            branch_name = str(event.row_key.value)
            stats = self.git.get_branch_stats(branch_name)
            info_widget = self.query_one("#branch-info", BranchInfo)
            info_widget.set_branch(branch_name, stats)
    
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
        self._update_sync_status()
        self.notify("Refreshed")


def run_tui():
    """Run the TUI and handle the result."""
    app = DotManApp()
    result = app.run()
    return result
