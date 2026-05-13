"""Tests for the restore command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    """Return a Click CLI runner."""
    return CliRunner()


def test_restore_help(runner):
    """Test restore help command."""
    result = runner.invoke(cli, ["restore", "--help"])
    assert result.exit_code == 0
    assert "Restore a file from history" in result.output


@patch("dot_man.operations.get_operations")
@patch("dot_man.ui.confirm")
def test_restore_commit(mock_confirm, mock_get_ops, integration_runner, tmp_path):
    """Test restoring a commit."""
    runner = integration_runner

    # Mock ops
    mock_ops = mock_get_ops.return_value
    mock_ops.get_sections.return_value = ["mysection"]

    class MockSection:
        paths = [tmp_path / "test.txt"]

        def get_repo_path(self, p, r):
            return r / "mysection/test.txt"

    mock_ops.get_section.return_value = MockSection()
    mock_ops.git.repo.git.show.return_value = "restored content"

    mock_confirm.return_value = True

    target_file = tmp_path / "test.txt"
    target_file.write_text("old content")

    result = runner.invoke(cli, ["restore", str(target_file), "abc1234"])

    assert result.exit_code == 0, result.output
    assert target_file.read_text() == "restored content"
    assert (
        tmp_path / "home/.config/dot-man/repo/mysection/test.txt"
    ).read_text() == "restored content"


def test_restore_without_init(runner, tmp_path):
    """Test restore without initialization."""
    with patch("dot_man.cli.common.REPO_DIR", tmp_path / "norepo"):
        result = runner.invoke(cli, ["restore", "~/.bashrc", "HEAD"])
        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()
