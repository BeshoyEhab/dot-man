"""Tests for dot-man core modules."""

import pytest
from pathlib import Path


class TestSecretScanner:
    """Test secret detection patterns."""

    def test_detects_api_key(self):
        """Should detect API key patterns."""
        from dot_man.secrets import SecretScanner

        scanner = SecretScanner()
        content = "export API_KEY=sk_live_123456789abcdef"
        matches = list(scanner.scan_content(content))
        
        assert len(matches) == 1
        assert matches[0].pattern_name == "Generic API Key"

    def test_detects_private_key(self):
        """Should detect private key headers."""
        from dot_man.secrets import SecretScanner

        scanner = SecretScanner()
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        matches = list(scanner.scan_content(content))
        
        assert len(matches) >= 1
        assert any(m.pattern_name == "Private Key" for m in matches)

    def test_detects_aws_key(self):
        """Should detect AWS access key IDs."""
        from dot_man.secrets import SecretScanner

        scanner = SecretScanner()
        # Note: Don't use 'EXAMPLE' as it triggers false positive (contains 'example')
        content = "AWS_KEY=AKIAIOSFODNN7TESTKEY1"  # AKIA + 16 chars
        matches = list(scanner.scan_content(content))
        
        assert len(matches) >= 1

    def test_ignores_false_positives(self):
        """Should ignore example/dummy values."""
        from dot_man.secrets import SecretScanner

        scanner = SecretScanner()
        content = "api_key = your_key_here"
        matches = list(scanner.scan_content(content))
        
        assert len(matches) == 0

    def test_redact_content(self):
        """Should redact secrets from content."""
        from dot_man.secrets import SecretScanner

        scanner = SecretScanner()
        # Use a pattern that will definitely match
        content = "api_key=my_super_secret_key_12345\nOTHER=normal"
        redacted, count = scanner.redact_content(content)
        
        assert count >= 1
        assert "my_super_secret" not in redacted


class TestConfig:
    """Test configuration parsing."""

    def test_valid_update_strategies(self):
        """Should accept valid update strategies."""
        from dot_man.constants import VALID_UPDATE_STRATEGIES

        assert "replace" in VALID_UPDATE_STRATEGIES
        assert "rename_old" in VALID_UPDATE_STRATEGIES
        assert "ignore" in VALID_UPDATE_STRATEGIES


class TestFiles:
    """Test file operations."""

    def test_get_file_status_missing(self):
        """Should return correct status for missing files."""
        from dot_man.files import get_file_status

        status = get_file_status(
            Path("/nonexistent/file1"),
            Path("/nonexistent/file2")
        )
        assert status == "MISSING"

    def test_compare_files_identical(self, tmp_path):
        """Should detect identical files."""
        from dot_man.files import compare_files

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("hello")
        file2.write_text("hello")

        assert compare_files(file1, file2) is True

    def test_compare_files_different(self, tmp_path):
        """Should detect different files."""
        from dot_man.files import compare_files
        import time

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("hello")
        time.sleep(0.15)  # Ensure different mtime (compare_files has 0.1s tolerance)
        file2.write_text("world")

        assert compare_files(file1, file2) is False

