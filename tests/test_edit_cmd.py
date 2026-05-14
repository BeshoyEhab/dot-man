"""Tests for cli/edit_cmd.py — edit command."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestEditHelp:
    def test_edit_help(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "editor" in result.output.lower()

    def test_edit_help_raw_mode(self, runner):
        result = runner.invoke(cli, ["edit", "--raw", "--help"])
        assert result.exit_code == 0

    def test_edit_global_help(self, runner):
        result = runner.invoke(cli, ["edit", "--global", "--help"])
        assert result.exit_code == 0
        assert "--global" in result.output

    def test_edit_with_editor_help(self, runner):
        result = runner.invoke(cli, ["edit", "--editor", "vim", "--help"])
        assert result.exit_code in [0, 2]
