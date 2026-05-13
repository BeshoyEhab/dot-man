"""Tests for the show command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.constants import REPO_DIR


@pytest.fixture
def runner():
    """Return a Click CLI runner."""
    return CliRunner()


def test_show_help(runner):
    """Test show help command."""
    result = runner.invoke(cli, ["show", "--help"])
    assert result.exit_code == 0
    assert "View full diff for a specific commit" in result.output


@patch("dot_man.cli.show_cmd.subprocess.run")
def test_show_commit(mock_run, integration_runner):
    """Test showing a commit."""
    runner = integration_runner

    result = runner.invoke(cli, ["show", "abc1234"])
    assert result.exit_code == 0

    mock_run.assert_called_once_with(
        ["git", "show", "--color=always", "abc1234"], cwd=REPO_DIR
    )


def test_show_without_init(runner, tmp_path):
    """Test show without initialization."""
    with patch("dot_man.cli.common.REPO_DIR", tmp_path / "norepo"):
        result = runner.invoke(cli, ["show", "HEAD"])
        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()
