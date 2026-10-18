"""Tests for the global CLI flags (U1).

Covers ``--quiet``, ``--yes``, ``--no-input``, ``--no-color`` and ``--json``
on the root group, both at the ``ui`` module level and end-to-end through
the ``cli`` group.
"""

import json

import pytest
from click.testing import CliRunner

from dot_man import ui
from dot_man.cli.interface import cli


class TestGlobalFlagHelp:
    """The root group advertises every global flag."""

    def test_root_help_lists_global_flags(self):
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        for flag in ["--quiet", "--yes", "--no-input", "--no-color", "--json"]:
            assert flag in result.output, f"{flag} missing from --help"


class TestQuietFlag:
    """--quiet silences informational output but never errors."""

    def test_quiet_suppresses_info_success_and_warn(self, capsys):
        ui.configure(quiet=True)

        ui.info("info-marker")
        ui.success("success-marker")
        ui.warn("warn-marker")

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "info-marker" not in combined
        assert "success-marker" not in combined
        assert "warn-marker" not in combined

    def test_quiet_still_prints_errors(self, capsys):
        ui.configure(quiet=True)

        ui.error("error-marker", exit_code=0)

        assert "error-marker" in capsys.readouterr().err

    def test_default_prints_info(self, capsys):
        ui.configure(quiet=False)

        ui.info("hello-marker")

        assert "hello-marker" in capsys.readouterr().out


class TestYesFlag:
    """--yes auto-confirms prompts; --no-input refuses them."""

    def test_yes_auto_confirms(self):
        ui.configure(yes=True)

        assert ui.confirm("Proceed?") is True

    def test_no_input_makes_confirm_fail_fast(self):
        ui.configure(no_input=True)

        with pytest.raises(SystemExit) as excinfo:
            ui.confirm("Proceed?")

        assert excinfo.value.code == 2

    def test_no_input_makes_ask_fail_fast(self):
        ui.configure(no_input=True)

        with pytest.raises(SystemExit) as excinfo:
            ui.ask("Name?")

        assert excinfo.value.code == 2


class TestNoColorFlag:
    """--no-color disables ANSI colour on both consoles."""

    def test_no_color_disables_colour(self):
        ui.configure(no_color=True)

        assert ui.console.no_color is True
        assert ui.error_console.no_color is True

    def test_colour_is_default(self):
        ui.configure(no_color=False)

        assert ui.console.no_color is False
        assert ui.error_console.no_color is False


class TestGlobalJsonFlag:
    """--json is recorded on the context and honoured by ``status``."""

    def test_json_mode_is_recorded(self):
        ui.configure(json=True)

        assert ui.json_mode() is True

    def test_status_honours_global_json(self, integration_runner):
        result = integration_runner.invoke(cli, ["--json", "status"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "sections" in payload
        assert "summary" in payload
