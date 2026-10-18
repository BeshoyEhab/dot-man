"""Tests for cli/template_cmd.py — template command."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

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
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


class TestTemplateHelp:
    def test_template_help(self, runner):
        """Template help."""
        result = runner.invoke(cli, ["template", "--help"])
        assert result.exit_code == 0


class TestTemplateList:
    def test_template_list_help(self, runner):
        """Template list help."""
        result = runner.invoke(cli, ["template", "list", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_list_runs(self, clean_env):
        """Template list runs."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.global_config import GlobalConfig

        GlobalConfig().create_default()

        result = runner.invoke(cli, ["template", "list"])

        assert result.exit_code == 0, result.output


class TestTemplateSet:
    def test_template_set_help(self, runner):
        """Template set help."""
        result = runner.invoke(cli, ["template", "set", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_set_runs(self, clean_env):
        """Template set runs."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.global_config import GlobalConfig

        GlobalConfig().create_default()

        result = runner.invoke(cli, ["template", "set", "MACHINE", "test-machine"])

        assert result.exit_code == 0, result.output

    def test_template_set_from_env(self, clean_env):
        """Template set from environment."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.global_config import GlobalConfig

        GlobalConfig().create_default()

        result = runner.invoke(
            cli, ["template", "set", "TEST_VAR", "--from-env", "HOME"]
        )

        assert result.exit_code == 0, result.output


class TestTemplateGet:
    def test_template_get_help(self, runner):
        """Template get help."""
        result = runner.invoke(cli, ["template", "get", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_get_runs(self, clean_env):
        """Template get runs."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        from dot_man.global_config import GlobalConfig

        GlobalConfig().create_default()

        result = runner.invoke(cli, ["template", "get", "MACHINE"])

        assert result.exit_code == 0, result.output


class TestTemplateDelete:
    def test_template_delete_help(self, runner):
        """Template delete help."""
        result = runner.invoke(cli, ["template", "delete", "--help"])
        assert result.exit_code in [0, 2]


class TestTemplateSystem:
    def test_template_system_help(self, runner):
        """Template system help."""
        result = runner.invoke(cli, ["template", "system", "--help"])
        assert result.exit_code in [0, 2]

    def test_template_system_runs(self, runner):
        """Template system runs."""
        result = runner.invoke(cli, ["template", "system"])
        assert result.exit_code == 0, result.output


class TestTemplateCallbackEdgeCases:
    """Error and empty-data branches of the template subcommands.

    These call the Click callbacks directly so the failure paths are
    deterministic (no dependency on the ambient environment).
    """

    @staticmethod
    def _ops(data):
        from unittest.mock import MagicMock

        ops = MagicMock()
        ops.global_config._data = data
        return ops

    def test_set_initialises_non_dict_templates(self):
        from dot_man.cli import template_cmd

        ops = self._ops({"templates": "not-a-dict"})
        with patch("dot_man.operations.get_operations", return_value=ops):
            template_cmd.template_set.callback("KEY", "value", None)

        assert ops.global_config._data["templates"] == {"KEY": "value"}
        ops.global_config.save.assert_called_once()

    def test_set_from_env_missing_value_errors(self):
        from dot_man.cli import template_cmd

        ops = self._ops({})
        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch.dict(os.environ, {}, clear=True),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_set.callback("KEY", None, "MISSING_VAR")

        mock_error.assert_called_once()
        assert (
            mock_error.call_args.args[0]
            == "Environment variable 'MISSING_VAR' is not set"
        )

    def test_set_failure_is_reported(self):
        from dot_man.cli import template_cmd

        with (
            patch(
                "dot_man.operations.get_operations",
                side_effect=RuntimeError("boom"),
            ),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_set.callback("KEY", "value", None)

        assert mock_error.call_args.args[0] == "boom"

    def test_get_failure_is_reported(self):
        from dot_man.cli import template_cmd

        with (
            patch(
                "dot_man.operations.get_operations",
                side_effect=RuntimeError("nope"),
            ),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_get.callback("KEY")

        assert mock_error.call_args.args[0] == "nope"

    def test_list_with_no_templates_prints_placeholder(self, capsys):
        from dot_man.cli import template_cmd

        ops = self._ops({})
        with patch("dot_man.operations.get_operations", return_value=ops):
            template_cmd.template_list.callback()

        assert "No templates defined" in capsys.readouterr().out

    def test_list_system_variable_failure_is_rendered(self, capsys):
        from dot_man.cli import template_cmd

        ops = self._ops({})

        def _boom():
            raise RuntimeError("unavailable")

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch.dict(template_cmd.SYSTEM_VARS, {"BROKEN": _boom}),
        ):
            template_cmd.template_list.callback()

        assert "{BROKEN}" in capsys.readouterr().out

    def test_list_failure_is_reported(self):
        from dot_man.cli import template_cmd

        with (
            patch(
                "dot_man.operations.get_operations",
                side_effect=RuntimeError("list boom"),
            ),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_list.callback()

        assert mock_error.call_args.args[0] == "list boom"

    def test_system_variable_failure_is_rendered(self, capsys):
        from dot_man.cli import template_cmd

        def _boom():
            raise RuntimeError("system boom")

        with patch.dict(template_cmd.SYSTEM_VARS, {"BROKEN": _boom}):
            template_cmd.template_system.callback()

        # The failed variable is annotated with its source and error text.
        assert "failed" in capsys.readouterr().out

    def test_system_failure_is_reported(self):
        from dot_man.cli import template_cmd

        with (
            patch.object(
                template_cmd.ui.console, "print", side_effect=RuntimeError("render")
            ),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_system.callback()

        assert mock_error.call_args.args[0] == "render"

    def test_substitute_system_variable_failure_is_skipped(self, capsys):
        from dot_man.cli import template_cmd

        ops = self._ops({})

        def _boom():
            raise OSError("no value")

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch.dict(template_cmd.SYSTEM_VARS, {"BROKEN": _boom}),
        ):
            template_cmd.template_substitute.callback("{{BROKEN}}")

        assert "{BROKEN}" in capsys.readouterr().out

    def test_substitute_failure_is_reported(self):
        from dot_man.cli import template_cmd

        with (
            patch(
                "dot_man.operations.get_operations",
                side_effect=RuntimeError("sub boom"),
            ),
            patch("dot_man.cli.template_cmd.error") as mock_error,
        ):
            template_cmd.template_substitute.callback("{{OS}}")

        assert mock_error.call_args.args[0] == "sub boom"
