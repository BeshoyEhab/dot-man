"""Tests for cli/navigate_preview.py — branch/commit/list display helpers.

All cases run against a REAL git repo at the patched ``REPO_DIR``
(registry-based fixtures), asserting on what actually reaches the
console. The only mock is the diff-failure fallback: ``branch_exists``
gates the range so the exception is not constructible through real
branch state.
"""

from contextlib import ExitStack
from unittest.mock import patch

import pytest

from dot_man.cli.navigate_preview import (
    get_commits_with_file_changes,
    show_branch_diff_preview,
    show_commit_diff,
    show_commits_list,
)
from tests.conftest import _dot_man_patches


@pytest.fixture
def preview_env(tmp_path):
    """Hermetic env with a real repo: default@{commit1, commit2+tag} + work.

    commit1 (root): ``a.txt``.
    commit2: adds 13 files (``f01..f12`` + edited ``a.txt``) and carries
    the ``v1.0`` tag — gives parents, >10 changed files, ``files_more``
    and a tag simultaneously.
    branch ``work``: one more change to ``a.txt`` so a real two-branch
    diff exists.
    Yields ``(repo, default_branch, work)``.
    """
    from git import Repo

    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    with ExitStack() as stack:
        for p in _dot_man_patches(
            dot_man_dir, repo_dir, backups_dir, global_toml, home
        ):
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        repo_dir.mkdir(parents=True)
        repo = Repo.init(repo_dir)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Tester")
            config.set_value("user", "email", "tester@example.com")

        # commit 1 (root)
        (repo_dir / "a.txt").write_text("v1\n")
        repo.index.add(["a.txt"])
        repo.index.commit("Initial commit")

        # commit 2: 12 new files + edit → 13 files changed
        for i in range(1, 13):
            (repo_dir / f"f{i:02d}.txt").write_text("x\n")
        (repo_dir / "a.txt").write_text("v2\n")
        repo.index.add([f"f{i:02d}.txt" for i in range(1, 13)] + ["a.txt"])
        repo.index.commit("Add twelve files")

        default_branch = repo.active_branch.name
        repo.create_tag("v1.0")

        # work branch with a real divergence
        repo.create_head("work").checkout()
        (repo_dir / "a.txt").write_text("work change\n")
        repo.index.add(["a.txt"])
        repo.index.commit("Work change")
        repo.heads[default_branch].checkout()

        yield repo, default_branch, "work"


@pytest.fixture
def empty_repo_env(tmp_path):
    """Hermetic env with a real repo that has NO commits (unborn HEAD)."""
    from git import Repo

    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    with ExitStack() as stack:
        for p in _dot_man_patches(
            dot_man_dir, repo_dir, backups_dir, global_toml, home
        ):
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        repo_dir.mkdir(parents=True)
        repo = Repo.init(repo_dir)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Tester")
            config.set_value("user", "email", "tester@example.com")

        yield repo


def _out(capsys):
    """Whitespace-normalized console output (rich wraps long lines)."""
    return " ".join(capsys.readouterr().out.split())


class TestBranchDiffPreview:
    """show_branch_diff_preview renders a real two-branch diff."""

    def test_lists_changed_files_between_branches(self, preview_env, capsys):
        _, default_branch, work = preview_env

        show_branch_diff_preview(None, default_branch, work)

        out = _out(capsys)
        assert f"From: {default_branch}" in out
        assert f"To: {work}" in out
        assert "Changed files:" in out
        assert "a.txt" in out

    def test_no_differences_when_branches_point_same_commit(self, preview_env, capsys):
        _, default_branch, _ = preview_env

        show_branch_diff_preview(None, default_branch, default_branch)

        out = _out(capsys)
        assert "Changed files:" in out
        assert "(no differences)" in out

    def test_show_diff_renders_full_diff_header(self, preview_env, capsys):
        _, default_branch, work = preview_env

        show_branch_diff_preview(None, default_branch, work, show_diff=True)

        out = _out(capsys)
        assert "Full Diff:" in out
        assert "Changed files:" in out

    def test_diff_failure_warns_instead_of_raising(self, capsys):
        """The fallback message renders when the git diff call blows up."""
        with patch("dot_man.cli.navigate_preview.GitManager") as mock_gm:
            mock_gm.return_value.branch_exists.return_value = True
            mock_gm.return_value.repo.git.diff.side_effect = RuntimeError("boom")

            show_branch_diff_preview(None, "main", "work")

        out = _out(capsys)
        assert "Could not diff branches: boom" in out


class TestCommitDiff:
    """show_commit_diff renders real commit metadata and file lists."""

    def test_lists_files_with_truncation_past_ten(self, preview_env, capsys):
        repo, _, _ = preview_env
        commit = repo.head.commit  # default tip = commit2 (13 files)

        show_commit_diff(None, commit.hexsha)

        out = _out(capsys)
        assert "Commit Details" in out
        assert commit.hexsha[:7] in out
        assert "Add twelve files" in out
        assert "Tester <tester@example.com>" in out
        assert "Files changed:" in out
        assert "a.txt" in out
        # >10 entries → truncated tail
        assert "... and " in out and "more" in out

    def test_invalid_sha_falls_back_to_warning(self, preview_env, capsys):
        show_commit_diff(None, "deadbeef")

        out = _out(capsys)
        assert "Could not show commit diff" in out


class TestCommitsList:
    """show_commits_list renders tags, files_more and empty states."""

    def test_shows_tagged_commit_with_files_overflow(self, preview_env, capsys):
        _, default_branch, _ = preview_env

        show_commits_list(None, default_branch)

        out = _out(capsys)
        assert "Commit History on" in out
        assert "🏷 v1.0" in out
        assert "Add twelve files" in out
        # 13 files → shown 5, overflow printed
        assert "... and 8 more" in out

    def test_files_only_shows_overflow_marker(self, preview_env, capsys):
        _, default_branch, _ = preview_env

        show_commits_list(None, default_branch, files_only=True)

        out = _out(capsys)
        assert "Files:" in out
        assert "... and 8 more" in out

    def test_files_only_empty_history_message(self, empty_repo_env, capsys):
        show_commits_list(None, "main", files_only=True)

        out = _out(capsys)
        assert "(no commits with tracked file changes)" in out

    def test_no_commits_message(self, empty_repo_env, capsys):
        show_commits_list(None, "main")

        out = _out(capsys)
        assert "(no commits)" in out


class TestGetCommitsWithFileChanges:
    """get_commits_with_file_changes keeps only commits touching files."""

    def test_filters_empty_commits_and_keeps_overflow_count(self, preview_env):
        _, default_branch, _ = preview_env

        commits = get_commits_with_file_changes(None, default_branch)

        messages = [c["message"] for c in commits]
        assert "Add twelve files" in messages
        assert "Initial commit" in messages
        assert all(c["files"] for c in commits)
        tagged = next(c for c in commits if c["message"] == "Add twelve files")
        assert len(tagged["files"]) == 5
        assert tagged["files_more"] == 8
