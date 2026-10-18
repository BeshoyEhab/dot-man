"""Tests for the deprecated show command (folded into `log --commit`)."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man import constants
from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    """Return a Click CLI runner."""
    return CliRunner()


def test_show_help_marks_deprecated(runner):
    """`show --help` points at the replacement."""
    result = runner.invoke(cli, ["show", "--help"])
    assert result.exit_code == 0
    assert "DEPRECATED" in result.output
    assert "log --commit" in result.output


@patch("dot_man.cli.log_cmd.subprocess.run")
def test_show_commit(mock_run, integration_runner):
    """A deprecated `show` still renders the commit and warns."""
    result = integration_runner.invoke(cli, ["show", "abc1234"])
    assert result.exit_code == 0

    mock_run.assert_called_once_with(
        ["git", "show", "--color=always", "abc1234"], cwd=constants.get_repo_dir()
    )
    assert "deprecated" in result.output.lower()
    assert "log --commit" in result.output


def test_show_without_init(runner, tmp_path):
    """Test show without initialization."""
    with patch("dot_man.constants.REPO_DIR", tmp_path / "norepo"):
        result = runner.invoke(cli, ["show", "HEAD"])
        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()


@patch("dot_man.cli.log_cmd.subprocess.run", side_effect=OSError("spawn fail"))
def test_show_subprocess_failure_reports_error(mock_run, integration_runner):
    """A failing git spawn exits with the error message."""
    result = integration_runner.invoke(cli, ["show", "abc1234"])

    assert result.exit_code == 1
    assert "spawn fail" in result.output


class TestLogCommit:
    """`log --commit` is the canonical single-commit view (replaces `show`)."""

    @patch("dot_man.cli.log_cmd.subprocess.run")
    def test_log_commit_shows_commit(self, mock_run, integration_runner):
        result = integration_runner.invoke(cli, ["log", "--commit", "abc1234"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["git", "show", "--color=always", "abc1234"],
            cwd=constants.get_repo_dir(),
        )

    @patch("dot_man.cli.log_cmd.subprocess.run")
    def test_log_commit_short_flag(self, mock_run, integration_runner):
        result = integration_runner.invoke(cli, ["log", "-C", "HEAD"])

        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["git", "show", "--color=always", "HEAD"], cwd=constants.get_repo_dir()
        )
