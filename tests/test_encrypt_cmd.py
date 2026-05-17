"""Tests for encrypt command."""

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestEncryptHelp:
    """Test encrypt command help."""

    def test_encrypt_help(self):
        """Test encrypt help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower()
        assert "decrypt" in result.output.lower()

    def test_encrypt_encrypt_help(self):
        """Test encrypt encrypt subcommand help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "encrypt", "--help"])
        assert result.exit_code == 0

    def test_encrypt_decrypt_help(self):
        """Test encrypt decrypt subcommand help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "decrypt", "--help"])
        assert result.exit_code == 0

    def test_encrypt_status_help(self):
        """Test encrypt status subcommand help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "status", "--help"])
        assert result.exit_code == 0


class TestEncryptActions:
    """Test encrypt action validation."""

    def test_invalid_action(self):
        """Test that invalid action is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "invalid"])
        assert result.exit_code == 2

    @patch("dot_man.cli.encrypt_cmd.detect_available_encryption")
    @patch("dot_man.cli.encrypt_cmd._show_encryption_status")
    def test_encrypt_status_no_tools(self, mock_status, mock_detect):
        """Test encrypt status with no encryption tools."""
        mock_detect.return_value = []
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 1
        assert "GPG" in result.output or "AGE" in result.output


class TestEncryptionMethods:
    """Test encryption method options."""

    def test_encrypt_method_option(self):
        """Test --method option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "--method" in result.output or "-m" in result.output

    def test_encrypt_recipient_option(self):
        """Test --recipient option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "--recipient" in result.output or "-r" in result.output


class TestEncryptWithoutInit:
    """Test encrypt without initialization."""

    def test_encrypt_encrypt_without_init(self):
        """Test encrypt encrypt without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "encrypt", "test"])
        assert result.exit_code in [0, 1]

    def test_encrypt_decrypt_without_init(self):
        """Test encrypt decrypt without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "decrypt", "test"])
        assert result.exit_code in [0, 1]

    def test_encrypt_status_without_init(self):
        """Test encrypt status without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code in [0, 1]


class TestEncryptMethodChoices:
    """Test encrypt method choice validation."""

    def test_encrypt_gpg_method(self):
        """Test gpg method is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "gpg" in result.output.lower()

    def test_encrypt_age_method(self):
        """Test age method is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert "age" in result.output.lower()
