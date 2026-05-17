"""Tests for 'dot-man export' command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestExportHelp:
    """Test export command help."""

    def test_export_help(self):
        """Test that export help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "tar" in result.output
        assert "zip" in result.output
        assert "json" in result.output


class TestExportFormat:
    """Test export format validation."""

    def test_invalid_format(self):
        """Test that invalid format is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "invalid", "output"])
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()


class TestExportOptions:
    """Test export command options."""

    def test_export_with_branch_option(self):
        """Test export with branch option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert "--branch" in result.output or "-b" in result.output
