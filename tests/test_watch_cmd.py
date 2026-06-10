"""Tests for cli/watch_cmd.py — watch command."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.cli.watch_cmd import _PollingWatcher


class FakePollingWatcher:
    """Fake _PollingWatcher that records constructor args and triggers callback."""

    instances: list = []

    def __init__(self, paths, callback, interval=2.0):
        self.paths = paths
        self.callback = callback
        self.interval = interval
        self.instances.append(self)

    def start(self):
        if self.paths:
            self.callback([self.paths[0]])

    def stop(self):
        pass


class TestPollingWatcher:
    """Direct unit tests for _PollingWatcher."""

    def test_constructor_stores_values(self):
        paths = [Path("/a"), Path("/b")]
        cb = MagicMock()
        w = _PollingWatcher(paths, cb, interval=3.0)
        assert w._paths == paths
        assert w._callback == cb
        assert w._interval == 3.0

    def test_collect_files_from_file_paths(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("x")
        f2 = tmp_path / "b.txt"
        f2.write_text("y")
        w = _PollingWatcher([f1, f2], MagicMock())
        files = w._collect_files()
        assert sorted(files) == sorted([f1, f2])

    def test_collect_files_from_directory(self, tmp_path):
        d = tmp_path / "sub"
        d.mkdir()
        f1 = d / "a.txt"
        f1.write_text("x")
        f2 = d / "b.txt"
        f2.write_text("y")
        w = _PollingWatcher([d], MagicMock())
        files = w._collect_files()
        assert sorted(files) == sorted([f1, f2])

    def test_collect_files_mixed_file_and_directory(self, tmp_path):
        f1 = tmp_path / "top.txt"
        f1.write_text("x")
        d = tmp_path / "sub"
        d.mkdir()
        f2 = d / "nested.txt"
        f2.write_text("y")
        w = _PollingWatcher([f1, d], MagicMock())
        files = w._collect_files()
        assert sorted(files) == sorted([f1, f2])

    def test_collect_files_skips_nonexistent(self, tmp_path):
        missing = tmp_path / "missing.txt"
        w = _PollingWatcher([missing], MagicMock())
        assert w._collect_files() == []

    def test_snapshot_captures_mtimes(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("x")
        w = _PollingWatcher([f1], MagicMock())
        snap = w._snapshot()
        assert f1 in snap
        assert isinstance(snap[f1], float)
        assert snap[f1] > 0

    def test_snapshot_handles_oserror_during_stat(self):
        f1 = MagicMock(spec=Path)
        f1.stat.side_effect = OSError("bad")
        w = _PollingWatcher([f1], MagicMock())
        with patch.object(w, "_collect_files", return_value=[f1]):
            snap = w._snapshot()
        assert f1 not in snap

    def test_loop_detects_mtime_change(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("old")
        collected: list[Path] = []
        w = _PollingWatcher([f1], collected.extend, interval=0.01)

        snapshots = [
            {f1: 0.0},  # initial: stale mtime
            {f1: f1.stat().st_mtime},  # current: different mtime
        ]

        def stop_after(_secs):
            w._stop.set()

        with patch.object(w, "_snapshot", side_effect=snapshots):
            with patch("dot_man.cli.watch_cmd.time.sleep", stop_after):
                w._loop()
        assert f1 in collected

    def test_loop_detects_deletion(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("old")
        collected: list[Path] = []
        w = _PollingWatcher([f1], collected.extend, interval=0.01)

        snapshots = [
            {f1: 12345.0},  # initial: file existed
            {},  # current: file gone
        ]

        def stop_after(_secs):
            w._stop.set()

        with patch.object(w, "_snapshot", side_effect=snapshots):
            with patch("dot_man.cli.watch_cmd.time.sleep", stop_after):
                w._loop()
        assert f1 in collected

    def test_loop_does_not_call_callback_when_nothing_changed(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("stable")
        cb = MagicMock()
        w = _PollingWatcher([f1], cb, interval=0.01)

        snapshots = [
            {f1: 100.0},  # initial
            {f1: 100.0},  # current: same mtime
        ]

        def stop_after(_secs):
            w._stop.set()

        with patch.object(w, "_snapshot", side_effect=snapshots):
            with patch("dot_man.cli.watch_cmd.time.sleep", stop_after):
                w._loop()
        cb.assert_not_called()

    def test_start_starts_thread(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("x")
        w = _PollingWatcher([f1], MagicMock(), interval=0.01)
        try:
            w.start()
            assert w._thread.is_alive()
        finally:
            w.stop()
        assert not w._thread.is_alive()

    def test_stop_joins_thread(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f1.write_text("x")
        w = _PollingWatcher([f1], MagicMock(), interval=0.01)
        w.start()
        w.stop()
        assert not w._thread.is_alive()


class TestWatchCommand:
    """Integration tests for the watch CLI command."""

    @pytest.fixture(autouse=True)
    def _clear_fake_instances(self):
        FakePollingWatcher.instances.clear()
        yield

    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "Watch" in result.output or "watch" in result.output
        assert "--interval" in result.output
        assert "--dry-run" in result.output

    def test_warns_no_sections(self, integration_runner):
        result = integration_runner.invoke(cli, ["watch"])
        assert result.exit_code == 0
        assert "No sections configured" in result.output

    def test_dry_run_shows_preview(self, integration_runner, tmp_path):
        from dot_man.operations import reset_operations

        home = tmp_path / "home"
        test_file = home / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("data\n")
        integration_runner.invoke(cli, ["add", str(test_file)])
        reset_operations()

        with ExitStack() as stack:
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._WATCHDOG_AVAILABLE", False)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._PollingWatcher", FakePollingWatcher)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
            )

            result = integration_runner.invoke(cli, ["watch", "--dry-run"])
        assert result.exit_code == 0
        assert "Would save" in result.output

    def test_interval_passed_to_watcher(self, integration_runner, tmp_path):
        from dot_man.operations import reset_operations

        home = tmp_path / "home"
        test_file = home / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("data\n")
        integration_runner.invoke(cli, ["add", str(test_file)])
        reset_operations()

        with ExitStack() as stack:
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._WATCHDOG_AVAILABLE", False)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._PollingWatcher", FakePollingWatcher)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
            )

            result = integration_runner.invoke(cli, ["watch", "--interval", "5.0"])
        assert result.exit_code == 0
        assert FakePollingWatcher.instances[-1].interval == 5.0

    def test_no_commit_skips_git_commit(self, integration_runner, tmp_path):
        from dot_man.core import GitManager
        from dot_man.operations import reset_operations

        home = tmp_path / "home"
        test_file = home / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("v1\n")
        integration_runner.invoke(cli, ["add", str(test_file)])
        test_file.write_text("v2\n")
        reset_operations()

        git = GitManager()
        commits_before = len(list(git.repo.iter_commits(max_count=10)))

        with ExitStack() as stack:
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._WATCHDOG_AVAILABLE", False)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._PollingWatcher", FakePollingWatcher)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
            )

            result = integration_runner.invoke(cli, ["watch", "--no-commit"])
        assert result.exit_code == 0

        commits_after = len(list(git.repo.iter_commits(max_count=10)))
        assert commits_after == commits_before

    def test_custom_message_prefix(self, integration_runner, tmp_path):
        from dot_man.core import GitManager
        from dot_man.operations import reset_operations

        home = tmp_path / "home"
        test_file = home / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("v1\n")
        integration_runner.invoke(cli, ["add", str(test_file)])
        test_file.write_text("v2\n")
        reset_operations()

        with ExitStack() as stack:
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._WATCHDOG_AVAILABLE", False)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd._PollingWatcher", FakePollingWatcher)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
            )

            result = integration_runner.invoke(cli, ["watch", "--message", "wip: "])
        assert result.exit_code == 0

        git = GitManager()
        last = git.repo.head.commit
        assert "wip:" in last.message
