"""Tests for cli/common.py — parse_branch_arg, completions, require_init."""

from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestParseBranchArg:
    """Test parse_branch_arg with various input formats."""

    def test_simple_branch(self):
        from dot_man.cli.common import parse_branch_arg

        with patch("dot_man.cli.common.GitManager") as MockGM:
            mock_gm = MockGM.return_value
            mock_gm.list_tags.return_value = []
            result = parse_branch_arg("main")
        assert result["type"] == "branch"
        assert result["target"] == "main"

    def test_tag_format(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main@v1.0")
        assert result["type"] == "tag"
        assert result["base"] == "main"
        assert result["target"] == "v1.0"

    def test_commit_sha(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abcdef1")
        assert result["type"] == "commit"
        assert result["target"] == "abcdef1"

    def test_full_commit_sha(self):
        from dot_man.cli.common import parse_branch_arg

        sha = "a" * 40
        result = parse_branch_arg(sha)
        assert result["type"] == "commit"
        assert result["target"] == sha

    def test_branch_at_commit(self):
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("main@abcdef1")
        assert result["type"] == "commit"
        assert result["base"] == "main"
        assert result["target"] == "abcdef1"


class TestRequireInit:
    """Test the require_init decorator."""

    def test_require_init_no_dir(self, tmp_path):
        fake_dir = tmp_path / "nonexistent"
        runner = CliRunner()
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", fake_dir / "repo"),
        ):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code == 1
            assert "init" in result.output.lower()

    def test_require_init_dir_exists_no_git(self, tmp_path):
        fake_dir = tmp_path / "dotman"
        fake_dir.mkdir()
        repo_dir = fake_dir / "repo"
        repo_dir.mkdir()
        # No .git directory
        runner = CliRunner()
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", repo_dir),
        ):
            result = runner.invoke(cli, ["status"])
            assert result.exit_code != 0


class TestCompletionCaching:
    """Test completion cache operations."""

    def test_clear_all_caches(self):
        from dot_man.cli.common import _clear_all_caches

        _clear_all_caches()
        # Should not raise

    def test_clear_completion_cache(self):
        from dot_man.cli.common import _clear_completion_cache

        _clear_completion_cache()
        # Should not raise


class TestHandleException:
    """Test centralized exception handler."""

    def test_handle_dotman_error(self):
        from dot_man.cli.common import handle_exception
        from dot_man.exceptions import DotManError

        # DotManError calls ui.error which calls SystemExit
        with pytest.raises(SystemExit):
            handle_exception(DotManError("test error", exit_code=2))

    def test_handle_keyboard_interrupt(self, capsys):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit) as exc_info:
            handle_exception(KeyboardInterrupt())
        assert exc_info.value.code == 130

    def test_handle_generic_exception(self):
        from dot_man.cli.common import handle_exception

        with pytest.raises(SystemExit):
            handle_exception(RuntimeError("something broke"))


class TestDotManGroup:
    """Test custom Click group with command suggestions."""

    def test_unknown_command_suggestion(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["statsu"])
        assert result.exit_code != 0

    def test_unknown_command_no_match(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["zzzznonexistent"])
        assert result.exit_code != 0


class TestErrorSuccessWarn:
    """Test error/success/warn helpers."""

    def test_success_helper(self):
        from dot_man.cli.common import success

        success("test message")

    def test_warn_helper(self):
        from dot_man.cli.common import warn

        warn("test warning")


# ─── coverage floor: handle_exception zero-exit, command decorator,
#     help skip, shared-sync reporting, tag-check failure,
#     secret-handler branches ───────────────────────────────────────


def test_handle_exception_dotman_error_zero_exit_prints_only(capsys):
    """DotManError(exit_code=0) takes the print-only path and returns."""
    from dot_man.cli.common import handle_exception
    from dot_man.exceptions import DotManError

    handle_exception(DotManError("all good", exit_code=0), "Test")

    captured = capsys.readouterr()
    assert "all good" in captured.out + captured.err


def test_command_decorator_builds_click_command():
    from dot_man.cli.common import command

    @command(name="demo-cmd")
    def demo():
        """Demo command."""
        pass

    assert isinstance(demo, click.Command)
    assert demo.name == "demo-cmd"
    result = CliRunner().invoke(demo, [])
    assert result.exit_code == 0


def test_help_skips_hidden_commands():
    """A hidden HAPPY_PATH entry is skipped by the short help listing (163)."""
    from dot_man.cli import common

    hidden_cmd = click.Command("hidden-thing", help="Hidden helper")
    hidden_cmd.hidden = True
    cli.add_command(hidden_cmd)
    try:
        with patch.object(common, "HAPPY_PATH_COMMANDS", ("hidden-thing",)):
            result = CliRunner().invoke(cli, ["--help"])
    finally:
        cli.commands.pop("hidden-thing", None)

    assert result.exit_code == 0
    assert "hidden-thing" not in result.output
    assert "help-all" in result.output


def test_sync_shared_sections_reports_propagation_and_errors(capsys):
    from dot_man.cli import common
    from dot_man.shared_sync import SharedSyncReport

    report = SharedSyncReport(
        shared_sections=["fish"],
        propagated={"server": ["fish"]},
        errors={"work": "boom"},
    )

    class FakeSync:
        def __init__(self, ops):
            pass

        def sync(self):
            return report

    with patch("dot_man.shared_sync.SharedSectionSync", FakeSync):
        common.sync_shared_sections(object())

    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "shared → 'server': fish" in out
    assert "Shared-section sync failed for 'work': boom" in out


def test_sync_shared_sections_swallows_import_errors(caplog):
    import logging as _logging

    from dot_man.cli import common

    caplog.set_level(_logging.DEBUG)

    with patch(
        "dot_man.shared_sync.SharedSectionSync",
        side_effect=RuntimeError("sync dead"),
    ):
        common.sync_shared_sections(object())

    assert "Shared-section sync skipped" in caplog.text


def test_parse_branch_arg_tag_lookup_failure_falls_back(caplog):
    import logging as _logging

    from dot_man.cli import common

    caplog.set_level(_logging.DEBUG)

    with patch("dot_man.cli.common.GitManager", side_effect=RuntimeError("no repo")):
        result = common.parse_branch_arg("some-branch")

    assert result == {"type": "branch", "base": "some-branch", "target": "some-branch"}
    assert "Could not check tags" in caplog.text


class TestSecretHandlerBranches:
    """Choice branches of get_secret_handler's prompt loop."""

    @staticmethod
    def _match():
        from pathlib import Path

        from dot_man.secrets import SecretMatch, Severity

        return SecretMatch(
            file=Path("f.txt"),
            line_number=1,
            line_content="secret-line",
            pattern_name="Private Key",
            severity=Severity.HIGH,
            matched_text="secret-line",
        )

    @staticmethod
    def _make_handler(tmp_path, monkeypatch):
        from dot_man.cli.common import get_secret_handler

        monkeypatch.setattr("dot_man.secrets.DOT_MAN_DIR", tmp_path)
        return get_secret_handler()

    def test_choice_one_ignores(self, tmp_path, monkeypatch):
        handler = self._make_handler(tmp_path, monkeypatch)
        with patch("dot_man.ui.ask", return_value="1"):
            assert handler(self._match()) == "IGNORE"

    def test_choice_three_allows_then_short_circuits(
        self, tmp_path, monkeypatch, capsys
    ):
        handler = self._make_handler(tmp_path, monkeypatch)
        match = self._match()

        with patch("dot_man.ui.ask", return_value="3"):
            assert handler(match) == "IGNORE"
        assert "Added to skip list." in capsys.readouterr().out

        # Second pass hits the allow-list short circuit (no prompt).
        assert handler(match) == "IGNORE"
        assert not capsys.readouterr().out

    def test_choice_four_redacts_then_short_circuits(
        self, tmp_path, monkeypatch, capsys
    ):
        handler = self._make_handler(tmp_path, monkeypatch)
        match = self._match()

        with patch("dot_man.ui.ask", return_value="4"):
            assert handler(match) == "REDACT"
        assert "Will always redact this secret." in capsys.readouterr().out

        assert handler(match) == "REDACT"
        assert not capsys.readouterr().out

    def test_invalid_choice_defaults_to_redact(self, tmp_path, monkeypatch):
        handler = self._make_handler(tmp_path, monkeypatch)
        with patch("dot_man.ui.ask", return_value="9"):
            assert handler(self._match()) == "REDACT"
