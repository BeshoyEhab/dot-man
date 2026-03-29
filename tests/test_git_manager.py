"""Tests for dot_man.core GitManager."""

import pytest
from pathlib import Path
from git import Repo

from dot_man.core import GitManager
from dot_man.exceptions import (
    GitOperationError,
    BranchNotFoundError,
    NotInitializedError,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with an initial commit."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Tester")
        config.set_value("user", "email", "test@test.com")
    # Initial commit so HEAD exists
    (repo_path / "init.txt").write_text("initial")
    repo.index.add(["init.txt"])
    repo.index.commit("Initial commit")
    return GitManager(repo_path)


class TestGitManagerInit:
    """Tests for GitManager initialization."""

    def test_repo_property(self, git_repo):
        assert git_repo.repo is not None
        assert isinstance(git_repo.repo, Repo)

    def test_repo_not_initialized(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        gm = GitManager(empty)
        with pytest.raises(NotInitializedError):
            _ = gm.repo

    def test_is_initialized_true(self, git_repo):
        assert git_repo.is_initialized() is True

    def test_is_initialized_false(self, tmp_path):
        empty = tmp_path / "nope"
        empty.mkdir()
        gm = GitManager(empty)
        assert gm.is_initialized() is False

    def test_init_creates_repo(self, tmp_path):
        repo_path = tmp_path / "new_repo"
        gm = GitManager(repo_path)
        gm.init()
        assert (repo_path / ".git").exists()
        assert (repo_path / ".gitignore").exists()

    def test_init_sets_default_user(self, tmp_path):
        repo_path = tmp_path / "new_repo"
        gm = GitManager(repo_path)
        gm.init()
        reader = gm.repo.config_reader()
        assert reader.get_value("user", "name") == "dot-man"


class TestBranches:
    """Tests for branch operations."""

    def test_current_branch(self, git_repo):
        branch = git_repo.current_branch()
        assert branch in ("main", "master")

    def test_list_branches(self, git_repo):
        branches = git_repo.list_branches()
        assert len(branches) >= 1

    def test_branch_exists(self, git_repo):
        current = git_repo.current_branch()
        assert git_repo.branch_exists(current) is True
        assert git_repo.branch_exists("nonexistent-branch-xyz") is False

    def test_create_branch(self, git_repo):
        git_repo.create_branch("test-branch")
        assert git_repo.branch_exists("test-branch") is True

    def test_checkout_existing(self, git_repo):
        git_repo.create_branch("feature")
        git_repo.checkout("feature")
        assert git_repo.current_branch() == "feature"

    def test_checkout_with_create(self, git_repo):
        git_repo.checkout("new-branch", create=True)
        assert git_repo.current_branch() == "new-branch"

    def test_checkout_nonexistent_raises(self, git_repo):
        with pytest.raises(BranchNotFoundError):
            git_repo.checkout("doesnt-exist")

    def test_delete_branch(self, git_repo):
        git_repo.create_branch("to-delete")
        git_repo.delete_branch("to-delete")
        assert git_repo.branch_exists("to-delete") is False

    def test_delete_current_branch_raises(self, git_repo):
        current = git_repo.current_branch()
        with pytest.raises(GitOperationError, match="Cannot delete"):
            git_repo.delete_branch(current)

    def test_delete_nonexistent_branch_raises(self, git_repo):
        with pytest.raises(BranchNotFoundError):
            git_repo.delete_branch("no-such-branch")

    def test_delete_branch_force(self, git_repo):
        # Create branch with unique commit
        git_repo.checkout("unmerged", create=True)
        (git_repo._repo_path / "unmerged.txt").write_text("data")
        git_repo.commit("unmerged commit")
        git_repo.checkout(git_repo.list_branches()[0])
        # Force delete unmerged branch
        git_repo.delete_branch("unmerged", force=True)
        assert git_repo.branch_exists("unmerged") is False


class TestCommits:
    """Tests for staging, committing, and history."""

    def test_is_dirty_clean(self, git_repo):
        assert git_repo.is_dirty() is False

    def test_is_dirty_after_change(self, git_repo):
        (git_repo._repo_path / "new.txt").write_text("dirty")
        assert git_repo.is_dirty() is True

    def test_commit_returns_sha(self, git_repo):
        (git_repo._repo_path / "file.txt").write_text("content")
        sha = git_repo.commit("Test commit")
        assert sha is not None
        assert len(sha) == 40  # Full SHA

    def test_commit_nothing_returns_none(self, git_repo):
        assert git_repo.commit("Empty") is None

    def test_add_all(self, git_repo):
        (git_repo._repo_path / "staged.txt").write_text("data")
        git_repo.add_all()
        # File should be staged
        assert "staged.txt" not in git_repo.repo.untracked_files

    def test_get_status_untracked(self, git_repo):
        (git_repo._repo_path / "untracked.txt").write_text("data")
        status = git_repo.get_status()
        assert "untracked.txt" in status["untracked"]

    def test_get_status_modified(self, git_repo):
        # Modify a tracked file
        (git_repo._repo_path / "init.txt").write_text("modified")
        status = git_repo.get_status()
        assert "init.txt" in status["modified"]

    def test_get_commits(self, git_repo):
        commits = list(git_repo.get_commits(count=5))
        assert len(commits) >= 1
        assert "sha" in commits[0]
        assert "message" in commits[0]
        assert "author" in commits[0]
        assert "date" in commits[0]

    def test_get_commits_multiple(self, git_repo):
        for i in range(3):
            (git_repo._repo_path / f"file{i}.txt").write_text(f"content{i}")
            git_repo.commit(f"Commit {i}")
        commits = list(git_repo.get_commits(count=10))
        assert len(commits) >= 4  # 3 + initial


class TestRemote:
    """Tests for remote operations."""

    def test_has_remote_false(self, git_repo):
        assert git_repo.has_remote() is False

    def test_get_remote_url_none(self, git_repo):
        assert git_repo.get_remote_url() is None

    def test_set_remote(self, git_repo):
        git_repo.set_remote("https://github.com/test/repo.git")
        assert git_repo.has_remote() is True
        assert git_repo.get_remote_url() == "https://github.com/test/repo.git"

    def test_set_remote_update(self, git_repo):
        git_repo.set_remote("https://old.url")
        git_repo.set_remote("https://new.url")
        assert git_repo.get_remote_url() == "https://new.url"

    def test_fetch_no_remote_raises(self, git_repo):
        with pytest.raises(GitOperationError, match="No remote"):
            git_repo.fetch()

    def test_push_no_remote_raises(self, git_repo):
        with pytest.raises(GitOperationError, match="No remote"):
            git_repo.push()

    def test_pull_no_remote_raises(self, git_repo):
        with pytest.raises(GitOperationError, match="No remote"):
            git_repo.pull()


class TestBranchStats:
    """Tests for branch stats and file reading."""

    def test_get_branch_stats(self, git_repo):
        current = git_repo.current_branch()
        stats = git_repo.get_branch_stats(current)
        assert stats["commit_count"] >= 1
        assert stats["file_count"] >= 1
        assert stats["last_commit_date"] != "N/A"

    def test_get_branch_stats_nonexistent(self, git_repo):
        stats = git_repo.get_branch_stats("no-such-branch")
        assert stats["commit_count"] == 0

    def test_get_all_branch_stats(self, git_repo):
        git_repo.create_branch("branch-a")
        git_repo.create_branch("branch-b")
        stats = git_repo.get_all_branch_stats()
        names = [s["name"] for s in stats]
        assert "branch-a" in names
        assert "branch-b" in names

    def test_get_sync_status_no_remote(self, git_repo):
        status = git_repo.get_sync_status()
        assert status["remote_configured"] is False

    def test_get_file_from_branch(self, git_repo):
        current = git_repo.current_branch()
        content = git_repo.get_file_from_branch(current, "init.txt")
        assert content == "initial"

    def test_get_file_from_branch_nonexistent(self, git_repo):
        current = git_repo.current_branch()
        content = git_repo.get_file_from_branch(current, "no-file.txt")
        assert content is None

    def test_get_file_from_different_branch(self, git_repo):
        original = git_repo.current_branch()
        git_repo.checkout("other", create=True)
        (git_repo._repo_path / "other.txt").write_text("other-content")
        git_repo.commit("add other")
        git_repo.checkout(original)

        content = git_repo.get_file_from_branch("other", "other.txt")
        assert content == "other-content"
        # File shouldn't exist in original branch
        assert git_repo.get_file_from_branch(original, "other.txt") is None
