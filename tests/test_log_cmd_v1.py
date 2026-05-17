"""Tests for cli/log_cmd.py — log, diff, checkout commands."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestLogCommand:
    def test_log_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["log", "--help"])
        assert result.exit_code == 0
        assert "--diff" in result.output or "-d" in result.output
        assert "--stat" in result.output
        assert "--interactive" in result.output or "-i" in result.output

    def test_log_basic(self, integration_runner):
        result = integration_runner.invoke(cli, ["log"])
        assert result.exit_code == 0

    def test_log_with_count(self, integration_runner):
        result = integration_runner.invoke(cli, ["log", "-n", "5"])
        assert result.exit_code == 0

    def test_log_with_stat(self, integration_runner):
        result = integration_runner.invoke(cli, ["log", "--stat"])
        assert result.exit_code == 0

    def test_log_with_diff(self, integration_runner):
        result = integration_runner.invoke(cli, ["log", "--diff"])
        assert result.exit_code == 0

    def test_log_untracked_file(self, integration_runner):
        result = integration_runner.invoke(cli, ["log", "/nonexistent/file"])
        # May show "not tracked" or just succeed with empty output
        assert result.exit_code in (0, 1)


class TestDiffCommand:
    def test_diff_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0
        assert "--branch" in result.output or "-b" in result.output
        assert "--staged" in result.output
        assert "--rich" in result.output

    def test_diff_basic(self, integration_runner):
        result = integration_runner.invoke(cli, ["diff"])
        assert result.exit_code == 0

    def test_diff_staged(self, integration_runner):
        result = integration_runner.invoke(cli, ["diff", "--staged"])
        assert result.exit_code == 0

    def test_diff_no_rich(self, integration_runner):
        result = integration_runner.invoke(cli, ["diff", "--no-rich"])
        assert result.exit_code == 0


class TestCheckoutCommand:
    def test_checkout_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["checkout", "--help"])
        assert result.exit_code == 0
        assert "DEPRECATED" in result.output or "deprecated" in result.output

    def test_checkout_invalid_target(self, integration_runner):
        result = integration_runner.invoke(cli, ["checkout", "nonexistent_xyz"])
        # Should fail or show deprecation warning
        assert result.exit_code != 0 or "deprecated" in result.output.lower()
