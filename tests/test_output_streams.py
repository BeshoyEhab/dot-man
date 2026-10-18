"""U4: diagnostics belong on stderr; stdout stays machine-readable.

``ui.error`` already used a stderr console, but warnings and the
uncaught-exception diagnostics still printed to stdout, which corrupts
``--json`` output for scripts. These tests pin the stream split:
informational output -> stdout, warnings/errors/diagnostics -> stderr.
"""

import json

import pytest
from click.testing import CliRunner


class TestUiStreamRouting:
    """The ``ui`` helpers route to the conventional stream."""

    def test_warn_goes_to_stderr_only(self, capsys):
        from dot_man import ui

        ui.configure()
        ui.warn("something odd happened")

        captured = capsys.readouterr()
        assert "something odd happened" in captured.err
        assert "something odd happened" not in captured.out

    def test_error_goes_to_stderr_only(self, capsys):
        from dot_man import ui

        ui.configure()
        with pytest.raises(SystemExit) as exc:
            ui.error("fatal problem")

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "fatal problem" in captured.err
        assert "fatal problem" not in captured.out

    def test_info_and_success_stay_on_stdout(self, capsys):
        from dot_man import ui

        ui.configure()
        ui.info("hello info")
        ui.success("all done")

        captured = capsys.readouterr()
        assert "hello info" in captured.out
        assert "all done" in captured.out
        assert captured.err == ""


class TestHandleExceptionStreamRouting:
    """Uncaught-exception diagnostics are diagnostics, not data."""

    def test_generic_diagnostics_go_to_stderr(self, capsys):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit) as exc:
            handle_exception(ValueError("kaboom"), "Thing")

        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "kaboom" in captured.err
        assert captured.out.strip() == ""

    def test_keyboard_interrupt_goes_to_stderr(self, capsys):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit) as exc:
            handle_exception(KeyboardInterrupt(), "Thing")

        assert exc.value.code == 130
        captured = capsys.readouterr()
        assert "cancelled" in captured.err.lower()
        assert captured.out.strip() == ""


class TestWarnIfDirtyStreamRouting:
    """The uncommitted-changes warning must not pollute stdout."""

    def test_warning_goes_to_stderr(self, capsys):
        from dot_man import ui
        from dot_man.cli.common import warn_if_dirty

        ui.configure()

        class _Git:
            def is_dirty(self) -> bool:
                return True

        class _Ops:
            git = _Git()

        warn_if_dirty(_Ops(), "main")

        captured = capsys.readouterr()
        assert "uncommitted changes" in captured.err
        assert "uncommitted changes" not in captured.out


class TestJsonStdoutStaysClean:
    """``--json`` stdout must parse even though diagnostics exist."""

    def test_status_json_stdout_is_pure_json(self, integration_runner):
        from dot_man.cli.interface import cli

        result = integration_runner.invoke(cli, ["--json", "status"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.stdout)
        assert isinstance(payload, dict)

    def test_failing_command_keeps_stdout_free_of_diagnostics(
        self, uninitialized_runner
    ):
        """A failing command writes its diagnostic to stderr, not stdout."""
        from dot_man.cli.interface import cli

        result = uninitialized_runner.invoke(cli, ["audit"])

        assert result.exit_code == 1
        assert "Error:" in result.stderr
        assert "Error:" not in result.stdout


class TestCliRunnerStreams:
    """Guard the assumption the stream tests rely on."""

    def test_cli_runner_separates_stdout_and_stderr(self):
        import click

        @click.command()
        def _cmd():
            click.echo("out")
            click.echo("err", err=True)

        result = CliRunner().invoke(_cmd, [])

        assert result.stdout == "out\n"
        assert result.stderr == "err\n"
