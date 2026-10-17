"""Tests for cli/watch_cmd.py — watch command."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.cli.watch_cmd import _PollingWatcher
from dot_man.exceptions import DotManError


def _wait_for_flush(collected, timeout=5.0):
    """Wait for the debounced handler callback to fire."""
    import time

    deadline = time.time() + timeout
    while not collected and time.time() < deadline:
        time.sleep(0.05)


class ManualTimer:
    """threading.Timer replacement that only fires when told to."""

    instances: list = []

    def __init__(self, secs, fn):
        self._fn = fn
        self.daemon = True
        self.cancelled = False
        ManualTimer.instances.append(self)

    def cancel(self):
        self.cancelled = True

    def start(self):
        pass

    def fire(self):
        self._fn()


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


def _make_watch_file(integration_runner, tmp_path, name=".testrc", content="data\n"):
    """Add a tracked file and return its path."""
    from dot_man.operations import reset_operations

    home = tmp_path / "home"
    test_file = home / name
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(content)
    integration_runner.invoke(cli, ["add", str(test_file)])
    reset_operations()
    return test_file


def _run_watch_polling(integration_runner, args):
    """Invoke watch with the polling backend faked out."""
    with ExitStack() as stack:
        stack.enter_context(patch("dot_man.cli.watch_cmd._WATCHDOG_AVAILABLE", False))
        stack.enter_context(
            patch("dot_man.cli.watch_cmd._PollingWatcher", FakePollingWatcher)
        )
        stack.enter_context(
            patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
        )
        return integration_runner.invoke(cli, ["watch", *args])


class TestDotManEventHandler:
    """Direct tests for the watchdog _DotManEventHandler."""

    def _make_handler(self, tmp_path, tracked):
        pytest.importorskip("watchdog")
        from dot_man.cli.watch_cmd import _DotManEventHandler

        collected: list = []
        handler = _DotManEventHandler(tracked, collected.extend)
        return handler, collected

    def _event(self, path, is_dir=False):
        from types import SimpleNamespace

        return SimpleNamespace(src_path=str(path), is_directory=is_dir)

    def test_is_tracked_exact_file(self, tmp_path):
        handler, _ = self._make_handler(tmp_path, [tmp_path / "a.txt"])
        assert handler._is_tracked(str(tmp_path / "a.txt"))
        assert not handler._is_tracked(str(tmp_path / "other.txt"))

    def test_is_tracked_nested_under_directory(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        handler, _ = self._make_handler(tmp_path, [tmp_path])
        assert handler._is_tracked(str(sub / "nested.txt"))

    def test_on_modified_triggers_callback(self, tmp_path):
        target = tmp_path / "a.txt"
        target.write_text("x")
        handler, collected = self._make_handler(tmp_path, [target])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_modified(self._event(target))
        _wait_for_flush(collected)
        assert collected == [target]

    def test_on_modified_ignores_directories(self, tmp_path):
        handler, collected = self._make_handler(tmp_path, [tmp_path])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_modified(self._event(tmp_path, is_dir=True))
        _wait_for_flush(collected, timeout=0.3)
        assert collected == []

    def test_on_modified_ignores_untracked(self, tmp_path):
        handler, collected = self._make_handler(tmp_path, [tmp_path / "a.txt"])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_modified(self._event(tmp_path / "nope.txt"))
        _wait_for_flush(collected, timeout=0.3)
        assert collected == []

    def test_on_created_triggers_callback(self, tmp_path):
        target = tmp_path / "new.txt"
        target.write_text("x")
        handler, collected = self._make_handler(tmp_path, [target])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_created(self._event(target))
        _wait_for_flush(collected)
        assert collected == [target]

    def test_on_created_ignores_directories(self, tmp_path):
        handler, collected = self._make_handler(tmp_path, [tmp_path])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_created(self._event(tmp_path, is_dir=True))
        _wait_for_flush(collected, timeout=0.3)
        assert collected == []

    def test_on_deleted_triggers_callback(self, tmp_path):
        target = tmp_path / "gone.txt"
        handler, collected = self._make_handler(tmp_path, [target])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_deleted(self._event(target))
        _wait_for_flush(collected)
        assert collected == [target]

    def test_on_deleted_ignores_untracked(self, tmp_path):
        handler, collected = self._make_handler(tmp_path, [tmp_path / "a.txt"])
        handler.DEBOUNCE_SECONDS = 0.05
        handler.on_deleted(self._event(tmp_path / "elsewhere.txt"))
        _wait_for_flush(collected, timeout=0.3)
        assert collected == []

    def test_debounce_cancels_previous_timer(self, tmp_path):
        ManualTimer.instances.clear()
        target = tmp_path / "a.txt"
        target.write_text("x")
        handler, collected = self._make_handler(tmp_path, [target])
        with patch("threading.Timer", ManualTimer):
            handler.on_modified(self._event(target))
            handler.on_modified(self._event(target))
        assert len(ManualTimer.instances) == 2
        assert ManualTimer.instances[0].cancelled
        assert not ManualTimer.instances[1].cancelled
        ManualTimer.instances[1].fire()
        assert collected == [target]
        ManualTimer.instances.clear()

    def test_flush_without_pending_does_nothing(self, tmp_path):
        handler, collected = self._make_handler(tmp_path, [tmp_path])
        handler._flush()
        assert collected == []


class TestWatchNoPaths:
    """Test watch with sections that track nothing."""

    def test_warns_no_paths_to_watch(self, integration_runner):
        from unittest.mock import MagicMock

        from dot_man.operations import reset_operations

        section = MagicMock()
        section.paths = []
        ops = MagicMock()
        ops.get_sections.return_value = ["empty"]
        ops.get_section.return_value = section
        reset_operations()
        with patch("dot_man.operations.get_operations", return_value=ops):
            result = integration_runner.invoke(cli, ["watch"])
        assert result.exit_code == 0
        assert "No paths to watch" in result.output


class TestWatchSymlinks:
    """Test watch symlink scanning and save warnings."""

    def test_symlink_paths_warn(self, integration_runner, tmp_path):
        _make_watch_file(integration_runner, tmp_path, name=".normalrc")
        link_target = tmp_path / "home" / ".realrc"
        link_target.write_text("real\n")
        linked = _make_watch_file(integration_runner, tmp_path, name=".linkedrc")
        linked.unlink()
        linked.symlink_to(link_target)

        with patch("dot_man.interactive.prompt_symlink_action", return_value="ignore"):
            result = _run_watch_polling(integration_runner, [])
        assert result.exit_code == 0
        assert "symlink" in result.output


class TestWatchOnChangeBranches:
    """Test on_change save/commit/error branches through the CLI."""

    def test_reports_secrets_redacted_and_commits(self, integration_runner, tmp_path):
        test_file = _make_watch_file(integration_runner, tmp_path)
        test_file.write_text("key = AKIAIOSFODNN7REALKEY1\n")
        result = _run_watch_polling(integration_runner, [])
        assert result.exit_code == 0
        assert "secret(s) redacted" in result.output
        assert "committed" in result.output

    def test_reports_save_errors(self, integration_runner, tmp_path):
        from dot_man.operations import get_operations

        _make_watch_file(integration_runner, tmp_path)
        ops = get_operations()
        with patch.object(
            ops,
            "save_all",
            return_value={
                "saved": 1,
                "secrets": [],
                "errors": ["copy boom"],
                "symlinks": [],
            },
        ):
            result = _run_watch_polling(integration_runner, [])
        assert result.exit_code == 0
        assert "copy boom" in result.output

    def test_save_dotman_error_warns(self, integration_runner, tmp_path):
        from dot_man.operations import get_operations

        _make_watch_file(integration_runner, tmp_path)
        ops = get_operations()
        with patch.object(ops, "save_all", side_effect=DotManError("save exploded")):
            result = _run_watch_polling(integration_runner, [])
        assert result.exit_code == 0
        assert "Save failed" in result.output

    def test_save_unexpected_error_warns(self, integration_runner, tmp_path):
        from dot_man.operations import get_operations

        _make_watch_file(integration_runner, tmp_path)
        ops = get_operations()
        with patch.object(ops, "save_all", side_effect=RuntimeError("weird")):
            result = _run_watch_polling(integration_runner, [])
        assert result.exit_code == 0
        assert "Unexpected error" in result.output


class TestWatchObserverBackend:
    """Test the watchdog observer startup path."""

    def test_observer_schedules_and_stops(self, integration_runner, tmp_path):
        pytest.importorskip("watchdog")
        from unittest.mock import MagicMock

        _make_watch_file(integration_runner, tmp_path)
        mock_observer = MagicMock()
        with ExitStack() as stack:
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.Observer", return_value=mock_observer)
            )
            stack.enter_context(
                patch("dot_man.cli.watch_cmd.time.sleep", side_effect=KeyboardInterrupt)
            )
            result = integration_runner.invoke(cli, ["watch"])
        assert result.exit_code == 0
        assert mock_observer.schedule.called
        assert mock_observer.start.called
        assert mock_observer.stop.called
        assert mock_observer.join.called
        assert "Stopped" in result.output


class TestWatchSecretAudit:
    """S13: redacted secrets must leave a visible audit trail."""

    def test_watch_reports_redacted_secrets(self, integration_runner, tmp_path):
        from dot_man.operations import reset_operations

        test_file = _make_watch_file(integration_runner, tmp_path)
        test_file.write_text("key = AKIAIOSFODNN7REALKEY1\n")
        reset_operations()

        result = _run_watch_polling(integration_runner, ["--no-commit"])

        assert result.exit_code == 0, result.output
        assert "AWS Access Key ID" in result.output
        assert "Secrets were detected" in result.output
        # The live secret value must never be echoed.
        assert "AKIAIOSFODNN7REALKEY1" not in result.output


class TestWatchTopLevelErrors:
    """Test watch command-level error handling."""

    def test_dotman_error_exits(self, integration_runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=DotManError("no repo here"),
        ):
            result = integration_runner.invoke(cli, ["watch"])
        assert result.exit_code != 0
        assert "no repo here" in result.output

    def test_unexpected_error_exits(self, integration_runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=RuntimeError("total meltdown"),
        ):
            result = integration_runner.invoke(cli, ["watch"])
        assert result.exit_code != 0
        assert "Watch failed" in result.output
