"""Utility functions for dot-man."""

import os
import shutil
import subprocess
from pathlib import Path


def get_editor() -> str:
    """Get the user's preferred text editor.

    Returns:
        Editor command name
    """
    # Priority order: VISUAL, EDITOR, fallbacks
    for env_var in ("VISUAL", "EDITOR"):
        editor = os.environ.get(env_var)
        if editor:
            return editor

    # Fallback to common editors
    for editor in ("nano", "vim", "vi", "notepad"):
        if shutil.which(editor):
            return editor

    return "nano"


def open_in_editor(path: Path, editor: str | None = None) -> bool:
    """Open a file in the text editor.

    Returns:
        True if editor exited successfully, False otherwise
    """
    editor = editor or get_editor()

    try:
        result = subprocess.run([editor, str(path)])
        return result.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size.

    Args:
        size_bytes: Size in bytes (int or float)

    Returns:
        Human-readable size string (e.g., "2.3 MB")
    """
    size_num = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size_num) < 1024:
            return f"{size_num:.1f} {unit}"
        size_num /= 1024
    return f"{size_num:.1f} PB"


def get_directory_size(path: Path) -> int:
    """Get the total size of a directory in bytes."""
    if not path.exists():
        return 0

    if path.is_file():
        return path.stat().st_size

    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except (OSError, PermissionError):
                pass
    return total


def count_files(path: Path) -> int:
    """Count files in a directory (recursively)."""
    if not path.exists():
        return 0
    if path.is_file():
        return 1

    count = 0
    for item in path.rglob("*"):
        if item.is_file():
            count += 1
    return count


def confirm(prompt: str, default: bool = False) -> bool:
    """Ask for user confirmation.

    Args:
        prompt: The question to ask
        default: Default value if user just presses Enter

    Returns:
        True if user confirmed, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"

    try:
        response = input(prompt + suffix + " ").strip().lower()
        if not response:
            return default
        return response in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def is_git_installed() -> bool:
    """Check if git is installed and available."""
    return shutil.which("git") is not None


def get_hostname() -> str:
    """Get the system hostname."""
    import socket

    return socket.gethostname()


def get_username() -> str:
    """Get the current username."""
    import getpass

    return getpass.getuser()
