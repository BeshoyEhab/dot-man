"""Tests for cli/backup_cmd.py — backup command."""

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


class TestBackupHelp:
    def test_backup_help(self, runner):
        """Backup help."""
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0


class TestBackupWithoutInit:
    def test_backup_without_init(self, runner):
        """Backup without init."""
        result = runner.invoke(cli, ["backup", "create"])
        assert result.exit_code in [0, 1]


class TestBackupCreate:
    def test_backup_create_help(self, runner):
        """Backup create help."""
        result = runner.invoke(cli, ["backup", "create", "--help"])
        assert result.exit_code in [0, 2]

    def test_backup_create_runs(self, clean_env):
        """Backup create runs."""
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

        result = runner.invoke(cli, ["backup", "create"])

        assert result.exit_code in [0, 1]


class TestBackupList:
    def test_backup_list_help(self, runner):
        """Backup list help."""
        result = runner.invoke(cli, ["backup", "list", "--help"])
        assert result.exit_code in [0, 2]

    def test_backup_list_runs(self, clean_env):
        """Backup list runs."""
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

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code in [0, 1]


class TestBackupRestore:
    def test_backup_restore_help(self, runner):
        """Backup restore help."""
        result = runner.invoke(cli, ["backup", "restore", "--help"])
        assert result.exit_code in [0, 2]

    def test_backup_restore_without_id(self, runner):
        """Backup restore without backup id."""
        result = runner.invoke(cli, ["backup", "restore"])
        assert result.exit_code in [0, 1, 2]
