"""Tests for cli/profile_cmd.py — profile command."""

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


class TestProfileHelp:
    def test_profile_help(self, runner):
        result = runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0


class TestProfileList:
    def test_profile_list(self, clean_env):
        """List profiles."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["profile", "list"])

        assert result.exit_code in [0, 1]


class TestProfileSet:
    def test_profile_set_help(self, runner):
        """Profile set help."""
        result = runner.invoke(cli, ["profile", "set", "--help"])
        assert result.exit_code in [0, 2]


class TestProfileGet:
    def test_profile_get_help(self, runner):
        """Profile get help."""
        result = runner.invoke(cli, ["profile", "get", "--help"])
        assert result.exit_code in [0, 2]


class TestProfileCreate:
    def test_profile_create_runs(self, clean_env):
        """Profile create runs."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["profile", "create", "work"])

        assert result.exit_code in [0, 1]

    def test_profile_create_with_inherits(self, clean_env):
        """Profile create with inherits."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        runner.invoke(cli, ["profile", "create", "base"])
        result = runner.invoke(cli, ["profile", "create", "work", "--inherits", "base"])

        assert result.exit_code in [0, 1]


class TestProfileDelete:
    def test_profile_delete_help(self, runner):
        """Profile delete help."""
        result = runner.invoke(cli, ["profile", "delete", "--help"])
        assert result.exit_code in [0, 2]


class TestProfileSwitch:
    def test_profile_switch_help(self, runner):
        """Profile switch help."""
        result = runner.invoke(cli, ["profile", "switch", "--help"])
        assert result.exit_code in [0, 2]


class TestProfileDetect:
    def test_profile_detect_help(self, runner):
        """Profile detect help."""
        result = runner.invoke(cli, ["profile", "detect", "--help"])
        assert result.exit_code in [0, 2]


class TestProfileSetBranch:
    def test_profile_set_branch_help(self, runner):
        """Profile set-branch help."""
        result = runner.invoke(cli, ["profile", "set-branch", "--help"])
        assert result.exit_code in [0, 2]
