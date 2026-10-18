"""Tests for ui module — real output and behavior assertions."""

import pytest


class TestPrintBanner:
    """Banner renders title, and subtitle when given."""

    def test_banner_title_only(self, capsys):
        from dot_man import ui

        ui.print_banner("My Title")

        out = capsys.readouterr().out
        assert "My Title" in out

    def test_banner_with_subtitle(self, capsys):
        from dot_man import ui

        ui.print_banner("My Title", subtitle="Sub line")

        out = capsys.readouterr().out
        assert "My Title" in out
        assert "Sub line" in out


class TestMessageHelpers:
    """info/success/warn/hint print their message text."""

    def test_info(self, capsys):
        from dot_man import ui

        ui.info("hello info")

        assert "hello info" in capsys.readouterr().out

    def test_success(self, capsys):
        from dot_man import ui

        ui.success("did it")

        assert "did it" in capsys.readouterr().out

    def test_warn(self, capsys):
        from dot_man import ui

        ui.warn("careful")

        # Warnings are diagnostics: they belong on stderr, not stdout.
        assert "careful" in capsys.readouterr().err

    def test_hint(self, capsys):
        from dot_man import ui

        ui.hint("try this")

        assert "try this" in capsys.readouterr().out


class TestError:
    """error() prints to stderr and exits via SystemExit."""

    def test_error_exits(self, capsys):
        from dot_man import ui

        with pytest.raises(SystemExit) as exc:
            ui.error("boom", exit_code=1)

        assert exc.value.code == 1
        assert "boom" in capsys.readouterr().err

    def test_error_no_exit_on_zero(self, capsys):
        from dot_man import ui

        ui.error("just noting", exit_code=0)

        assert "just noting" in capsys.readouterr().err


class TestConfirmAsk:
    """confirm()/ask() wire the question through and return the answer."""

    def test_confirm_yes(self, monkeypatch):
        from unittest.mock import MagicMock

        from dot_man import ui

        fake = MagicMock(return_value=True)
        monkeypatch.setattr("dot_man.ui.Confirm.ask", fake)

        assert ui.confirm("Proceed?") is True
        asked = fake.call_args[0][0]
        assert "Proceed?" in asked

    def test_confirm_no(self, monkeypatch):
        from unittest.mock import MagicMock

        from dot_man import ui

        monkeypatch.setattr("dot_man.ui.Confirm.ask", MagicMock(return_value=False))

        assert ui.confirm("Proceed?", default=True) is False

    def test_ask_returns_answer(self, monkeypatch):
        from unittest.mock import MagicMock

        from dot_man import ui

        fake = MagicMock(return_value="typed!")
        monkeypatch.setattr("dot_man.ui.Prompt.ask", fake)

        assert ui.ask("Name?", default="anon") == "typed!"


class TestSuggestCommand:
    """suggest_command finds close matches and admits defeat."""

    def test_close_match(self):
        from dot_man import ui

        assert ui.suggest_command("stauts", ["status", "deploy"]) == "status"

    def test_no_match(self):
        from dot_man import ui

        assert ui.suggest_command("zzzzqq", ["status", "deploy"]) is None


class TestNextSteps:
    """next_steps() lists guidance, or stays silent when empty."""

    def test_lists_steps(self, capsys):
        from dot_man import ui

        ui.next_steps(["run dot-man status", "then navigate"])

        out = capsys.readouterr().out
        assert "Next Steps" in out
        assert "run dot-man status" in out
        assert "then navigate" in out

    def test_empty_is_silent(self, capsys):
        from dot_man import ui

        ui.next_steps([])

        assert capsys.readouterr().out == ""


class TestSection:
    """section() frames the title and shows content when given."""

    def test_section_with_content(self, capsys):
        from dot_man import ui

        ui.section("Deploy Report", "3 files moved")

        out = capsys.readouterr().out
        assert "Deploy Report" in out
        assert "3 files moved" in out

    def test_section_without_content(self, capsys):
        from dot_man import ui

        ui.section("Empty", "")

        out = capsys.readouterr().out
        assert "Empty" in out
