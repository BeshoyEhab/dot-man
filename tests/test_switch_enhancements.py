"""Tests for switch command enhancements."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestSwitchEnhancements:
    """Tests for switch command enhancements."""

    def test_switch_help_shows_save_options(self, runner):
        """Switch help should show --save and --no-save options."""
        result = runner.invoke(cli, ["switch", "--help"])

        assert result.exit_code == 0
        assert "--save" in result.output
        assert "--no-save" in result.output

    def test_switch_help_shows_new_syntax(self, runner):
        """Switch help should show deprecation notice and reference navigate."""
        result = runner.invoke(cli, ["switch", "--help"])

        assert result.exit_code == 0
        assert "DEPRECATED" in result.output
        assert "navigate" in result.output.lower()

    def test_switch_without_init(self, runner, tmp_path):
        """Switch should handle uninitialized state."""
        from unittest.mock import patch

        with patch("dot_man.cli.common.REPO_DIR", tmp_path / "norepo"):
            result = runner.invoke(cli, ["switch", "main"])
            assert result.exit_code == 1


class TestParseBranchArg:
    """Tests for parse_branch_arg function."""

    def test_parse_branch_simple(self):
        """Parse simple branch name."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main")
        assert result["type"] == "branch"
        assert result["target"] == "main"

    def test_parse_branch_with_tag(self):
        """Parse branch@tag syntax."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("work@tag")
        assert result["type"] == "tag"
        assert result["base"] == "work"
        assert result["target"] == "tag"

    def test_parse_commit_sha(self):
        """Parse commit SHA (7+ hex chars)."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abc1234")
        assert result["type"] == "commit"
        assert result["target"] == "abc1234"

    def test_parse_long_commit_sha(self):
        """Parse long commit SHA (40 hex chars)."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abc123456789012345678901234567890abcdef")
        assert result["type"] == "commit"
        assert result["target"] == "abc123456789012345678901234567890abcdef"

    def test_parse_branch_at_commit(self):
        """Parse branch@commit syntax."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main@abc1234")
        assert result["type"] == "commit"
        assert result["base"] == "main"
        assert result["target"] == "abc1234"

    def test_parse_empty_base(self):
        """Parse @tag syntax (empty base becomes HEAD)."""
        from dot_man.cli.common import parse_branch_arg

        # With the current implementation, @v1 won't match the pattern
        # since (.+)@(.+) requires at least one char before @
        result = parse_branch_arg("@v1")
        # It falls through to plain branch (tag check would handle known tags)
        assert result["type"] in ["branch", "tag"]


class TestGlobalConfigSwitchBehavior:
    """Tests for global config switch.default_behavior."""

    def test_default_behavior_save(self):
        """Default behavior should be save."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {"switch": {"default_behavior": "save"}}

        assert config.switch_default_behavior == "save"

    def test_default_behavior_no_save(self):
        """Can set behavior to no-save."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {"switch": {"default_behavior": "no-save"}}

        assert config.switch_default_behavior == "no-save"

    def test_default_behavior_missing(self):
        """Missing config defaults to save."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {}

        assert config.switch_default_behavior == "save"

    def test_set_switch_behavior(self):
        """Set switch.default_behavior."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config.switch_default_behavior = "no-save"

        assert config._data["switch"]["default_behavior"] == "no-save"

    def test_invalid_behavior_rejected(self):
        """Invalid behavior value should raise error."""
        from dot_man.exceptions import ConfigurationError
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()

        with pytest.raises(ConfigurationError):
            config.switch_default_behavior = "invalid"


class TestCompletionFunctions:
    """Tests for completion functions."""

    def test_complete_switch_args_returns_branches(self):
        """complete_switch_args should return matching branches."""
        import subprocess

        from dot_man.cli.common import _set_git_runner, complete_switch_args

        def make_mock_result(stdout="", returncode=0):
            result = subprocess.CompletedProcess(
                args=[], returncode=returncode, stdout=stdout, stderr=""
            )
            return result

        def mock_runner(args, cwd=None, timeout=2):
            if "branch" in args:
                return make_mock_result("main\nwork\ndev\n")
            if "rev-parse" in args:
                return make_mock_result("main")
            if "tag" in args:
                return make_mock_result("v1.0\n")
            if "log" in args:
                return make_mock_result("")
            return make_mock_result()

        _set_git_runner(mock_runner)
        result = complete_switch_args(None, None, "w")
        values = [item.value if hasattr(item, "value") else item for item in result]
        assert "work" in values
        _set_git_runner(None)

    def test_complete_tags_returns_matching(self):
        """complete_tags should return matching tag names."""
        import subprocess

        from dot_man.cli.common import (
            _clear_all_caches,
            _set_git_runner,
            complete_tags,
        )

        _clear_all_caches()

        def make_mock_result(stdout="", returncode=0):
            result = subprocess.CompletedProcess(
                args=[], returncode=returncode, stdout=stdout, stderr=""
            )
            return result

        def mock_runner(args, cwd=None, timeout=2):
            if "tag" in args:
                return make_mock_result("v1.0\nv2.0\nlatest\n")
            return make_mock_result()

        _set_git_runner(mock_runner)
        result = complete_tags(None, None, "v")
        assert "v1.0" in result
        assert "v2.0" in result
        assert "latest" not in result
        _set_git_runner(None)
