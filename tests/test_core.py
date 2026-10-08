"""Strong tests for core.py — GitManager and core git operations.

Merged replacement for test_core.py, test_core_v1.py, and
test_git_manager_extended.py. Every test drives a real git repository
(GitPython) and asserts exact values: branch names, commit SHAs, file
contents, status buckets, and error messages.
"""

import re
from pathlib import Path

import pytest
from git import Repo

from dot_man.core import GitManager
from dot_man.exceptions import BranchNotFoundError, GitOperationError

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_repo(tmp_path):
    """Fresh git repository with user config but no commits yet."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")
    return repo_dir


@pytest.fixture
def committed_repo(temp_repo):
    """temp_repo with one commit, so branch operations are possible."""
    repo = Repo(temp_repo)
    (temp_repo / "a.txt").write_text("A")
    repo.index.add(["a.txt"])
    repo.index.commit("Initial")
    return temp_repo


def active_branch_name(repo_path):
    """Return the checked-out branch name for a repository path."""
    return Repo(repo_path).active_branch.name


# =============================================================================
# Construction and init
# =============================================================================


class TestGitManagerConstruction:
    """GitManager binds to the repository it is given."""

    def test_binds_to_existing_repo(self, temp_repo):
        """Construction must expose the real repository, not a stub.

        If GitManager pointed anywhere else, every later operation would
        silently act on the wrong repository.
        """
        gm = GitManager(temp_repo)

        assert Path(gm.repo.working_dir).resolve() == temp_repo.resolve()
        assert gm.repo.bare is False

    def test_init_on_existing_repo_is_idempotent(self, committed_repo):
        """Re-running init on a live repo must be a harmless no-op.

        Users re-run init from docs/troubleshooting; it must not rewrite
        history, drop branches, or fail.
        """
        gm = GitManager(committed_repo)
        branches_before = sorted(gm.list_branches())
        head_before = Repo(committed_repo).head.commit.hexsha

        assert gm.init() is None
        assert sorted(gm.list_branches()) == branches_before
        assert Repo(committed_repo).head.commit.hexsha == head_before
        assert gm.is_initialized() is True

    def test_init_on_fresh_dir_creates_empty_repo(self, tmp_path):
        """init() on a plain directory must create a usable, empty repo.

        The first-run happy path starts here: after init, listing
        branches and tags must answer cleanly (empty lists), not raise.
        """
        fresh = tmp_path / "fresh"
        fresh.mkdir()
        gm = GitManager(fresh)
        assert gm.is_initialized() is False

        assert gm.init() is None
        assert gm.is_initialized() is True
        assert (fresh / ".git").exists()
        assert gm.list_branches() == []
        assert gm.list_tags() == []


# =============================================================================
# current_branch
# =============================================================================


class TestCurrentBranch:
    """Reporting of the checked-out branch, including detached HEAD."""

    def test_matches_active_branch(self, committed_repo):
        """current_branch() must equal git's own active branch.

        The old test hardcoded 'master', which breaks wherever the
        default branch is named differently; compare against git instead.
        """
        expected = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)

        assert gm.current_branch() == expected

    def test_detached_head_reports_head(self, committed_repo):
        """On a detached HEAD there is no branch, so 'HEAD' is returned.

        Navigation code relies on this sentinel to detect detached state
        instead of crashing or inventing a branch name.
        """
        repo = Repo(committed_repo)
        repo.git.checkout("--detach")
        gm = GitManager(committed_repo)

        assert gm.current_branch() == "HEAD"


# =============================================================================
# Listing branches
# =============================================================================


class TestListBranches:
    """list_branches() must report exactly the refs git has."""

    def test_includes_created_branches(self, committed_repo):
        """Every created branch appears; the set has no extras.

        A missing or phantom branch here would mislead navigate/status.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("feature")
        gm.create_branch("develop")

        assert set(gm.list_branches()) == {default, "feature", "develop"}

    def test_multi_branch_fixture_exact_set(self, git_repo_with_branches):
        """On the renamed-main fixture the answer is exactly three names.

        Guards against returning stale refs or dropping renamed branches.
        """
        gm = GitManager(git_repo_with_branches)

        assert set(gm.list_branches()) == {"main", "work", "personal"}

    def test_includes_slash_and_unicode_names(self, committed_repo):
        """Slash (feature/x) and unicode (bränch) refs must be listed.

        Config branches commonly use slashes; dropping them would hide
        whole configurations from the user.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("feature/x")
        gm.create_branch("bränch")

        assert set(gm.list_branches()) == {default, "feature/x", "bränch"}


# =============================================================================
# branch_exists
# =============================================================================


class TestBranchExists:
    """Existence checks must be exact for present and absent refs."""

    def test_present_and_absent_branches(self, committed_repo):
        """True for real branches, False for invented ones.

        navigate uses this to decide create-vs-switch, so a false
        positive would overwrite a user's expectations.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("feature")

        assert gm.branch_exists(default) is True
        assert gm.branch_exists("feature") is True
        assert gm.branch_exists("nonexistent") is False

    def test_slash_unicode_and_prefix_lookalikes(self, committed_repo):
        """'feature' alone must not match 'feature/x'; unicode must work.

        Prefix confusion would send users to the wrong branch, and
        unicode names are valid git refs that must resolve.
        """
        gm = GitManager(committed_repo)
        gm.create_branch("feature/x")
        gm.create_branch("bränch")

        assert gm.branch_exists("feature/x") is True
        assert gm.branch_exists("bränch") is True
        assert gm.branch_exists("feature") is False


# =============================================================================
# create_branch
# =============================================================================


class TestCreateBranch:
    """create_branch() adds a ref without disturbing the working tree."""

    def test_creates_exact_branch_without_switching(self, committed_repo):
        """The new branch exists but HEAD stays where it was.

        Creating a branch as a side effect of switching would change the
        user's configuration unexpectedly.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)

        gm.create_branch("new-branch")

        assert gm.branch_exists("new-branch") is True
        assert gm.current_branch() == default
        assert "new-branch" in gm.list_branches()

    def test_creates_slash_and_unicode_branch_names(self, committed_repo):
        """Ref names with slashes and accents survive creation exactly.

        A sanitizer that mangled 'feature/x' would make configurations
        unfindable later.
        """
        gm = GitManager(committed_repo)

        gm.create_branch("feature/x")
        gm.create_branch("bränch")

        assert gm.branch_exists("feature/x") is True
        assert gm.branch_exists("bränch") is True


# =============================================================================
# delete_branch
# =============================================================================


class TestDeleteBranch:
    """delete_branch() removes exactly the requested ref, or explains."""

    def test_deletes_only_the_target_branch(self, committed_repo):
        """After deletion the target is gone and siblings remain.

        Deleting more than asked would destroy another configuration.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("keep-me")
        gm.create_branch("to-delete")

        gm.delete_branch("to-delete")

        assert gm.branch_exists("to-delete") is False
        assert gm.branch_exists("keep-me") is True
        assert set(gm.list_branches()) == {default, "keep-me"}

    def test_deletes_slash_named_branch(self, committed_repo):
        """Slash-named refs delete like any other (no path mangling).

        Treating 'feature/x' as a path would fail or delete the wrong ref.
        """
        gm = GitManager(committed_repo)
        gm.create_branch("feature/x")

        gm.delete_branch("feature/x")

        assert "feature/x" not in gm.list_branches()

    def test_deleting_current_branch_raises(self, committed_repo):
        """Deleting the checked-out branch is refused with a clear error.

        Git itself forbids it; the user must see why, not a raw
        git traceback.
        """
        gm = GitManager(committed_repo)

        with pytest.raises(GitOperationError, match="Cannot delete the current branch"):
            gm.delete_branch(active_branch_name(committed_repo))

    def test_deleting_missing_branch_raises(self, committed_repo):
        """A typo'd branch name must surface as BranchNotFoundError.

        Silently succeeding would let scripts believe cleanup happened.
        """
        gm = GitManager(committed_repo)

        with pytest.raises(BranchNotFoundError, match="Branch not found: ghost"):
            gm.delete_branch("ghost")


# =============================================================================
# checkout
# =============================================================================


class TestCheckout:
    """checkout() moves HEAD and the working tree to the named branch."""

    def test_checkouts_existing_branch(self, git_repo_with_branches):
        """HEAD and git agree after switching to 'work'.

        This is the core of navigate; disagreement means the switch
        half-happened.
        """
        gm = GitManager(git_repo_with_branches)

        gm.checkout("work")

        assert gm.current_branch() == "work"
        assert Repo(git_repo_with_branches).active_branch.name == "work"

    def test_checkout_creates_branch_when_requested(self, git_repo):
        """create=True must both create and switch to the new branch."""
        gm = GitManager(git_repo)

        gm.checkout("new-branch", create=True)

        assert gm.current_branch() == "new-branch"
        assert Repo(git_repo).active_branch.name == "new-branch"
        assert gm.branch_exists("new-branch") is True

    def test_checkout_create_on_existing_branch_is_noop(self, git_repo):
        """create=True with an existing name must not fail or duplicate.

        Users combine create flags in scripts; hitting an already-used
        branch name should just land on it.
        """
        default = active_branch_name(git_repo)
        gm = GitManager(git_repo)
        branches_before = sorted(gm.list_branches())

        gm.checkout(default, create=True)

        assert gm.current_branch() == default
        assert sorted(gm.list_branches()) == branches_before

    def test_checkout_missing_branch_raises(self, git_repo_with_branches):
        """Unknown branch names raise BranchNotFoundError verbatim.

        The exact message names the typo so users can fix it immediately.
        """
        gm = GitManager(git_repo_with_branches)

        with pytest.raises(BranchNotFoundError, match="Branch not found: ghost"):
            gm.checkout("ghost")

    def test_checkout_slash_branch_flips_unique_files(self, committed_repo):
        """Switching branches must add/remove that branch's own files.

        A file present on one configuration and absent on another is the
        whole point of per-branch dotfiles; a stale working tree would
        leak settings between configurations.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("feature/x")
        gm.checkout("feature/x")
        (committed_repo / "only_feature.txt").write_text("F")
        gm.add_all()
        gm.commit("feature only")

        assert (committed_repo / "only_feature.txt").exists()
        assert gm.current_branch() == "feature/x"

        gm.checkout(default)

        assert not (committed_repo / "only_feature.txt").exists()
        assert gm.current_branch() == default

        gm.checkout("feature/x")

        assert (committed_repo / "only_feature.txt").exists()
        assert gm.current_branch() == "feature/x"

    def test_checkout_unicode_branch(self, committed_repo):
        """Unicode branch names check out intact (no normalization).

        Mangled names would orphan a user's accented configuration.
        """
        gm = GitManager(committed_repo)
        gm.create_branch("bränch")

        gm.checkout("bränch")

        assert gm.current_branch() == "bränch"
        assert Repo(committed_repo).active_branch.name == "bränch"

    def test_create_branch_with_space_rejected_before_writing_ref(self, committed_repo):
        """Invalid branch names fail at creation, not later as broken refs.

        git forbids spaces in ref names, but GitPython's create_head writes
        the ref file anyway — git then ignores it ("ignoring ref with broken
        name") while list_branches() still reports it, so stats and branch
        listings disagree. GitManager must validate with git's own
        check-ref-format before creating anything.
        """
        gm = GitManager(committed_repo)
        before = set(gm.list_branches())

        with pytest.raises(GitOperationError, match="Invalid branch name 'has space'"):
            gm.create_branch("has space")

        assert set(gm.list_branches()) == before
        assert not (committed_repo / ".git" / "refs" / "heads" / "has space").exists()
        with pytest.raises(BranchNotFoundError):
            gm.checkout("has space")


# =============================================================================
# Commits: retrieval
# =============================================================================


class TestGetCommits:
    """get_commits()/get_commits_detailed() mirror git history exactly."""

    def test_get_commits_exact_history(self, git_repo_with_commits):
        """Newest-first messages match git, with correct sha and keys.

        'At least one commit' proved nothing; navigation prompts show
        these messages, so they must be the real ones.
        """
        gm = GitManager(git_repo_with_commits)
        repo = Repo(git_repo_with_commits)

        commits = list(gm.get_commits(count=10))

        assert [c["message"] for c in commits] == [
            c.message for c in repo.iter_commits()
        ]
        assert commits[0]["sha"] == repo.head.commit.hexsha[:7]
        assert set(commits[0]) == {"sha", "message", "author", "date"}
        assert commits[0]["author"] == "Test"

    def test_get_commits_count_zero_returns_empty(self, git_repo_with_commits):
        """count=0 must yield nothing, not the whole history.

        Guarded loop bounds (show 0 entries) must not be interpreted as
        'unlimited'.
        """
        gm = GitManager(git_repo_with_commits)

        assert list(gm.get_commits(count=0)) == []

    def test_get_commits_count_beyond_history(self, git_repo_with_commits):
        """Asking for more commits than exist returns exactly the history.

        A larger-than-history count must clamp, not raise or pad.
        """
        gm = GitManager(git_repo_with_commits)
        total = len(list(Repo(git_repo_with_commits).iter_commits()))

        assert len(list(gm.get_commits(count=total + 50))) == total

    def test_get_commits_detailed_exact_fields(self, git_repo_with_commits):
        """Detailed entries carry the full sha, real author, and files.

        The UI renders these fields verbatim; empty or wrong values would
        mislead during conflict resolution.
        """
        gm = GitManager(git_repo_with_commits)
        repo = Repo(git_repo_with_commits)

        detail = gm.get_commits_detailed()
        first = detail[0]

        assert len(detail) == len(list(repo.iter_commits()))
        assert first["full_sha"] == repo.head.commit.hexsha
        assert first["sha"] == repo.head.commit.hexsha[:7]
        assert first["message"] == repo.head.commit.message
        assert first["author"] == "Test"
        assert first["author_email"] == "test@test.com"
        assert first["files"] == list(repo.head.commit.stats.files)
        assert first["parent_count"] == 1
        assert first["is_merge"] is False
        assert first["tags"] == []
        assert set(first) == {
            "author",
            "author_email",
            "date",
            "deletions",
            "files",
            "files_more",
            "full_message",
            "full_sha",
            "insertions",
            "is_merge",
            "message",
            "parent_count",
            "relative_date",
            "sha",
            "tags",
        }

    @pytest.mark.parametrize(
        "count,expected",
        [(0, 0), (2, 2)],
        ids=["zero", "at-limit"],
    )
    def test_get_commits_detailed_count_limits(
        self, git_repo_with_commits, count, expected
    ):
        """count=0 yields none; count=2 yields exactly two entries.

        The old assertion only checked '<= 2', which a bug returning 0
        or 1 would still satisfy.
        """
        gm = GitManager(git_repo_with_commits)

        assert len(gm.get_commits_detailed(count=count)) == expected

    def test_get_commits_detailed_beyond_history(self, git_repo_with_commits):
        """count larger than the history clamps to the full log."""
        gm = GitManager(git_repo_with_commits)
        total = len(list(Repo(git_repo_with_commits).iter_commits()))

        assert len(gm.get_commits_detailed(count=total + 50)) == total


# =============================================================================
# Committing
# =============================================================================


class TestCommitOperations:
    """add_all()/commit() write history or report 'nothing to commit'."""

    def test_add_and_commit_returns_head_sha(self, committed_repo):
        """commit() returns the new head sha and records the message.

        The old test only checked 'not None'; callers compare the sha to
        decide whether a save actually landed.
        """
        (committed_repo / "b.txt").write_text("B")
        gm = GitManager(committed_repo)

        gm.add_all()
        sha = gm.commit("Test commit")
        repo = Repo(committed_repo)

        assert sha == repo.head.commit.hexsha
        assert repo.head.commit.message == "Test commit"
        assert "b.txt" in repo.head.commit.stats.files

    def test_commit_without_changes_returns_none(self, committed_repo):
        """A clean tree commits nothing and reports None.

        Callers use None to distinguish 'already saved' from a real sha;
        raising here would break idempotent save scripts.
        """
        gm = GitManager(committed_repo)

        assert gm.commit("Second commit") is None

    def test_commit_staged_file_via_repo_index(self, committed_repo):
        """Files staged directly through gm.repo.index commit normally.

        Exercises the public repo handle: staged content must land at
        HEAD with the exact message.
        """
        (committed_repo / "new_file.txt").write_text("new data")
        gm = GitManager(committed_repo)
        gm.repo.index.add(["new_file.txt"])

        sha = gm.commit("Add new file")
        repo = Repo(committed_repo)

        assert sha == repo.head.commit.hexsha
        assert repo.head.commit.message == "Add new file"
        assert repo.head.commit.stats.files == {
            "new_file.txt": {
                "change_type": "A",
                "deletions": 0,
                "insertions": 1,
                "lines": 1,
            }
        }

    def test_commit_unicode_message_and_filename(self, committed_repo):
        """Accented messages and space/unicode filenames survive intact.

        Localization or non-ASCII paths must not be stripped, or the
        user's config file would go untracked.
        """
        (committed_repo / "ünï file.txt").write_text("contént")
        gm = GitManager(committed_repo)

        gm.add_all()
        sha = gm.commit("Uniçode messäge ✓")
        repo = Repo(committed_repo)

        assert sha == repo.head.commit.hexsha
        assert repo.head.commit.message == "Uniçode messäge ✓"
        assert (
            gm.get_file_from_branch(active_branch_name(committed_repo), "ünï file.txt")
            == "contént"
        )


# =============================================================================
# Status: initialized / dirty / get_status
# =============================================================================


class TestIsInitialized:
    """is_initialized() distinguishes real dot-man repos from non-repos."""

    def test_initialized_repo_is_true(self, git_repo):
        """A real repository answers True."""
        gm = GitManager(git_repo)

        assert gm.is_initialized() is True

    def test_missing_path_is_false(self, tmp_path):
        """A path that was never initialized answers False, not an error.

        First-run flows probe before prompting; raising here would abort
        onboarding.
        """
        gm = GitManager(tmp_path / "empty")

        assert gm.is_initialized() is False


class TestIsDirty:
    """is_dirty() must detect both untracked additions and edits."""

    def test_clean_repo_is_not_dirty(self, git_repo):
        """A freshly committed tree is clean (no false alarms)."""
        gm = GitManager(git_repo)

        assert gm.is_dirty() is False

    def test_untracked_file_makes_dirty(self, committed_repo):
        """An untracked file counts as dirty — it is unsaved work."""
        gm = GitManager(committed_repo)
        (committed_repo / "new.txt").write_text("new")

        assert gm.is_dirty() is True

    def test_modified_tracked_file_makes_dirty(self, git_repo):
        """Editing a tracked file counts as dirty even without staging."""
        gm = GitManager(git_repo)
        (git_repo / "test.txt").write_text("changed content")

        assert gm.is_dirty() is True


class TestGetStatus:
    """get_status() buckets working-tree changes exactly."""

    def test_clean_repo_exact_buckets(self, git_repo):
        """Clean repo: all four buckets present and empty.

        Old tests checked isinstance/keys only; exact equality pins the
        bucket names callers read.
        """
        gm = GitManager(git_repo)

        assert gm.get_status() == {
            "modified": [],
            "new": [],
            "deleted": [],
            "untracked": [],
        }

    def test_untracked_file_bucket_exact(self, git_repo):
        """The new file lands in 'untracked' and nowhere else."""
        gm = GitManager(git_repo)
        (git_repo / "untracked.txt").write_text("untracked")

        assert gm.get_status() == {
            "modified": [],
            "new": [],
            "deleted": [],
            "untracked": ["untracked.txt"],
        }

    def test_modified_deleted_untracked_simultaneously(self, committed_repo):
        """All three change kinds at once land in their own buckets.

        Real sessions mix edits, deletions, and new files; a parser that
        merged or dropped buckets would hide changes from status/diff.
        """
        repo = Repo(committed_repo)
        (committed_repo / "gone.txt").write_text("to delete")
        repo.index.add(["gone.txt"])
        repo.index.commit("add gone")
        (committed_repo / "a.txt").write_text("A modified")
        (committed_repo / "gone.txt").unlink()
        (committed_repo / "untracked.txt").write_text("u")
        gm = GitManager(committed_repo)

        assert gm.get_status() == {
            "modified": ["a.txt"],
            "new": [],
            "deleted": ["gone.txt"],
            "untracked": ["untracked.txt"],
        }

    def test_staged_new_file_lands_in_new_bucket(self, committed_repo):
        """A git-added file shows up as 'new', not in no bucket at all.

        The index-vs-worktree diff never reports additions, and staged
        files are not untracked either — without a HEAD-vs-index pass the
        'new' bucket could never be populated (suspected bug).
        """
        repo = Repo(committed_repo)
        (committed_repo / "staged.txt").write_text("s")
        repo.index.add(["staged.txt"])
        gm = GitManager(committed_repo)

        assert gm.get_status() == {
            "modified": [],
            "new": ["staged.txt"],
            "deleted": [],
            "untracked": [],
        }

    def test_staged_deletion_lands_in_deleted_bucket(self, committed_repo):
        """A staged deletion (file removed AND git-added) is 'deleted'.

        The file is gone from both worktree and index, so the
        index-vs-worktree diff sees nothing — only HEAD-vs-index does.
        """
        repo = Repo(committed_repo)
        (committed_repo / "a.txt").unlink()
        repo.index.remove(["a.txt"])
        gm = GitManager(committed_repo)

        assert gm.get_status() == {
            "modified": [],
            "new": [],
            "deleted": ["a.txt"],
            "untracked": [],
        }

    def test_staged_then_edited_file_counts_once_in_modified(self, committed_repo):
        """Staged edit + further worktree edit = one 'modified' entry.

        Two diffs both see the change (HEAD->index and index->worktree);
        naively appending both would double-count the same file.
        """
        repo = Repo(committed_repo)
        (committed_repo / "a.txt").write_text("staged edit")
        repo.index.add(["a.txt"])
        (committed_repo / "a.txt").write_text("staged edit + more")
        gm = GitManager(committed_repo)

        assert gm.get_status() == {
            "modified": ["a.txt"],
            "new": [],
            "deleted": [],
            "untracked": [],
        }

    def test_staged_files_on_unborn_head_are_new(self, temp_repo):
        """Before the first commit, staged files are still 'new'.

        init -> add -> status is dot-man's happy path; HEAD does not
        exist yet, which made HEAD-vs-index comparisons raise.
        """
        repo = Repo(temp_repo)
        (temp_repo / "first.txt").write_text("f")
        repo.index.add(["first.txt"])
        gm = GitManager(temp_repo)

        assert gm.get_status() == {
            "modified": [],
            "new": ["first.txt"],
            "deleted": [],
            "untracked": [],
        }


# =============================================================================
# Branch stats
# =============================================================================


class TestBranchStats:
    """get_all_branch_stats() summarizes every branch with exact fields."""

    def test_stats_for_every_branch_exact_fields(self, git_repo_with_branches):
        """Each branch yields a record with the four documented keys.

        The old test only checked 'a list with >= 1 item'; callers render
        these fields directly, so names and keys must be exact.
        """
        gm = GitManager(git_repo_with_branches)
        expected_msg = Repo(git_repo_with_branches).head.commit.message

        stats = gm.get_all_branch_stats()

        assert {s["name"] for s in stats} == {"main", "work", "personal"}
        for record in stats:
            assert set(record) == {
                "name",
                "last_commit_date",
                "last_commit_msg",
                "file_count",
            }
            assert record["last_commit_msg"] == expected_msg
            assert re.fullmatch(
                r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}",
                record["last_commit_date"],
            )

    def test_stats_exactly_cover_git_visible_branches(self, committed_repo):
        """Stats match list_branches() exactly, unicode and slashes included.

        Space-containing names are invalid per git's ref rules; after the
        create-time validation they cannot exist at all, so the two views
        (ref files vs git for-each-ref) can no longer diverge.
        """
        gm = GitManager(committed_repo)
        initial = Repo(committed_repo).active_branch.name
        gm.create_branch("feature/x")
        gm.create_branch("bränch")

        stats = gm.get_all_branch_stats()

        assert {s["name"] for s in stats} == {initial, "feature/x", "bränch"}
        assert {s["name"] for s in stats} == set(gm.list_branches())


# =============================================================================
# Tags
# =============================================================================


class TestListTags:
    """list_tags() reports exactly the tags git has."""

    def test_no_tags_returns_empty_list(self, temp_repo):
        """A tagless repo answers [], not None or an error."""
        gm = GitManager(temp_repo)

        assert gm.list_tags() == []

    def test_fixture_repo_exact_tags(self, git_repo_with_tags):
        """Externally created (annotated) tags appear exactly as named."""
        gm = GitManager(git_repo_with_tags)

        assert gm.list_tags() == ["v1.0", "v2.0"]

    def test_lightweight_tags_created_and_listed(self, committed_repo):
        """Tags created via GitManager (no message) are lightweight.

        Both must be listed exactly; tag objects with no payload confirm
        the lightweight form.
        """
        gm = GitManager(committed_repo)

        gm.create_tag("v1.0")
        gm.create_tag("v2.0")

        assert gm.list_tags() == ["v1.0", "v2.0"]
        assert Repo(committed_repo).tags["v1.0"].tag is None
        assert Repo(committed_repo).tags["v2.0"].tag is None

    def test_annotated_vs_lightweight_explicit(self, committed_repo):
        """A message makes an annotated tag; omitting it makes lightweight.

        Only annotated tags carry release notes, so the distinction must
        be observable from both GitManager and git.
        """
        gm = GitManager(committed_repo)

        gm.create_tag("light")
        gm.create_tag("annot", message="Release notes")

        assert gm.list_tags() == ["annot", "light"]
        assert Repo(committed_repo).tags["annot"].tag is not None
        assert Repo(committed_repo).tags["annot"].tag.message == "Release notes"
        assert Repo(committed_repo).tags["light"].tag is None

    def test_unicode_tag_name(self, committed_repo):
        """Accented tag names create, list, and resolve to the commit.

        Normalizing accents would orphan version markers in non-English
        projects.
        """
        gm = GitManager(committed_repo)
        head_sha = Repo(committed_repo).head.commit.hexsha

        gm.create_tag("täge")

        assert gm.list_tags() == ["täge"]
        assert gm.get_tag_commit("täge") == head_sha[:7]

    def test_tag_name_with_space_raises(self, committed_repo):
        """Git forbids spaces in tag names; the error must be wrapped.

        Surfacing GitOperationError (with git's reason) beats a raw
        traceback for a simple typo.
        """
        gm = GitManager(committed_repo)

        with pytest.raises(GitOperationError, match="not a valid tag name"):
            gm.create_tag("täg é")


class TestTagOperations:
    """Tag delete and tag-to-commit resolution."""

    def test_delete_tag_removes_it_exactly(self, committed_repo):
        """The created tag disappears; the list ends empty."""
        gm = GitManager(committed_repo)

        gm.create_tag("temp-tag", message="Temp")
        assert gm.list_tags() == ["temp-tag"]

        gm.delete_tag("temp-tag")

        assert gm.list_tags() == []

    def test_delete_missing_tag_raises(self, committed_repo):
        """Deleting an unknown tag reports Tag not found, not silence.

        Scripts chaining tag cleanup depend on knowing a tag never
        existed versus was removed.
        """
        gm = GitManager(committed_repo)

        with pytest.raises(BranchNotFoundError, match="Tag not found: ghost-tag"):
            gm.delete_tag("ghost-tag")

    def test_get_tag_commit_matches_head(self, committed_repo):
        """A tag on HEAD resolves to HEAD's abbreviated sha.

        Exact equality (old test only checked a prefix) pins the
        abbreviation callers display during navigation.
        """
        gm = GitManager(committed_repo)
        head_sha = Repo(committed_repo).head.commit.hexsha
        gm.create_tag("v1.0.0")

        tag_commit = gm.get_tag_commit("v1.0.0")

        assert tag_commit == head_sha[:7]

    def test_get_tag_commit_dereferences_annotated_tag(self, git_repo_with_tags):
        """An annotated tag resolves to its commit, not the tag object.

        Tag objects have their own sha; returning it would point
        navigation at the wrong commit.
        """
        gm = GitManager(git_repo_with_tags)
        head_sha = Repo(git_repo_with_tags).head.commit.hexsha

        tag_commit = gm.get_tag_commit("v1.0")

        assert tag_commit == head_sha[:7]

    def test_get_tag_commit_missing_tag_returns_none(self, git_repo):
        """An unknown tag resolves to None instead of raising."""
        gm = GitManager(git_repo)

        assert gm.get_tag_commit("nonexistent-tag") is None


# =============================================================================
# get_file_from_branch
# =============================================================================


class TestGetFileFromBranch:
    """Reading file contents out of another branch's tree."""

    def test_existing_file_returns_content(self, git_repo_with_branches):
        """A tracked file on 'main' comes back byte-exact ('test')."""
        gm = GitManager(git_repo_with_branches)

        assert gm.get_file_from_branch("main", "test.txt") == "test"

    def test_missing_file_returns_none(self, git_repo_with_branches):
        """An absent path yields None (not an exception), so callers can
        offer defaults when a config lacks an optional file."""
        gm = GitManager(git_repo_with_branches)

        assert gm.get_file_from_branch("main", "nonexistent.txt") is None

    def test_missing_branch_returns_none(self, git_repo_with_branches):
        """A typo'd branch yields None rather than BranchNotFoundError.

        Diff/preview flows probe branches speculatively; None keeps them
        responsive."""
        gm = GitManager(git_repo_with_branches)

        assert gm.get_file_from_branch("ghost", "test.txt") is None

    def test_nested_unicode_path_on_other_branch(self, committed_repo):
        """dir/file.txt with unicode content reads back from its branch.

        Nested paths and non-ASCII bytes are exactly what real configs
        contain; both must survive the cross-branch read.
        """
        default = active_branch_name(committed_repo)
        gm = GitManager(committed_repo)
        gm.create_branch("feature/x")
        gm.checkout("feature/x")
        (committed_repo / "dir").mkdir()
        (committed_repo / "dir" / "file.txt").write_text("nested ünï code")
        gm.add_all()
        gm.commit("nested file")
        gm.checkout(default)

        assert gm.get_file_from_branch("feature/x", "dir/file.txt") == "nested ünï code"

    def test_filename_with_space_and_unicode(self, committed_repo):
        """A file named 'ünï file.txt' reads back with exact content.

        Paths with spaces are common in localized setups and break
        naive word-splitting implementations."""
        (committed_repo / "ünï file.txt").write_text("späce content")
        gm = GitManager(committed_repo)
        gm.add_all()
        gm.commit("unicode file")
        branch = active_branch_name(committed_repo)

        assert gm.get_file_from_branch(branch, "ünï file.txt") == "späce content"


# =============================================================================
# Remotes
# =============================================================================


class TestRemotes:
    """Remote configuration: presence, URL, and replacement."""

    def test_has_remote_false_without_remote(self, committed_repo):
        """A fresh repo reports no remote (exact False, not truthy junk)."""
        gm = GitManager(committed_repo)

        assert gm.has_remote() is False

    def test_get_remote_url_is_none_without_remote(self, committed_repo):
        """No remote means exactly None — not '' or a placeholder URL.

        Callers branch on None to offer 'dot-man remote set' guidance."""
        gm = GitManager(committed_repo)

        assert gm.get_remote_url() is None

    def test_set_remote_then_get_exact_url(self, committed_repo):
        """The URL round-trips byte-for-byte after set_remote()."""
        gm = GitManager(committed_repo)

        gm.set_remote("https://github.com/test/repo.git")

        assert gm.get_remote_url() == "https://github.com/test/repo.git"

    def test_set_remote_replaces_existing(self, committed_repo):
        """A second set_remote() overwrites rather than adding a second.

        Stale remotes would push to the wrong host after a repo move."""
        gm = GitManager(committed_repo)
        gm.set_remote("https://github.com/test/repo.git")

        gm.set_remote("https://github.com/test/moved.git")

        assert gm.get_remote_url() == "https://github.com/test/moved.git"
        assert gm.has_remote() is True

    def test_has_remote_transitions_false_to_true(self, committed_repo):
        """has_remote flips exactly False -> True once configured."""
        gm = GitManager(committed_repo)

        assert gm.has_remote() is False
        gm.set_remote("https://github.com/test/repo.git")
        assert gm.has_remote() is True


# =============================================================================
# Sync
# =============================================================================


class TestSync:
    """fetch() fails loudly and specifically when unconfigured."""

    def test_fetch_without_remote_raises(self, committed_repo):
        """fetch with no remote raises GitOperationError naming the fix.

        The old test only checked the exception type; the exact message
        tells the user which command to run next.
        """
        gm = GitManager(committed_repo)

        with pytest.raises(GitOperationError, match="No remote configured"):
            gm.fetch()
