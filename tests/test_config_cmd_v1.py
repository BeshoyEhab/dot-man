"""Tests for cli/config_cmd.py — config defaults/tutorial."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestConfigDefaults:
    def test_config_defaults(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "defaults"])
        assert result.exit_code == 0
        assert "switch.default_behavior" in result.output
        assert "remote.auto_sync" in result.output
        assert "defaults.secrets_filter" in result.output
        assert "defaults.update_strategy" in result.output
        assert "security.strict_mode" in result.output

    def test_config_defaults_no_duplicate_text(self):
        """Verify the triplicated 'To change a setting' was fixed."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "defaults"])
        assert result.exit_code == 0
        count = result.output.count("To change a setting:")
        assert count == 1, f"Found {count} occurrences, expected 1"


class TestConfigList:
    def test_config_list(self, integration_runner):
        result = integration_runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0


class TestConfigCreate:
    def test_config_create(self, integration_runner):
        result = integration_runner.invoke(cli, ["config", "create", "--force"])
        assert result.exit_code == 0

    def test_config_create_minimal(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["config", "create", "--minimal", "--force"]
        )
        assert result.exit_code == 0


class TestConfigTutorial:
    def test_tutorial_basic(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "basic"])
        assert result.exit_code == 0

    def test_tutorial_hooks(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "hooks"])
        assert result.exit_code == 0

    def test_tutorial_templates(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "templates"])
        assert result.exit_code == 0

    def test_tutorial_advanced(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "advanced"])
        assert result.exit_code == 0

    def test_tutorial_secrets(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "secrets"])
        assert result.exit_code == 0

    def test_tutorial_activate(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "activate"])
        assert result.exit_code == 0

    def test_tutorial_presets(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "presets"])
        assert result.exit_code == 0

    def test_tutorial_directories(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "directories"])
        assert result.exit_code == 0

    def test_tutorial_invalid_section(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "tutorial", "--section", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown" in result.output or "Available" in result.output
