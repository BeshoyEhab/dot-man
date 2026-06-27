"""Tests for cli/status_cmd.py — status command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_ops():
    """Create a mock DotManOperations for status tests."""
    ops = MagicMock()
    ops.current_branch = "main"
    ops.global_config.remote_url = "git@github.com:user/dotfiles.git"

    shell_section = MagicMock()
    shell_section.paths = [MagicMock()]
    shell_section.inherits = []

    config_section = MagicMock()
    config_section.paths = [MagicMock()]
    config_section.inherits = ["base"]

    ops.get_sections.return_value = ["shell", "config"]
    ops.get_section.side_effect = lambda name: {
        "shell": shell_section,
        "config": config_section,
    }[name]

    shell_path = MagicMock()
    shell_path.__str__ = lambda self: "/home/user/.bashrc"
    config_path = MagicMock()
    config_path.__str__ = lambda self: "/home/user/.config/nvim/init.lua"

    ops.get_detailed_status.return_value = [
        {"section": "shell", "local_path": shell_path, "status": "IDENTICAL"},
        {"section": "config", "local_path": config_path, "status": "MODIFIED"},
    ]

    ops.git.is_dirty.return_value = False
    return ops


class TestStatusHappyPath:
    """Test basic status output."""

    def test_returns_zero_exit_code(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_calls_get_detailed_status(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            runner.invoke(cli, ["status"])
        mock_ops.get_detailed_status.assert_called_once()

    def test_calls_get_sections(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            runner.invoke(cli, ["status"])
        mock_ops.get_sections.assert_called()

    def test_shows_inherits_metadata(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusNoSections:
    """Test when no sections are tracked."""

    def test_no_sections_returns_zero(self, runner, mock_ops):
        mock_ops.get_sections.return_value = []
        mock_ops.get_detailed_status.return_value = []
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusVerbose:
    """Test --verbose flag."""

    def test_verbose_returns_zero(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status", "--verbose"])
        assert result.exit_code == 0

    def test_verbose_flag_accepted(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status", "-v"])
        assert result.exit_code == 0


class TestStatusSecrets:
    """Test --secrets flag."""

    def test_secrets_flag_scans_files(self, runner, mock_ops):
        mock_scanner = MagicMock()
        mock_scanner.scan_file.return_value = []
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.status_cmd.get_custom_scanner", return_value=mock_scanner):
                result = runner.invoke(cli, ["status", "--secrets"])
        assert result.exit_code == 0
        mock_scanner.scan_file.assert_called()

    def test_no_secrets_flag_skips_scan(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.status_cmd.get_custom_scanner") as mock_scanner:
                runner.invoke(cli, ["status"])
        mock_scanner.assert_not_called()

    def test_secrets_flag_reports_findings(self, runner, mock_ops):
        mock_match = MagicMock()
        mock_match.pattern_name = "API Key"
        mock_scanner = MagicMock()
        mock_scanner.scan_file.return_value = [mock_match]

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.__str__ = lambda self: "/home/user/.bashrc"

        mock_ops.get_detailed_status.return_value = [
            {"section": "shell", "local_path": mock_path, "status": "MODIFIED"}
        ]

        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.status_cmd.get_custom_scanner", return_value=mock_scanner):
                result = runner.invoke(cli, ["status", "--secrets"])
        assert result.exit_code == 0


class TestStatusTruncation:
    """Test section and path truncation."""

    def test_many_sections_returns_zero(self, runner, mock_ops):
        sections = {}
        for i in range(15):
            s = MagicMock()
            s.paths = [MagicMock()]
            s.inherits = []
            sections[f"section{i}"] = s
        mock_ops.get_sections.return_value = list(sections.keys())
        mock_ops.get_section.side_effect = lambda name: sections[name]

        status_items = [
            {"section": f"section{i}", "local_path": MagicMock(), "status": "IDENTICAL"}
            for i in range(15)
        ]
        mock_ops.get_detailed_status.return_value = status_items

        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_many_paths_returns_zero(self, runner, mock_ops):
        section = MagicMock()
        section.paths = [MagicMock() for _ in range(10)]
        section.inherits = []

        status_items = [
            {"section": "big", "local_path": MagicMock(), "status": "IDENTICAL"}
            for _ in range(10)
        ]
        mock_ops.get_detailed_status.return_value = status_items
        mock_ops.get_sections.return_value = ["big"]
        mock_ops.get_section.side_effect = lambda name: section

        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusDirtyRepo:
    """Test dirty repo warning."""

    def test_dirty_repo_returns_zero(self, runner, mock_ops):
        mock_ops.git.is_dirty.return_value = True
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0

    def test_clean_repo_returns_zero(self, runner, mock_ops):
        mock_ops.git.is_dirty.return_value = False
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusRemoteNotConfigured:
    """Test remote not configured display."""

    def test_no_remote_returns_zero(self, runner, mock_ops):
        mock_ops.global_config.remote_url = None
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusExceptions:
    """Test exception handling."""

    def test_dotman_error(self, runner, mock_ops):
        from dot_man.exceptions import DotManError

        with patch("dot_man.operations.get_operations", side_effect=DotManError("fail")):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0

    def test_keyboard_interrupt(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", side_effect=KeyboardInterrupt()):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0

    def test_generic_exception(self, runner, mock_ops):
        with patch("dot_man.operations.get_operations", side_effect=RuntimeError("boom")):
            result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0
