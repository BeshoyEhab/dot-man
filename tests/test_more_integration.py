"""Tests for core operations and file handling."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import os


class TestGitManagerBranches:
    """Test GitManager branch operations."""

    def test_branch_exists_true(self, tmp_path):
        """Test branch_exists returns True for existing branch."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        # Create initial commit
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        # Create branch
        repo.create_head("feature")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        assert git.branch_exists("feature") is True

    def test_branch_exists_false(self, tmp_path):
        """Test branch_exists returns False for non-existing branch."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        assert git.branch_exists("nonexistent") is False

    def test_create_branch(self, tmp_path):
        """Test creating a branch."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        git.create_branch("new-branch")
        assert git.branch_exists("new-branch")

    def test_checkout_existing_branch(self, tmp_path):
        """Test checking out an existing branch."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        repo.create_head("feature")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        git.checkout("feature")
        assert git.current_branch() == "feature"

    def test_checkout_with_create(self, tmp_path):
        """Test checkout with create=True."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        git.checkout("new-branch", create=True)
        assert git.branch_exists("new-branch")

    def test_is_dirty_clean(self, tmp_path):
        """Test is_dirty returns False for clean repo."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        assert git.is_dirty() is False

    def test_is_dirty_dirty(self, tmp_path):
        """Test is_dirty returns True for dirty repo."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        # Add untracked file
        (repo_dir / "new.txt").write_text("new")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        assert git.is_dirty() is True


class TestGitManagerStatus:
    """Test GitManager status operations."""

    def test_get_status_clean(self, tmp_path):
        """Test get_status for clean repo."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        status = git.get_status()
        assert status["modified"] == []
        assert status["untracked"] == []

    def test_get_status_untracked(self, tmp_path):
        """Test get_status detects untracked files."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        (repo_dir / "untracked.txt").write_text("untracked")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        status = git.get_status()
        assert "untracked.txt" in status["untracked"]

    def test_get_status_modified(self, tmp_path):
        """Test get_status detects modified files."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        test_file = repo_dir / "test.txt"
        test_file.write_text("original")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        test_file.write_text("modified")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        status = git.get_status()
        assert "test.txt" in status["modified"]


class TestGitManagerCommits:
    """Test GitManager commit operations."""

    def test_commit_with_message(self, tmp_path):
        """Test commit creates a commit with message."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        commit_sha = git.commit("Test commit message")
        assert commit_sha is not None

    def test_commit_nothing_to_commit(self, tmp_path):
        """Test commit returns None when nothing to commit."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        # No changes
        commit_sha = git.commit("Another commit")
        assert commit_sha is None


class TestGitManagerRemote:
    """Test GitManager remote operations."""

    def test_has_remote_false(self, tmp_path):
        """Test has_remote returns False when no remote."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        assert git.has_remote() is False

    def test_set_remote(self, tmp_path):
        """Test setting remote URL."""
        from git import Repo
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        
        git.set_remote("https://github.com/user/repo.git")
        assert git.has_remote() is True
        assert "github.com" in git.get_remote_url()


class TestFileOperations:
    """Test file operations."""

    def test_compare_files_identical(self, tmp_path):
        """Test compare_files returns True for identical files."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        content = "identical content"
        file1.write_text(content)
        file2.write_text(content)
        
        assert compare_files(file1, file2) is True

    def test_compare_files_different(self, tmp_path):
        """Test compare_files returns False for different files."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        file1.write_text("content A")
        file2.write_text("content B")
        
        assert compare_files(file1, file2) is False

    def test_compare_files_missing(self, tmp_path):
        """Test compare_files handles missing file."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "exists.txt"
        file2 = tmp_path / "missing.txt"
        
        file1.write_text("test")
        
        assert compare_files(file1, file2) is False
        assert compare_files(file2, file1) is False


class TestConstants:
    """Test constants module."""

    def test_default_branch(self):
        """Test DEFAULT_BRANCH constant."""
        from dot_man.constants import DEFAULT_BRANCH
        assert DEFAULT_BRANCH == "main"


class TestExceptions:
    """Test exception classes."""

    def test_dotman_error(self):
        """Test DotManError can be raised and caught."""
        from dot_man.exceptions import DotManError
        
        with pytest.raises(DotManError) as exc:
            raise DotManError("Test error")
        
        assert str(exc.value) == "Test error"
        assert exc.value.exit_code == 1

    def test_not_initialized_error(self):
        """Test NotInitializedError."""
        from dot_man.exceptions import NotInitializedError
        
        with pytest.raises(NotInitializedError) as exc:
            raise NotInitializedError("Not initialized")
        
        assert "Not initialized" in str(exc.value)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        from dot_man.exceptions import ConfigurationError
        
        with pytest.raises(ConfigurationError) as exc:
            raise ConfigurationError("Config error")
        
        assert "Config error" in str(exc.value)

    def test_git_operation_error(self):
        """Test GitOperationError."""
        from dot_man.exceptions import GitOperationError
        
        with pytest.raises(GitOperationError) as exc:
            raise GitOperationError("Git error")
        
        # GitOperationError has exit_code 5
        assert exc.value.exit_code == 5