"""Tests for consistent exit codes and centralized error handling.

Every CLI error path must:
- exit via ``raise SystemExit(code)`` (never bare ``sys.exit()``),
- route unexpected failures through ``handle_exception()`` from ``common.py``,
- preserve the canonical exit codes (0 ok, 1 error, 2 usage, 130 interrupted).
"""

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


class TestUiErrorConsistency:
    """ui.error must raise SystemExit directly, not call sys.exit."""

    def test_error_preserves_exit_code(self):
        from dot_man import ui

        with pytest.raises(SystemExit) as exc_info:
            ui.error("boom", exit_code=3)
        assert exc_info.value.code == 3

    def test_error_does_not_call_sys_exit(self):
        from dot_man import ui

        with patch("sys.exit", side_effect=AssertionError("must not call sys.exit")):
            with pytest.raises(SystemExit) as exc_info:
                ui.error("boom", exit_code=3)
        assert exc_info.value.code == 3

    def test_error_exit_code_zero_does_not_exit(self):
        from dot_man import ui

        # exit_code=0 means "print only, caller decides" — must not raise.
        ui.error("just a message", exit_code=0)


class TestNavigateCentralRouting:
    """_navigate_impl must delegate failures to handle_exception."""

    def test_navigate_impl_calls_handle_exception(self):
        from dot_man.cli.navigate_cmd import _navigate_impl

        boom = RuntimeError("boom")
        with (
            patch(
                "dot_man.cli.navigate_cmd.handle_exception",
                side_effect=SystemExit(1),
            ) as mock_handle,
            patch(
                "dot_man.operations.get_operations",
                side_effect=boom,
            ),
        ):
            with pytest.raises(SystemExit):
                _navigate_impl(
                    {"type": "branch", "target": "work"},
                    False,
                    False,
                    None,
                    "auto",
                    False,
                    False,
                    False,
                )
        mock_handle.assert_called_once_with(boom, "Navigate")


class TestBootstrapCentralRouting:
    """bootstrap error paths must go through common.error."""

    def test_unknown_pm_routes_through_error_helper(self, runner):
        from dot_man.cli.interface import cli

        with patch("dot_man.cli.bootstrap_cmd.error") as mock_error:
            mock_error.side_effect = SystemExit(1)
            result = runner.invoke(cli, ["bootstrap", "--pm", "unknown-pm", "git"])
        assert result.exit_code == 1
        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        assert "unknown-pm" in args[0]
        assert kwargs.get("exit_code", 1) == 1

    def test_no_pm_routes_through_error_helper(self, runner):
        from dot_man.cli.interface import cli

        with (
            patch(
                "dot_man.cli.bootstrap_cmd._detect_package_manager",
                return_value=None,
            ),
            patch("dot_man.cli.bootstrap_cmd.error") as mock_error,
        ):
            mock_error.side_effect = SystemExit(1)
            result = runner.invoke(cli, ["bootstrap"])
        assert result.exit_code == 1
        mock_error.assert_called_once()


class TestConfigGetCentralRouting:
    """config get on a missing key must go through common.error."""

    def test_missing_key_routes_through_error_helper(self, runner):
        from unittest.mock import MagicMock

        from dot_man.cli.interface import cli

        cfg = MagicMock()
        cfg._data = {}
        with (
            patch("dot_man.cli.config_cmd.GlobalConfig", return_value=cfg),
            patch("dot_man.cli.config_cmd.error") as mock_error,
        ):
            mock_error.side_effect = SystemExit(1)
            result = runner.invoke(cli, ["config", "get", "nope.missing"])
        assert result.exit_code == 1
        mock_error.assert_called_once()
        assert "nope.missing" in mock_error.call_args[0][0]


class TestDoctorFailureExit:
    """doctor must report failures with a single error(..., exit_code=1)."""

    def test_failure_path_calls_error_once_with_exit_1(self, runner, tmp_path):
        from dot_man.cli.interface import cli

        dot_man_dir = tmp_path / "dm"
        repo_dir = dot_man_dir / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / ".git").mkdir()
        with (
            patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch(
                "dot_man.operations.get_operations",
                side_effect=RuntimeError("ops boom"),
            ),
            patch("dot_man.cli.doctor_cmd.error") as mock_error,
        ):
            mock_error.side_effect = SystemExit(1)
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        assert "check(s) failed" in args[0]
        assert kwargs.get("exit_code", 1) == 1


class TestDotManGroupCentralHandling:
    """DotManGroup must route unexpected errors through handle_exception."""

    def _mini_cli(self):
        from dot_man.cli.common import DotManGroup

        @click.group(cls=DotManGroup)
        def mini():
            """Mini CLI for testing central handling."""

        @mini.command()
        def boom():
            """Raise an unexpected error."""
            raise RuntimeError("boom")

        @mini.command()
        def cfgfail():
            """Raise a typed DotManError."""
            from dot_man.exceptions import ConfigurationError

            raise ConfigurationError("bad config")

        @mini.command()
        def sysexit():
            """Exit directly — must pass through untouched."""
            from dot_man.cli.common import error

            error("direct", exit_code=3)

        return mini

    def test_unexpected_error_becomes_diagnostic_exit_1(self, runner):
        mini = self._mini_cli()
        result = runner.invoke(mini, ["boom"])
        assert result.exit_code == 1
        assert not isinstance(result.exception, RuntimeError)
        assert "Unexpected error" in result.output

    def test_dotman_error_keeps_its_exit_code(self, runner):
        mini = self._mini_cli()
        result = runner.invoke(mini, ["cfgfail"])
        assert result.exit_code == 7
        assert "bad config" in result.output

    def test_click_usage_errors_untouched(self, runner):
        mini = self._mini_cli()
        result = runner.invoke(mini, ["boom", "--bogus-flag"])
        assert result.exit_code == 2

    def test_direct_system_exit_passthrough(self, runner):
        mini = self._mini_cli()
        result = runner.invoke(mini, ["sysexit"])
        assert result.exit_code == 3


class TestHandleExceptionExitCodes:
    """handle_exception must preserve canonical exit codes."""

    def test_dotman_error_exit_code_propagates(self):
        from dot_man.cli.common import ExitCode, handle_exception
        from dot_man.exceptions import ConfigurationError

        with pytest.raises(SystemExit) as exc_info:
            handle_exception(ConfigurationError("bad config"))
        assert exc_info.value.code == ConfigurationError.exit_code
        assert exc_info.value.code == ExitCode.CONFIG

    def test_keyboard_interrupt_maps_to_130(self):
        from dot_man.cli.common import ExitCode, handle_exception

        with pytest.raises(SystemExit) as exc_info:
            handle_exception(KeyboardInterrupt())
        assert exc_info.value.code == 130
        assert exc_info.value.code == ExitCode.INTERRUPTED

    def test_exit_code_constants(self):
        from dot_man.cli.common import ExitCode

        assert ExitCode.OK == 0
        assert ExitCode.ERROR == 1
        assert ExitCode.USAGE == 2
        assert ExitCode.INTERRUPTED == 130
