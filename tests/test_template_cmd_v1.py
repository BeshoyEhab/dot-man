"""Tests for cli/template_cmd.py — template set/get/list/system/substitute."""

import os

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestTemplateHelp:
    def test_template_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "--help"])
        assert result.exit_code == 0
        assert "template" in result.output.lower()

    def test_template_set_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "set", "--help"])
        assert result.exit_code == 0
        assert "--from-env" in result.output

    def test_template_system_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "system", "--help"])
        assert result.exit_code == 0


class TestTemplateSet:
    def test_set_simple(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["template", "set", "MACHINE", "work-laptop"]
        )
        assert result.exit_code == 0
        assert "MACHINE" in result.output
        assert "work-laptop" in result.output

    def test_set_from_env(self, integration_runner):
        os.environ["TEST_KEY_DOTMAN"] = "test_value_123"
        try:
            result = integration_runner.invoke(
                cli, ["template", "set", "MY_KEY", "--from-env", "TEST_KEY_DOTMAN"]
            )
            assert result.exit_code == 0
            assert "test_value_123" in result.output
        finally:
            del os.environ["TEST_KEY_DOTMAN"]

    def test_set_from_env_missing(self, integration_runner):
        result = integration_runner.invoke(
            cli,
            ["template", "set", "MISSING", "--from-env", "NONEXISTENT_VAR_DOTMAN_XYZ"],
        )
        assert result.exit_code != 0

    def test_set_no_value(self, integration_runner):
        result = integration_runner.invoke(cli, ["template", "set", "EMPTY"])
        assert result.exit_code != 0


class TestTemplateGet:
    def test_get_existing(self, integration_runner):
        integration_runner.invoke(cli, ["template", "set", "FOO", "bar"])
        result = integration_runner.invoke(cli, ["template", "get", "FOO"])
        assert result.exit_code == 0
        assert "bar" in result.output

    def test_get_missing(self, integration_runner):
        result = integration_runner.invoke(cli, ["template", "get", "NONEXISTENT"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()


class TestTemplateList:
    def test_list_empty(self, integration_runner):
        result = integration_runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "Template" in result.output or "template" in result.output

    def test_list_with_templates(self, integration_runner):
        integration_runner.invoke(cli, ["template", "set", "KEY1", "val1"])
        integration_runner.invoke(cli, ["template", "set", "KEY2", "val2"])
        result = integration_runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "KEY1" in result.output
        assert "KEY2" in result.output

    def test_list_shows_system_vars(self, integration_runner):
        result = integration_runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert "HOSTNAME" in result.output


class TestTemplateSystem:
    def test_system_vars(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["template", "system"])
        assert result.exit_code == 0
        assert "HOSTNAME" in result.output
        assert "USER" in result.output
        assert "HOME" in result.output
        assert "SHELL" in result.output
        assert "OS" in result.output


class TestTemplateSubstitute:
    def test_substitute_system_vars(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["template", "substitute", "user={{USER}}"]
        )
        assert result.exit_code == 0
        assert "user=" in result.output
        # Should have substituted the real username
        assert "{{USER}}" not in result.output

    def test_substitute_custom_var(self, integration_runner):
        integration_runner.invoke(cli, ["template", "set", "MYVAR", "hello"])
        result = integration_runner.invoke(
            cli, ["template", "substitute", "val={{MYVAR}}"]
        )
        assert result.exit_code == 0
        assert "val=hello" in result.output

    def test_substitute_mixed(self, integration_runner):
        integration_runner.invoke(cli, ["template", "set", "ROLE", "dev"])
        result = integration_runner.invoke(
            cli,
            ["template", "substitute", "{{USER}} on {{HOSTNAME}} as {{ROLE}}"],
        )
        assert result.exit_code == 0
        assert "dev" in result.output
