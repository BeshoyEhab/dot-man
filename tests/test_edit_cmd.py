"""Tests for cli/edit_cmd.py — edit command."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestEditHelp:
    def test_edit_help(self):
        """Test edit help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "edit" in result.output.lower()
        assert "editor" in result.output.lower()


class TestEditWithoutInit:
    def test_edit_requires_init(self):
        """Test edit requires initialization."""
        runner = CliRunner()
        result = runner.invoke(cli, ["edit"])
        assert result.exit_code == 1


class TestEditOptions:
    def test_edit_editor_option(self):
        """Test --editor option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", "--help"])
        assert "--editor" in result.output

    def test_edit_global_option(self):
        """Test --global option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", "--help"])
        assert "--global" in result.output

    def test_edit_raw_option(self):
        """Test --raw option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["edit", "--help"])
        assert "--raw" in result.output