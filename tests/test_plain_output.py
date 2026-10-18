"""Tests for --plain output and width-aware rendering (U11).

``--plain`` swaps emoji/box-drawing for ASCII markers; the shared printers
use Rich's width-aware rules instead of hardcoded line lengths, and
``truncate_text`` clips to terminal cells rather than a magic slice.
"""

import pytest

from dot_man import ui
from dot_man.cli.interface import cli


@pytest.fixture(autouse=True)
def _reset_ui_state():
    """Keep the process-wide ui flags from leaking between tests."""
    ui.configure()
    yield
    ui.configure()


class TestPlainMode:
    """--plain replaces emoji and box-drawing with plain ASCII."""

    def test_plain_flag_is_recorded(self):
        ui.configure(plain=True)

        assert ui.plain() is True

    def test_plain_success_uses_ascii_marker(self, capsys):
        ui.configure(plain=True)

        ui.success("build-done")

        out = capsys.readouterr().out
        assert "[ok]" in out
        assert "✓" not in out

    def test_default_success_uses_emoji(self, capsys):
        ui.configure(plain=False)

        ui.success("build-done")

        assert "✓" in capsys.readouterr().out

    def test_plain_warn_and_error_use_ascii(self, capsys):
        ui.configure(plain=True)

        ui.warn("careful")
        ui.error("bad", exit_code=0)

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "[!]" in combined
        assert "[x]" in combined
        assert "⚠" not in combined
        assert "✗" not in combined

    def test_icon_returns_fallback_when_plain(self):
        ui.configure(plain=True)

        assert ui.icon("📁", "DIR") == "DIR"

    def test_icon_returns_emoji_by_default(self):
        ui.configure(plain=False)

        assert ui.icon("📁", "DIR") == "📁"

    def test_section_is_ascii_when_plain(self, capsys):
        ui.configure(plain=True)

        ui.section("Title", "")

        out = capsys.readouterr().out
        assert "Title" in out
        assert "┌" not in out


class TestWidthAwareRules:
    """Rules size themselves to the console rather than a fixed 50."""

    def test_plain_rule_uses_ascii(self, capsys):
        ui.configure(plain=True)

        ui.rule()

        line = capsys.readouterr().out.strip()
        assert line
        assert set(line) <= {"-", " "}

    def test_default_rule_uses_box_drawing(self, capsys):
        ui.configure(plain=False)

        ui.rule()

        assert "─" in capsys.readouterr().out

    def test_rule_spans_console_width(self, capsys):
        ui.configure(plain=True)

        ui.rule()

        line = capsys.readouterr().out.rstrip("\n")
        assert len(line) == ui.console.width


class TestTruncateText:
    """Width-aware truncation replaces ``display_path[-32:]``."""

    def test_short_text_is_unchanged(self):
        assert ui.truncate_text("short", 10) == "short"

    def test_long_text_is_clipped(self):
        result = ui.truncate_text("x" * 100, 10)

        assert len(result) <= 10

    def test_long_text_gets_an_ellipsis(self):
        result = ui.truncate_text("x" * 100, 10)

        assert result.endswith("…")


class TestPlainGlobalFlag:
    """--plain is advertised and accepted by the root group."""

    def test_root_help_lists_plain(self):
        from click.testing import CliRunner

        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--plain" in result.output

    def test_plain_is_applied_from_cli(self, uninitialized_runner):
        """The group callback applies --plain before the subcommand runs."""
        uninitialized_runner.invoke(cli, ["--plain", "status"])

        assert ui.plain() is True
