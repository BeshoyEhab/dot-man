"""Tests for 'dot-man encrypt' command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestEncryptHelp:
    """Test encrypt command help."""

    def test_encrypt_help(self):
        """Test that encrypt help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower()
        assert "decrypt" in result.output.lower()
        assert "status" in result.output.lower()


class TestEncryptAction:
    """Test encrypt action validation."""

    def test_invalid_action(self):
        """Test that invalid action is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "invalid"])
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()


class TestEncryptOptions:
    """Test encrypt command options."""

    def test_encrypt_method_option(self):
        """Test encrypt method option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "--method" in result.output or "-m" in result.output

    def test_encrypt_recipient_option(self):
        """Test encrypt recipient option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "--recipient" in result.output or "-r" in result.output
