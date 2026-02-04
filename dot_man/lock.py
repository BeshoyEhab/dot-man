"""File locking mechanism to prevent concurrent operations."""

from __future__ import annotations
import fcntl
import os
import contextlib
from pathlib import Path
from typing import IO, Optional, Generator

from .exceptions import DotManError

class LockError(DotManError):
    """Raised when a lock cannot be acquired."""
    pass

class FileLock:
    """
    Context manager for advisory file locking using fcntl.
    
    Ensures that only one process can perform critical operations (like deploy/save)
    at a time. Fails fast if the lock is held by another process.
    """

    def __init__(self, lock_file: Path) -> None:
        self.lock_file = lock_file
        self._fd: Optional[IO] = None

    def __enter__(self) -> None:
        """Acquire the lock."""
        # Ensure directory exists
        if not self.lock_file.parent.exists():
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._fd = open(self.lock_file, "w")
            # LOCK_EX: Exclusive lock
            # LOCK_NB: Non-blocking (fail if locked)
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Lock is held by another process
            if self._fd:
                self._fd.close()
            raise LockError(f"Could not acquire lock on {self.lock_file}. Is another dot-man process running?")
        except OSError as e:
            if self._fd:
                self._fd.close()
            raise LockError(f"Failed to lock {self.lock_file}: {e}")

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release the lock."""
        if self._fd:
            try:
                # unlocking happens automatically on close, but being explicit is good
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass  # Ignore errors during unlock/close
            finally:
                self._fd.close()
                self._fd = None
