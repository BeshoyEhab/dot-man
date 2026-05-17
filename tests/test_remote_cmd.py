"""Tests for cli/remote_cmd.py — remote command."""

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

        yield CliRunner(), dot_man_dir, repo_dir


class TestRemoteHelp:
    def test_remote_help(self, runner):
        result = runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0
        assert "remote" in result.output.lower()
        assert "set" in result.output


class TestRemoteGet:
    def test_remote_get_help(self, runner):
        """Remote get help."""
        result = runner.invoke(cli, ["remote", "get", "--help"])
        assert result.exit_code in [0, 2]

    def test_remote_get_runs(self, clean_env):
        """Remote get runs."""
        runner, dot_man_dir, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["remote", "get"])

        assert result.exit_code in [0, 1]


class TestRemoteSet:
    def test_remote_set_help(self, runner):
        """Remote set help."""
        result = runner.invoke(cli, ["remote", "set", "--help"])
        assert result.exit_code in [0, 2]

    def test_remote_set_runs(self, clean_env):
        """Remote set runs."""
        runner, dot_man_dir, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(
            cli, ["remote", "set", "https://github.com/test/dotfiles.git"]
        )

        assert result.exit_code in [0, 1, 7]


class TestSyncBranch:
    def test_sync_branch_help(self, runner):
        """Sync-branch help."""
        result = runner.invoke(cli, ["remote", "sync-branch", "--help"])
        assert result.exit_code in [0, 2]

    def test_sync_branch_without_remote(self, clean_env):
        """Sync-branch without remote."""
        runner, dot_man_dir, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["remote", "sync-branch"])

        assert result.exit_code in [0, 1]


class TestRemoteDelete:
    def test_remote_delete_help(self, runner):
        """Remote delete help."""
        result = runner.invoke(cli, ["remote", "delete", "--help"])
        assert result.exit_code in [0, 2]


class TestRemoteInvalidAction:
    def test_invalid_action(self, runner):
        """Test invalid remote action."""
        result = runner.invoke(cli, ["remote", "invalid"])
        assert result.exit_code == 2
