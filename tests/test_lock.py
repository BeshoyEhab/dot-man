"""Tests for lock module."""


class TestFileLock:
    """Test FileLock class."""

    def test_file_lock_init(self, tmp_path):
        """Test FileLock initialization."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        assert lock.lock_file == lock_path

    def test_file_lock_context(self, tmp_path):
        """Test FileLock as context manager."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        assert hasattr(lock, "__enter__")
        assert hasattr(lock, "__exit__")

    def test_file_lock_acquire_release(self, tmp_path):
        """Test FileLock acquire and release."""
        from dot_man.lock import FileLock

        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        lock.__enter__()
        lock.__exit__(None, None, None)
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
