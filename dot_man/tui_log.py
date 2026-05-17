"""TUI Log viewer for dot-man."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Label, ListItem, ListView, Markdown

from .operations import get_operations


class CommitItem(ListItem):
    """A list item representing a single commit."""

    def __init__(self, commit: dict):
        super().__init__()
        self.commit = commit

    def compose(self) -> ComposeResult:
        sha = self.commit["sha"][:7]
        msg = self.commit["message"].split("\n")[0]
        yield Label(f"[cyan]{sha}[/cyan] {msg}")


class LogViewerApp(App):
    """A Textual app to view git commit history and diffs."""

    CSS = """
    #commit-list {
        width: 30%;
        border-right: solid green;
    }
    #commit-details {
        width: 70%;
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ListView(id="commit-list")
            with Vertical(id="commit-details"):
                yield Markdown(id="diff-view")
        yield Footer()

    def on_mount(self) -> None:
        ops = get_operations()
        commits = list(ops.git.get_commits(count=50))

        commit_list = self.query_one("#commit-list", ListView)
        for commit in commits:
            commit_list.append(CommitItem(commit))

        if commits:
            self._show_commit_diff(commits[0]["sha"])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, CommitItem):
            self._show_commit_diff(event.item.commit["sha"])

    def _show_commit_diff(self, sha: str) -> None:
        ops = get_operations()
        try:
            # We want the diff and stats
            commit_obj = ops.git.repo.commit(sha)

            md_content = f"# Commit {sha}\n\n"
            md_content += (
                f"**Author:** {commit_obj.author.name} <{commit_obj.author.email}>\n\n"
            )
            md_content += f"**Date:** {commit_obj.authored_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message_text = str(commit_obj.message)
            md_content += f"**Message:**\n\n```\n{message_text}\n```\n\n"

            diff_text = ops.git.repo.git.show(sha, patch=True, color="never")
            md_content += f"## Diff\n\n```diff\n{diff_text}\n```"

            diff_view = self.query_one("#diff-view", Markdown)
            diff_view.update(md_content)
        except Exception as e:
            diff_view = self.query_one("#diff-view", Markdown)
            diff_view.update(f"Error loading commit diff: {e}")


if __name__ == "__main__":
    app = LogViewerApp()
    app.run()
