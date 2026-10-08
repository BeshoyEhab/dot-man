"""Tests for dot_man.core GitManager."""

import pytest
from git import Repo

from dot_man.core import GitManager
from dot_man.exceptions import (
    BranchNotFoundError,
    GitOperationError,
    NotInitializedError,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with an initial commit.

    Layout (tests needing the on-disk path use ``tmp_path / "repo"``):
    one tracked file ``init.txt`` ("initial"), one commit "Initial commit",
    user name "Tester".
    """
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

    def test_repo_property(self, git_repo, tmp_path):
        """repo exposes the GitPython Repo bound to the fixture's own directory."""
        assert isinstance(git_repo.repo, Repo)
        assert git_repo.repo.working_dir == str(tmp_path / "repo")

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

    def test_current_branch(self, git_repo, tmp_path):
        """current_branch matches the repo's real active branch, not a hardcoded default."""
        initial = Repo(tmp_path / "repo").active_branch.name
        assert git_repo.current_branch() == initial

    def test_list_branches(self, git_repo, tmp_path):
        """A fresh fixture has exactly one branch - the default HEAD, no extras."""
        initial = Repo(tmp_path / "repo").active_branch.name
        assert set(git_repo.list_branches()) == {initial}

    def test_branch_exists(self, git_repo):
        current = git_repo.current_branch()
        assert git_repo.branch_exists(current) is True
        assert git_repo.branch_exists("nonexistent-branch-xyz") is False

    def test_create_branch(self, git_repo, tmp_path):
        """Creating a branch yields exactly {default, new} - nothing else appears."""
        initial = Repo(tmp_path / "repo").active_branch.name
        git_repo.create_branch("test-branch")
        assert git_repo.branch_exists("test-branch") is True
        assert set(git_repo.list_branches()) == {initial, "test-branch"}

    def test_list_branches_with_slash_name(self, git_repo, tmp_path):
        """Hierarchical refs (feature/x) must show up as one exact entry, not split."""
        initial = Repo(tmp_path / "repo").active_branch.name
        git_repo.create_branch("feature/x")
        assert set(git_repo.list_branches()) == {initial, "feature/x"}

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

    def test_delete_branch(self, git_repo, tmp_path):
        """Deleting a branch returns the branch list to exactly the default set."""
        initial = Repo(tmp_path / "repo").active_branch.name
        git_repo.create_branch("to-delete")
        git_repo.delete_branch("to-delete")
        assert git_repo.branch_exists("to-delete") is False
        assert set(git_repo.list_branches()) == {initial}

    def test_delete_current_branch_raises(self, git_repo):
        current = git_repo.current_branch()
        with pytest.raises(GitOperationError, match="Cannot delete"):
            git_repo.delete_branch(current)

    def test_delete_nonexistent_branch_raises(self, git_repo):
        with pytest.raises(BranchNotFoundError):
            git_repo.delete_branch("no-such-branch")

    def test_delete_branch_force(self, git_repo, tmp_path):
        """Force delete removes an unmerged branch once HEAD is back on the original."""
        path = tmp_path / "repo"
        original = git_repo.current_branch()
        git_repo.checkout("unmerged", create=True)
        (path / "unmerged.txt").write_text("data")
        git_repo.commit("unmerged commit")
        git_repo.checkout(original)
        git_repo.delete_branch("unmerged", force=True)
        assert git_repo.branch_exists("unmerged") is False
        assert set(git_repo.list_branches()) == {original}

    @pytest.mark.parametrize(
        "name",
        ["bränche", "分支", "naïve-branch"],
        ids=["umlaut", "cjk", "accented"],
    )
    def test_unicode_branch_lifecycle(self, git_repo, name):
        """Non-ASCII ref names must survive create/exists/checkout/delete unmangled."""
        original = git_repo.current_branch()
        git_repo.checkout(name, create=True)
        assert git_repo.branch_exists(name) is True
        assert git_repo.current_branch() == name
        assert name in git_repo.list_branches()
        git_repo.checkout(original)
        git_repo.delete_branch(name)
        assert git_repo.branch_exists(name) is False


class TestCommits:
    """Tests for staging, committing, and history."""

    def test_is_dirty_clean(self, git_repo):
        assert git_repo.is_dirty() is False

    def test_is_dirty_after_change(self, git_repo, tmp_path):
        (tmp_path / "repo" / "new.txt").write_text("dirty")
        assert git_repo.is_dirty() is True

    def test_commit_returns_sha(self, git_repo, tmp_path):
        """commit returns the full sha of the commit it actually created at HEAD."""
        path = tmp_path / "repo"
        (path / "file.txt").write_text("content")
        sha = git_repo.commit("Test commit")
        assert sha == Repo(path).head.commit.hexsha

    def test_commit_nothing_returns_none(self, git_repo):
        assert git_repo.commit("Empty") is None

    def test_add_all(self, git_repo, tmp_path):
        (tmp_path / "repo" / "staged.txt").write_text("data")
        git_repo.add_all()
        # File should be staged
        assert "staged.txt" not in git_repo.repo.untracked_files

    def test_get_status_untracked(self, git_repo, tmp_path):
        (tmp_path / "repo" / "untracked.txt").write_text("data")
        status = git_repo.get_status()
        assert "untracked.txt" in status["untracked"]

    def test_get_status_modified(self, git_repo, tmp_path):
        # Modify a tracked file
        (tmp_path / "repo" / "init.txt").write_text("modified")
        status = git_repo.get_status()
        assert "init.txt" in status["modified"]

    def test_get_status_mixed_buckets(self, git_repo, tmp_path):
        """Each of modified/untracked/deleted lands in exactly its own bucket."""
        path = tmp_path / "repo"
        (path / "second.txt").write_text("second")
        git_repo.add_all()
        git_repo.commit("add second")
        (path / "init.txt").write_text("changed")
        (path / "second.txt").unlink()
        (path / "untracked.txt").write_text("new")
        status = git_repo.get_status()
        assert set(status["modified"]) == {"init.txt"}
        assert set(status["deleted"]) == {"second.txt"}
        assert set(status["untracked"]) == {"untracked.txt"}

    def test_get_commits(self, git_repo, tmp_path):
        """The single fixture commit is reported with its exact sha/message/author."""
        head = Repo(tmp_path / "repo").head.commit
        commits = list(git_repo.get_commits(count=5))
        assert len(commits) == 1
        assert commits[0]["sha"] == head.hexsha[:7]
        assert commits[0]["message"] == "Initial commit"
        assert commits[0]["author"] == "Tester"
        assert commits[0]["date"] == head.committed_datetime.isoformat()

    def test_get_commits_multiple(self, git_repo, tmp_path):
        """History is newest-first with exactly one entry per commit."""
        path = tmp_path / "repo"
        for i in range(3):
            (path / f"file{i}.txt").write_text(f"content{i}")
            git_repo.commit(f"Commit {i}")
        commits = list(git_repo.get_commits(count=10))
        assert len(commits) == 4  # 3 + initial
        assert [c["message"] for c in commits] == [
            "Commit 2",
            "Commit 1",
            "Commit 0",
            "Initial commit",
        ]

    def test_commit_unicode_message_round_trips(self, git_repo, tmp_path):
        """A unicode commit message must survive the git round-trip intact."""
        path = tmp_path / "repo"
        message = "Ünïcödé mèsságé ✨"
        (path / "unicode.txt").write_text("x")
        git_repo.commit(message)
        commits = list(git_repo.get_commits(count=5))
        assert commits[0]["message"] == message
        assert commits[0]["sha"] == Repo(path).head.commit.hexsha[:7]


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
        """Fixture stats are exact: one commit, one file, the known message/date."""
        current = git_repo.current_branch()
        stats = git_repo.get_branch_stats(current)
        assert stats["commit_count"] == 1
        assert stats["file_count"] == 1
        assert stats["last_commit_msg"] == "Initial commit"
        assert stats["last_commit_date"][:4].isdigit()
        assert stats["last_commit_date"] != "N/A"

    def test_get_branch_stats_nonexistent(self, git_repo):
        stats = git_repo.get_branch_stats("no-such-branch")
        assert stats == {
            "commit_count": 0,
            "last_commit_date": "N/A",
            "last_commit_msg": "N/A",
            "file_count": 0,
        }

    def test_get_all_branch_stats(self, git_repo, tmp_path):
        """Stats are produced for exactly the branches that exist, no extras."""
        initial = Repo(tmp_path / "repo").active_branch.name
        git_repo.create_branch("branch-a")
        git_repo.create_branch("branch-b")
        stats = git_repo.get_all_branch_stats()
        names = [s["name"] for s in stats]
        assert set(names) == {initial, "branch-a", "branch-b"}

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

    def test_get_file_from_different_branch(self, git_repo, tmp_path):
        path = tmp_path / "repo"
        original = git_repo.current_branch()
        git_repo.checkout("other", create=True)
        (path / "other.txt").write_text("other-content")
        git_repo.commit("add other")
        git_repo.checkout(original)

        content = git_repo.get_file_from_branch("other", "other.txt")
        assert content == "other-content"
        # File shouldn't exist in original branch
        assert git_repo.get_file_from_branch(original, "other.txt") is None

    def test_get_file_from_branch_nested_path(self, git_repo, tmp_path):
        """Nested repo paths resolve on the branch that owns them, not others."""
        path = tmp_path / "repo"
        original = git_repo.current_branch()
        git_repo.checkout("nested", create=True)
        (path / "dir").mkdir()
        (path / "dir" / "file.txt").write_text("nested-content")
        git_repo.commit("add nested file")
        git_repo.checkout(original)

        assert git_repo.get_file_from_branch("nested", "dir/file.txt") == (
            "nested-content"
        )
        assert git_repo.get_file_from_branch(original, "dir/file.txt") is None
