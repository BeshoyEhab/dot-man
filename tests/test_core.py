"""Tests for core.py — GitManager and core git operations."""

import pytest
from git import Repo


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    repo = Repo.init(repo_dir)
    config_writer = repo.config_writer()
    config_writer.set_value("user", "name", "Test User")
    config_writer.set_value("user", "email", "test@test.com")
    config_writer.release()

    yield repo_dir


class TestGitManagerBasics:
    def test_git_manager_init(self, temp_repo):
        """Test GitManager initialization."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        assert gm.repo is not None

    def test_current_branch(self, temp_repo):
        """Test getting current branch."""
        from dot_man.core import GitManager

        # Create initial commit for branch operations
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        gm = GitManager(temp_repo)
        branch = gm.current_branch()
        assert branch == "master"

    def test_list_branches(self, temp_repo):
        """Test listing branches."""
        from dot_man.core import GitManager

        # Create initial commit first
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        repo.create_head("feature")

        gm = GitManager(temp_repo)
        branches = gm.list_branches()
        assert "master" in branches
        assert "feature" in branches

    def test_list_tags_empty(self, temp_repo):
        """Test listing tags when none exist."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        tags = gm.list_tags()
        assert tags == []

    def test_list_tags_with_tags(self, temp_repo):
        """Test listing tags."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        repo = Repo(temp_repo)

        # Add a commit first
        (temp_repo / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        repo.create_tag("v1.0.0")

        tags = gm.list_tags()
        assert "v1.0.0" in tags


class TestGitManagerBranches:
    def test_branch_exists(self, temp_repo):
        """Test checking if branch exists."""
        # Create initial commit first
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        repo.create_head("feature")

        assert gm.branch_exists("master")
        assert gm.branch_exists("feature")
        assert not gm.branch_exists("nonexistent")

    def test_create_branch(self, temp_repo):
        """Test creating a branch."""
        # Create initial commit first
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        gm.create_branch("new-branch")

        assert "new-branch" in gm.list_branches()

    def test_checkout_branch(self, temp_repo):
        """Test checking out a branch."""
        # Create initial commit first
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        repo.create_head("feature")

        gm.checkout("feature")

        assert gm.current_branch() == "feature"

    def test_delete_branch(self, temp_repo):
        """Test deleting a branch."""
        # Create initial commit first
        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        repo.create_head("to-delete")

        gm.delete_branch("to-delete")

        assert "to-delete" not in gm.list_branches()


class TestGitManagerCommits:
    def test_get_commits(self, temp_repo):
        """Test getting commits."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("First commit")

        commits = list(gm.get_commits(count=10))
        assert len(commits) >= 1

    def test_get_commits_detailed(self, temp_repo):
        """Test getting detailed commits."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("First commit")

        commits = gm.get_commits_detailed(count=10)
        assert len(commits) >= 1
        assert "sha" in commits[0]
        assert "message" in commits[0]


class TestGitManagerStatus:
    def test_is_initialized(self, temp_repo):
        """Test is_initialized check."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        assert gm.is_initialized()

    def test_is_dirty_clean(self, temp_repo):
        """Test is_dirty when clean."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        assert not gm.is_dirty()

    def test_is_dirty_dirty(self, temp_repo):
        """Test is_dirty when dirty."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        (temp_repo / "new.txt").write_text("new")

        assert gm.is_dirty()

    def test_get_status(self, temp_repo):
        """Test get_status."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        status = gm.get_status()
        assert isinstance(status, dict)


class TestGitManagerCommits2:
    def test_add_and_commit(self, temp_repo):
        """Test adding and committing."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        gm.add_all()
        sha = gm.commit("Test commit")

        assert sha is not None

    def test_commit_without_changes(self, temp_repo):
        """Test commit with no changes returns None."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        gm.add_all()
        gm.commit("First commit")

        # No new changes
        result = gm.commit("Second commit")
        assert result is None


class TestGitManagerTags:
    def test_create_tag(self, temp_repo):
        """Test creating a tag."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        gm.create_tag("v1.0.0")

        assert "v1.0.0" in gm.list_tags()

    def test_delete_tag(self, temp_repo):
        """Test deleting a tag."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        repo.create_tag("v1.0.0")
        gm.delete_tag("v1.0.0")

        assert "v1.0.0" not in gm.list_tags()

    def test_get_tag_commit(self, temp_repo):
        """Test getting commit SHA for a tag."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)

        (temp_repo / "test.txt").write_text("test")
        repo = Repo(temp_repo)
        repo.index.add(["test.txt"])
        commit = repo.index.commit("Initial")

        repo.create_tag("v1.0.0")

        tag_commit = gm.get_tag_commit("v1.0.0")
        assert tag_commit is not None
        assert tag_commit.startswith(commit.hexsha[:7])


class TestGitManagerRemote:
    def test_has_remote_false(self, temp_repo):
        """Test has_remote when no remote."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        assert not gm.has_remote()

    def test_get_remote_url_none(self, temp_repo):
        """Test get_remote_url when no remote."""
        from dot_man.core import GitManager

        gm = GitManager(temp_repo)
        assert gm.get_remote_url() is None


class TestGitManagerSync:
    def test_fetch_raises_without_remote(self, temp_repo):
        """Test fetch raises without remote."""
        from dot_man.core import GitManager
        from dot_man.exceptions import GitOperationError

        gm = GitManager(temp_repo)
        # Should raise without remote
        with pytest.raises(GitOperationError):
            gm.fetch()
