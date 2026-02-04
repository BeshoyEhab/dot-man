"""File operations for dot-man."""

from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Iterator, Callable

from .constants import REPO_DIR
from .secrets import (
    filter_secrets,
    SecretMatch,
    SecretScanner,
    SecretGuard,
    PermanentRedactGuard,
)


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

    if not src_path.exists() or not src_path.is_file():
        return False, []

    # 1. Read source
    try:
        with src_path.open("r", encoding="utf-8", newline="") as f:
            src_content = f.read()
    except (UnicodeDecodeError, OSError):
        # Binary file or read error - fallback to direct copy if different
        return _handle_binary_copy(src_path, dest_path, check_secrets)

    # 2. Filter secrets
    final_content = src_content
    if check_secrets:
        # Wrap handler to include implicit Guard checking
        allow_guard = SecretGuard()
        redact_guard = PermanentRedactGuard()

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
    if dest_path.exists() and dest_path.is_file():
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


# Simple metadata cache: {path_str: (mtime, size)}
_metadata_cache: dict[str, tuple[float, int]] = {}


def get_cached_metadata(path: Path) -> tuple[float, int] | None:
    """Get cached metadata if available and valid."""
    p_str = str(path)
    if p_str in _metadata_cache:
        return _metadata_cache[p_str]
    return None


def update_metadata_cache(path: Path) -> None:
    """Update cache with current file metadata."""
    try:
        stat = path.stat()
        _metadata_cache[str(path)] = (stat.st_mtime, stat.st_size)
    except OSError:
        pass


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
    ignore_patterns: list[str] | None = None,  # Deprecated, use exclude_patterns
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
        ignore_patterns: Deprecated alias for exclude_patterns
        secret_handler: Callback for detected secrets
        follow_symlinks: Whether to follow symbolic links during traversal

    Returns:
        Tuple of (files_copied, files_failed, detected_secrets)
    """
    include_patterns = include_patterns or []
    exclude_patterns = (
        exclude_patterns if exclude_patterns is not None else (ignore_patterns or [])
    )
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
                    check_secrets=filter_secrets_enabled
                )
                all_secrets.extend(secrets)
                if saved:
                    files_copied += 1
            except Exception:
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

        # Efficient chunked comparison
        import filecmp

        is_same = filecmp.cmp(file1, file2, shallow=False)
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


def iter_tracked_files(
    config_sections: list[dict],
) -> Iterator[tuple[Path, Path, str]]:
    """Iterate over tracked files from configuration.

    Yields:
        Tuple of (local_path, repo_path, status)
    """
    for section in config_sections:
        local_path = section["local_path"]
        repo_path = section["repo_path"]

        if local_path.is_dir():
            # Handle directory
            repo_rels = set()
            local_rels = set()

            if repo_path.exists():
                repo_rels = {
                    p.relative_to(repo_path)
                    for p in repo_path.rglob("*")
                    if p.is_file()
                }

            if local_path.exists():
                local_rels = {
                    p.relative_to(local_path)
                    for p in local_path.rglob("*")
                    if p.is_file()
                }

            all_rels = sorted(repo_rels | local_rels)

            for rel in all_rels:
                local_file = local_path / rel
                repo_file = repo_path / rel

                in_repo = rel in repo_rels
                in_local = rel in local_rels

                if in_repo and not in_local:
                    yield local_file, repo_file, "DELETED"
                elif in_local and not in_repo:
                    yield local_file, repo_file, "NEW"
                else:
                    # Both exist, check content
                    if compare_files(local_file, repo_file):
                        yield local_file, repo_file, "IDENTICAL"
                    else:
                        yield local_file, repo_file, "MODIFIED"
        else:
            # Handle file
            status = get_file_status(local_path, repo_path)
            yield local_path, repo_path, status


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
