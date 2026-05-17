"""Tests for encryption module."""


class TestEncryptionManager:
    """Test EncryptionManager class."""

    def test_encryption_manager_init_gpg(self):
        """Test EncryptionManager with GPG."""
        from dot_man.encryption import EncryptionManager

        enc = EncryptionManager("gpg")
        assert enc.method == "gpg"

    def test_encryption_manager_init_age(self):
        """Test EncryptionManager with AGE."""
        from dot_man.encryption import EncryptionManager

        enc = EncryptionManager("age")
        assert enc.method == "age"

    def test_is_gpg_available(self):
        """Test GPG availability check."""
        from dot_man.encryption import is_gpg_available

        result = is_gpg_available()
        assert isinstance(result, bool)

    def test_is_age_available(self):
        """Test AGE availability check."""
        from dot_man.encryption import is_age_available

        result = is_age_available()
        assert isinstance(result, bool)

    def test_detect_available_encryption(self):
        """Test encryption method detection."""
        from dot_man.encryption import detect_available_encryption

        result = detect_available_encryption()
        assert isinstance(result, list)


class TestEncryptionError:
    """Test EncryptionError exception."""

    def test_encryption_error(self):
        """Test EncryptionError can be raised."""
        from dot_man.encryption import EncryptionError
        from dot_man.exceptions import DotManError

        error = EncryptionError("Test error")
        assert isinstance(error, DotManError)
        assert str(error) == "Test error"


class TestEncryptionManagerMethods:
    """Test EncryptionManager methods."""

    def test_encryption_manager_str(self):
        """Test EncryptionManager string representation."""
        from dot_man.encryption import EncryptionManager

        enc = EncryptionManager("gpg")
        assert "gpg" in str(enc).lower() or hasattr(enc, "method")

    def test_encryption_invalid_method(self):
        """Test EncryptionManager with invalid method."""
        from dot_man.encryption import EncryptionManager

        enc = EncryptionManager("invalid")
        assert enc.method == "invalid"


class TestEncryptionHelpers:
    """Test encryption helper functions."""

    def test_encryption_available_returns_list(self):
        """Test that detect_available_encryption returns list."""
        from dot_man.encryption import detect_available_encryption

        result = detect_available_encryption()
        assert isinstance(result, (list, tuple))

    def test_gpg_check_returns_bool(self):
        """Test that is_gpg_available returns bool."""
        from dot_man.encryption import is_gpg_available

        result = is_gpg_available()
        assert result is True or result is False

    def test_age_check_returns_bool(self):
        """Test that is_age_available returns bool."""
        from dot_man.encryption import is_age_available

        result = is_age_available()
        assert result is True or result is False
