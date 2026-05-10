"""Tests for core module - GitManager and related functionality."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from git import Repo


class TestGitManagerBasic:
    """Test GitManager basic functionality."""

    def test_git_manager_init(self, tmp_path):
        """Test GitManager initialization."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        Repo.init(repo_dir)
        
        gm = GitManager(repo_dir)
        assert gm is not None

    def test_git_manager_current_branch(self, tmp_path):
        """Test getting current branch."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        gm = GitManager(repo_dir)
        branch = gm.current_branch
        assert branch is not None

    def test_git_manager_list_branches(self, tmp_path):
        """Test listing branches."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        repo.create_head("feature")
        repo.create_head("develop")
        
        gm = GitManager(repo_dir)
        branches = gm.list_branches()
        assert "main" in branches or "master" in branches
        assert "feature" in branches

    def test_git_manager_create_branch(self, tmp_path):
        """Test creating a branch."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        gm = GitManager(repo_dir)
        gm.create_branch("new-branch")
        
        assert "new-branch" in gm.list_branches()

    def test_git_manager_delete_branch(self, tmp_path):
        """Test deleting a branch."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        repo.create_head("to-delete")
        
        gm = GitManager(repo_dir)
        gm.delete_branch("to-delete")
        
        assert "to-delete" not in gm.list_branches()

    def test_git_manager_create_tag(self, tmp_path):
        """Test creating a tag."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        gm = GitManager(repo_dir)
        gm.create_tag("v1.0")
        
        assert "v1.0" in gm.list_tags()

    def test_git_manager_list_tags(self, tmp_path):
        """Test listing tags."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        repo.create_tag("v1.0")
        repo.create_tag("v2.0")
        
        gm = GitManager(repo_dir)
        tags = gm.list_tags()
        assert "v1.0" in tags
        assert "v2.0" in tags


class TestGitManagerRemote:
    """Test GitManager remote functionality."""

    def test_git_manager_set_remote(self, tmp_path):
        """Test setting remote URL."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        gm = GitManager(repo_dir)
        gm.set_remote("https://github.com/test/repo.git")
        
        assert gm.get_remote_url() == "https://github.com/test/repo.git"

    def test_git_manager_get_remote_no_remote(self, tmp_path):
        """Test getting remote when none set."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        gm = GitManager(repo_dir)
        url = gm.get_remote_url()
        assert url is None or url == ""

    def test_git_manager_has_remote(self, tmp_path):
        """Test checking if remote exists."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        gm = GitManager(repo_dir)
        
        assert gm.has_remote() is False
        
        gm.set_remote("https://github.com/test/repo.git")
        
        assert gm.has_remote() is True


class TestGitManagerStatus:
    """Test GitManager status checking."""

    def test_git_manager_is_dirty_clean(self, tmp_path):
        """Test is_dirty when repo is clean."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        gm = GitManager(repo_dir)
        assert gm.is_dirty() is False

    def test_git_manager_is_dirty_dirty(self, tmp_path):
        """Test is_dirty when repo has changes."""
        from dot_man.core import GitManager
        
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")
        
        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")
        
        (repo_dir / "new.txt").write_text("new")
        
        gm = GitManager(repo_dir)
        assert gm.is_dirty() is True