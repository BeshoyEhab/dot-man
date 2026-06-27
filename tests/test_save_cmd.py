"""Tests for cli/save_cmd.py — save command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_ops():
    """Create a mock DotManOperations with sensible defaults."""
    ops = MagicMock()
    ops.current_branch = "main"
    ops.get_sections.return_value = ["shell", "config"]
    ops.git.commit.return_value = "abc1234"

    shell_section = MagicMock()
    shell_path = MagicMock()
    shell_repo_path = MagicMock()
    shell_path.exists.return_value = True
    shell_repo_path.exists.return_value = True
    shell_section.paths = [shell_path]
    shell_section.get_repo_path.return_value = shell_repo_path

    config_section = MagicMock()
    config_path = MagicMock()
    config_repo_path = MagicMock()
    config_path.exists.return_value = True
    config_repo_path.exists.return_value = True
    config_section.paths = [config_path]
    config_section.get_repo_path.return_value = config_repo_path

    ops.get_section.side_effect = lambda name: {
        "shell": shell_section,
        "config": config_section,
    }[name]

    ops.save_all.return_value = {
        "saved": 5,
        "secrets": [],
        "errors": [],
        "symlinks": [],
    }
    return ops


class TestSaveDryRun:
    """Test --dry-run flag."""

    def test_dry_run_no_changes(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=True):
                result = runner.invoke(cli, ["save", "--dry-run"])
        assert result.exit_code == 0
        mock_ops.save_all.assert_not_called()

    def test_dry_run_with_changes(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--dry-run"])
        assert result.exit_code == 0
        mock_ops.save_all.assert_not_called()

    def test_dry_run_never_saves(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                runner.invoke(cli, ["save", "--dry-run"])
        mock_ops.save_all.assert_not_called()


class TestSaveForce:
    """Test --force flag."""

    def test_force_skips_confirmation(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force"])
        assert result.exit_code == 0
        mock_ops.save_all.assert_called_once()

    def test_no_force_prompts_confirmation(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                with patch("dot_man.cli.save_cmd.ui") as mock_ui:
                    mock_ui.confirm.return_value = False
                    runner.invoke(cli, ["save"])
        mock_ops.save_all.assert_not_called()

    def test_confirm_yes_saves(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                with patch("dot_man.cli.save_cmd.ui") as mock_ui:
                    mock_ui.confirm.return_value = True
                    runner.invoke(cli, ["save"])
        mock_ops.save_all.assert_called_once()


class TestSaveSectionFilter:
    """Test --section filter."""

    def test_valid_section_filter(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force", "--section", "shell"])
        assert result.exit_code == 0

    def test_invalid_section_filter(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["save", "--section", "nonexistent"])
        assert result.exit_code == 1


class TestSaveCommit:
    """Test --commit flag."""

    def test_commit_with_message(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(
                    cli, ["save", "--force", "--commit", "-m", "my commit"]
                )
        assert result.exit_code == 0
        mock_ops.git.commit.assert_called_once_with("my commit")

    def test_commit_without_message(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force", "--commit"])
        assert result.exit_code == 0
        mock_ops.git.commit.assert_called_once()
        commit_msg = mock_ops.git.commit.call_args[0][0]
        assert "[dot-man] Save" in commit_msg
        # "config" is filtered out as a non-relevant section
        assert "sections: shell" in commit_msg

    def test_commit_auto_message_truncates_many_sections(self, runner, mock_ops):
        mock_ops.get_sections.return_value = ["a", "b", "c", "d", "e"]
        mock_sections = {}
        for name in ["a", "b", "c", "d", "e"]:
            section_mock = MagicMock()
            section_mock.paths = [MagicMock()]
            section_mock.get_repo_path.return_value = MagicMock()
            mock_sections[name] = section_mock
        mock_ops.get_section.side_effect = lambda name: mock_sections[name]

        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force", "--commit"])
        assert result.exit_code == 0
        mock_ops.git.commit.assert_called_once()
        commit_msg = mock_ops.git.commit.call_args[0][0]
        assert "+2 more" in commit_msg

    def test_commit_no_saved_files(self, runner, mock_ops):
        mock_ops.save_all.return_value = {
            "saved": 0,
            "secrets": [],
            "errors": [],
            "symlinks": [],
        }
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                runner.invoke(cli, ["save", "--force", "--commit"])
        mock_ops.git.commit.assert_not_called()

    def test_commit_returns_none_sha(self, runner, mock_ops):
        mock_ops.git.commit.return_value = None
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force", "--commit"])
        assert result.exit_code == 0

    def test_commit_defaults_only_message(self, runner, mock_ops):
        mock_ops.get_sections.return_value = ["defaults", "config"]
        mock_sections = {}
        for name in ["defaults", "config"]:
            section_mock = MagicMock()
            section_mock.paths = [MagicMock()]
            section_mock.get_repo_path.return_value = MagicMock()
            mock_sections[name] = section_mock
        mock_ops.get_section.side_effect = lambda name: mock_sections[name]

        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force", "--commit"])
        assert result.exit_code == 0
        mock_ops.git.commit.assert_called_once()
        commit_msg = mock_ops.git.commit.call_args[0][0]
        assert "sections:" not in commit_msg


class TestSaveSecretsAndErrors:
    """Test secrets and error reporting."""

    def test_secrets_warning(self, runner, mock_ops):
        mock_ops.save_all.return_value = {
            "saved": 3,
            "secrets": [{"type": "api_key"}],
            "errors": [],
            "symlinks": [],
        }
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force"])
        assert result.exit_code == 0

    def test_errors_reported(self, runner, mock_ops):
        mock_ops.save_all.return_value = {
            "saved": 2,
            "secrets": [],
            "errors": ["Permission denied on /foo"],
            "symlinks": [],
        }
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                with patch("dot_man.ui.error") as mock_error:
                    runner.invoke(cli, ["save", "--force"])
        mock_error.assert_called()

    def test_symlinks_warned(self, runner, mock_ops):
        mock_ops.save_all.return_value = {
            "saved": 1,
            "secrets": [],
            "errors": [],
            "symlinks": ["/home/user/.bashrc"],
        }
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.save_cmd.compare_files", return_value=False):
                result = runner.invoke(cli, ["save", "--force"])
        assert result.exit_code == 0


class TestSaveExceptions:
    """Test exception handling."""

    def test_dotman_error(self, runner, mock_ops):
        from dot_man.exceptions import DotManError

        with patch("dot_man.operations.get_operations", side_effect=DotManError("test error")):
            result = runner.invoke(cli, ["save"])
        assert result.exit_code != 0

    def test_keyboard_interrupt(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", side_effect=KeyboardInterrupt()):
            result = runner.invoke(cli, ["save"])
        assert result.exit_code != 0

    def test_generic_exception(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", side_effect=RuntimeError("boom")):
            result = runner.invoke(cli, ["save"])
        assert result.exit_code != 0


class TestWarnSymlinks:
    """Test _warn_symlinks helper."""

    def test_warn_symlinks_with_symlinks(self):
        from dot_man.cli.save_cmd import _warn_symlinks

        with patch("dot_man.cli.save_cmd.ui") as mock_ui:
            _warn_symlinks({"symlinks": ["/path/to/link"]})
            assert mock_ui.console.print.call_count == 2

    def test_warn_symlinks_empty(self):
        from dot_man.cli.save_cmd import _warn_symlinks

        with patch("dot_man.cli.save_cmd.ui") as mock_ui:
            _warn_symlinks({"symlinks": []})
            mock_ui.console.print.assert_not_called()

    def test_warn_symlinks_no_key(self):
        from dot_man.cli.save_cmd import _warn_symlinks

        with patch("dot_man.cli.save_cmd.ui") as mock_ui:
            _warn_symlinks({})
            mock_ui.console.print.assert_not_called()
