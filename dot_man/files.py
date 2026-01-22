"""File operations for dot-man."""

import shutil
from pathlib import Path
from typing import Iterator, Callable

from .constants import REPO_DIR
from .secrets import filter_secrets, SecretMatch, SecretScanner, SecretGuard, PermanentRedactGuard


def check_file_save_status(
    src_path: Path, 
    dest_path: Path, 
    check_secrets: bool = True
) -> tuple[bool, bool]:
    """Check if a file needs saving by examining content and secrets in a single read.
    
    This function reads the source file ONCE and checks:
    1. Whether the content matches the destination (unchanged)
    2. Whether there are unhandled secrets (if check_secrets is True)
    
    Args:
        src_path: Source file path (local file)
        dest_path: Destination file path (repo file)
        check_secrets: Whether to scan for unhandled secrets
        
    Returns:
        Tuple of (is_unchanged, has_unhandled_secrets)
        - is_unchanged: True if files are identical (content + permissions)
        - has_unhandled_secrets: True if there are secrets needing user decision
    """
    # Quick checks first (no file read needed)
    if not src_path.exists() or not src_path.is_file():
        return False, False
    
    if not dest_path.exists():
        # New file - definitely needs saving
        if check_secrets:
            # Still need to check for secrets
            try:
                with src_path.open("r", encoding="utf-8", newline="") as f:
                    content = f.read()
            except (UnicodeDecodeError, OSError):
                return False, False  # Binary or unreadable
            
            scanner = SecretScanner()
            allow_guard = SecretGuard()
            redact_guard = PermanentRedactGuard()
            
            for match in scanner.scan_content(content, src_path):
                if not allow_guard.is_allowed(src_path, match.line_content, match.pattern_name):
                    if not redact_guard.should_redact(src_path, match.line_content, match.pattern_name):
                        return False, True  # Not unchanged, has unhandled secrets
            
        return False, False  # Not unchanged (new file), no unhandled secrets
    
    # Both files exist - compare
    try:
        src_stat = src_path.stat()
        dest_stat = dest_path.stat()
        
        # Quick size check
        if src_stat.st_size != dest_stat.st_size:
            return False, False  # Different size = changed, don't bother with secret check
        
        # Permission check
        if src_stat.st_mode != dest_stat.st_mode:
            return False, False  # Different permissions = needs update
        
    except OSError:
        return False, False  # Stat failed, assume changed
    
    # Read source file ONCE for content comparison and secret scanning
    try:
        with src_path.open("r", encoding="utf-8", newline="") as f:
            src_content = f.read()
    except UnicodeDecodeError:
        # Binary file - use filecmp for comparison, no secrets
        import filecmp
        is_same = filecmp.cmp(src_path, dest_path, shallow=False)
        return is_same, False
    except OSError:
        return False, False
    
    # Read destination for comparison
    try:
        with dest_path.open("r", encoding="utf-8", newline="") as f:
            dest_content = f.read()
    except (UnicodeDecodeError, OSError):
        return False, False  # Can't compare, assume changed
    
    # Content comparison
    is_unchanged = (src_content == dest_content)
    
    # Only check for secrets if file is unchanged (optimization: if changed, we process anyway)
    if is_unchanged and check_secrets:
        scanner = SecretScanner()
        allow_guard = SecretGuard()
        redact_guard = PermanentRedactGuard()
        
        for match in scanner.scan_content(src_content, src_path):
            if not allow_guard.is_allowed(src_path, match.line_content, match.pattern_name):
                if not redact_guard.should_redact(src_path, match.line_content, match.pattern_name):
                    return True, True  # Unchanged but has unhandled secrets
        
        return True, False  # Unchanged, no unhandled secrets
    
    return is_unchanged, False


def has_unhandled_secrets(file_path: Path) -> bool:
    """Check if a file contains secrets not in allow list or permanent redact list.
    
    Returns True if there are secrets that need user decision, False otherwise.
    """
    if not file_path.exists() or not file_path.is_file():
        return False
    
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False  # Binary file or read error, no text secrets
    
    scanner = SecretScanner()
    allow_guard = SecretGuard()
    redact_guard = PermanentRedactGuard()
    
    for match in scanner.scan_content(content, file_path):
        # Check if this secret is already handled
        if allow_guard.is_allowed(file_path, match.line_content, match.pattern_name):
            continue  # Allowed, will be skipped
        if redact_guard.should_redact(file_path, match.line_content, match.pattern_name):
            continue  # Will be auto-redacted
        
        # Found an unhandled secret
        return True
    
    return False



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
                with source.open("r", encoding="utf-8", newline="") as f:
                    content = f.read()
                
                filtered_content, secrets = filter_secrets(
                    content, callback=secret_handler, file_path=source
                )
                detected_secrets = secrets
                
                with destination.open("w", encoding="utf-8", newline="") as f:
                    f.write(filtered_content)
                
                # Preserve original file permissions (e.g., executable bit)
                destination.chmod(source.stat().st_mode)
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

    except OSError:
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
    secret_handler: Callable[[SecretMatch], str] | None = None,
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
    exclude_patterns = (
        exclude_patterns if exclude_patterns is not None else (ignore_patterns or [])
    )
    files_copied = 0
    files_skipped = 0
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

        # Optimized: check unchanged status and secrets in a single file read
        is_unchanged, has_secrets = check_file_save_status(
            src_path, dest_path, check_secrets=filter_secrets_enabled
        )
        
        if is_unchanged and not has_secrets:
            files_skipped += 1
            continue  # File unchanged and no unhandled secrets, skip

        success, secrets = copy_file(
            src_path, dest_path, filter_secrets_enabled, secret_handler=secret_handler
        )
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

        # Quick size check first
        stat1 = file1.stat()
        stat2 = file2.stat()
        
        if stat1.st_size != stat2.st_size:
            return False

        # NOTE: mtime optimization removed - git checkout updates mtimes,
        # making this unreliable for dotfile sync scenarios.
        # Always use content-based comparison for accuracy.

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
    except OSError:
        return None
