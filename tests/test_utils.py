"""Tests for utils module."""


class TestSha256Hex:
    """Test sha256_hex function."""

    def test_sha256_hex_basic(self):
        """Test basic sha256_hex."""
        from dot_man.utils import sha256_hex

        result = sha256_hex("hello")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_sha256_hex_empty(self):
        """Test sha256_hex with empty string."""
        from dot_man.utils import sha256_hex

        result = sha256_hex("")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_sha256_hex_consistency(self):
        """Test sha256_hex is consistent."""
        from dot_man.utils import sha256_hex

        result1 = sha256_hex("test")
        result2 = sha256_hex("test")
        assert result1 == result2


class TestHumanSize:
    """Test human_size function."""

    def test_human_size_bytes(self):
        """Test human_size with bytes."""
        from dot_man.utils import human_size

        result = human_size(500)
        assert "B" in result

    def test_human_size_kilobytes(self):
        """Test human_size with kilobytes."""
        from dot_man.utils import human_size

        result = human_size(1024)
        assert "KB" in result

    def test_human_size_megabytes(self):
        """Test human_size with megabytes."""
        from dot_man.utils import human_size

        result = human_size(1024 * 1024)
        assert "MB" in result

    def test_human_size_gigabytes(self):
        """Test human_size with gigabytes."""
        from dot_man.utils import human_size

        result = human_size(1024 * 1024 * 1024)
        assert "GB" in result


class TestIsGitInstalled:
    """Test is_git_installed function."""

    def test_is_git_installed(self):
        """Test is_git_installed returns bool."""
        from dot_man.utils import is_git_installed

        result = is_git_installed()
        assert isinstance(result, bool)


class TestGetHostname:
    """Test get_hostname function."""

    def test_get_hostname_returns_str(self):
        """Test get_hostname returns string."""
        from dot_man.utils import get_hostname

        result = get_hostname()
        assert isinstance(result, str)


class TestGetUsername:
    """Test get_username function."""

    def test_get_username_returns_str(self):
        """Test get_username returns string."""
        from dot_man.utils import get_username

        result = get_username()
        assert isinstance(result, str)


class TestGetEditor:
    """Test get_editor function."""

    def test_get_editor_no_env(self):
        """Test get_editor without env vars."""
        from dot_man.utils import get_editor

        result = get_editor()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_editor_priority(self):
        """Test get_editor prioritizes VISUAL over EDITOR."""
        import os

        from dot_man.utils import get_editor

        original_env = os.environ.copy()
        try:
            os.environ["VISUAL"] = "vim"
            os.environ["EDITOR"] = "nano"
            from dot_man.utils import get_editor

            result = get_editor()
            assert result in ["vim", "nano"]
        finally:
            os.environ.clear()
            os.environ.update(original_env)
