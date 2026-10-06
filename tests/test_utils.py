"""Tests for utils module."""

from unittest.mock import patch


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


class TestDirectoryTraversal:
    """Test get_directory_size and count_files share one traversal."""

    def test_single_file(self, tmp_path):
        """Both helpers handle a direct file path."""
        from dot_man.utils import count_files, get_directory_size

        target = tmp_path / "data.bin"
        target.write_bytes(b"x" * 100)

        assert get_directory_size(target) == 100
        assert count_files(target) == 1

    def test_missing_path(self, tmp_path):
        """Both helpers return 0 for a missing path."""
        from dot_man.utils import count_files, get_directory_size

        missing = tmp_path / "nope"

        assert get_directory_size(missing) == 0
        assert count_files(missing) == 0

    def test_directory(self, tmp_path):
        """Both helpers agree on a directory tree."""
        from dot_man.utils import count_files, get_directory_size

        (tmp_path / "a.txt").write_bytes(b"a" * 10)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.txt").write_bytes(b"b" * 20)

        assert count_files(tmp_path) == 2
        assert get_directory_size(tmp_path) == 30


class TestGetEditorFallback:
    """Fallback chain when VISUAL/EDITOR are unset."""

    def test_which_fallback(self, monkeypatch):
        """First editor found on PATH wins."""
        import shutil

        from dot_man.utils import get_editor

        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr(
            shutil, "which", lambda name: "/usr/bin/vim" if name == "vim" else None
        )

        assert get_editor() == "vim"

    def test_which_none_returns_nano(self, monkeypatch):
        """Nothing on PATH falls back to nano."""
        import shutil

        from dot_man.utils import get_editor

        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr(shutil, "which", lambda name: None)

        assert get_editor() == "nano"


class TestOpenInEditor:
    """open_in_editor translates process results to bool."""

    def test_success(self, tmp_path):
        """Exit 0 means True, invoked with editor and path."""
        from unittest.mock import MagicMock

        from dot_man.utils import open_in_editor

        target = tmp_path / "f.txt"
        target.write_text("x")

        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as run:
            assert open_in_editor(target, editor="myeditor") is True
        run.assert_called_once_with(["myeditor", str(target)])

    def test_nonzero_exit(self, tmp_path):
        """Nonzero exit means False."""
        from unittest.mock import MagicMock

        from dot_man.utils import open_in_editor

        target = tmp_path / "f.txt"
        target.write_text("x")

        with patch("subprocess.run", return_value=MagicMock(returncode=3)):
            assert open_in_editor(target, editor="myeditor") is False

    def test_spawn_failure(self, tmp_path):
        """Unlaunchable editor means False, not an exception."""
        from dot_man.utils import open_in_editor

        target = tmp_path / "f.txt"
        target.write_text("x")

        with patch("subprocess.run", side_effect=OSError("no such editor")):
            assert open_in_editor(target, editor="nope") is False


class TestStatErrorTolerance:
    """Unstatable files are skipped without breaking the walk."""

    def test_stat_error_skipped(self, tmp_path):
        """OSError on stat() yields size 0 instead of raising."""
        from unittest.mock import MagicMock

        from dot_man import utils

        broken = MagicMock()
        broken.stat.side_effect = OSError("denied")

        with patch("dot_man.utils._iter_files", return_value=[broken]):
            assert utils.get_directory_size(tmp_path) == 0


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
