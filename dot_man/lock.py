"""File locking mechanism to prevent concurrent operations."""

from __future__ import annotations

__all__ = ["FileLock", "LockError"]
import fcntl
import threading
import time
from pathlib import Path
from typing import IO, Optional

from .exceptions import DotManError


class LockError(DotManError):
    """Raised when a lock cannot be acquired."""

    pass


class FileLock:
    """
    Context manager for advisory file locking using fcntl.

    Ensures that only one process can perform critical operations (like
    deploy/save) at a time. Waits (blocking, up to ``timeout``) for a lock
    held by another process before giving up.

    Locks are reentrant *within a thread* for the same path: a transaction
    that wraps several operations which each take the same lock (e.g.
    navigate wrapping save + deploy) does not deadlock against itself.
    """

    _local = threading.local()

    def __init__(
        self,
        lock_file: Path,
        timeout: float = 10.0,
        poll_interval: float = 0.05,
    ) -> None:
        self.lock_file = lock_file
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fd: Optional[IO] = None
        self._reentrant = False

    def _held(self) -> dict:
        held = getattr(self._local, "held", None)
        if held is None:
            held = {}
            self._local.held = held
        return held

    def __enter__(self) -> "FileLock":
        """Acquire the lock, waiting up to ``timeout`` seconds."""
        key = str(self.lock_file)
        held = self._held()
        if key in held:
            held[key] += 1
            self._reentrant = True
            return self

        # Ensure directory exists
        if not self.lock_file.parent.exists():
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            fd = open(self.lock_file, "w")
        except OSError as e:
            raise LockError(f"Failed to lock {self.lock_file}: {e}")

        deadline = time.monotonic() + self.timeout
        while True:
            try:
                # LOCK_EX: Exclusive lock; LOCK_NB: don't block in the kernel,
                # we poll so we can enforce our own timeout.
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    fd.close()
                    raise LockError(
                        f"Could not acquire lock on {self.lock_file}. "
                        "Is another dot-man process running?"
                    )
                time.sleep(self.poll_interval)
            except OSError as e:
                fd.close()
                raise LockError(f"Failed to lock {self.lock_file}: {e}")

        self._fd = fd
        held[key] = 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Release the lock."""
        key = str(self.lock_file)
        held = self._held()

        if self._reentrant:
            self._reentrant = False
            if key in held:
                held[key] -= 1
                if held[key] <= 0:
                    held.pop(key, None)
            return

        if self._fd:
            try:
                # unlocking happens automatically on close, but being explicit is good
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass  # Ignore errors during unlock/close
            finally:
                self._fd.close()
                self._fd = None
        held.pop(key, None)
