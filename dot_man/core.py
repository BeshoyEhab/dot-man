"""Git operations wrapper for dot-man."""

from pathlib import Path
from typing import Iterator

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError

from .constants import REPO_DIR, DEFAULT_BRANCH, GIT_IGNORE_PATTERNS
from .exceptions import (
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
        except OSError:
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

        except (GitCommandError, OSError) as e:
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
        except (GitCommandError, OSError, ValueError) as e:
            raise GitOperationError(f"Failed to create branch '{name}': {e}")

    def checkout(self, branch: str, create: bool = False) -> None:
        """Checkout a branch, optionally creating it."""
        try:
            if create and not self.branch_exists(branch):
                self.create_branch(branch)

            self.repo.heads[branch].checkout()
        except IndexError:
            raise BranchNotFoundError(f"Branch not found: {branch}")
        except (GitCommandError, OSError) as e:
            raise GitOperationError(f"Failed to checkout '{branch}': {e}")

    def is_dirty(self) -> bool:
        """Check if the repository has uncommitted changes."""
        return self.repo.is_dirty(untracked_files=True)

    def get_status(self) -> dict[str, list[str]]:
        """Get the repository status.

        Returns:
            Dictionary with keys: 'modified', 'new', 'deleted', 'untracked'
        """
        status: dict[str, list[str]] = {
            "modified": [],
            "new": [],
            "deleted": [],
            "untracked": [],
        }

        # Get diff from index
        for diff in self.repo.index.diff(None):
            if diff.a_path:
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
        except (GitCommandError, OSError) as e:
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
        except (GitCommandError, OSError, ValueError) as e:
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
                    "message": str(commit.message).strip().split("\n")[0],
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                }
        except (GitCommandError, ValueError, OSError):
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
        except OSError as e:
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
        except (GitCommandError, ValueError) as e:
            raise GitOperationError(f"Failed to set remote: {e}")

    def fetch(self) -> None:
        """Fetch from origin remote."""
        if not self.has_remote():
            raise GitOperationError("No remote configured. Use 'dot-man remote set <url>' first.")
        try:
            self.repo.remotes.origin.fetch()
        except (GitCommandError, ValueError) as e:
            raise GitOperationError(f"Failed to fetch: {e}")

    def pull(self, rebase: bool = True) -> str:
        """Pull from origin remote.
        
        Automatically stashes uncommitted changes before pulling and
        restores them after.
        
        Returns:
            Summary message of what happened.
        """
        if not self.has_remote():
            raise GitOperationError("No remote configured. Use 'dot-man remote set <url>' first.")
        
        stashed = False
        try:
            current = self.current_branch()
            # Check if remote branch exists
            remote_refs = [ref.name for ref in self.repo.remotes.origin.refs]
            remote_branch = f"origin/{current}"
            
            if remote_branch not in remote_refs:
                return f"Remote branch '{current}' not found. Nothing to pull."
            
            # Stash uncommitted changes if dirty
            if self.is_dirty():
                self.repo.git.stash("save", "dot-man-auto-stash")
                stashed = True
            
            # Perform the pull
            if rebase:
                result = self.repo.git.pull("--rebase", "origin", current)
            else:
                result = self.repo.git.pull("origin", current)
            
            # Restore stashed changes
            if stashed:
                try:
                    self.repo.git.stash("pop")
                except GitCommandError as stash_error:
                    # Stash pop failed - likely a conflict
                    return (
                        f"{result if result else 'Pulled successfully.'}\n"
                        f"⚠ Warning: Stash pop failed. Your changes are in 'git stash'. "
                        f"Run 'git stash pop' manually to restore them.\n"
                        f"Error: {stash_error.stderr}"
                    )
            
            return result if result else "Already up to date."
        except GitCommandError as e:
            # Restore stash even on error
            if stashed:
                try:
                    self.repo.git.stash("pop")
                except Exception:
                    pass  # Best effort
            
            if "CONFLICT" in str(e.stdout) or "conflict" in str(e.stderr):
                raise GitOperationError(
                    "Merge conflict detected. Please resolve conflicts in:\n"
                    f"  {self._repo_path}\n"
                    "Then run 'git rebase --continue' or 'git rebase --abort'"
                )
            raise GitOperationError(f"Failed to pull: {e.stderr}")
        except OSError as e:
            # Restore stash even on error
            if stashed:
                try:
                    self.repo.git.stash("pop")
                except Exception:
                    pass  # Best effort
            raise GitOperationError(f"Failed to pull: {e}")

    def push(self, set_upstream: bool = True) -> str:
        """Push to origin remote.
        
        Returns:
            Summary message of what happened.
        """
        if not self.has_remote():
            raise GitOperationError("No remote configured. Use 'dot-man remote set <url>' first.")
        try:
            current = self.current_branch()
            if set_upstream:
                result = self.repo.git.push("-u", "origin", current)
            else:
                result = self.repo.git.push("origin", current)
            return result if result else "Pushed successfully."
        except GitCommandError as e:
            if "rejected" in str(e.stderr):
                raise GitOperationError(
                    "Push rejected. Remote has changes. Run 'dot-man sync' to pull first."
                )
            raise GitOperationError(f"Failed to push: {e.stderr}")
        except (GitCommandError, OSError) as e:
            raise GitOperationError(f"Failed to push: {e}")

    def get_branch_stats(self, branch_name: str) -> dict:
        """Get stats for a specific branch.
        
        Returns:
            Dictionary with: commit_count, last_commit_date, last_commit_msg, file_count
        """
        try:
            branch = self.repo.heads[branch_name]
            commits = list(self.repo.iter_commits(branch, max_count=100))
            
            last_commit = commits[0] if commits else None
            
            # Count files in branch
            tree = branch.commit.tree
            file_count = sum(1 for _ in tree.traverse() if _.type == 'blob')  # type: ignore 
            
            return {
                "commit_count": len(commits),
                "last_commit_date": last_commit.committed_datetime.strftime("%Y-%m-%d %H:%M") if last_commit else "N/A",
                "last_commit_msg": str(last_commit.message).strip().split("\n")[0][:50] if last_commit else "N/A",
                "file_count": file_count,
            }
        except (GitCommandError, ValueError, IndexError, OSError):
            return {
                "commit_count": 0,
                "last_commit_date": "N/A",
                "last_commit_msg": "N/A",
                "file_count": 0,
            }

    def get_sync_status(self) -> dict:
        """Get sync status with remote.
        
        Returns:
            Dictionary with: ahead, behind, remote_configured
        """
        if not self.has_remote():
            return {"ahead": 0, "behind": 0, "remote_configured": False}
        
        try:
            self.fetch()
            current = self.current_branch()
            remote_branch = f"origin/{current}"
            
            # Check if remote branch exists
            remote_refs = [ref.name for ref in self.repo.remotes.origin.refs]
            if remote_branch not in remote_refs:
                return {"ahead": 0, "behind": 0, "remote_configured": True, "remote_branch_exists": False}
            
            # Count ahead/behind
            ahead = len(list(self.repo.iter_commits(f"{remote_branch}..{current}")))
            behind = len(list(self.repo.iter_commits(f"{current}..{remote_branch}")))
            
            return {
                "ahead": ahead,
                "behind": behind,
                "remote_configured": True,
                "remote_branch_exists": True,
            }
        except (GitCommandError, ValueError, OSError):
            return {"ahead": 0, "behind": 0, "remote_configured": True, "error": True}

    def get_file_from_branch(self, branch: str, file_path: str) -> str | None:
        """Read a file's content from a specific branch without checkout.
        
        Args:
            branch: Branch name to read from
            file_path: Relative path within the repo
            
        Returns:
            File content as string, or None if file doesn't exist
        """
        try:
            # Use git show to read file from branch
            from typing import cast
            return cast(str | None, self.repo.git.show(f"{branch}:{file_path}"))
        except GitCommandError:
            # File doesn't exist in that branch
            return None
        except (GitCommandError, ValueError, OSError):
            return None

