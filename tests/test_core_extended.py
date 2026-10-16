"""Extended tests for GitManager (init, checkout_commit, delete_branch, etc.)."""

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from git import GitCommandError, Repo

from dot_man.constants import GIT_IGNORE_PATTERNS
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
        """init on an existing repo must not clobber user files.

        First-time setup (git identity, initial history) must not re-run on a
        repo that already exists — and a user-customized .gitignore must keep
        its content: init may only APPEND dot-man's ignore patterns that are
        missing, never overwrite the file.
        """
        repo_path = tmp_path / "existing"
        repo_path.mkdir(parents=True)
        repo = Repo.init(repo_path)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Existing")
            config.set_value("user", "email", "existing@test.com")
        (repo_path / "keep.txt").write_text("keep")
        repo.index.add(["keep.txt"])
        repo.index.commit("keep me")
        (repo_path / ".gitignore").write_text("# my own ignores\n*.local\n")
        gm = GitManager(repo_path)
        gm.init()
        reopened = Repo(repo_path)
        assert reopened.config_reader().get_value("user", "name") == "Existing"
        assert [c.message.strip() for c in reopened.iter_commits()] == ["keep me"]
        gitignore = (repo_path / ".gitignore").read_text()
        # User content survives...
        assert "# my own ignores" in gitignore
        assert "*.local" in gitignore
        # ...and dot-man's missing patterns are merged in, not lost.
        assert ".DS_Store" in gitignore
        assert "*.pyc" in gitignore

    def test_init_existing_repo_gitignore_not_duplicated(self, tmp_path):
        """Re-running init on a repo whose .gitignore already contains
        dot-man's patterns must not append duplicates."""
        repo_path = tmp_path / "existing"
        repo_path.mkdir(parents=True)
        Repo.init(repo_path)
        full = "\n".join(GIT_IGNORE_PATTERNS) + "\n"
        (repo_path / ".gitignore").write_text(full)
        gm = GitManager(repo_path)
        gm.init()
        gm.init()
        content = (repo_path / ".gitignore").read_text()
        assert content.count(".DS_Store") == 1
        assert content == full  # byte-identical: nothing appended


class TestCurrentBranch:
    """Test current_branch method."""

    def test_current_branch_normal(self, tmp_path):
        """current_branch should return the repo's actual initial branch name.

        Git's default branch depends on the host's init.defaultBranch config,
        so the name must come from the repo, never a hardcoded guess.
        """
        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        assert gm.current_branch() == initial

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

    def test_checkout_commit_updates_working_tree(self, tmp_path):
        """checkout_commit must update the worktree, not just the HEAD ref.

        Moving only ``head.reference`` leaves the checked-out files on the
        newer commit, so callers that read REPO_DIR (rollback, navigate to a
        tag/commit) deploy stale content instead of the requested one.
        """
        repo_path = _init_repo(tmp_path)
        repo = Repo(repo_path)
        (repo_path / "README.md").write_text("# changed")
        repo.index.add(["README.md"])
        repo.index.commit("Second commit")
        first_sha = list(repo.iter_commits())[-1].hexsha

        gm = GitManager(repo_path)
        gm.checkout_commit(first_sha)

        assert (repo_path / "README.md").read_text() == "# dot-man"

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
        """commit should return the full SHA of the commit it created."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "test.txt").write_text("hello")
        sha = gm.commit("Add test.txt")
        assert sha == Repo(repo_path).head.commit.hexsha
        assert len(sha) == 40

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
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        commits = gm.get_commits_detailed(count=5, branch=initial)
        assert len(commits) == 1
        assert commits[0]["message"] == "Initial commit"

    def test_get_commits_zero_count(self, tmp_path):
        """get_commits(count=0) should yield nothing, not the full history."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        assert list(gm.get_commits(count=0)) == []

    def test_get_commits_count_exceeds_history(self, tmp_path):
        """get_commits should cap at real history when count overshoots."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        for n in range(2):
            (repo_path / f"file{n}.txt").write_text(str(n))
            gm.add_all()
            gm.commit(f"commit {n}")
        commits = list(gm.get_commits(count=100))
        assert [c["message"] for c in commits] == [
            "commit 1",
            "commit 0",
            "Initial commit",
        ]

    def test_unicode_commit_message_round_trip(self, tmp_path):
        """get_commits should return unicode commit messages unchanged.

        Commit messages pass through git's object store, so a round trip
        catches any encoding mangling of non-ASCII text.
        """
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "unicode.txt").write_text("content")
        gm.add_all()
        gm.commit("dôcument café — 日本語 ✓")
        commits = list(gm.get_commits(count=5))
        assert commits[0]["message"] == "dôcument café — 日本語 ✓"


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

    def test_branch_name_with_slash_lifecycle(self, tmp_path):
        """create/checkout/delete should handle branch names containing slashes.

        Slash names create nested ref directories (refs/heads/feature/), which
        naive flat-path handling would break.
        """
        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        gm.create_branch("feature/x")
        assert "feature/x" in gm.list_branches()
        gm.checkout("feature/x")
        assert gm.current_branch() == "feature/x"
        gm.checkout(initial)
        gm.delete_branch("feature/x")
        assert "feature/x" not in gm.list_branches()


class TestRelativeDate:
    """Test _relative_date method."""

    @pytest.mark.parametrize(
        "offset,expected",
        [
            pytest.param(timedelta(seconds=30), "just now", id="just-now"),
            pytest.param(timedelta(minutes=5), "5 min ago", id="minutes"),
            pytest.param(timedelta(hours=3), "3 hours ago", id="hours"),
            pytest.param(timedelta(days=4), "4 days ago", id="days"),
            pytest.param(timedelta(weeks=3), "3 weeks ago", id="weeks"),
            pytest.param(timedelta(days=60), "2 months ago", id="months"),
            pytest.param(timedelta(days=800), "2 years ago", id="years"),
        ],
    )
    def test_relative_date_buckets(self, offset, expected):
        """_relative_date should bucket ages from seconds through years."""
        gm = GitManager()
        dt = datetime.now(timezone.utc) - offset
        assert gm._relative_date(dt) == expected


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
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        stats = gm.get_branch_stats(initial)
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
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        gm.create_branch("feature")
        stats = gm.get_all_branch_stats()
        names = [s["name"] for s in stats]
        assert initial in names
        assert "feature" in names

    def test_get_all_branch_stats_single(self, tmp_path):
        """get_all_branch_stats should work with single branch."""
        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        stats = gm.get_all_branch_stats()
        assert len(stats) == 1
        assert stats[0]["name"] == initial


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
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        content = gm.get_file_from_branch(initial, "README.md")
        assert content is not None
        assert "# dot-man" in content

    def test_get_file_from_branch_nonexistent(self, tmp_path):
        """get_file_from_branch should return None for missing file."""
        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        content = gm.get_file_from_branch(initial, "nonexistent.txt")
        assert content is None

    def test_get_file_from_branch_nested_unicode(self, tmp_path):
        """get_file_from_branch should read a nested path with unicode content.

        Exercises directory separators inside the ref path and UTF-8 decoding
        of blob bytes in one round trip.
        """
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "nested").mkdir()
        (repo_path / "nested" / "settings.ini").write_text("naïve = wörld ✓")
        gm.add_all()
        gm.commit("add nested unicode file")
        content = gm.get_file_from_branch(gm.current_branch(), "nested/settings.ini")
        assert content == "naïve = wörld ✓"


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


def _seed_bare_origin(tmp_path: Path, name: str = "origin.git"):
    """Create a bare origin repo seeded with one commit via a temp clone."""
    bare = tmp_path / name
    Repo.init(bare, bare=True)
    seed_dir = tmp_path / f"seed-{name.replace('.git', '')}"
    seed = Repo.clone_from(str(bare), str(seed_dir))
    with seed.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")
    (seed_dir / "f.txt").write_text("line1\nline2\n")
    seed.index.add(["f.txt"])
    seed.index.commit("seed commit")
    branch = seed.active_branch.name
    seed.git.push("-u", "origin", branch)
    return bare, branch


def _clone_from(bare: Path, dest: Path):
    """Clone a bare repo with test identity configured."""
    clone = Repo.clone_from(str(bare), str(dest))
    with clone.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")
    return clone


class TestInitFailure:
    """Test GitManager.init() failure mapping."""

    def test_init_on_existing_file_raises(self, tmp_path):
        """init should raise GitOperationError when path is a file."""
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        gm = GitManager(blocker)
        with pytest.raises(GitOperationError, match="Failed to initialize"):
            gm.init()


class TestCurrentBranchDetached:
    """Test current_branch in detached HEAD state."""

    def test_detached_head_returns_head(self, tmp_path):
        """current_branch should return HEAD when detached."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        sha = next(gm.get_commits())["sha"]
        gm.checkout_commit(sha)
        assert gm.current_branch() == "HEAD"


class TestCreateBranchFailure:
    """Test create_branch failure mapping."""

    def test_create_branch_empty_name_raises(self, tmp_path):
        """An empty name fails git's ref validation before any write."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(GitOperationError, match="Invalid branch name"):
            gm.create_branch("")


class TestCheckoutOverwriteConflict:
    """Test checkout failure mapping."""

    def test_checkout_overwriting_untracked_raises(self, tmp_path):
        """checkout should raise GitOperationError when untracked files clash."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        repo = Repo(repo_path)
        initial = repo.active_branch.name
        repo.create_head("other")
        repo.heads["other"].checkout()
        (repo_path / "clash.txt").write_text("tracked version")
        repo.index.add(["clash.txt"])
        repo.index.commit("tracked clash file")
        repo.heads[initial].checkout()
        (repo_path / "clash.txt").write_text("untracked version")
        with pytest.raises(GitOperationError, match="Failed to checkout"):
            gm.checkout("other")


class TestCheckoutCommitBlob:
    """Test checkout_commit failure mapping."""

    def test_checkout_commit_blob_sha_raises(self, tmp_path):
        """checkout_commit should raise GitOperationError for a blob SHA."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        blob_sha = gm.repo.git.rev_parse("HEAD:README.md").strip()
        with pytest.raises(GitOperationError, match="Failed to checkout commit"):
            gm.checkout_commit(blob_sha)


class TestCreateTagFailure:
    """Test create_tag failure mapping."""

    def test_create_tag_bad_ref_raises(self, tmp_path):
        """create_tag should raise GitOperationError for unknown ref."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with pytest.raises(GitOperationError, match="Failed to create tag"):
            gm.create_tag("v-bad", ref="no-such-ref")


class TestDeleteTagFailure:
    """Test delete_tag failure mapping."""

    def test_delete_tag_readonly_refs_raises(self, tmp_path):
        """delete_tag should raise GitOperationError when git cannot delete."""
        import os

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_tag("v1.0")
        tags_dir = repo_path / ".git" / "refs" / "tags"
        os.chmod(tags_dir, 0o555)
        try:
            with pytest.raises(GitOperationError, match="Failed to delete tag"):
                gm.delete_tag("v1.0")
        finally:
            os.chmod(tags_dir, 0o755)
        assert "v1.0" in gm.list_tags()


class TestGetStatusChangeTypes:
    """Test get_status modified/deleted classification."""

    def test_modified_files_listed(self, tmp_path):
        """get_status should list edited tracked files as modified."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "README.md").write_text("# changed")
        status = gm.get_status()
        assert "README.md" in status["modified"]
        assert status["deleted"] == []

    def test_deleted_files_listed(self, tmp_path):
        """get_status should list removed tracked files as deleted."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "README.md").unlink()
        status = gm.get_status()
        assert "README.md" in status["deleted"]
        assert status["modified"] == []

    def test_modified_deleted_and_untracked_together(self, tmp_path):
        """get_status should classify all three change buckets at once.

        Mixing the change types catches classification code that only works
        when a single bucket is non-empty.
        """
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        (repo_path / "extra.txt").write_text("tracked later")
        gm.add_all()
        gm.commit("add extra tracked file")
        (repo_path / "README.md").write_text("# modified")
        (repo_path / "extra.txt").unlink()
        (repo_path / "fresh.txt").write_text("untracked")
        status = gm.get_status()
        assert status["modified"] == ["README.md"]
        assert status["deleted"] == ["extra.txt"]
        assert status["untracked"] == ["fresh.txt"]


class TestAddAllFailure:
    """Test add_all failure mapping."""

    def test_add_all_after_git_removed_raises(self, tmp_path):
        """add_all should raise GitOperationError when .git is gone."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        _ = gm.repo
        shutil.rmtree(repo_path / ".git")
        with pytest.raises(GitOperationError, match="Failed to stage"):
            gm.add_all()


class TestCommitFailure:
    """Test commit failure mapping."""

    def test_commit_corrupt_ref_raises(self, tmp_path):
        """commit should raise GitOperationError when HEAD ref is corrupt."""
        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        (repo_path / "extra.txt").write_text("x")
        ref = repo_path / ".git" / "refs" / "heads" / initial
        ref.write_text("garbage-not-a-sha\n")
        with pytest.raises(GitOperationError, match="Failed to commit"):
            gm.commit("boom")


class TestEmptyRepoCommits:
    """Test commit listing on repos without commits."""

    def test_get_commits_empty_repo(self, tmp_path):
        """get_commits should yield nothing when the repo has no commits."""
        repo_path = tmp_path / "empty"
        repo_path.mkdir()
        Repo.init(repo_path)
        gm = GitManager(repo_path)
        assert list(gm.get_commits()) == []

    def test_get_commits_detailed_empty_repo(self, tmp_path):
        """get_commits_detailed should return [] when repo has no commits."""
        repo_path = tmp_path / "empty"
        repo_path.mkdir()
        Repo.init(repo_path)
        gm = GitManager(repo_path)
        assert gm.get_commits_detailed() == []


class TestDeleteBranchFailures:
    """Test delete_branch error mapping."""

    def test_delete_unmerged_branch_raises(self, tmp_path):
        """delete_branch should raise BranchNotMergedError for unmerged work."""
        from dot_man.exceptions import BranchNotMergedError

        repo_path = _init_repo(tmp_path)
        initial = Repo(repo_path).active_branch.name
        gm = GitManager(repo_path)
        gm.create_branch("unmerged")
        gm.checkout("unmerged")
        (repo_path / "unique.txt").write_text("diverged")
        gm.add_all()
        gm.commit("diverged commit")
        gm.checkout(initial)
        with pytest.raises(BranchNotMergedError, match="not fully merged"):
            gm.delete_branch("unmerged")

    def test_delete_branch_oserror_raises(self, tmp_path):
        """delete_branch should map OSError to GitOperationError."""
        from unittest.mock import patch

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("victim")
        with patch.object(gm.repo, "delete_head", side_effect=OSError("disk full")):
            with pytest.raises(GitOperationError, match="Failed to delete branch"):
                gm.delete_branch("victim")

    def test_delete_branch_git_failure_raises(self, tmp_path):
        """delete_branch should map unexpected git failures."""
        from unittest.mock import patch

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.create_branch("victim")
        with patch.object(
            gm.repo, "delete_head", side_effect=GitCommandError("delete", 1)
        ):
            with pytest.raises(GitOperationError, match="Failed to delete branch"):
                gm.delete_branch("victim")


class TestSetRemoteFailure:
    """Test set_remote failure mapping."""

    def test_set_remote_backend_failure_raises(self, tmp_path):
        """set_remote should raise GitOperationError when git fails."""
        from unittest.mock import patch

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        with patch.object(
            Repo, "create_remote", side_effect=GitCommandError("remote", 128)
        ):
            with pytest.raises(GitOperationError, match="Failed to set remote"):
                gm.set_remote("https://example.com/repo.git")


class TestFetchFailure:
    """Test fetch failure mapping."""

    def test_fetch_unreachable_remote_raises(self, tmp_path):
        """fetch should raise GitOperationError for a dead remote URL."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.set_remote(str(tmp_path / "does-not-exist.git"))
        with pytest.raises(GitOperationError, match="Failed to fetch"):
            gm.fetch()


class TestPullFlows:
    """Test pull() remote flows against real local bare origins."""

    def test_pull_missing_remote_branch(self, tmp_path):
        """pull should report when the remote branch does not exist."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        empty_bare = tmp_path / "empty.git"
        Repo.init(empty_bare, bare=True)
        gm.set_remote(str(empty_bare))
        current = gm.current_branch()
        result = gm.pull()
        assert result == f"Remote branch '{current}' not found. Nothing to pull."

    def test_pull_fast_forward_rebase(self, tmp_path):
        """pull should fast-forward to newly pushed origin commits."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "new.txt").write_text("from origin\n")
        other.index.add(["new.txt"])
        other.index.commit("origin advance")
        other.git.push("origin", branch)

        head_before = Repo(str(work_dir)).head.commit.hexsha
        gm = GitManager(work_dir)
        result = gm.pull()
        assert isinstance(result, str) and len(result) > 0
        assert (work_dir / "new.txt").read_text() == "from origin\n"
        work_head = Repo(str(work_dir)).head.commit
        assert work_head.hexsha != head_before
        assert work_head.message.strip() == "origin advance"

    def test_pull_stashes_dirty_work(self, tmp_path):
        """pull should stash uncommitted changes and restore them."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "new.txt").write_text("from origin\n")
        other.index.add(["new.txt"])
        other.index.commit("origin advance")
        other.git.push("origin", branch)

        (work_dir / "f.txt").write_text("line1\nline2\nlocal edit\n")
        head_before = Repo(str(work_dir)).head.commit.hexsha
        gm = GitManager(work_dir)
        result = gm.pull()
        assert isinstance(result, str) and len(result) > 0
        assert (work_dir / "new.txt").read_text() == "from origin\n"
        assert "local edit" in (work_dir / "f.txt").read_text()
        work_head = Repo(str(work_dir)).head.commit
        assert work_head.hexsha != head_before
        assert work_head.message.strip() == "origin advance"

    def test_pull_merge_mode(self, tmp_path):
        """pull with rebase=False should merge origin commits."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "new.txt").write_text("from origin\n")
        other.index.add(["new.txt"])
        other.index.commit("origin advance")
        other.git.push("origin", branch)

        head_before = Repo(str(work_dir)).head.commit.hexsha
        gm = GitManager(work_dir)
        result = gm.pull(rebase=False)
        assert isinstance(result, str) and len(result) > 0
        assert (work_dir / "new.txt").read_text() == "from origin\n"
        work_head = Repo(str(work_dir)).head.commit
        assert work_head.hexsha != head_before
        assert work_head.message.strip() == "origin advance"

    def test_pull_conflict_raises(self, tmp_path):
        """pull should raise GitOperationError on rebase conflicts."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "f.txt").write_text("OTHER\nline2\n")
        other.index.add(["f.txt"])
        other.index.commit("origin conflicting change")
        other.git.push("origin", branch)

        gm = GitManager(work_dir)
        (work_dir / "f.txt").write_text("LOCAL\nline2\n")
        gm.add_all()
        gm.commit("local conflicting change")
        with pytest.raises(GitOperationError, match="Merge conflict"):
            gm.pull()

    def test_pull_stash_pop_conflict_warns(self, tmp_path):
        """pull should warn when stashed changes clash with pulled commits."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "f.txt").write_text("OTHER\nline2\n")
        other.index.add(["f.txt"])
        other.index.commit("origin change")
        other.git.push("origin", branch)

        gm = GitManager(work_dir)
        (work_dir / "f.txt").write_text("WORKDIRTY\nline2\n")
        result = gm.pull()
        assert "Stash pop failed" in result

    def test_pull_deleted_origin_raises_and_restores_stash(self, tmp_path):
        """pull should restore the stash when the origin vanished."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        (work_dir / "f.txt").write_text("line1\nline2\nprecious edit\n")
        shutil.rmtree(bare)
        gm = GitManager(work_dir)
        with pytest.raises(GitOperationError, match="Failed to pull"):
            gm.pull()
        assert "precious edit" in (work_dir / "f.txt").read_text()

    def test_pull_oserror_raises(self, tmp_path):
        """pull should map OSError to GitOperationError."""
        from unittest.mock import patch

        bare, _ = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        gm = GitManager(work_dir)
        with patch("git.cmd.Git.execute", side_effect=OSError("disk full")):
            with pytest.raises(GitOperationError, match="Failed to pull"):
                gm.pull()

    def test_pull_oserror_restores_stash(self, tmp_path):
        """pull should restore stashed changes when disk operations fail."""
        from unittest.mock import patch

        from git.cmd import Git

        bare, _ = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        (work_dir / "f.txt").write_text("line1\nline2\nprecious edit\n")
        gm = GitManager(work_dir)
        real_execute = Git.execute

        def fail_on_pull(execute_self, *args, **kwargs):
            cmd = args[0] if args else kwargs.get("command", "")
            if "pull" in str(cmd):
                raise OSError("disk full")
            return real_execute(execute_self, *args, **kwargs)

        with patch("git.cmd.Git.execute", autospec=True, side_effect=fail_on_pull):
            with pytest.raises(GitOperationError, match="Failed to pull"):
                gm.pull()
        assert "precious edit" in (work_dir / "f.txt").read_text()


class TestPushFlows:
    """Test push() flows against real local bare origins."""

    def test_push_new_commit(self, tmp_path):
        """push should publish local commits to the origin."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        gm = GitManager(work_dir)
        (work_dir / "pushed.txt").write_text("hello\n")
        gm.add_all()
        gm.commit("push me")
        result = gm.push()
        assert isinstance(result, str) and len(result) > 0
        assert Repo(str(bare)).heads[branch].commit.message.strip() == "push me"

    def test_push_without_upstream_flag(self, tmp_path):
        """push without set_upstream should still publish commits."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        gm = GitManager(work_dir)
        (work_dir / "pushed.txt").write_text("hello\n")
        gm.add_all()
        gm.commit("push me flat")
        result = gm.push(set_upstream=False)
        assert isinstance(result, str) and len(result) > 0
        assert Repo(str(bare)).heads[branch].commit.message.strip() == "push me flat"

    def test_push_rejected_raises(self, tmp_path):
        """push should raise GitOperationError when the remote moved first."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "new.txt").write_text("origin wins\n")
        other.index.add(["new.txt"])
        other.index.commit("origin wins")
        other.git.push("origin", branch)

        gm = GitManager(work_dir)
        (work_dir / "stale.txt").write_text("stale work\n")
        gm.add_all()
        gm.commit("stale commit")
        with pytest.raises(GitOperationError, match="Push rejected"):
            gm.push()

    def test_push_deleted_origin_raises(self, tmp_path):
        """push should raise GitOperationError when the origin vanished."""
        bare, _ = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        gm = GitManager(work_dir)
        (work_dir / "stale.txt").write_text("stale work\n")
        gm.add_all()
        gm.commit("stale commit")
        shutil.rmtree(bare)
        with pytest.raises(GitOperationError, match="Failed to push"):
            gm.push()

    def test_push_oserror_raises(self, tmp_path):
        """push should map OSError to GitOperationError."""
        from unittest.mock import patch

        bare, _ = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        gm = GitManager(work_dir)
        (work_dir / "pushed.txt").write_text("hello\n")
        gm.add_all()
        gm.commit("push me")
        with patch("git.cmd.Git.execute", side_effect=OSError("disk full")):
            with pytest.raises(GitOperationError, match="Failed to push"):
                gm.push()


class TestGetAllBranchStatsEdgeCases:
    """Test get_all_branch_stats empty and malformed output paths."""

    def test_empty_repo_returns_empty(self, tmp_path):
        """get_all_branch_stats should return [] with no branches."""
        repo_path = tmp_path / "empty"
        repo_path.mkdir()
        Repo.init(repo_path)
        gm = GitManager(repo_path)
        assert gm.get_all_branch_stats() == []

    def test_git_failure_returns_empty(self, tmp_path):
        """get_all_branch_stats should return [] when git fails."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        _ = gm.repo
        shutil.rmtree(repo_path / ".git")
        assert gm.get_all_branch_stats() == []

    def test_blank_and_malformed_lines_skipped(self, tmp_path):
        """get_all_branch_stats should skip blank and malformed lines."""
        from unittest.mock import patch

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        _ = gm.repo
        payload = "main|2025-01-02|subject here\n\nnot-enough-parts"
        with patch("git.cmd.Git.execute", return_value=payload):
            stats = gm.get_all_branch_stats()
        assert stats == [
            {
                "name": "main",
                "last_commit_date": "2025-01-02",
                "last_commit_msg": "subject here",
                "file_count": None,
            }
        ]


class TestGetSyncStatusFlows:
    """Test get_sync_status against real local bare origins."""

    def test_ahead_and_behind_counts(self, tmp_path):
        """get_sync_status should count diverged commits both ways."""
        bare, branch = _seed_bare_origin(tmp_path)
        work_dir = tmp_path / "work"
        _clone_from(bare, work_dir)
        other = _clone_from(bare, tmp_path / "other")
        (tmp_path / "other" / "new.txt").write_text("origin\n")
        other.index.add(["new.txt"])
        other.index.commit("origin advance")
        other.git.push("origin", branch)

        gm = GitManager(work_dir)
        (work_dir / "local.txt").write_text("local\n")
        gm.add_all()
        gm.commit("local advance")
        status = gm.get_sync_status()
        assert status["ahead"] == 1
        assert status["behind"] == 1
        assert status["remote_configured"] is True
        assert status["remote_branch_exists"] is True

    def test_missing_remote_branch(self, tmp_path):
        """get_sync_status should flag a remote without the branch."""
        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        empty_bare = tmp_path / "empty.git"
        Repo.init(empty_bare, bare=True)
        gm.set_remote(str(empty_bare))
        status = gm.get_sync_status()
        assert status["remote_configured"] is True
        assert status["remote_branch_exists"] is False
        assert status["ahead"] == 0
        assert status["behind"] == 0

    def test_fetch_failure_returns_error(self, tmp_path):
        """get_sync_status should return an error dict when fetch fails."""
        from unittest.mock import patch

        repo_path = _init_repo(tmp_path)
        gm = GitManager(repo_path)
        gm.set_remote(str(tmp_path / "does-not-exist.git"))
        with patch.object(gm, "fetch", side_effect=GitCommandError("fetch", 128)):
            status = gm.get_sync_status()
        assert status == {
            "ahead": 0,
            "behind": 0,
            "remote_configured": True,
            "error": True,
        }
