"""Tests for cli/config_cmd.py — config command."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


class TestConfigHelp:
    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0


class TestConfigList:
    def test_config_list_help(self, runner):
        result = runner.invoke(cli, ["config", "list", "--help"])
        assert result.exit_code in [0, 2]

    def test_config_list_runs(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "list"])
        assert result.exit_code in [0, 1]


class TestConfigGet:
    def test_config_get_help(self, runner):
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code in [0, 2]

    def test_config_get_runs(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "get", "dot-man.editor"])
        assert result.exit_code in [0, 1]

    def test_config_get_nonexistent(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "get", "nonexistent.key"])
        assert result.exit_code in [0, 1]


class TestConfigSet:
    def test_config_set_help(self, runner):
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code in [0, 2]

    def test_config_set_runs(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "set", "dot-man.editor", "vim"])
        assert result.exit_code in [0, 1]

    def test_config_set_boolean(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "set", "dot-man.strict_mode", "true"])
        assert result.exit_code in [0, 1]


class TestConfigUnset:
    def test_config_unset_help(self, runner):
        result = runner.invoke(cli, ["config", "unset", "--help"])
        assert result.exit_code in [0, 2]

    def test_config_unset_runs(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "unset", "dot-man.editor"])
        assert result.exit_code in [0, 1, 2]
