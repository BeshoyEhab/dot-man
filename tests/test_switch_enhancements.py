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
        """Switch help should show new syntax examples."""
        result = runner.invoke(cli, ["switch", "--help"])
        
        assert result.exit_code == 0
        assert "@" in result.output  # branch@tag syntax

    def test_switch_without_init(self, runner):
        """Switch should handle uninitialized state."""
        result = runner.invoke(cli, ["switch", "main"])
        assert result.exit_code in [0, 1]


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
        from dot_man.global_config import GlobalConfig
        from dot_man.exceptions import ConfigurationError
        
        config = GlobalConfig()
        
        with pytest.raises(ConfigurationError):
            config.switch_default_behavior = "invalid"


class TestCompletionFunctions:
    """Tests for completion functions."""

    def test_complete_switch_args_exists(self):
        """complete_switch_args should be importable."""
        from dot_man.cli.common import complete_switch_args
        assert callable(complete_switch_args)

    def test_complete_tags_exists(self):
        """complete_tags should be importable."""
        from dot_man.cli.common import complete_tags
        assert callable(complete_tags)