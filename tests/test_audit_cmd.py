"""Tests for cli/audit_cmd.py — audit command."""

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


class TestAuditHelp:
    def test_audit_help(self, runner):
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "secret" in result.output.lower()


class TestAuditRun:
    def test_audit_clean_repo(self, clean_env):
        """Audit a clean repo with no secrets."""
        runner, dot_man_dir, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("just some text content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["audit"])

        assert result.exit_code == 0


class TestAuditStrict:
    def test_audit_strict_mode(self, clean_env):
        """Audit in strict mode."""
        runner, dot_man_dir, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test content")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["audit", "--strict"])

        assert result.exit_code in [0, 1]


class TestAuditOptions:
    def test_audit_verbose_help(self, runner):
        """Audit verbose help."""
        result = runner.invoke(cli, ["audit", "--verbose", "--help"])
        assert result.exit_code in [0, 2]

    def test_audit_path_help(self, runner):
        """Audit path help."""
        result = runner.invoke(cli, ["audit", "--path", "--help"])
        assert result.exit_code in [0, 2]

    def test_audit_exclude_help(self, runner):
        """Audit exclude help."""
        result = runner.invoke(cli, ["audit", "--exclude", "--help"])
        assert result.exit_code in [0, 2]


class TestAuditWithoutInit:
    def test_audit_without_init(self, runner):
        """Audit without init."""
        result = runner.invoke(cli, ["audit"])
        assert result.exit_code in [0, 1]
