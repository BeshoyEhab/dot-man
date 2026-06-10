"""Tests for cli/config_cmd.py — config command."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.config_cmd import _run_interactive_tutorial, _show_section_examples
from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


class TestConfigHelp:
    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower()
        assert "create" in result.output.lower()


class TestConfigList:
    def test_config_list_help(self, runner):
        result = runner.invoke(cli, ["config", "list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower()

    def test_config_list_without_init(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 1
        assert "global config not found" in result.output.lower()


class TestConfigGet:
    def test_config_get_help(self, runner):
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code == 0
        assert "get" in result.output.lower()

    def test_config_get_without_init(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "get", "dot-man.editor"])
        assert result.exit_code == 1
        assert "global config not found" in result.output.lower()

    def test_config_get_nonexistent_without_init(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "get", "nonexistent.key"])
        assert result.exit_code == 1
        assert "global config not found" in result.output.lower()


class TestConfigSet:
    def test_config_set_help(self, runner):
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output.lower()

    def test_config_set_creates_config(self, clean_env):
        runner, _, _, global_toml = clean_env
        assert not global_toml.exists()
        result = runner.invoke(cli, ["config", "set", "dot-man.editor", "vim"])
        assert result.exit_code == 0, result.output
        assert global_toml.exists()

    def test_config_set_boolean_value(self, clean_env):
        runner, _, _, global_toml = clean_env
        result = runner.invoke(cli, ["config", "set", "dot-man.strict_mode", "true"])
        assert result.exit_code == 0, result.output
        assert global_toml.exists()


class TestConfigDefaults:
    """Tests for the 'config defaults' subcommand."""

    def test_config_defaults_help(self, runner):
        result = runner.invoke(cli, ["config", "defaults", "--help"])
        assert result.exit_code == 0
        assert "Show all configurable defaults" in result.output

    def test_config_defaults_shows_settings(self, runner):
        result = runner.invoke(cli, ["config", "defaults"])
        assert result.exit_code == 0
        assert "Configurable Defaults" in result.output
        assert "switch.default_behavior" in result.output
        assert "remote.auto_sync" in result.output
        assert "security.strict_mode" in result.output
        assert "backup.max_count" in result.output
        assert "Section-level settings" in result.output


class TestConfigListInitialized:
    """Tests for 'config list' against an initialized repo."""

    def test_config_list_shows_global_config(self, integration_runner):
        result = integration_runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0
        assert "Global Configuration" in result.output

    def test_config_list_shows_configured_keys(self, integration_runner):
        integration_runner.invoke(
            cli, ["config", "set", "remote.url", "git@example.com"]
        )
        result = integration_runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0
        assert "remote.url" in result.output
        assert "git@example.com" in result.output


class TestConfigGetExistingKey:
    """Tests for 'config get' against an initialized repo."""

    def test_get_existing_key(self, integration_runner):
        integration_runner.invoke(
            cli, ["config", "set", "remote.url", "git@example.com"]
        )
        result = integration_runner.invoke(cli, ["config", "get", "remote.url"])
        assert result.exit_code == 0
        assert "git@example.com" in result.output

    def test_get_nonexistent_key_errors(self, integration_runner):
        result = integration_runner.invoke(cli, ["config", "get", "nonexistent.key"])
        assert result.exit_code == 1
        assert "Key not found" in result.output

    def test_get_dict_section(self, integration_runner):
        integration_runner.invoke(
            cli, ["config", "set", "custom.nested.key", "deep_value"]
        )
        result = integration_runner.invoke(cli, ["config", "get", "custom.nested"])
        assert result.exit_code == 0
        assert "deep_value" in result.output
        assert "Section" in result.output


class TestConfigSetValues:
    """Tests for 'config set' with value verification."""

    def test_set_string_and_verify(self, integration_runner):
        r = integration_runner.invoke(
            cli, ["config", "set", "remote.url", "git@example.com:test.git"]
        )
        assert r.exit_code == 0
        assert "Set" in r.output
        r2 = integration_runner.invoke(cli, ["config", "get", "remote.url"])
        assert "git@example.com:test.git" in r2.output

    def test_set_boolean_true(self, integration_runner):
        r = integration_runner.invoke(
            cli, ["config", "set", "remote.auto_sync", "true"]
        )
        assert r.exit_code == 0
        r2 = integration_runner.invoke(cli, ["config", "get", "remote.auto_sync"])
        assert "True" in r2.output

    def test_set_boolean_false(self, integration_runner):
        r = integration_runner.invoke(
            cli, ["config", "set", "remote.auto_sync", "false"]
        )
        assert r.exit_code == 0
        r2 = integration_runner.invoke(cli, ["config", "get", "remote.auto_sync"])
        assert "False" in r2.output

    def test_set_creates_new_section(self, integration_runner):
        r = integration_runner.invoke(
            cli, ["config", "set", "custom.key", "custom_value"]
        )
        assert r.exit_code == 0
        r2 = integration_runner.invoke(cli, ["config", "get", "custom.key"])
        assert "custom_value" in r2.output

    def test_set_key_path_conflict_errors(self, integration_runner):
        integration_runner.invoke(cli, ["config", "set", "custom", "string_value"])
        result = integration_runner.invoke(
            cli, ["config", "set", "custom.subkey", "value"]
        )
        assert result.exit_code == 1
        assert "Key path conflict" in result.output


class TestConfigCreate:
    """Tests for the 'config create' subcommand."""

    def test_create_without_init_fails(self, clean_env):
        runner, *_ = clean_env
        result = runner.invoke(cli, ["config", "create", "--force"])
        assert result.exit_code != 0
        assert (
            "not initialized" in result.output.lower()
            or "init" in result.output.lower()
        )

    def test_create_default_with_examples(self, integration_runner):
        result = integration_runner.invoke(cli, ["config", "create", "--force"])
        assert result.exit_code == 0
        assert "Created config with examples" in result.output

    def test_create_minimal(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["config", "create", "--minimal", "--force"]
        )
        assert result.exit_code == 0
        assert "minimal config" in result.output

    def test_create_force_overwrite(self, integration_runner):
        integration_runner.invoke(cli, ["config", "create", "--force"])
        result = integration_runner.invoke(cli, ["config", "create", "--force"])
        assert result.exit_code == 0
        assert "Created config" in result.output

    def test_create_without_force_prompt_cancel(self, integration_runner):
        integration_runner.invoke(cli, ["config", "create", "--force"])
        with patch("dot_man.cli.config_cmd.ui.confirm", return_value=False):
            result = integration_runner.invoke(cli, ["config", "create"])
        assert result.exit_code == 0
        assert "Cancelled" in result.output


class TestConfigTutorial:
    """Tests for the 'config tutorial' subcommand."""

    def test_tutorial_help(self, runner):
        result = runner.invoke(cli, ["config", "tutorial", "--help"])
        assert result.exit_code == 0
        assert "Interactive configuration tutorial" in result.output

    def test_tutorial_section_basic(self, runner):
        result = runner.invoke(cli, ["config", "tutorial", "--section", "basic"])
        assert result.exit_code == 0
        assert "Basic File Tracking" in result.output

    def test_tutorial_section_directories(self, runner):
        result = runner.invoke(cli, ["config", "tutorial", "--section", "directories"])
        assert result.exit_code == 0
        assert "Directory Tracking" in result.output

    def test_tutorial_section_hooks(self, runner):
        result = runner.invoke(cli, ["config", "tutorial", "--section", "hooks"])
        assert result.exit_code == 0
        assert "Pre/Post Deploy Hooks" in result.output

    def test_tutorial_section_unknown(self, runner):
        result = runner.invoke(cli, ["config", "tutorial", "--section", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown section" in result.output
        assert "basic" in result.output

    def test_tutorial_interactive_flag(self, runner):
        with patch("builtins.input", return_value=""):
            result = runner.invoke(cli, ["config", "tutorial", "--interactive"])
        assert result.exit_code == 0
        assert "Tutorial Complete" in result.output

    def test_tutorial_menu_choice_basic(self, runner):
        with patch("rich.prompt.Prompt.ask", return_value="1"):
            result = runner.invoke(cli, ["config", "tutorial"])
        assert result.exit_code == 0
        assert "Basic File Tracking" in result.output

    def test_tutorial_menu_choice_quit(self, runner):
        with patch("rich.prompt.Prompt.ask", return_value="Q"):
            result = runner.invoke(cli, ["config", "tutorial"])
        assert result.exit_code == 0
        assert "Goodbye" in result.output

    def test_tutorial_menu_choice_interactive(self, runner):
        with (
            patch("rich.prompt.Prompt.ask", return_value="I"),
            patch("builtins.input", return_value=""),
        ):
            result = runner.invoke(cli, ["config", "tutorial"])
        assert result.exit_code == 0
        assert "Tutorial Complete" in result.output

    def test_tutorial_menu_choice_presets(self, runner):
        with patch("rich.prompt.Prompt.ask", return_value="9"):
            result = runner.invoke(cli, ["config", "tutorial"])
        assert result.exit_code == 0
        assert "Quick Setup Presets" in result.output

    def test_tutorial_menu_choice_create_tip(self, runner):
        with patch("rich.prompt.Prompt.ask", return_value="C"):
            result = runner.invoke(cli, ["config", "tutorial"])
        assert result.exit_code == 0
        assert "dot-man config create" in result.output


class TestShowSectionExamples:
    """Tests for _show_section_examples helper function."""

    def test_unknown_section_calls_error(self):
        with patch("dot_man.cli.config_cmd.ui.error") as mock_error:
            _show_section_examples("nonexistent")
            mock_error.assert_called_once_with(
                "Unknown section: nonexistent", exit_code=0
            )

    def test_unknown_section_lists_available(self):
        with patch("dot_man.cli.config_cmd.ui.error"):
            with patch("dot_man.cli.config_cmd.ui.console.print") as mock_print:
                _show_section_examples("nonexistent")
                call_args = " ".join(str(c) for c in mock_print.call_args_list)
                assert "basic" in call_args

    def test_basic_section_runs_without_error(self):
        with patch("dot_man.cli.config_cmd.ui.console.print"):
            _show_section_examples("basic")

    def test_all_sections_run_without_error(self):
        sections = [
            "basic",
            "directories",
            "hooks",
            "templates",
            "advanced",
            "secrets",
            "activate",
            "presets",
        ]
        for section in sections:
            with patch("dot_man.cli.config_cmd.ui.console.print"):
                _show_section_examples(section)


class TestRunInteractiveTutorial:
    """Tests for _run_interactive_tutorial helper."""

    def test_tutorial_completes_successfully(self):
        with (
            patch("builtins.input", return_value=""),
            patch("dot_man.cli.config_cmd.ui.console.print"),
        ):
            _run_interactive_tutorial()

    def test_tutorial_shows_all_steps(self):
        captured = []

        def capture(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            captured.append(text)

        with (
            patch("builtins.input", return_value=""),
            patch("dot_man.cli.config_cmd.ui.console.print", side_effect=capture),
        ):
            _run_interactive_tutorial()
        full = " ".join(captured)
        assert "Step 1" in full
        assert "Step 2" in full
        assert "Step 3" in full
        assert "Step 4" in full
        assert "Step 5" in full
        assert "Step 6" in full
        assert "Tutorial Complete" in full
