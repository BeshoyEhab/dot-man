"""Tests for core.py — GitManager extended operations."""

from git import Repo

from dot_man.core import GitManager


class TestGitManagerCommitsDetailed:
    """Test get_commits_detailed."""

    def test_get_commits_detailed(self, git_repo_with_commits):
        gm = GitManager(git_repo_with_commits)
        commits = gm.get_commits_detailed()
        assert len(commits) > 0
        for c in commits:
            assert "sha" in c
            assert "message" in c

    def test_get_commits_detailed_with_count(self, git_repo_with_commits):
        gm = GitManager(git_repo_with_commits)
        commits = gm.get_commits_detailed(count=2)
        assert len(commits) <= 2


class TestGitManagerBranchStats:
    """Test get_all_branch_stats."""

    def test_branch_stats(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        stats = gm.get_all_branch_stats()
        assert isinstance(stats, list)
        assert len(stats) >= 1


class TestGitManagerIsDirty:
    """Test dirty detection."""

    def test_clean_repo(self, git_repo):
        gm = GitManager(git_repo)
        assert not gm.is_dirty()

    def test_dirty_repo(self, git_repo):
        gm = GitManager(git_repo)
        (git_repo / "test.txt").write_text("changed content")
        assert gm.is_dirty()


class TestGitManagerListBranches:
    """Test branch listing."""

    def test_list_branches(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        branches = gm.list_branches()
        assert "main" in branches
        assert "work" in branches
        assert "personal" in branches


class TestGitManagerListTags:
    """Test tag listing."""

    def test_list_tags(self, git_repo_with_tags):
        gm = GitManager(git_repo_with_tags)
        tags = gm.list_tags()
        assert "v1.0" in tags
        assert "v2.0" in tags


class TestGitManagerTagOperations:
    """Test tag create/delete/commit."""

    def test_create_tag(self, git_repo):
        gm = GitManager(git_repo)
        gm.create_tag("test-tag", message="Test message")
        assert "test-tag" in gm.list_tags()

    def test_delete_tag(self, git_repo):
        gm = GitManager(git_repo)
        gm.create_tag("temp-tag", message="Temp")
        assert "temp-tag" in gm.list_tags()
        gm.delete_tag("temp-tag")
        assert "temp-tag" not in gm.list_tags()

    def test_get_tag_commit(self, git_repo_with_tags):
        gm = GitManager(git_repo_with_tags)
        commit = gm.get_tag_commit("v1.0")
        assert commit is not None
        assert len(commit) > 6

    def test_get_tag_commit_nonexistent(self, git_repo):
        gm = GitManager(git_repo)
        commit = gm.get_tag_commit("nonexistent-tag")
        assert commit is None


class TestGitManagerCheckout:
    """Test checkout operations."""

    def test_checkout_existing(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        gm.checkout("work")
        repo = Repo(git_repo_with_branches)
        assert repo.active_branch.name == "work"

    def test_checkout_create_new(self, git_repo):
        gm = GitManager(git_repo)
        gm.checkout("new-branch", create=True)
        repo = Repo(git_repo)
        assert repo.active_branch.name == "new-branch"


class TestGitManagerCommit:
    """Test commit operations."""

    def test_commit_with_changes(self, git_repo):
        gm = GitManager(git_repo)
        (git_repo / "new_file.txt").write_text("new data")
        gm.repo.index.add(["new_file.txt"])
        gm.commit("Add new file")
        repo = Repo(git_repo)
        assert "Add new file" in repo.head.commit.message

    def test_commit_empty(self, git_repo):
        gm = GitManager(git_repo)
        result = gm.commit("Empty commit")
        assert result is None  # nothing to commit


class TestGitManagerBranchExists:
    """Test branch existence check."""

    def test_existing_branch(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        assert gm.branch_exists("work")

    def test_nonexistent_branch(self, git_repo):
        gm = GitManager(git_repo)
        assert not gm.branch_exists("nonexistent-branch-xyz")


class TestGitManagerGetFileFromBranch:
    """Test reading files from other branches."""

    def test_get_file_existing(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        content = gm.get_file_from_branch("main", "test.txt")
        assert content == "test"

    def test_get_file_nonexistent(self, git_repo_with_branches):
        gm = GitManager(git_repo_with_branches)
        content = gm.get_file_from_branch("main", "nonexistent.txt")
        assert content is None


class TestGitManagerGetStatus:
    """Test repository status."""

    def test_clean_status(self, git_repo):
        gm = GitManager(git_repo)
        status = gm.get_status()
        assert isinstance(status, dict)
        assert "modified" in status
        assert "new" in status
        assert "deleted" in status
        assert "untracked" in status

    def test_dirty_status(self, git_repo):
        gm = GitManager(git_repo)
        (git_repo / "untracked.txt").write_text("untracked")
        status = gm.get_status()
        assert "untracked.txt" in status["untracked"]


class TestGitManagerIsInitialized:
    """Test initialization check."""

    def test_initialized(self, git_repo):
        gm = GitManager(git_repo)
        assert gm.is_initialized()

    def test_not_initialized(self, tmp_path):
        gm = GitManager(tmp_path / "empty")
        assert not gm.is_initialized()


class TestGitManagerGetCommits:
    """Test basic commit retrieval."""

    def test_get_commits(self, git_repo_with_commits):
        gm = GitManager(git_repo_with_commits)
        commits = list(gm.get_commits(count=5))
        assert len(commits) >= 1
        assert "sha" in commits[0]
        assert "message" in commits[0]
