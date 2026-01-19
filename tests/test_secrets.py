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
    assert guard.allow_list_path == temp_config_dir / ".dotman-allowed-secrets.json"
    assert guard._allowed_secrets == []


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

    # Case 2: Callback says IGNORE
    def ignore_cb(match: SecretMatch) -> str:
        return "IGNORE"

    redacted_ignore, count_ignore = scanner.redact_content(content, callback=ignore_cb)
    assert "secret_pass" in redacted_ignore
    assert "REDACTED" not in redacted_ignore
    assert count_ignore == 0


def test_filter_secrets_callback():
    """Test filter_secrets wrapper with callback."""
    content = "api_key = 'abcdef1234567890abcdef1234567890'"

    def skip_cb(match: SecretMatch) -> str:
        # Simulate ignoring/skipping
        return "IGNORE"

    filtered, matches = filter_secrets(content, callback=skip_cb)

    # Should find the match
    assert len(matches) == 1
    # But content should NOT be redacted
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
