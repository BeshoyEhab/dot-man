"""Tests for cli/edit_cmd.py — edit command."""

from unittest.mock import ANY, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.edit_cmd import _open_raw_editor
from dot_man.cli.interface import cli


class TestOpenRawEditor:
    """Unit tests for _open_raw_editor helper."""

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_uses_specified_editor(self, mock_gc, mock_open_in_editor, tmp_path):
        """Specified editor argument takes highest priority."""
        target = tmp_path / "test.toml"
        target.write_text("test")
        mock_gc.return_value.editor = "vim_config"

        _open_raw_editor(target, "test config", editor="vim")

        mock_open_in_editor.assert_called_once_with(target, "vim")

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_falls_back_to_config_editor(self, mock_gc, mock_open_in_editor, tmp_path):
        """Uses editor from GlobalConfig when no explicit editor given."""
        target = tmp_path / "test.toml"
        target.write_text("test")
        mock_gc.return_value.editor = "vim_config"

        _open_raw_editor(target, "test config")

        mock_open_in_editor.assert_called_once_with(target, "vim_config")

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="get_editor_result")
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_falls_back_to_get_editor(
        self, mock_gc, mock_get_editor, mock_open_in_editor, tmp_path
    ):
        """Uses get_editor() fallback when no editor arg and no config editor."""
        target = tmp_path / "test.toml"
        target.write_text("test")
        mock_gc.return_value.editor = None  # Config has no editor

        _open_raw_editor(target, "test config")

        mock_open_in_editor.assert_called_once_with(target, "get_editor_result")

    @patch("dot_man.utils.open_in_editor", return_value=False)
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_handles_editor_failure(self, mock_gc, mock_open_in_editor, tmp_path):
        """Error when editor exits with non-zero."""
        target = tmp_path / "test.toml"
        target.write_text("test")

        with pytest.raises(SystemExit):
            _open_raw_editor(target, "test config")

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_editor_priority_order(self, mock_gc, mock_open_in_editor, tmp_path):
        """Specified editor > config editor > get_editor()."""
        target = tmp_path / "test.toml"
        target.write_text("test")
        mock_gc.return_value.editor = "vim_config"

        _open_raw_editor(target, "test config", editor="custom_editor")
        mock_open_in_editor.assert_called_once_with(target, "custom_editor")

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.cli.edit_cmd.GlobalConfig")
    def test_handles_config_load_failure(self, mock_gc, mock_open_in_editor, tmp_path):
        """When GlobalConfig.load() fails, config_editor is None and falls through."""
        target = tmp_path / "test.toml"
        target.write_text("test")
        from dot_man.exceptions import DotManError

        mock_gc.return_value.load.side_effect = DotManError("config error")

        with patch("dot_man.utils.get_editor", return_value="fallback_editor"):
            _open_raw_editor(target, "test config", editor=None)

        mock_open_in_editor.assert_called_once_with(target, "fallback_editor")


class TestEditCommand:
    """Integration tests for edit CLI command."""

    def test_help(self, integration_runner):
        """--help shows usage."""
        result = integration_runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "edit" in result.output.lower()
        assert "editor" in result.output.lower()
        assert "--raw" in result.output
        assert "--global" in result.output

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="nano")
    def test_raw_opens_file(
        self, mock_get_editor, mock_open_in_editor, integration_runner, tmp_path
    ):
        """--raw opens dot-man.toml with default editor."""
        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
        ):
            result = integration_runner.invoke(cli, ["edit", "--raw"])

        assert result.exit_code == 0
        mock_open_in_editor.assert_called_once()
        assert mock_open_in_editor.call_args[0][0] == repo_dir / "dot-man.toml"

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="nano")
    def test_raw_with_custom_editor(
        self, mock_get_editor, mock_open_in_editor, integration_runner, tmp_path
    ):
        """--raw --editor uses specified editor."""
        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
        ):
            result = integration_runner.invoke(
                cli, ["edit", "--raw", "--editor", "vim"]
            )

        assert result.exit_code == 0
        mock_open_in_editor.assert_called_once_with(repo_dir / "dot-man.toml", "vim")

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="nano")
    def test_raw_global(
        self, mock_get_editor, mock_open_in_editor, integration_runner, tmp_path
    ):
        """--raw --global opens global.toml."""
        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
        ):
            result = integration_runner.invoke(cli, ["edit", "--raw", "--global"])

        assert result.exit_code == 0
        mock_open_in_editor.assert_called_once_with(global_toml, ANY)

    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="nano")
    def test_raw_file_not_found(
        self, mock_get_editor, mock_open_in_editor, integration_runner, tmp_path
    ):
        """--raw errors when file doesn't exist."""
        missing = tmp_path / "nonexistent"

        with patch("dot_man.cli.edit_cmd.REPO_DIR", missing):
            result = integration_runner.invoke(cli, ["edit", "--raw"])

        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("dot_man.cli.edit_cmd.questionary.select")
    @patch("dot_man.utils.open_in_editor", return_value=True)
    @patch("dot_man.utils.get_editor", return_value="nano")
    def test_interactive_quit(
        self,
        mock_get_editor,
        mock_open_in_editor,
        mock_select,
        integration_runner,
        tmp_path,
    ):
        """Interactive TUI: quit immediately."""
        mock_select.return_value.ask.return_value = "quit"

        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
        ):
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0

    @patch("dot_man.interactive.run_global_wizard")
    @patch("dot_man.cli.edit_cmd.questionary.select")
    def test_interactive_global_wizard(
        self,
        mock_select,
        mock_wizard,
        integration_runner,
        tmp_path,
    ):
        """Interactive TUI: select global config wizard."""
        mock_select.return_value.ask.side_effect = ["global", "quit"]

        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
            patch("dot_man.utils.open_in_editor", return_value=True),
            patch("dot_man.utils.get_editor", return_value="nano"),
        ):
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0
        mock_wizard.assert_called_once()

    @patch("dot_man.interactive.run_section_wizard")
    @patch("dot_man.cli.edit_cmd.questionary.select")
    def test_interactive_section_wizard(
        self,
        mock_select,
        mock_wizard,
        integration_runner,
        tmp_path,
    ):
        """Interactive TUI: select a section wizard."""
        mock_select.return_value.ask.side_effect = ["section:test", "quit"]

        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
            patch("dot_man.utils.open_in_editor", return_value=True),
            patch("dot_man.utils.get_editor", return_value="nano"),
        ):
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0
        mock_wizard.assert_called_once()

    @patch("dot_man.interactive.run_templates_wizard")
    @patch("dot_man.cli.edit_cmd.questionary.select")
    def test_interactive_templates_wizard(
        self,
        mock_select,
        mock_wizard,
        integration_runner,
        tmp_path,
    ):
        """Interactive TUI: select templates wizard."""
        mock_select.return_value.ask.side_effect = ["templates", "quit"]

        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
            patch("dot_man.utils.open_in_editor", return_value=True),
            patch("dot_man.utils.get_editor", return_value="nano"),
        ):
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0
        mock_wizard.assert_called_once()

    @patch("dot_man.cli.edit_cmd.questionary.select")
    def test_interactive_raw_from_menu(
        self,
        mock_select,
        integration_runner,
        tmp_path,
    ):
        """Interactive TUI: select 'Open Raw File' from menu."""
        mock_select.return_value.ask.return_value = "raw"

        repo_dir = tmp_path / "home" / ".config" / "dot-man" / "repo"
        global_toml = tmp_path / "home" / ".config" / "dot-man" / "global.toml"

        with (
            patch("dot_man.cli.edit_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.edit_cmd.GLOBAL_TOML", global_toml),
            patch("dot_man.utils.open_in_editor", return_value=True),
            patch("dot_man.utils.get_editor", return_value="nano"),
        ):
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0

    def test_requires_init(self, tmp_path):
        """Edit requires initialization."""
        fake_dir = tmp_path / "nonexistent"
        runner = CliRunner()
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", fake_dir / "repo"),
        ):
            result = runner.invoke(cli, ["edit"])
            assert result.exit_code == 1
