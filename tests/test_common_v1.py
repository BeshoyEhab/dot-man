"""Tests for cli/common.py — parse_branch_arg, completions, require_init."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestParseBranchArg:
    """Test parse_branch_arg with various input formats."""

    def test_simple_branch(self):
        from dot_man.cli.common import parse_branch_arg

        with patch("dot_man.cli.common.GitManager") as MockGM:
            mock_gm = MockGM.return_value
            mock_gm.list_tags.return_value = []
            result = parse_branch_arg("main")
        assert result["type"] == "branch"
        assert result["target"] == "main"

    def test_tag_format(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main@v1.0")
        assert result["type"] == "tag"
        assert result["base"] == "main"
        assert result["target"] == "v1.0"

    def test_commit_sha(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abcdef1")
        assert result["type"] == "commit"
        assert result["target"] == "abcdef1"

    def test_full_commit_sha(self):
        from dot_man.cli.common import parse_branch_arg

        sha = "a" * 40
        result = parse_branch_arg(sha)
        assert result["type"] == "commit"
        assert result["target"] == sha

    def test_branch_at_commit(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main@abcdef1")
        assert result["type"] == "commit"
        assert result["base"] == "main"
        assert result["target"] == "abcdef1"


class TestRequireInit:
    """Test the require_init decorator."""

    def test_require_init_no_dir(self, tmp_path):
        fake_dir = tmp_path / "nonexistent"
        runner = CliRunner()
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", fake_dir / "repo"),
        ):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 1
            assert "init" in result.output.lower()

    def test_require_init_dir_exists_no_git(self, tmp_path):
        fake_dir = tmp_path / "dotman"
        fake_dir.mkdir()
        repo_dir = fake_dir / "repo"
        repo_dir.mkdir()
        # No .git directory
        runner = CliRunner()
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", repo_dir),
        ):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code != 0


class TestCompletionCaching:
    """Test completion cache operations."""

    def test_clear_all_caches(self):
        from dot_man.cli.common import _clear_all_caches

        _clear_all_caches()
        # Should not raise

    def test_clear_completion_cache(self):
        from dot_man.cli.common import _clear_completion_cache

        _clear_completion_cache()
        # Should not raise


class TestHandleException:
    """Test centralized exception handler."""

    def test_handle_dotman_error(self):
        from dot_man.cli.common import handle_exception
        from dot_man.exceptions import DotManError

        # DotManError calls ui.error which calls SystemExit
        with pytest.raises(SystemExit):
            handle_exception(DotManError("test error", exit_code=2))

    def test_handle_keyboard_interrupt(self, capsys):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit) as exc_info:
            handle_exception(KeyboardInterrupt())
        assert exc_info.value.code == 130

    def test_handle_generic_exception(self):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit):
            handle_exception(RuntimeError("something broke"))


class TestDotManGroup:
    """Test custom Click group with command suggestions."""

    def test_unknown_command_suggestion(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["statsu"])
        assert result.exit_code != 0

    def test_unknown_command_no_match(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["zzzznonexistent"])
        assert result.exit_code != 0


class TestErrorSuccessWarn:
    """Test error/success/warn helpers."""

    def test_success_helper(self):
        from dot_man.cli.common import success

        success("test message")

    def test_warn_helper(self):
        from dot_man.cli.common import warn

        warn("test warning")
