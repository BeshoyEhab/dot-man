"""Tests for 'dot-man import' command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestImportHelp:
    """Test import command help."""

    def test_import_help(self):
        """Test that import help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "--help"])
        assert result.exit_code == 0
        assert "chezmoi" in result.output
        assert "yadm" in result.output
        assert "stow" in result.output


class TestImportWithoutInit:
    """Test import command without initialization."""

    def test_import_requires_init(self):
        """Test that import requires initialization."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "chezmoi"])
        assert result.exit_code == 1


class TestImportSources:
    """Test import source validation."""

    def test_invalid_source(self):
        """Test that invalid source is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "invalid"])
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()
