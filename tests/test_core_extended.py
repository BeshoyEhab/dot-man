"""Extended tests for GitManager (init, checkout_commit, delete_branch, etc.)."""

from pathlib import Path

import pytest
from git import Repo

from dot_man.core import GitManager
from dot_man.exceptions import (
    BranchNotFoundError,
    GitOperationError,
    NotInitializedError,
)


def _init_repo(tmp_path: Path) -> Path:
    """Initialize a real git repo with an initial commit."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir(parents=True)
    repo = Repo.init(repo_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")
    (repo_path / "README.md").write_text("# dot-man")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo_path


class TestInit:
    """Test GitManager.init() method."""

    def test_init_creates_repo(self, tmp_path):
        """init should create a new git repo."""
        repo_path = tmp_path / "new_repo"
        gm = GitManager(repo_path)
        gm.init()
        assert (repo_path / ".git").exists()
        assert (repo_path / ".gitignore").exists()

    def test_init_creates_gitignore(self, tmp_path):
        """init should create .gitignore with patterns."""
        repo_path = tmp_path / "new_repo"
        gm = GitManager(repo_path)
        gm.init()
        content = (repo_path / ".gitignore").read_text()
        assert ".DS_Store" in content
        assert "*.pyc" in content

    def test_init_sets_config(self, tmp_path):
        """init should set git config."""
        repo_path = tmp_path / "new_repo"
        gm = GitManager(repo_path)
        gm.init()
        repo = Repo(repo_path)
        assert repo.config_reader().get_value("user", "name") == "dot-man"

    def test_init_existing_repo_does_not_reinit(self, tmp_path):
        """init on existing repo should not overwrite .gitignore."""
        repo_path = tmp_path / "existing"
        repo_path.mkdir(parents=True)
        Repo.init(repo_path)
        gm = GitManager(repo_path)
        gm.init()
        # Should not raise


class TestCurrentBranch:
    """Test current_branch method."""

    def test_current_branch_normal(self, tmp_path):
        """current_branch should return branch name."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        assert gm.current_branch() == "master"

    def test_current_branch_after_checkout(self, tmp_path):
        """current_branch should reflect branch switches."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("feature")
        gm.checkout("feature")
        assert gm.current_branch() == "feature"


class TestCheckout:
    """Test checkout method."""

    def test_checkout_error(self, tmp_path):
        """checkout should raise BranchNotFoundError for nonexistent branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(BranchNotFoundError):
            gm.checkout("nonexistent")

    def test_checkout_create(self, tmp_path):
        """checkout with create=True should create and checkout."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.checkout("new-branch", create=True)
        assert gm.current_branch() == "new-branch"


class TestCheckoutCommit:
    """Test checkout_commit method."""

    def test_checkout_commit_by_sha(self, tmp_path):
        """checkout_commit should checkout a specific commit."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        sha = gm.get_commits().__next__()["sha"]
        gm.checkout_commit(sha)
        # Should be in detached HEAD state
        assert gm.repo.head.is_detached

    def test_checkout_commit_invalid_sha(self, tmp_path):
        """checkout_commit should raise on invalid SHA."""
        from gitdb.exc import BadName

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises((GitOperationError, BadName)):
            gm.checkout_commit("0000000")


class TestDeleteTag:
    """Test delete_tag method."""

    def test_delete_tag_not_found(self, tmp_path):
        """delete_tag should raise on nonexistent tag."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(BranchNotFoundError):
            gm.delete_tag("nonexistent")

    def test_delete_tag_existing(self, tmp_path):
        """delete_tag should remove existing tag."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_tag("v1.0")
        assert "v1.0" in gm.list_tags()
        gm.delete_tag("v1.0")
        assert "v1.0" not in gm.list_tags()


class TestAddAllCommit:
    """Test add_all and commit methods."""

    def test_commit_with_changes(self, tmp_path):
        """commit should create a commit with changes."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "test.txt").write_text("hello")
        sha = gm.commit("Add test.txt")
        assert sha is not None
        assert len(sha) >= 7

    def test_commit_nothing_to_commit(self, tmp_path):
        """commit should return None when nothing to commit."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        sha = gm.commit("Nothing")
        assert sha is None


class TestGetCommits:
    """Test get_commits method."""

    def test_get_commits(self, tmp_path):
        """get_commits should return the initial commit."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        commits = list(gm.get_commits(count=5))
        assert len(commits) == 1
        assert commits[0]["message"] == "Initial commit"
        assert len(commits[0]["sha"]) == 7

    def test_get_commits_detailed(self, tmp_path):
        """get_commits_detailed should return detailed commit info."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        commits = gm.get_commits_detailed(count=5)
        assert len(commits) == 1
        assert commits[0]["sha"] is not None
        assert commits[0]["message"] is not None
        assert isinstance(commits[0]["insertions"], int)
        assert isinstance(commits[0]["deletions"], int)
        assert "sha" in commits[0]
        assert "insertions" in commits[0]
        assert "deletions" in commits[0]

    def test_get_commits_detailed_with_branch(self, tmp_path):
        """get_commits_detailed should accept branch param."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        commits = gm.get_commits_detailed(count=5, branch="master")
        assert len(commits) == 1


class TestDeleteBranch:
    """Test delete_branch method."""

    def test_delete_branch_not_found(self, tmp_path):
        """delete_branch should raise on nonexistent branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(BranchNotFoundError):
            gm.delete_branch("nonexistent")

    def test_delete_branch_current(self, tmp_path):
        """delete_branch should raise when deleting current branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(GitOperationError, match="Cannot delete the current branch"):
            gm.delete_branch(gm.current_branch())

    def test_delete_branch_success(self, tmp_path):
        """delete_branch should remove a non-current branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("feature")
        assert "feature" in gm.list_branches()
        gm.delete_branch("feature")
        assert "feature" not in gm.list_branches()

    def test_delete_branch_force(self, tmp_path):
        """delete_branch with force=True should work."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("feature")
        gm.delete_branch("feature", force=True)
        assert "feature" not in gm.list_branches()


class TestRelativeDate:
    """Test _relative_date method."""

    def test_just_now(self):
        """_relative_date should show 'just now' for recent time."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(seconds=30)
        assert gm._relative_date(dt) == "just now"

    def test_minutes_ago(self):
        """_relative_date should show minutes."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert gm._relative_date(dt) == "5 min ago"

    def test_hours_ago(self):
        """_relative_date should show hours."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(hours=3)
        assert gm._relative_date(dt) == "3 hours ago"

    def test_days_ago(self):
        """_relative_date should show days."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(days=4)
        assert gm._relative_date(dt) == "4 days ago"

    def test_weeks_ago(self):
        """_relative_date should show weeks."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(weeks=3)
        assert gm._relative_date(dt) == "3 weeks ago"

    def test_months_ago(self):
        """_relative_date should show months."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(days=60)
        assert gm._relative_date(dt) == "2 months ago"

    def test_years_ago(self):
        """_relative_date should show years."""
        from datetime import datetime, timedelta, timezone

        from dot_man.core import GitManager

        gm = GitManager()
        dt = datetime.now(timezone.utc) - timedelta(days=800)
        assert gm._relative_date(dt) == "2 years ago"


class TestGetTagsForCommit:
    """Test _get_tags_for_commit method."""

    def test_no_tags(self, tmp_path):
        """_get_tags_for_commit should return empty for commit without tags."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        sha = list(gm.get_commits())[0]["sha"]
        tags = gm._get_tags_for_commit(sha)
        assert tags == []

    def test_with_tags(self, tmp_path):
        """_get_tags_for_commit should return tags pointing to commit."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_tag("v1.0")
        sha = list(gm.get_commits())[0]["sha"]
        tags = gm._get_tags_for_commit(sha)
        assert "v1.0" in tags


class TestGetBranchStats:
    """Test get_branch_stats method."""

    def test_branch_stats_basic(self, tmp_path):
        """get_branch_stats should return stats for valid branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        stats = gm.get_branch_stats("master")
        assert stats["commit_count"] == 1
        assert stats["file_count"] == 1
        assert stats["last_commit_msg"] == "Initial commit"

    def test_branch_stats_nonexistent(self, tmp_path):
        """get_branch_stats should return zeros for nonexistent branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        stats = gm.get_branch_stats("nonexistent")
        assert stats["commit_count"] == 0


class TestGetAllBranchStats:
    """Test get_all_branch_stats method."""

    def test_get_all_branch_stats(self, tmp_path):
        """get_all_branch_stats should return stats for all branches."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("feature")
        stats = gm.get_all_branch_stats()
        names = [s["name"] for s in stats]
        assert "master" in names
        assert "feature" in names

    def test_get_all_branch_stats_single(self, tmp_path):
        """get_all_branch_stats should work with single branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        stats = gm.get_all_branch_stats()
        assert len(stats) == 1
        assert stats[0]["name"] == "master"


class TestSetRemote:
    """Test set_remote method."""

    def test_set_remote_new(self, tmp_path):
        """set_remote should create new remote."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.set_remote("https://example.com/repo.git")
        assert gm.has_remote()
        assert gm.get_remote_url() == "https://example.com/repo.git"

    def test_set_remote_update(self, tmp_path):
        """set_remote should update existing remote URL."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.set_remote("https://example.com/old.git")
        gm.set_remote("https://example.com/new.git")
        assert gm.get_remote_url() == "https://example.com/new.git"


class TestFetch:
    """Test fetch method."""

    def test_fetch_no_remote(self, tmp_path):
        """fetch should raise without remote."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(GitOperationError, match="No remote configured"):
            gm.fetch()


class TestGetFileFromBranch:
    """Test get_file_from_branch method."""

    def test_get_file_from_branch_existing(self, tmp_path):
        """get_file_from_branch should read file content from branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        content = gm.get_file_from_branch("master", "README.md")
        assert content is not None
        assert "# dot-man" in content

    def test_get_file_from_branch_nonexistent(self, tmp_path):
        """get_file_from_branch should return None for missing file."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        content = gm.get_file_from_branch("master", "nonexistent.txt")
        assert content is None


class TestErrorHandling:
    """Test error handling paths."""

    def test_not_initialized_error(self, tmp_path):
        """Accessing repo on non-init dir should raise."""
        repo_path = tmp_path / "not_a_repo"
        repo_path.mkdir()
        gm = GitManager(repo_path)
        with pytest.raises(NotInitializedError):
            _ = gm.repo

    def test_is_initialized_oserror(self, tmp_path):
        """is_initialized should return False on OSError."""
        repo_path = tmp_path / "nonexistent"
        gm = GitManager(repo_path)
        assert gm.is_initialized() is False

    def test_get_status_new_file(self, tmp_path):
        """get_status should detect new files."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "new.txt").write_text("new content")
        status = gm.get_status()
        assert "untracked" in status
        assert "new.txt" in status["untracked"]

    def test_get_status_modified(self, tmp_path):
        """get_status should detect modified files."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "README.md").write_text("# modified content")
        status = gm.get_status()
        assert "modified" in status


class TestRepoProperty:
    """Test the repo property."""

    def test_repo_cached(self, tmp_path):
        """repo property should cache the Repo instance."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        r1 = gm.repo
        r2 = gm.repo
        assert r1 is r2

    def test_repo_lazy_load(self, tmp_path):
        """repo should be lazily loaded."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        assert gm._repo is None
        _ = gm.repo
        assert gm._repo is not None


class TestGetSyncStatus:
    """Test get_sync_status method."""

    def test_no_remote(self, tmp_path):
        """get_sync_status should indicate no remote."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        status = gm.get_sync_status()
        assert status["remote_configured"] is False
