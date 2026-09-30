"""Tests for two-level help: `help` (happy path), `help-all` (everything).

Bare `--help` follows the short listing; aliases and deprecated shims
only appear in `help-all`.
"""

import importlib
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.common import HAPPY_PATH_COMMANDS
from dot_man.cli.interface import cli

# NOTE: dot_man.cli.help_cmd shadows the help_cmd module (it is the
# `help` Command) — resolve the module via importlib so patch targets
# work on all Python versions (mock uses pkgutil.resolve_name on 3.12+
# but getattr-chain on <=3.11, which hits the Command).
help_mod = importlib.import_module("dot_man.cli.help_cmd")

HAPPY_PATH = list(HAPPY_PATH_COMMANDS)
ADVANCED = ["encrypt", "template", "watch"]
ALIASES = ["nav", "aud"]
DEPRECATED = ["switch", "checkout"]


def lists_command(output: str, name: str) -> bool:
    """True if the Commands listing has a row for `name` (not a substring)."""
    return re.search(rf"(?m)^\s*{re.escape(name)}\s", output) is not None


@pytest.fixture
def runner():
    return CliRunner()


class TestHelpCommand:
    def test_help_lists_only_happy_path(self, runner):
        result = runner.invoke(cli, ["help"])
        assert result.exit_code == 0
        for name in HAPPY_PATH:
            assert lists_command(result.output, name)

    def test_help_hides_advanced_commands(self, runner):
        result = runner.invoke(cli, ["help"])
        assert result.exit_code == 0
        for name in ADVANCED + ALIASES + DEPRECATED:
            assert not lists_command(result.output, name)

    def test_help_points_to_help_all(self, runner):
        result = runner.invoke(cli, ["help"])
        assert result.exit_code == 0
        assert "help-all" in result.output


class TestHelpAllCommand:
    def test_help_all_lists_everything(self, runner):
        result = runner.invoke(cli, ["help-all"])
        assert result.exit_code == 0
        for name in HAPPY_PATH + ADVANCED + ALIASES + DEPRECATED:
            assert lists_command(result.output, name)

    def test_help_all_includes_help_commands(self, runner):
        result = runner.invoke(cli, ["help-all"])
        assert result.exit_code == 0
        assert "help-all" in result.output


class TestBareHelpFlag:
    def test_bare_help_is_short(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for name in HAPPY_PATH:
            assert lists_command(result.output, name)
        for name in ADVANCED + ALIASES + DEPRECATED:
            assert not lists_command(result.output, name)
        assert "help-all" in result.output


class TestInstallMan:
    def test_install_man_copies_man_page(self, runner, tmp_path):
        with patch.object(Path, "home", return_value=tmp_path):
            result = runner.invoke(cli, ["help", "--install-man"])
        assert result.exit_code == 0
        installed = tmp_path / ".local" / "share" / "man" / "man1" / "dot-man.1"
        assert installed.is_file()
        assert installed.read_text().startswith(".TH")

    def test_install_man_missing_source_errors(self, runner, tmp_path):
        with (
            patch.object(Path, "home", return_value=tmp_path),
            patch.object(help_mod, "MAN_SOURCE", tmp_path / "missing.1"),
        ):
            result = runner.invoke(cli, ["help", "--install-man"])
        assert result.exit_code != 0
