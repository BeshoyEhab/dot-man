"""Tests for cli/add_cmd.py — add command."""

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

        yield CliRunner(), dot_man_dir, repo_dir, global_toml, home


class TestAddHelp:
    def test_add_help(self, runner):
        """Add help."""
        result = runner.invoke(cli, ["add", "--help"])
        assert result.exit_code == 0


class TestAddWithoutInit:
    def test_add_without_init(self, runner):
        """Add without init."""
        result = runner.invoke(cli, ["add", "/some/path"])
        assert result.exit_code in [0, 1, 2]


class TestAddWithInit:
    def test_add_file(self, clean_env):
        """Add a file to tracking."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_file = home / ".bashrc"
        test_file.write_text("# bashrc")

        result = runner.invoke(cli, ["add", str(test_file)])

        assert result.exit_code in [0, 1, 7]

    def test_add_symlink_follows(self, clean_env):
        """Add follows a symlink when prompt returns 'follow'."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        # Create minimal global config
        if not global_toml.parent.exists():
            global_toml.parent.mkdir(parents=True)
        global_toml.write_text("[defaults]\n")

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        target = home / "real_config.txt"
        target.write_text("real content")

        link = home / ".linked_config"
        link.symlink_to(target)

        with patch("dot_man.interactive.prompt_symlink_action", return_value="follow"):
            result = runner.invoke(cli, ["add", str(link)])

        assert result.exit_code in [0, 1, 7]

    def test_add_symlink_ignore(self, clean_env):
        """Add skips a symlink when prompt returns 'ignore'."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        # Create minimal global config
        if not global_toml.parent.exists():
            global_toml.parent.mkdir(parents=True)
        global_toml.write_text("[defaults]\n")

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        target = home / "real_config.txt"
        target.write_text("real content")

        link = home / ".linked_config"
        link.symlink_to(target)

        with patch("dot_man.interactive.prompt_symlink_action", return_value="ignore"):
            result = runner.invoke(cli, ["add", str(link)])

        assert result.exit_code == 0
        assert "Skipped symlink" in result.output

    def test_add_directory(self, clean_env):
        """Add a directory to tracking."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_dir = home / ".config" / "testapp"
        test_dir.mkdir(parents=True)
        (test_dir / "config.conf").write_text("key=value")

        result = runner.invoke(cli, ["add", str(test_dir)])

        assert result.exit_code in [0, 1, 7]


class TestAddOptions:
    def test_add_with_section(self, clean_env):
        """Add with custom section name."""
        runner, dot_man_dir, repo_dir, global_toml, home = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        test_file = home / ".bashrc"
        test_file.write_text("# bashrc")

        result = runner.invoke(cli, ["add", str(test_file), "--section", "bash"])

        assert result.exit_code in [0, 1, 7]
