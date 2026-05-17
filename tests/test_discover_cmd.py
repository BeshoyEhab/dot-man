"""Tests for 'dot-man discover' command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestDiscoverHelp:
    """Test discover command help."""

    def test_discover_help(self):
        """Test that discover help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert result.exit_code == 0
        assert "discover" in result.output.lower()


class TestDiscoverOptions:
    """Test discover command options."""

    def test_discover_extended_option(self):
        """Test discover extended option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert "--include-extended" in result.output
        assert "--no-extended" in result.output

    def test_discover_add_option(self):
        """Test discover add option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert "--add" in result.output
