"""Tests using shared fixtures for GitManager operations."""

import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, ".")


class TestGitManagerFixtures:
    """Test GitManager using fixtures."""

    def test_list_branches(self, git_repo_with_branches):
        from dot_man.core import GitManager

        git = GitManager(git_repo_with_branches)
        branches = git.list_branches()
        assert "main" in branches
        assert "work" in branches

    def test_list_tags(self, git_repo_with_tags):
        from dot_man.core import GitManager

        git = GitManager(git_repo_with_tags)
        tags = git.list_tags()
        assert "v1.0" in tags

    def test_get_commits(self, git_repo_with_commits):
        from dot_man.core import GitManager

        git = GitManager(git_repo_with_commits)
        commits = list(git.get_commits(count=10))
        assert len(commits) == 4  # 1 initial + 3 from fixture

    def test_create_branch(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        git.create_branch("new-branch")
        assert git.branch_exists("new-branch")

    def test_checkout_branch(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        git.create_branch("feature")
        git.checkout("feature")
        assert git.current_branch() == "feature"

    def test_create_tag(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        git.create_tag("v1.0")
        assert "v1.0" in git.list_tags()

    def test_delete_tag(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        git.create_tag("temp")
        git.delete_tag("temp")
        assert "temp" not in git.list_tags()

    def test_get_tag_commit(self, git_repo_with_tags):
        from dot_man.core import GitManager

        git = GitManager(git_repo_with_tags)
        commit = git.get_tag_commit("v1.0")
        assert commit is not None
        assert len(commit) == 7

    def test_is_dirty_true(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        (git._repo_path / "new.txt").write_text("new")
        assert git.is_dirty() is True

    def test_is_dirty_false(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        assert git.is_dirty() is False

    def test_get_status_untracked(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        (git._repo_path / "untracked.txt").write_text("content")
        status = git.get_status()
        assert "untracked.txt" in status["untracked"]

    def test_checkout_commit(self, git_repo_with_commits):
        from dot_man.core import GitManager

        git = GitManager(git_repo_with_commits)
        commits = list(git.get_commits(count=1))
        first_sha = commits[0]["sha"]
        git.checkout_commit(first_sha)

    def test_set_remote(self, git_repo):
        from dot_man.core import GitManager

        git = GitManager(git_repo)
        git.set_remote("https://github.com/test/repo.git")
        assert git.has_remote() is True


class TestBranchParsingParams:
    """Parametrized tests for branch parsing."""

    @pytest.mark.parametrize("branch", ["main", "work", "feature", "develop"])
    def test_parse_simple_branch(self, branch):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg(branch)
        assert result["type"] == "branch"
        assert result["target"] == branch

    @pytest.mark.parametrize("tag", ["v1", "v2", "latest"])
    def test_parse_tags_with_mock(self, tag):
        with patch("dot_man.cli.common.GitManager") as mock:
            mock.return_value.list_tags.return_value = ["v1", "v2", "latest"]
            from dot_man.cli.common import parse_branch_arg

            result = parse_branch_arg(tag)
            assert result["type"] == "tag"

    def test_parse_commit_7char(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abc1234")
        assert result["type"] == "commit"

    def test_parse_commit_40char(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("a" * 40)
        assert result["type"] == "commit"


class TestFileComparison:
    """Test file comparison."""

    def test_identical_files(self, tmp_path):
        from dot_man.files import compare_files

        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("same content")
        f2.write_text("same content")
        assert compare_files(f1, f2) is True

    def test_different_files(self, tmp_path):
        from dot_man.files import compare_files

        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("content A")
        f2.write_text("content B")
        assert compare_files(f1, f2) is False

    def test_missing_file(self, tmp_path):
        from dot_man.files import compare_files

        f1 = tmp_path / "exists.txt"
        f2 = tmp_path / "missing.txt"
        f1.write_text("test")
        assert compare_files(f1, f2) is False
