"""Tests for shell completion functions."""

import subprocess
from unittest.mock import patch

from dot_man.cli.common import _clear_all_caches, _set_git_runner, complete_sections


def make_mock_result(stdout="", returncode=0):
    """Create a mock subprocess result."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class TestCompleteSections:
    """Test complete_sections shell completion function."""

    def _make_config(self, tmp_path, content):
        """Create a dot-man config at the standard location."""
        repo_dir = tmp_path / ".dot-man" / "repo"
        repo_dir.mkdir(parents=True)
        config_file = repo_dir / "dot-man.toml"
        config_file.write_text(content)
        return repo_dir

    def test_complete_sections_returns_all(self, tmp_path):
        """complete_sections should return all section names."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]

[kitty]
paths = ["~/.config/kitty"]
""",
        )

        with patch("dot_man.dotman_config.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert "nvim" in result
            assert "kitty" in result

    def test_complete_sections_filters_by_prefix(self, tmp_path):
        """complete_sections should filter by incomplete prefix."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]

[kitty]
paths = ["~/.config/kitty"]

[neovim]
paths = ["~/.config/neovim"]
""",
        )

        with patch("dot_man.dotman_config.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "ki")
            assert result == ["kitty"]

            result = complete_sections(None, None, "ne")
            assert result == ["neovim"]

    def test_complete_sections_no_match_returns_empty(self, tmp_path):
        """complete_sections should return empty list when no match."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]
""",
        )

        with patch("dot_man.dotman_config.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "z")
            assert result == []

    def test_complete_sections_empty_config(self, tmp_path):
        """complete_sections should return empty list when no sections."""
        repo_dir = self._make_config(tmp_path, "")

        with patch("dot_man.dotman_config.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert result == []

    def test_complete_sections_missing_config(self, tmp_path):
        """complete_sections should return empty list when config missing."""
        repo_dir = tmp_path / ".dot-man" / "repo"
        repo_dir.mkdir(parents=True)

        with patch("dot_man.dotman_config.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert result == []


class TestCompleteCommits:
    """Test complete_commits shell completion on rollback target."""

    def test_complete_commits_returns_list(self):
        """complete_commits should return commit SHAs."""
        from dot_man.cli.common import complete_commits

        def mock_runner(args, cwd=None, timeout=2):
            return make_mock_result("abc1234\ndef5678\n")

        with patch("dot_man.cli.completions._git_runner", mock_runner):
            _set_git_runner(mock_runner)
            result = complete_commits(None, None, "")
            assert "abc1234" in result
            assert "def5678" in result
        _set_git_runner(None)

    def test_complete_commits_filters(self):
        """complete_commits should filter by prefix."""
        from dot_man.cli.common import complete_commits

        def mock_runner(args, cwd=None, timeout=2):
            return make_mock_result("abc1234\ndef5678\n")

        with patch("dot_man.cli.completions._git_runner", mock_runner):
            _set_git_runner(mock_runner)
            result = complete_commits(None, None, "abc")
            assert result == ["abc1234"]

            result = complete_commits(None, None, "xyz")
            assert result == []
        _set_git_runner(None)
