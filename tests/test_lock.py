"""Tests for lock module."""

import fcntl
from unittest.mock import patch

import pytest


class TestFileLock:
    """Test FileLock class."""

    def test_file_lock_init(self, tmp_path):
        """Test FileLock initialization."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        assert lock.lock_file == lock_path

    def test_file_lock_context(self, tmp_path):
        """Context manager holds the fd inside and releases after."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        with lock:
            assert lock._fd is not None
        assert lock._fd is None

    def test_file_lock_acquire_release(self, tmp_path):
        """Test FileLock acquire and release."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        lock.__enter__()
        lock.__exit__(None, None, None)
        assert lock._fd is None


class TestFileLockEdgeCases:
    """Uncovered paths: missing dirs, contention, IO failures."""

    def test_creates_missing_parent_dir(self, tmp_path):
        """Lock file in a missing directory creates parents on acquire."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "nested" / "dir" / "test.lock"
        lock = FileLock(lock_path)
        with lock:
            assert lock_path.exists()
        assert lock._fd is None

    def test_second_holder_gets_lock_error(self, tmp_path):
        """Real fcntl contention surfaces as LockError with fd cleanup."""
        from dot_man.lock import LockError

        lock_path = tmp_path / "test.lock"
        lock_path.write_text("")

        holder = open(lock_path, "w")
        try:
            fcntl.flock(holder, fcntl.LOCK_EX)

            from dot_man.lock import FileLock

            lock = FileLock(lock_path, timeout=0.05)
            with pytest.raises(LockError, match="another dot-man process"):
                lock.__enter__()
            assert lock._fd is None

            # Once the holder releases, the same lock acquires fine.
            fcntl.flock(holder, fcntl.LOCK_UN)
            with lock:
                assert lock._fd is not None
        finally:
            holder.close()

    def test_open_failure_raises_lock_error(self, tmp_path):
        """Unopenable lock file raises LockError without a dangling fd."""
        from dot_man.lock import FileLock, LockError

        lock = FileLock(tmp_path / "test.lock")
        with patch("builtins.open", side_effect=OSError("denied")):
            with pytest.raises(LockError, match="Failed to lock"):
                lock.__enter__()
        assert lock._fd is None

    def test_flock_oserror_closes_fd(self, tmp_path):
        """flock OSError (not contention) closes the opened fd, then raises."""
        from dot_man.lock import FileLock, LockError

        lock = FileLock(tmp_path / "test.lock")
        with patch.object(fcntl, "flock", side_effect=OSError("flock denied")):
            with pytest.raises(LockError, match="Failed to lock"):
                lock.__enter__()
        assert lock._fd is None

    def test_unlock_failure_ignored(self, tmp_path):
        """OSError during unlock is swallowed; fd still closed."""
        import fcntl as fcntl_mod

        from dot_man.lock import FileLock

        real_flock = fcntl_mod.flock

        def _fail_unlock(fd, op):
            if op == fcntl_mod.LOCK_UN:
                raise OSError("unlock denied")
            return real_flock(fd, op)

        lock = FileLock(tmp_path / "test.lock")
        with patch.object(fcntl_mod, "flock", side_effect=_fail_unlock):
            with lock:
                assert lock._fd is not None
        assert lock._fd is None


class TestLockError:
    """Test LockError exception."""

    def test_lock_error(self):
        """Test LockError can be raised."""
        from dot_man.exceptions import DotManError
        from dot_man.lock import LockError

        error = LockError("Lock failed")
        assert isinstance(error, DotManError)
        assert "Lock" in str(error)


class TestFileLockRetryAndReentrancy:
    """S11: wait for a contended lock; reentrant within a thread."""

    def test_waits_for_contended_lock(self, tmp_path):
        import threading
        import time

        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        acquired = threading.Event()

        def hold():
            with FileLock(lock_path):
                acquired.set()
                time.sleep(0.2)

        thread = threading.Thread(target=hold)
        thread.start()
        acquired.wait(timeout=2.0)

        waiter = FileLock(lock_path, timeout=2.0)
        with waiter:
            assert waiter._fd is not None
        thread.join()

    def test_times_out_and_raises(self, tmp_path):
        import threading
        import time

        from dot_man.lock import FileLock, LockError

        lock_path = tmp_path / "test.lock"
        acquired = threading.Event()

        def hold():
            with FileLock(lock_path):
                acquired.set()
                time.sleep(0.5)

        thread = threading.Thread(target=hold)
        thread.start()
        acquired.wait(timeout=2.0)

        with pytest.raises(LockError):
            FileLock(lock_path, timeout=0.05).__enter__()
        thread.join()

    def test_reentrant_same_thread(self, tmp_path):
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        outer = FileLock(lock_path)
        with outer:
            inner = FileLock(lock_path)
            with inner:
                assert outer._fd is not None
                assert inner._reentrant is True
            assert outer._fd is not None
        assert outer._fd is None
