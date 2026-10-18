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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
        (missing / ".git").mkdir(parents=True)

        with patch("dot_man.constants.REPO_DIR", missing):
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
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
            patch("dot_man.constants.DOT_MAN_DIR", fake_dir),
            patch("dot_man.constants.REPO_DIR", fake_dir / "repo"),
        ):
            result = runner.invoke(cli, ["edit"])
            assert result.exit_code == 1


class TestEditInteractiveMenu:
    """The interactive menu loop: sections, interrupt, raw fallback."""

    def test_build_menu_lists_real_sections(self, integration_runner, tmp_path):
        """Configured sections appear as selectable menu entries."""
        import questionary

        from dot_man.cli.edit_cmd import _edit_build_menu
        from dot_man.operations import get_operations

        rc = tmp_path / "home" / ".menurc"
        rc.write_text("menu test")
        result = integration_runner.invoke(
            cli, ["add", str(rc), "--section", "menusec"]
        )
        assert result.exit_code == 0, result.output

        choices = _edit_build_menu(get_operations())

        values = [getattr(c, "value", None) for c in choices]
        assert "section:menusec" in values
        assert "global" in values
        assert "quit" in values
        separators = [c.title for c in choices if isinstance(c, questionary.Separator)]
        assert "--- Sections ---" in separators

    def test_keyboard_interrupt_returns_quietly(self, integration_runner):
        """Ctrl-C at the menu exits edit with 0, no traceback."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value.ask.side_effect = KeyboardInterrupt
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Traceback" not in result.output

    def test_menu_error_falls_back_to_raw_editor(self, integration_runner):
        """A blown-up menu warns and opens the raw editor instead."""
        with (
            patch("questionary.select") as mock_select,
            patch("dot_man.utils.open_in_editor", return_value=True),
        ):
            mock_select.return_value.ask.side_effect = RuntimeError("menu boom")
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Interactive menu error: menu boom" in result.output
        assert "Falling back to raw editor..." in result.output
        assert "Edited dot-man.toml" in result.output


class TestEditAddNewFlow:
    """The 'Add New Section' menu action end-to-end."""

    def test_add_new_creates_section(self, integration_runner, tmp_path):
        """Picking add_new prompts, invokes add, and lands the section."""
        from dot_man.constants import DOT_MAN_TOML, REPO_DIR

        rc = tmp_path / "home" / ".newrc"
        rc.write_text("new section file")
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.path") as mock_path,
            patch("questionary.text") as mock_text,
            patch("builtins.input", return_value=""),
        ):
            mock_select.return_value.ask.side_effect = ["add_new", "quit"]
            mock_path.return_value.ask.return_value = str(rc)
            mock_text.return_value.ask.return_value = "newsec"
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Press Enter to continue..." in result.output
        assert "[newsec]" in (REPO_DIR / DOT_MAN_TOML).read_text()

    def test_add_new_missing_path_warns(self, integration_runner, tmp_path):
        """A non-existent path is rejected with a warning, then quit."""
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.path") as mock_path,
        ):
            mock_select.return_value.ask.side_effect = ["add_new", "quit"]
            mock_path.return_value.ask.return_value = str(tmp_path / "ghost.txt")
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Path does not exist:" in result.output

    def test_add_new_path_prompt_cancelled(self, integration_runner):
        """Empty path prompt aborts the flow silently."""
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.path") as mock_path,
        ):
            mock_select.return_value.ask.side_effect = ["add_new", "quit"]
            mock_path.return_value.ask.return_value = None
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Path does not exist:" not in result.output
        assert "Press Enter to continue..." not in result.output

    def test_add_new_name_prompt_cancelled(self, integration_runner, tmp_path):
        """Empty section-name prompt aborts before invoking add."""
        rc = tmp_path / "home" / ".newrc"
        rc.write_text("file")
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.path") as mock_path,
            patch("questionary.text") as mock_text,
        ):
            mock_select.return_value.ask.side_effect = ["add_new", "quit"]
            mock_path.return_value.ask.return_value = str(rc)
            mock_text.return_value.ask.return_value = None
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Press Enter to continue..." not in result.output

    def test_add_new_error_warned_not_crashed(self, integration_runner, tmp_path):
        """A failing add is reported through the flow's warning, not a crash."""
        rc = tmp_path / "home" / ".newrc"
        rc.write_text("file")
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.path") as mock_path,
            patch("questionary.text") as mock_text,
            patch("dot_man.cli.add_cmd.add", side_effect=RuntimeError("add exploded")),
        ):
            mock_select.return_value.ask.side_effect = ["add_new", "quit"]
            mock_path.return_value.ask.return_value = str(rc)
            mock_text.return_value.ask.return_value = "errsec"
            result = integration_runner.invoke(cli, ["edit"])

        assert result.exit_code == 0, result.output
        assert "Error adding section: add exploded" in result.output
