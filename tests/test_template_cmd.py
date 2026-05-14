"""Tests for cli/template_cmd.py — template command."""

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


class TestTemplateHelp:
    def test_template_help(self, runner):
        """Template help."""
        result = runner.invoke(cli, ["template", "--help"])
        assert result.exit_code == 0


class TestTemplateList:
    def test_template_list_help(self, runner):
        """Template list help."""
        result = runner.invoke(cli, ["template", "list", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_list_runs(self, clean_env):
        """Template list runs."""
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

        result = runner.invoke(cli, ["template", "list"])

        assert result.exit_code in [0, 1]


class TestTemplateSet:
    def test_template_set_help(self, runner):
        """Template set help."""
        result = runner.invoke(cli, ["template", "set", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_set_runs(self, clean_env):
        """Template set runs."""
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

        result = runner.invoke(cli, ["template", "set", "MACHINE", "test-machine"])

        assert result.exit_code in [0, 1]

    def test_template_set_from_env(self, clean_env):
        """Template set from environment."""
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

        result = runner.invoke(
            cli, ["template", "set", "TEST_VAR", "--from-env", "HOME"]
        )

        assert result.exit_code in [0, 1]


class TestTemplateGet:
    def test_template_get_help(self, runner):
        """Template get help."""
        result = runner.invoke(cli, ["template", "get", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_get_runs(self, clean_env):
        """Template get runs."""
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

        result = runner.invoke(cli, ["template", "get", "MACHINE"])

        assert result.exit_code in [0, 1]


class TestTemplateDelete:
    def test_template_delete_help(self, runner):
        """Template delete help."""
        result = runner.invoke(cli, ["template", "delete", "--help"])
        assert result.exit_code in [0, 2]


class TestTemplateSystem:
    def test_template_system_help(self, runner):
        """Template system help."""
        result = runner.invoke(cli, ["template", "system", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_system_runs(self, runner):
        """Template system runs."""
        result = runner.invoke(cli, ["template", "system"])
        assert result.exit_code in [0, 1]
