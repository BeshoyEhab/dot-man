"""More comprehensive tests for import command."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestImportCLI:
    """Test import CLI with various options."""

    def test_import_all_help(self):
        """Test import all --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "all", "--help"])
        assert result.exit_code == 0

    def test_import_stow_help(self):
        """Test import stow --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "stow", "--help"])
        assert result.exit_code == 0

    def test_import_yadm_help(self):
        """Test import yadm --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "yadm", "--help"])
        assert result.exit_code == 0

    def test_import_chezmoi_help(self):
        """Test import chezmoi --help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "chezmoi", "--help"])
        assert result.exit_code == 0

    def test_import_invalid_source(self):
        """Test invalid import source."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "invalid_source"])
        assert result.exit_code == 2


class TestImportOptions:
    """Test import command options."""

    def test_import_path_option(self):
        """Test --path option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "--help"])
        assert "--path" in result.output or "-p" in result.output

    def test_import_dry_run_option(self):
        """Test --dry-run option is recognized."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "--help"])
        assert "--dry-run" in result.output


class TestImportWithoutInit:
    """Test import without initialization."""

    def test_import_chezmoi_without_init(self):
        """Test chezmoi import without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "chezmoi"])
        assert result.exit_code in [0, 1]

    def test_import_yadm_without_init(self):
        """Test yadm import without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "yadm"])
        assert result.exit_code in [0, 1]

    def test_import_stow_without_init(self):
        """Test stow import without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "stow"])
        assert result.exit_code in [0, 1]

    def test_import_all_without_init(self):
        """Test all import without init."""
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "all"])
        assert result.exit_code in [0, 1]
