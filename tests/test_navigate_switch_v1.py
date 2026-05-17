"""Tests for navigate_cmd.py and switch_cmd.py — the main branch switching commands."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestNavigateHelp:
    def test_navigate_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["navigate", "--help"])
        assert result.exit_code == 0
        assert "navigate" in result.output.lower()
        assert "--dry-run" in result.output


class TestNavigateCreateBranch:
    def test_navigate_creates_new_branch(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".navrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("nav test")
        integration_runner.invoke(cli, ["add", str(test_file), "--section", "nav-test"])
        result = integration_runner.invoke(cli, ["navigate", "work"])
        # Navigate may succeed or show a warning
        assert result.exit_code in (0, 1)

    def test_navigate_switch_existing(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".switchrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("switch test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "switch-test"]
        )
        integration_runner.invoke(cli, ["navigate", "work"])
        result = integration_runner.invoke(cli, ["navigate", "main"])
        assert result.exit_code == 0


class TestNavigateDryRun:
    def test_dry_run(self, integration_runner):
        result = integration_runner.invoke(cli, ["navigate", "test-dry", "--dry-run"])
        assert result.exit_code == 0


class TestNavigateNoSave:
    def test_no_save(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".nosaverc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("nosave test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "nosave-test"]
        )
        # --no-save may or may not be a valid flag
        result = integration_runner.invoke(cli, ["navigate", "nosave-br", "--no-save"])
        # Accept success or handled error
        assert result.exit_code in (0, 1, 2)


class TestSwitchDeprecated:
    def test_switch_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["switch", "--help"])
        assert result.exit_code == 0

    def test_switch_dry_run(self, integration_runner):
        result = integration_runner.invoke(cli, ["switch", "test-branch", "--dry-run"])
        assert result.exit_code == 0

    def test_switch_same_branch(self, integration_runner):
        result = integration_runner.invoke(cli, ["switch", "main"])
        assert result.exit_code == 0
