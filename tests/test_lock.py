"""Tests for file locking mechanism."""

import threading
import time

import pytest

from dot_man.lock import FileLock, LockError
from dot_man.operations import get_operations


def test_lock_acquire_release(tmp_path):
    """Test basic lock acquisition and release."""
    lock_path = tmp_path / ".lock"
    lock = FileLock(lock_path)

    with lock:
        assert lock_path.exists()
        # Verify we can write to it
        assert lock._fd is not None

    # Verify lock is released (we can acquire it again)
    with lock:
        pass


def test_lock_concurrency(tmp_path):
    """Test that second acquisition fails when lock is held."""
    lock_path = tmp_path / ".lock"

    def hold_lock():
        with FileLock(lock_path):
            time.sleep(0.5)

    # Start thread holding lock
    t = threading.Thread(target=hold_lock)
    t.start()

    # Wait for thread to acquire lock
    time.sleep(0.1)

    # Try to acquire lock - should fail
    with pytest.raises(LockError, match="Could not acquire lock"):
        with FileLock(lock_path):
            pass

    t.join()


def test_operations_lock_integration(monkeypatch, tmp_path):
    """Verify operations allow successful execution with lock."""
    import dot_man.operations
    import dot_man.save_deploy_ops

    # Track whether lock was used
    lock_used = {"entered": False, "exited": False}

    class TrackedLock:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            lock_used["entered"] = True

        def __exit__(self, *args):
            lock_used["exited"] = True

    # Get operations instance and patch FileLock in save_deploy_ops where it's actually used
    op = get_operations()
    monkeypatch.setattr(dot_man.save_deploy_ops, "FileLock", TrackedLock)

    # Mock get_sections to return empty to avoid config loading issues
    monkeypatch.setattr(op, "get_sections", lambda: {})

    # Run save_all - should use the lock
    result = op.save_all()

    # Verify lock was used
    assert lock_used["entered"], "FileLock was not entered"
    assert lock_used["exited"], "FileLock was not exited"

    # Verify result structure
    assert "saved" in result
    assert "secrets" in result
    assert "errors" in result
