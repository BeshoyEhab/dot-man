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


class TestSecretMatchMasking:
    """S4: match lines must be printable without leaking the secret value."""

    def test_masked_line_hides_value(self):
        from pathlib import Path

        from dot_man.secrets import Severity

        match = SecretMatch(
            file=Path("x"),
            line_number=1,
            line_content="password = 'supersecret123'",
            pattern_name="Password Assignment",
            severity=Severity.HIGH,
            matched_text="supersecret123",
        )
        assert "supersecret123" not in match.masked_line
        assert "***" in match.masked_line
        assert "password" in match.masked_line

    def test_masked_line_without_match_is_unchanged(self):
        from pathlib import Path

        from dot_man.secrets import Severity

        match = SecretMatch(
            file=Path("x"),
            line_number=1,
            line_content="nothing here",
            pattern_name="none",
            severity=Severity.LOW,
            matched_text="",
        )
        assert match.masked_line == "nothing here"


class TestEntropy:
    """S9: entropy scoring for generic long strings."""

    def test_repeated_value_scores_low(self):
        from dot_man.secrets import shannon_entropy

        assert shannon_entropy("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") < 1.0

    def test_random_value_scores_high(self):
        from dot_man.secrets import shannon_entropy

        assert shannon_entropy("t7Rq2mZk9Lx4pVb8Nc1wYs6Ae3hJu0Df") > 3.5

    def test_low_entropy_long_string_not_flagged(self):
        scanner = SecretScanner()
        matches = list(
            scanner.scan_content("value = aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        )
        assert not any(m.pattern_name == "High Entropy String" for m in matches)

    def test_high_entropy_string_flagged(self):
        scanner = SecretScanner()
        matches = list(
            scanner.scan_content("value = t7Rq2mZk9Lx4pVb8Nc1wYs6Ae3hJu0DfQ2")
        )
        assert any(m.pattern_name == "High Entropy String" for m in matches)


class TestBroadenedPatterns:
    """S9: previously-missed token formats must be detected."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            (
                "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz",
                "GitHub Fine-Grained PAT",
            ),
            ("glpat-abcdefghijklmnopqrst", "GitLab Token"),
            ("xox" "b-123456789012-abcdefghijklmnop", "Slack Token"),
            ("ASIA1234567890ABCDEF", "AWS Session Token"),
        ],
    )
    def test_token_detected(self, value, expected):
        scanner = SecretScanner()
        names = {m.pattern_name for m in scanner.scan_content(f"token = {value}")}
        assert expected in names


class TestValueBasedFalsePositives:
    """S9: indicators match the value, not the whole line."""

    def test_comment_mentioning_example_does_not_mask_secret(self):
        scanner = SecretScanner()
        line = "api_key = AKIA1234567890ABCDEF  # example for docs"
        matches = list(scanner.scan_content(line))
        assert any(m.matched_text == "AKIA1234567890ABCDEF" for m in matches)

    def test_placeholder_value_is_skipped(self):
        scanner = SecretScanner()
        matches = list(scanner.scan_content("api_key = your_key_here_but_longer_value"))
        assert matches == []

    def test_env_var_reference_skipped(self):
        scanner = SecretScanner()
        matches = list(scanner.scan_content("password = ${MY_PASSWORD}"))
        assert matches == []


class TestCoverageGaps:
    """Edge paths kept exercised so module coverage stays above the floor."""

    def test_shannon_entropy_empty_string(self):
        from dot_man.secrets import shannon_entropy

        assert shannon_entropy("") == 0.0

    def test_scan_git_history_skips_binary_blob(self, tmp_path):
        from git import Repo

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        with repo.config_writer() as config:
            config.set_value("user", "name", "T")
            config.set_value("user", "email", "t@t.com")
        (repo_dir / "blob.bin").write_bytes(b"\x00\x01\x02AKIA1234567890ABCDEF")
        repo.index.add(["blob.bin"])
        repo.index.commit("binary")

        matches = list(SecretScanner().scan_git_history(repo))
        assert matches == []

    def test_scan_git_history_tolerates_broken_repo(self):
        from unittest.mock import MagicMock

        from git import GitCommandError

        repo = MagicMock()
        repo.iter_commits.side_effect = GitCommandError("iter_commits", "boom")
        repo.index.entries = {}
        assert list(SecretScanner().scan_git_history(repo)) == []

    def test_load_custom_patterns_handles_bad_shapes(self):
        from dot_man.secrets import load_custom_patterns

        assert load_custom_patterns({"a": 1}, ["a"]) == []
        assert load_custom_patterns({"a": "not-a-list"}, ["a"]) == []
        patterns = load_custom_patterns(
            {"a": [{"name": "bad", "pattern": "("}, {"nope": 1}]}, ["a"]
        )
        assert patterns == []

    def test_get_custom_scanner_falls_back_on_error(self):
        from unittest.mock import patch

        from dot_man.secrets import get_custom_scanner

        with patch(
            "dot_man.operations.get_operations", side_effect=RuntimeError("nope")
        ):
            scanner = get_custom_scanner()
        assert scanner.patterns
