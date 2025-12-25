"""Git operations wrapper for dot-man."""

from pathlib import Path
from typing import Iterator

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError

from .constants import REPO_DIR, DEFAULT_BRANCH, GIT_IGNORE_PATTERNS
from .exceptions import (
    GitNotFoundError,
    GitOperationError,
    BranchNotFoundError,
    NotInitializedError,
)


class GitManager:
    """Wrapper for git operations on the dot-man repository."""

    def __init__(self, repo_path: Path | None = None):
        self._repo_path = repo_path or REPO_DIR
        self._repo: Repo | None = None

    @property
    def repo(self) -> Repo:
        """Get the git repository object."""
        if self._repo is None:
            try:
                self._repo = Repo(self._repo_path)
            except InvalidGitRepositoryError:
                raise NotInitializedError(
                    f"Not a git repository: {self._repo_path}"
                )
        return self._repo

    def is_initialized(self) -> bool:
        """Check if the repository is initialized."""
        try:
            return self._repo_path.exists() and (self._repo_path / ".git").exists()
        except Exception:
            return False

    def init(self) -> None:
        """Initialize a new git repository."""
        try:
            self._repo_path.mkdir(parents=True, exist_ok=True)
            self._repo = Repo.init(self._repo_path)

            # Create .gitignore
            gitignore_path = self._repo_path / ".gitignore"
            gitignore_path.write_text("\n".join(GIT_IGNORE_PATTERNS) + "\n")

            # Configure git
            with self._repo.config_writer() as config:
                if not config.has_option("user", "name"):
                    config.set_value("user", "name", "dot-man")
                if not config.has_option("user", "email"):
                    config.set_value("user", "email", "dot-man@localhost")

        except Exception as e:
            raise GitOperationError(f"Failed to initialize repository: {e}")

    def current_branch(self) -> str:
        """Get the current branch name."""
        try:
            return self.repo.active_branch.name
        except TypeError:
            # Detached HEAD state
            return "HEAD"

    def list_branches(self) -> list[str]:
        """List all local branches."""
        return [head.name for head in self.repo.heads]

    def branch_exists(self, name: str) -> bool:
        """Check if a branch exists."""
        return name in self.list_branches()

    def create_branch(self, name: str) -> None:
        """Create a new branch."""
        try:
            self.repo.create_head(name)
        except Exception as e:
            raise GitOperationError(f"Failed to create branch '{name}': {e}")

    def checkout(self, branch: str, create: bool = False) -> None:
        """Checkout a branch, optionally creating it."""
        try:
            if create and not self.branch_exists(branch):
                self.create_branch(branch)

            self.repo.heads[branch].checkout()
        except IndexError:
            raise BranchNotFoundError(f"Branch not found: {branch}")
        except Exception as e:
            raise GitOperationError(f"Failed to checkout '{branch}': {e}")

    def is_dirty(self) -> bool:
        """Check if the repository has uncommitted changes."""
        return self.repo.is_dirty(untracked_files=True)

    def get_status(self) -> dict[str, list[str]]:
        """Get the repository status.

        Returns:
            Dictionary with keys: 'modified', 'new', 'deleted', 'untracked'
        """
        status = {
            "modified": [],
            "new": [],
            "deleted": [],
            "untracked": [],
        }

        # Get diff from index
        for diff in self.repo.index.diff(None):
            if diff.change_type == "M":
                status["modified"].append(diff.a_path)
            elif diff.change_type == "D":
                status["deleted"].append(diff.a_path)
            elif diff.change_type == "A":
                status["new"].append(diff.a_path)

        # Get untracked files
        status["untracked"] = self.repo.untracked_files

        return status

    def add_all(self) -> None:
        """Stage all changes."""
        try:
            self.repo.git.add(A=True)
        except Exception as e:
            raise GitOperationError(f"Failed to stage changes: {e}")

    def commit(self, message: str) -> str | None:
        """Create a commit with the given message.

        Returns:
            Commit SHA if commit was made, None if nothing to commit
        """
        if not self.is_dirty():
            return None

        try:
            self.add_all()
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except Exception as e:
            raise GitOperationError(f"Failed to commit: {e}")

    def get_commits(self, count: int = 10) -> Iterator[dict]:
        """Get recent commits.

        Yields:
            Dictionary with: sha, message, author, date
        """
        try:
            for commit in self.repo.iter_commits(max_count=count):
                yield {
                    "sha": commit.hexsha[:7],
                    "message": commit.message.strip().split("\n")[0],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                }
        except Exception:
            return

    def delete_branch(self, name: str, force: bool = False) -> None:
        """Delete a branch."""
        if not self.branch_exists(name):
            raise BranchNotFoundError(f"Branch not found: {name}")

        if name == self.current_branch():
            raise GitOperationError("Cannot delete the current branch")

        try:
            if force:
                self.repo.delete_head(name, force=True)
            else:
                self.repo.delete_head(name)
        except GitCommandError as e:
            if "not fully merged" in str(e.stderr):
                from .exceptions import BranchNotMergedError
                raise BranchNotMergedError(f"Branch '{name}' is not fully merged")
            raise GitOperationError(f"Failed to delete branch '{name}': {e}")
        except Exception as e:
            raise GitOperationError(f"Failed to delete branch '{name}': {e}")

    def has_remote(self) -> bool:
        """Check if a remote 'origin' exists."""
        return "origin" in [r.name for r in self.repo.remotes]

    def get_remote_url(self) -> str | None:
        """Get the URL of the 'origin' remote."""
        if not self.has_remote():
            return None
        return self.repo.remotes.origin.url

    def set_remote(self, url: str) -> None:
        """Set or update the 'origin' remote URL."""
        try:
            if self.has_remote():
                self.repo.remotes.origin.set_url(url)
            else:
                self.repo.create_remote("origin", url)
        except Exception as e:
            raise GitOperationError(f"Failed to set remote: {e}")
