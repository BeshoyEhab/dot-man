import json
from pathlib import Path
import pytest
from dot_man.secrets import SecretGuard, SecretMatch, SecretScanner, filter_secrets


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".config" / "dot-man"
    config_dir.mkdir(parents=True)
    return config_dir


def test_secret_guard_init(temp_config_dir):
    """Test SecretGuard initialization."""
    guard = SecretGuard(config_dir=temp_config_dir)
    assert guard.config_dir == temp_config_dir
    assert guard.list_path == temp_config_dir / ".dotman-allowed-secrets.json"
    assert guard._secrets == []


def test_add_and_check_allowed(temp_config_dir):
    """Test adding and checking for allowed secrets."""
    guard = SecretGuard(config_dir=temp_config_dir)

    file_path = "/home/user/.bashrc"
    secret_line = "export API_KEY='12345secret'"
    pattern_name = "Generic API Key"

    # Should not be allowed initially
    assert not guard.is_allowed(file_path, secret_line, pattern_name)

    # Add to allow list
    guard.add_allowed(file_path, secret_line, pattern_name)

    # Should now be allowed
    assert guard.is_allowed(file_path, secret_line, pattern_name)


def test_callback_redaction():
    """Test redact_content with a callback."""
    scanner = SecretScanner()
    content = "password = 'secret_pass'"

    # Case 1: Callback says REDACT
    def redact_cb(match: SecretMatch) -> str:
        return "REDACT"

    redacted, count = scanner.redact_content(content, callback=redact_cb)
    assert "REDACTED" in redacted
    assert count == 1

    # Case 2: Callback says KEEP (preserved as-is)
    def keep_cb(match: SecretMatch) -> str:
        return "KEEP"

    kept_content, count_kept = scanner.redact_content(content, callback=keep_cb)
    assert "secret_pass" in kept_content
    assert "REDACTED" not in kept_content
    assert count_kept == 0


def test_filter_secrets_callback():
    """Test filter_secrets wrapper with callback."""
    content = "api_key = 'abcdef1234567890abcdef1234567890'"

    def keep_cb(match: SecretMatch) -> str:
        # Simulate keeping/skipping redaction
        return "KEEP"

    filtered, matches = filter_secrets(content, callback=keep_cb)

    # Matches should be empty since we KEPT the secret (didn't redact)
    # filter_secrets now only returns secrets that were actually redacted
    assert len(matches) == 0
    # Content should NOT be redacted
    assert "REDACTED" not in filtered
    assert "abcdef" in filtered


def test_multiple_secrets_callback():
    """Test callback logic with multiple secrets."""
    scanner = SecretScanner()
    content = "api_key='12345678901234567890'\napi_key2='abcdefabcdefabcdefabcdef'"

    def conditional_cb(match: SecretMatch) -> str:
        if "12345" in match.matched_text:
            return "REDACT"
        return "IGNORE"

    redacted, count = scanner.redact_content(content, callback=conditional_cb)

    assert "***REDACTED***" in redacted  # First one redacted
    assert "abcdef" in redacted  # Second one visible
    assert count == 1


def test_scan_directory_pruning(tmp_path):
    """Test that scan_directory correctly prunes .git and excluded directories."""
    scanner = SecretScanner()

    # Setup directory structure
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "secret.txt").write_text(
        "aws_secret_access_key = 'git_secret'", encoding="utf-8"
    )

    excluded_dir = tmp_path / "node_modules"
    excluded_dir.mkdir()
    (excluded_dir / "secret.js").write_text(
        "aws_secret_access_key = 'node_secret'", encoding="utf-8"
    )

    included_dir = tmp_path / "src"
    included_dir.mkdir()
    (included_dir / "secret.py").write_text(
        "aws_secret_access_key = 'src_secret'", encoding="utf-8"
    )

    # 1. Scan with no exclusions (should skip .git but include node_modules)
    matches = list(scanner.scan_directory(tmp_path))
    match_texts = [m.matched_text for m in matches]

    # .git should be skipped by default
    assert not any("git_secret" in t for t in match_texts)
    # node_modules should be included (because default exclude is empty)
    assert any("node_secret" in t for t in match_texts)
    # src should be included
    assert any("src_secret" in t for t in match_texts)

    # 2. Scan with exclusion for node_modules
    matches_excluded = list(
        scanner.scan_directory(tmp_path, exclude_patterns=["node_modules"])
    )
    match_texts_excluded = [m.matched_text for m in matches_excluded]

    # .git skipped
    assert not any("git_secret" in t for t in match_texts_excluded)
    # node_modules skipped
    assert not any("node_secret" in t for t in match_texts_excluded)
    # src included
    assert any("src_secret" in t for t in match_texts_excluded)
