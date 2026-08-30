"""Extended tests for cli/revert_cmd.py — revert files from repository."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_ops():
    ops = MagicMock()
    ops.current_branch = "main"
    return ops


class TestRevertBasic:
    """Test basic revert functionality."""

    def test_revert_with_force(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = True
            result = runner.invoke(cli, ["revert", str(target), "--force"])
        assert result.exit_code == 0
        assert "Reverted" in result.output

    def test_revert_confirmed(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = True
            with patch("dot_man.cli.revert_cmd.ui") as mock_ui:
                mock_ui.confirm.return_value = True
                result = runner.invoke(cli, ["revert", str(target)])
        assert result.exit_code == 0

    def test_revert_aborted(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.revert_cmd.ui") as mock_ui:
                mock_ui.confirm.return_value = False
                result = runner.invoke(cli, ["revert", str(target)])
        assert result.exit_code == 0
        mock_ops.revert_file.assert_not_called()

    def test_revert_file_returns_false(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = False
            result = runner.invoke(cli, ["revert", str(target), "--force"])
        assert result.exit_code == 0
        # Should not crash when revert_file returns False


class TestRevertFromCommit:
    """Test revert from specific commit."""

    def test_revert_from_commit_not_found(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.repo.git.show.side_effect = Exception("Path not found")
            result = runner.invoke(
                cli, ["revert", str(target), "-c", "deadbeef", "--force"]
            )
        assert result.exit_code == 1

    def test_revert_from_commit_path_error(self, runner, mock_ops, tmp_path):
        """Test that commit revert handles relative_to errors."""
        target = tmp_path / "sub" / ".bashrc"
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.repo.git.show.side_effect = ValueError("Path not relative")
            result = runner.invoke(
                cli, ["revert", str(target), "-c", "abc123", "--force"]
            )
        assert result.exit_code == 1


class TestRevertExceptions:
    """Test exception handling."""

    def test_dotman_error(self, runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=Exception("no repo"),
        ):
            result = runner.invoke(cli, ["revert", "/tmp/test", "--force"])
        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_keyboard_interrupt(self, runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=KeyboardInterrupt(),
        ):
            result = runner.invoke(cli, ["revert", "/tmp/test", "--force"])
        assert result.exit_code != 0
