"""Tests for export command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestExportHelp:
    """Test export command help."""

    def test_export_help(self):
        """Test export help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "tar" in result.output.lower()
        assert "zip" in result.output.lower()
        assert "json" in result.output.lower()

    def test_export_tar_help(self):
        """Test export tar format help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "tar", "--help"])
        assert result.exit_code == 0

    def test_export_zip_help(self):
        """Test export zip format help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "zip", "--help"])
        assert result.exit_code == 0

    def test_export_json_help(self):
        """Test export json format help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "json", "--help"])
        assert result.exit_code == 0


class TestExportFormatValidation:
    """Test export format validation."""

    def test_invalid_format(self):
        """Test that invalid format is rejected."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "invalid", "output"])
        assert result.exit_code == 2


class TestExportOptions:
    """Test export command options."""

    def test_export_branch_option(self):
        """Test --branch option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert "--branch" in result.output or "-b" in result.output

    def test_export_include_secrets_option(self):
        """Test --include-secrets option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert "--include-secrets" in result.output


class TestExportWithoutInit:
    """Test export without initialization."""

    def test_export_tar_without_init(self):
        """Test export tar without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "tar", "backup.tar.gz"])
        assert result.exit_code in [0, 1]

    def test_export_zip_without_init(self):
        """Test export zip without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "zip", "backup.zip"])
        assert result.exit_code in [0, 1]

    def test_export_json_without_init(self):
        """Test export json without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "json", "manifest.json"])
        assert result.exit_code in [0, 1]


class TestExportOutputArgument:
    """Test export output argument."""

    def test_export_requires_output(self):
        """Test export requires output argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "tar"])
        assert result.exit_code == 2
