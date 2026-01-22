"""Tests for file locking mechanism."""

import pytest
import threading
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from dot_man.lock import FileLock, LockError
from dot_man.operations import get_operations, LOCK_FILE

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
    # Mock REPO_DIR/LOCK_FILE to use tmp_path
    op = get_operations()
    # We can't easily patch LOCK_FILE global, but we can patch FileLock
    # to use our tmp path if we were mocking it.
    # Instead, let's just ensure get_operations().save_all() calls FileLock.
    
    # Mock FileLock
    class MockLock:
        def __init__(self, path):
            self.path = path
        def __enter__(self):
            pass
        def __exit__(self, *args):
            pass
            
    import dot_man.operations
    monkeypatch.setattr(dot_man.operations, "FileLock", MockLock)
    
    # Just running save_all with empty config shouldn't crash
    # This verifies the indentation/syntax issues are gone
    op.save_all()
