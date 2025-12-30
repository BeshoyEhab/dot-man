"""File operations for dot-man."""

import shutil
from pathlib import Path
from typing import Iterator

from .constants import REPO_DIR
from .secrets import filter_secrets, SecretMatch


def ensure_directory(path: Path, mode: int = 0o755) -> None:
    """Ensure a directory exists with the specified mode."""
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(mode)


def copy_file(
    source: Path,
    destination: Path,
    filter_secrets_enabled: bool = True,
) -> tuple[bool, list[SecretMatch]]:
    """Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        filter_secrets_enabled: Whether to filter secrets from content

    Returns:
        Tuple of (success, list_of_detected_secrets)
    """
    detected_secrets: list[SecretMatch] = []

    try:
        # Ensure destination directory exists
        ensure_directory(destination.parent)

        if filter_secrets_enabled and source.is_file():
            # Read and filter content
            try:
                content = source.read_text(encoding="utf-8")
                filtered_content, secrets = filter_secrets(content)
                detected_secrets = secrets
                destination.write_text(filtered_content, encoding="utf-8")
            except UnicodeDecodeError:
                # Binary file - copy without filtering
                shutil.copy2(source, destination)
        else:
            # Direct copy
            if source.is_file():
                shutil.copy2(source, destination)
            elif source.is_dir():
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.copytree(source, destination)

        return True, detected_secrets

    except Exception:
        return False, detected_secrets


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
) -> tuple[int, int, list[SecretMatch]]:
    """Copy a directory recursively with pattern filtering.

    Args:
        source: Source directory path
        destination: Destination directory path
        filter_secrets_enabled: Whether to filter secrets
        include_patterns: Only include files matching these patterns (if specified)
        exclude_patterns: Exclude files matching these patterns
        ignore_patterns: Deprecated alias for exclude_patterns

    Returns:
        Tuple of (files_copied, files_failed, detected_secrets)
    """
    include_patterns = include_patterns or []
    exclude_patterns = exclude_patterns if exclude_patterns is not None else (ignore_patterns or [])
    files_copied = 0
    files_failed = 0
    all_secrets: list[SecretMatch] = []

    for src_path in source.rglob("*"):
        if src_path.is_dir():
            continue

        relative = src_path.relative_to(source)
        
        # Check exclude patterns first
        if exclude_patterns and matches_patterns(relative, exclude_patterns):
            continue
        
        # Check include patterns (if specified, file must match at least one)
        if include_patterns and not matches_patterns(relative, include_patterns):
            continue

        dest_path = destination / relative

        success, secrets = copy_file(src_path, dest_path, filter_secrets_enabled)
        all_secrets.extend(secrets)

        if success:
            files_copied += 1
        else:
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
            
        return file1.read_bytes() == file2.read_bytes()
    except Exception:
        return False


def get_file_status(
    local_path: Path, repo_path: Path
) -> str:
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
            if repo_path.exists():
                for repo_file in repo_path.rglob("*"):
                    if repo_file.is_file():
                        relative = repo_file.relative_to(repo_path)
                        local_file = local_path / relative
                        status = get_file_status(local_file, repo_file)
                        yield local_file, repo_file, status

            if local_path.exists():
                for local_file in local_path.rglob("*"):
                    if local_file.is_file():
                        relative = local_file.relative_to(local_path)
                        repo_file = repo_path / relative
                        if not repo_file.exists():
                            yield local_file, repo_file, "NEW"
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
    except Exception:
        return None
