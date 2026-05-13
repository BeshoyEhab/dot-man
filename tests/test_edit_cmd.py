"""Tests for cli/edit_cmd.py — edit command and _open_raw_editor helper."""

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
def initialized_runner(tmp_path):
    """Runner with a fully-initialized dot-man repo."""
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
        patch("dot_man.cli.init_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.init_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.init_cmd.BACKUPS_DIR", backups_dir),
        patch("dot_man.cli.add_cmd.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.backups.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.switch_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        r = CliRunner()
        result = r.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, f"Init failed:\n{result.output}"

        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        with git.repo.config_writer() as cfg:
            cfg.set_value("user", "name", "Tester")
            cfg.set_value("user", "email", "test@example.com")

        yield r, repo_dir, dot_man_dir, global_toml


class TestEditHelp:
    def test_edit_help_shows_raw_flag(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "--raw" in result.output

    def test_edit_help_shows_global_flag(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "--global" in result.output

    def test_edit_help_shows_editor_option(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "--editor" in result.output


class TestEditRequiresInit:
    def test_edit_without_init_fails(self, runner, tmp_path):
        fake_dot_man = tmp_path / "fake_config" / "dot-man"
        fake_repo = fake_dot_man / "repo"

        patches = [
            patch("dot_man.constants.DOT_MAN_DIR", fake_dot_man),
            patch("dot_man.constants.REPO_DIR", fake_repo),
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dot_man),
            patch("dot_man.cli.common.REPO_DIR", fake_repo),
            patch("dot_man.cli.edit_cmd.REPO_DIR", fake_repo),
        ]

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(cli, ["edit", "--raw"])

        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()


class TestEditRawMode:
    def test_raw_mode_opens_editor_on_toml(self, initialized_runner):
        runner, repo_dir, _, _ = initialized_runner
        toml_path = repo_dir / "dot-man.toml"
        assert toml_path.exists()

        with patch("dot_man.utils.open_in_editor", return_value=True) as mock_open:
            result = runner.invoke(cli, ["edit", "--raw"])

        assert result.exit_code == 0
        mock_open.assert_called_once()
        assert mock_open.call_args[0][0] == toml_path

    def test_raw_mode_global_opens_global_toml(self, initialized_runner):
        runner, _, _, global_toml = initialized_runner
        assert global_toml.exists()

        with patch("dot_man.utils.open_in_editor", return_value=True) as mock_open:
            result = runner.invoke(cli, ["edit", "--raw", "--global"])

        assert result.exit_code == 0
        assert mock_open.call_args[0][0] == global_toml

    def test_raw_mode_uses_custom_editor_flag(self, initialized_runner):
        runner, _, _, _ = initialized_runner

        with patch("dot_man.utils.open_in_editor", return_value=True) as mock_open:
            result = runner.invoke(cli, ["edit", "--raw", "--editor", "emacs"])

        assert result.exit_code == 0
        assert mock_open.call_args[0][1] == "emacs"

    def test_raw_mode_error_when_toml_missing(self, initialized_runner):
        runner, repo_dir, _, _ = initialized_runner
        (repo_dir / "dot-man.toml").unlink()

        result = runner.invoke(cli, ["edit", "--raw"])
        assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_raw_mode_editor_failure_reported(self, initialized_runner):
        runner, _, _, _ = initialized_runner

        with patch("dot_man.utils.open_in_editor", return_value=False):
            result = runner.invoke(cli, ["edit", "--raw"])

        assert result.exit_code != 0 or "error" in result.output.lower()


class TestOpenRawEditorHelper:
    """Unit tests for the _open_raw_editor helper function directly."""

    def test_helper_uses_editor_arg_priority(self, tmp_path):
        from dot_man.cli.edit_cmd import _open_raw_editor

        target = tmp_path / "dot-man.toml"
        target.write_text("[section]\npaths=[]\n")

        with (
            patch("dot_man.utils.open_in_editor", return_value=True) as mock_open,
            patch("dot_man.global_config.GlobalConfig.load"),
            patch(
                "dot_man.global_config.GlobalConfig.editor",
                new_callable=lambda: property(lambda self: "vim"),
            ),
        ):
            _open_raw_editor(target, "dot-man.toml", editor="nano")

        assert mock_open.call_args[0][1] == "nano"

    def test_helper_falls_back_to_get_editor(self, tmp_path):
        from dot_man.cli.edit_cmd import _open_raw_editor

        target = tmp_path / "dot-man.toml"
        target.write_text("[section]\npaths=[]\n")

        with (
            patch("dot_man.utils.open_in_editor", return_value=True) as mock_open,
            patch("dot_man.global_config.GlobalConfig.load"),
            patch(
                "dot_man.global_config.GlobalConfig.editor",
                new_callable=lambda: property(lambda self: None),
            ),
            patch("dot_man.utils.get_editor", return_value="vi"),
        ):
            _open_raw_editor(target, "dot-man.toml", editor=None)

        assert mock_open.call_args[0][1] == "vi"
