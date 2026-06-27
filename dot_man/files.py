"""File operations for dot-man."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Callable

from .secrets import (
    SecretMatch,
    filter_secrets,
)
from .utils import sha256_hex

__all__ = [
    "atomic_write_text",
    "smart_save_file",
    "copy_file",
    "copy_directory",
    "compare_files",
    "get_file_status",
    "matches_patterns",
    "backup_file",
    "ensure_directory",
    "clear_comparison_cache",
    "get_content_hash",
    "create_symlink",
    "deploy_file_or_symlink",
    "deploy_directory_with_symlinks",
]


def get_content_hash(content: str) -> str:
    """Get SHA256 hash of content for deduplication."""
    return sha256_hex(content)


def _get_secret_guard():
    """Lazy load SecretGuard only when needed."""
    from .secrets import SecretGuard

    return SecretGuard()


def _get_redact_guard():
    """Lazy load PermanentRedactGuard only when needed."""
    from .secrets import PermanentRedactGuard

    return PermanentRedactGuard()


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to a file atomically using a temporary file.

    Ensures line endings are preserved exactly as in content (using newline="").
    """
    # Create temp file in same directory to ensure atomic rename
    temp_path = path.with_suffix(f"{path.suffix}.tmp")

    try:
        with temp_path.open("w", encoding=encoding, newline="") as f:
            f.write(content)

        # Atomic rename
        os.replace(temp_path, path)
    except OSError:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def smart_save_file(
    src_path: Path,
    dest_path: Path,
    secret_handler: Callable[[SecretMatch], str] | None = None,
    check_secrets: bool = True,
) -> tuple[bool, list[SecretMatch]]:
    """Smartly save a file from source to destination.

    1. Reads source file once.
    2. Filters secrets (if enabled).
    3. Compares result with destination.
    4. Atomically writes if different.

    Returns:
        tuple(saved: bool, secrets: list[SecretMatch])
    """
    detected_secrets: list[SecretMatch] = []

    if not src_path.is_file():
        return False, []

    # 1. Read source
    try:
        with src_path.open("r", encoding="utf-8", newline="") as f:
            src_content = f.read()
    except (UnicodeDecodeError, OSError):
        # Binary file or read error - fallback to direct copy if different
        return _handle_binary_copy(src_path, dest_path, check_secrets)

    # 2. Filter secrets (lazy load guards only when needed)
    final_content = src_content
    detected_secrets = []
    if check_secrets:
        # Use lazy-loaded guards
        allow_guard = _get_secret_guard()
        redact_guard = _get_redact_guard()

        def wrapped_handler(match: SecretMatch) -> str:
            # Check allow list first
            if allow_guard.is_allowed(src_path, match.line_content, match.pattern_name):
                return "IGNORE"

            # Check permanent redact list
            if redact_guard.should_redact(
                src_path, match.line_content, match.pattern_name
            ):
                return "REDACT"

            # Delegate to user handler
            if secret_handler:
                return secret_handler(match)
            return "REDACT"

        final_content, detected_secrets = filter_secrets(
            src_content, callback=wrapped_handler, file_path=src_path
        )

    # 3. Compare with destination
    should_save = True
    if dest_path.is_file():
        try:
            # Check permissions first
            src_stat = src_path.stat()
            dest_stat = dest_path.stat()
            if src_stat.st_mode != dest_stat.st_mode:
                should_save = True
            else:
                # Compare content
                with dest_path.open("r", encoding="utf-8", newline="") as f:
                    dest_content = f.read()

                if final_content == dest_content:
                    should_save = False

        except (UnicodeDecodeError, OSError):
            should_save = True  # Assume changed if can't read dest

    # 4. Atomic Write if needed
    if should_save:
        ensure_directory(dest_path.parent)
        atomic_write_text(dest_path, final_content)
        # Copy permissions
        try:
            dest_path.chmod(src_path.stat().st_mode)
        except OSError:
            pass

    return should_save, detected_secrets


def _handle_binary_copy(
    src_path: Path, dest_path: Path, check_secrets: bool
) -> tuple[bool, list[SecretMatch]]:
    """Handle binary file copying (no secret filtering)."""
    # Simple binary comparison
    import filecmp

    if dest_path.exists() and filecmp.cmp(src_path, dest_path, shallow=False):
        # Check permissions
        if src_path.stat().st_mode == dest_path.stat().st_mode:
            return False, []

    ensure_directory(dest_path.parent)
    # shutil.copy2 copies data and metadata (permissions)
    # For binary, we can copy to temp then move to ensure atomicity
    temp_path = dest_path.with_suffix(f"{dest_path.suffix}.tmp")
    try:
        shutil.copy2(src_path, temp_path)
        os.replace(temp_path, dest_path)
    except OSError:
        return False, []

    return True, []


def ensure_directory(path: Path, mode: int = 0o755) -> None:
    """Ensure a directory exists with the specified mode."""
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)


# Cache for file comparisons: { "path1|path2": (mtime1, size1, mtime2, size2, result) }
_comparison_cache: dict[str, tuple[float, int, float, int, bool]] = {}


def clear_comparison_cache() -> None:
    """Clear the file comparison cache.

    Call this after branch switches or when files are known to have changed
    to prevent stale cached results. Also prevents memory growth in
    long-running processes like the TUI.
    """
    _comparison_cache.clear()


def copy_file(
    source: Path,
    destination: Path,
    filter_secrets_enabled: bool = True,
    secret_handler: Callable[[SecretMatch], str] | None = None,
) -> tuple[bool, list[SecretMatch]]:
    """Copy a file from source to destination.

    Wrapper around smart_save_file.
    """
    saved, secrets = smart_save_file(
        source,
        destination,
        secret_handler=secret_handler,
        check_secrets=filter_secrets_enabled,
    )
    return saved, secrets


def matches_patterns(path: Path, patterns: list[str]) -> bool:
    """Check if a path matches any of the given glob patterns."""
    from fnmatch import fnmatch

    name = path.name
    rel_str = str(path)

    for pattern in patterns:
        # Match against filename
        if fnmatch(name, pattern):
            return True
        # Match against relative path
        if fnmatch(rel_str, pattern):
            return True
    return False


def copy_directory(
    source: Path,
    destination: Path,
    filter_secrets_enabled: bool = True,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    secret_handler: Callable[[SecretMatch], str] | None = None,
    follow_symlinks: bool = False,
) -> tuple[int, int, list[SecretMatch]]:
    """Copy a directory recursively with pattern filtering and efficient pruning.

    Args:
        source: Source directory path
        destination: Destination directory path
        filter_secrets_enabled: Whether to filter secrets
        include_patterns: Only include files matching these patterns (if specified)
        exclude_patterns: Exclude files/directories matching these patterns
        secret_handler: Callback for detected secrets
        follow_symlinks: Whether to follow symbolic links during traversal

    Returns:
        Tuple of (files_copied, files_failed, detected_secrets)
    """
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []
    files_copied = 0
    files_failed = 0
    all_secrets: list[SecretMatch] = []

    # Use os.walk for better performance and control over directory recursion
    for root, dirs, files in os.walk(source, topdown=True, followlinks=follow_symlinks):
        root_path = Path(root)

        # Prune ignored directories in-place to avoid traversing them
        if exclude_patterns:
            # We need to calculate relative path for each dir to check against patterns
            # Note: dirs[:] = [d for d in dirs if not matches_patterns...]
            # The check needs to be efficient.

            # Since matches_patterns expects a Path relative to source, we construct it.
            # root_rel is the relative path of current directory from source.
            try:
                root_rel = root_path.relative_to(source)
            except ValueError:
                # Should not happen as we walk source
                continue

            # Iterate backwards to safely remove items
            for i in range(len(dirs) - 1, -1, -1):
                d_name = dirs[i]
                d_rel = root_rel / d_name

                # Check if this directory should be excluded
                if matches_patterns(d_rel, exclude_patterns):
                    del dirs[i]
                    continue

        # Process files
        for filename in files:
            src_file = root_path / filename

            # Calculate relative path from source root
            try:
                relative = src_file.relative_to(source)
            except ValueError:
                continue

            # Check exclude patterns
            if exclude_patterns and matches_patterns(relative, exclude_patterns):
                continue

            # Check include patterns (if specified, file must match at least one)
            if include_patterns and not matches_patterns(relative, include_patterns):
                continue

            dest_path = destination / relative

            try:
                # Use smart_save_file for single pass, robust saving
                saved, secrets = smart_save_file(
                    src_file,
                    dest_path,
                    secret_handler=secret_handler,
                    check_secrets=filter_secrets_enabled,
                )
                all_secrets.extend(secrets)
                if saved:
                    files_copied += 1
            except Exception as e:
                logging.warning("Failed to copy file %s: %s", src_file, e)
                files_failed += 1

    return files_copied, files_failed, all_secrets


def compare_files(file1: Path, file2: Path) -> bool:
    """Compare two files for equality.

    Returns:
        True if files are identical, False otherwise
    """
    if not file1.exists() or not file2.exists():
        return False

    try:
        if file1.is_dir() and file2.is_dir():
            # Compare directories
            from filecmp import dircmp

            dcmp = dircmp(file1, file2)
            if dcmp.diff_files or dcmp.left_only or dcmp.right_only or dcmp.funny_files:
                return False
            # Recursively check subdirectories
            for subdir in dcmp.common_dirs:
                if not compare_files(file1 / subdir, file2 / subdir):
                    return False
            return True

        # Quick size check first
        stat1 = file1.stat()
        stat2 = file2.stat()

        if stat1.st_size != stat2.st_size:
            return False

        # Check comparison cache
        # Key combining both paths ensures uniqueness for the pair
        cache_key = f"{file1}|{file2}"
        if cache_key in _comparison_cache:
            m1, s1, m2, s2, res = _comparison_cache[cache_key]
            # Verify cache validity: both files must match their cached metadata
            if (
                m1 == stat1.st_mtime
                and s1 == stat1.st_size
                and m2 == stat2.st_mtime
                and s2 == stat2.st_size
            ):
                return res

        # Efficient chunked comparison
        import filecmp

        is_same = filecmp.cmp(file1, file2, shallow=False)

        # Update cache
        _comparison_cache[cache_key] = (
            stat1.st_mtime,
            stat1.st_size,
            stat2.st_mtime,
            stat2.st_size,
            is_same,
        )

        return is_same
    except OSError:
        return False


def get_file_status(local_path: Path, repo_path: Path) -> str:
    """Get the status of a file compared to repo.

    Returns:
        One of: "NEW", "MODIFIED", "DELETED", "IDENTICAL"
    """
    local_exists = local_path.exists()
    repo_exists = repo_path.exists()

    if not local_exists and not repo_exists:
        return "MISSING"
    elif local_exists and not repo_exists:
        return "NEW"
    elif not local_exists and repo_exists:
        return "DELETED"
    elif compare_files(local_path, repo_path):
        return "IDENTICAL"
    else:
        return "MODIFIED"


def create_symlink(source: Path, destination: Path) -> bool:
    """Create a symbolic link from source to destination.

    Removes destination first if it exists (file or broken symlink).
    Creates parent directories as needed.

    Uses source.absolute() (not source.resolve()) so that if the source
    itself is a symlink, the new symlink points to the symlink path
    rather than following through to its target.

    Returns:
        True if symlink was created or already correct, False on failure.
    """
    try:
        # Use absolute path without following symlinks in the source
        source_abs = source.absolute()
        if not source_abs.exists():
            return False

        # If destination is already a symlink pointing to the right place, skip
        if destination.is_symlink():
            if destination.resolve() == source_abs.resolve():
                return True
            destination.unlink()
        elif destination.exists():
            backup_file(destination)
            destination.unlink()

        ensure_directory(destination.parent)
        destination.symlink_to(source_abs)
        return True
    except OSError:
        return False


def deploy_file_or_symlink(
    source: Path,
    destination: Path,
    deploy_method: str = "copy",
    filter_secrets_enabled: bool = True,
    secret_handler: Callable[[SecretMatch], str] | None = None,
) -> tuple[bool, list[SecretMatch]]:
    """Deploy a file from source to destination, either by copy or symlink.

    Args:
        source: Source file path
        destination: Destination file path
        deploy_method: "copy" (default) or "symlink"
        filter_secrets_enabled: Whether to apply secret filtering (only for copy)
        secret_handler: Callback for detected secrets (only for copy)

    Returns:
        Tuple of (success, detected_secrets)
    """
    if deploy_method == "symlink":
        success = create_symlink(source, destination)
        return success, []
    return copy_file(
        source,
        destination,
        filter_secrets_enabled=filter_secrets_enabled,
        secret_handler=secret_handler,
    )


def deploy_directory_with_symlinks(
    source: Path,
    destination: Path,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> tuple[int, int]:
    """Deploy a directory by creating symlinks for each file.

    Args:
        source: Source directory path
        destination: Destination directory path
        include_patterns: Only include files matching these patterns
        exclude_patterns: Exclude files/directories matching these patterns

    Returns:
        Tuple of (files_symlinked, files_failed)
    """
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns or []
    symlinked = 0
    failed = 0

    for root, dirs, files in os.walk(source, topdown=True, followlinks=False):
        root_path = Path(root)

        # Prune excluded directories
        if exclude_patterns:
            try:
                root_rel = root_path.relative_to(source)
            except ValueError:
                continue

            for i in range(len(dirs) - 1, -1, -1):
                d_name = dirs[i]
                d_rel = root_rel / d_name
                if matches_patterns(d_rel, exclude_patterns):
                    del dirs[i]

        for filename in files:
            src_file = root_path / filename
            try:
                relative = src_file.relative_to(source)
            except ValueError:
                continue

            if exclude_patterns and matches_patterns(relative, exclude_patterns):
                continue
            if include_patterns and not matches_patterns(relative, include_patterns):
                continue

            dest_path = destination / relative
            try:
                if create_symlink(src_file, dest_path):
                    symlinked += 1
                else:
                    failed += 1
            except Exception as e:
                logging.warning("Failed to create symlink %s: %s", src_file, e)
                failed += 1

    return symlinked, failed


def backup_file(path: Path) -> Path | None:
    """Create a backup of a file with .dotman-backup suffix.

    Returns:
        Path to backup file, or None if backup failed
    """
    if not path.exists():
        return None

    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_suffix(f"{path.suffix}.dotman-backup-{timestamp}")

    try:
        if path.is_file():
            shutil.copy2(path, backup_path)
        else:
            shutil.copytree(path, backup_path)
        return backup_path
    except OSError:
        return None
