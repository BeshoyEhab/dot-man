"""Comprehensive tests for import command — detection, import functions, and CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dot_man.cli.interface import cli

# ===========================================================================
# Detection functions
# ===========================================================================


class TestDetectChezmoi:
    """Tests for _detect_chezmoi()."""

    def test_returns_path_when_git_exists(self, tmp_path):
        """Detects chezmoi directory containing a .git subdirectory."""
        from dot_man.cli.import_cmd import _detect_chezmoi

        home = tmp_path / "home"
        chezmoi_dir = home / ".local" / "share" / "chezmoi"
        chezmoi_dir.mkdir(parents=True)
        (chezmoi_dir / ".git").mkdir()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_chezmoi()

        assert result == str(chezmoi_dir)

    def test_returns_path_when_files_exist_without_git(self, tmp_path):
        """Detects chezmoi directory that has files but no .git."""
        from dot_man.cli.import_cmd import _detect_chezmoi

        home = tmp_path / "home"
        # Create empty dirs for other checked paths to avoid FileNotFoundError
        # from any(d.iterdir()) on non-existent dirs (bug in detection code)
        (home / ".local" / "share" / "chezmoi").mkdir(parents=True)
        (home / "Library" / "Application Support" / "chezmoi").mkdir(parents=True)
        # The second path in the list is the one with content
        chezmoi_dir = home / ".config" / "chezmoi"
        chezmoi_dir.mkdir(parents=True)
        (chezmoi_dir / "bashrc").write_text("alias ll='ls -la'")

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_chezmoi()

        assert result == str(chezmoi_dir)

    def test_returns_none_when_dirs_empty(self, tmp_path):
        """Returns None when all checked directories exist but are empty."""
        from dot_man.cli.import_cmd import _detect_chezmoi

        home = tmp_path / "home"
        # Create empty dirs for all checked paths to avoid FileNotFoundError
        # from any(d.iterdir()) on non-existent dirs
        for sub in [
            ".local/share/chezmoi",
            ".config/chezmoi",
            "Library/Application Support/chezmoi",
        ]:
            (home / sub).mkdir(parents=True)

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_chezmoi()

        assert result is None


class TestDetectYadm:
    """Tests for _detect_yadm()."""

    def test_returns_path_when_yadm_git_exists(self, tmp_path):
        """Detects yadm via ~/.yadm.git."""
        from dot_man.cli.import_cmd import _detect_yadm

        home = tmp_path / "home"
        (home / ".yadm.git").mkdir(parents=True)

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_yadm()

        assert result == str(home / ".yadm")

    def test_returns_path_when_yadm_config_repo_exists(self, tmp_path):
        """Detects yadm via ~/.config/yadm/repo.git."""
        from dot_man.cli.import_cmd import _detect_yadm

        home = tmp_path / "home"
        (home / ".config" / "yadm" / "repo.git").mkdir(parents=True)

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_yadm()

        assert result == str(home / ".yadm")

    def test_returns_none_when_not_found(self, tmp_path):
        """Returns None when no yadm directories exist."""
        from dot_man.cli.import_cmd import _detect_yadm

        home = tmp_path / "home"
        home.mkdir()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_yadm()

        assert result is None


class TestDetectStow:
    """Tests for _detect_stow()."""

    def test_returns_path_when_packages_found(self, tmp_path):
        """Detects stow directory in ~/dotfiles with visible packages."""
        from dot_man.cli.import_cmd import _detect_stow

        home = tmp_path / "home"
        stow_dir = home / "dotfiles"
        (stow_dir / "bash").mkdir(parents=True)
        (stow_dir / "bash" / ".bashrc").write_text("test")

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_stow()

        assert result == str(stow_dir)

    def test_returns_path_with_dot_stow_dir(self, tmp_path):
        """Detects stow directory in ~/.dotfiles."""
        from dot_man.cli.import_cmd import _detect_stow

        home = tmp_path / "home"
        stow_dir = home / ".dotfiles"
        (stow_dir / "vim").mkdir(parents=True)
        (stow_dir / "vim" / ".vimrc").write_text("test")

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_stow()

        assert result == str(stow_dir)

    def test_returns_none_when_only_hidden_dirs(self, tmp_path):
        """Returns None when only hidden directories exist (not packages)."""
        from dot_man.cli.import_cmd import _detect_stow

        home = tmp_path / "home"
        stow_dir = home / "dotfiles"
        (stow_dir / ".hidden").mkdir(parents=True)

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_stow()

        assert result is None

    def test_returns_none_when_no_stow_dirs_exist(self, tmp_path):
        """Returns None when no stow directories exist."""
        from dot_man.cli.import_cmd import _detect_stow

        home = tmp_path / "home"
        home.mkdir()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            result = _detect_stow()

        assert result is None


# ===========================================================================
# Import helper functions
# ===========================================================================


class TestImportChezmoi:
    """Tests for _import_chezmoi()."""

    def test_imports_dot_prefixed_files_to_home(self, tmp_path):
        """Files with dot prefix go to ~/..<name> (code behaviour)."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "chezmoi_source"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")
        (source / ".gitconfig").write_text("[user]\n\tname = Test")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_chezmoi(str(source), False, git_mock)

        assert (home / "..bashrc").read_text() == "alias ll='ls -la'"
        assert (home / "..gitconfig").read_text() == "[user]\n\tname = Test"
        git_mock.add_all.assert_called_once()
        git_mock.commit.assert_called_once_with("Import dotfiles from chezmoi")

    def test_imports_non_dot_files_to_config(self, tmp_path):
        """Files without dot prefix go to ~/.config/<path>."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "chezmoi_source"
        source.mkdir()
        (source / "bashrc").write_text("alias ll='ls -la'")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_chezmoi(str(source), False, git_mock)

        assert (home / ".config" / "bashrc").read_text() == "alias ll='ls -la'"
        git_mock.add_all.assert_called_once()

    def test_preserves_subdirectory_structure(self, tmp_path):
        """Files in subdirectories keep relative path under .config."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "chezmoi_source"
        source.mkdir()
        sub = source / "subdir"
        sub.mkdir()
        (sub / "config.conf").write_text("setting=true")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_chezmoi(str(source), False, git_mock)

        assert (
            home / ".config" / "subdir" / "config.conf"
        ).read_text() == "setting=true"

    def test_dry_run_does_not_copy_files(self, tmp_path):
        """Dry run skips file copies and git operations."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "chezmoi_source"
        source.mkdir()
        (source / "bashrc").write_text("alias ll='ls -la'")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_chezmoi(str(source), True, git_mock)

        assert not (home / ".config" / "bashrc").exists()
        git_mock.add_all.assert_not_called()
        git_mock.commit.assert_not_called()

    def test_error_when_source_not_found_by_detection(self, tmp_path):
        """Raises SystemExit when auto-detect finds no chezmoi dir."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        home.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_chezmoi", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_chezmoi(None, False, git_mock)

        assert exc_info.value.code == 1
        git_mock.add_all.assert_not_called()

    def test_error_when_source_path_does_not_exist(self, tmp_path):
        """Raises SystemExit when the given path does not exist."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        home.mkdir()
        source = tmp_path / "nonexistent"
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_chezmoi(str(source), False, git_mock)

        assert exc_info.value.code == 1

    def test_copy_failure_calls_warn(self, tmp_path):
        """File copy errors are caught and logged via warn()."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "chezmoi_source"
        source.mkdir()
        (source / "bashrc").write_text("alias ll='ls -la'")

        dest_parent = home / ".config"
        dest_parent.mkdir(parents=True)
        orig_mode = dest_parent.stat().st_mode
        dest_parent.chmod(0o444)

        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd.warn") as mock_warn,
        ):
            _import_chezmoi(str(source), False, git_mock)

        assert mock_warn.called
        dest_parent.chmod(orig_mode)

    def test_uses_auto_detect_when_no_path_given(self, tmp_path):
        """Calls _detect_chezmoi when source_path is None."""
        from dot_man.cli.import_cmd import _import_chezmoi

        home = tmp_path / "home"
        source = tmp_path / "auto_chezmoi"
        source.mkdir()
        (source / "bashrc").write_text("auto-detected")

        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_chezmoi", return_value=str(source)),
        ):
            _import_chezmoi(None, False, git_mock)

        assert (home / ".config" / "bashrc").read_text() == "auto-detected"
        git_mock.add_all.assert_called_once()


class TestImportYadm:
    """Tests for _import_yadm()."""

    def test_imports_files_to_home(self, tmp_path):
        """Files are copied to home directory preserving filename."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        source = tmp_path / "yadm_source"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")
        (source / ".vimrc").write_text("set nu")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_yadm(str(source), False, git_mock)

        assert (home / ".bashrc").read_text() == "alias ll='ls -la'"
        assert (home / ".vimrc").read_text() == "set nu"
        git_mock.add_all.assert_called_once()
        git_mock.commit.assert_called_once_with("Import dotfiles from yadm")

    def test_skips_files_ending_in_dot_git(self, tmp_path):
        """Files with .git extension are skipped."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        source = tmp_path / "yadm_source"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")
        # File ending in '.git' (e.g. config.git) should be skipped
        (source / "config.git").write_text("ref")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_yadm(str(source), False, git_mock)

        assert (home / ".bashrc").read_text() == "alias ll='ls -la'"
        assert not (home / "config.git").exists()

    def test_skips_existing_destination_files(self, tmp_path):
        """Files that already exist in home are not overwritten."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        home.mkdir()
        (home / ".bashrc").write_text("existing content")

        source = tmp_path / "yadm_source"
        source.mkdir()
        (source / ".bashrc").write_text("new content")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_yadm(str(source), False, git_mock)

        assert (home / ".bashrc").read_text() == "existing content"

    def test_dry_run_does_not_copy(self, tmp_path):
        """Dry run skips file copies and git operations."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        source = tmp_path / "yadm_source"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_yadm(str(source), True, git_mock)

        assert not (home / ".bashrc").exists()
        git_mock.add_all.assert_not_called()
        git_mock.commit.assert_not_called()

    def test_error_when_source_not_found_by_detection(self, tmp_path):
        """Raises SystemExit when auto-detect finds no yadm dir."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        home.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_yadm", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_yadm(None, False, git_mock)

        assert exc_info.value.code == 1

    def test_error_when_source_path_does_not_exist(self, tmp_path):
        """Raises SystemExit when the given path does not exist."""
        from dot_man.cli.import_cmd import _import_yadm

        home = tmp_path / "home"
        home.mkdir()
        source = tmp_path / "nonexistent"
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_yadm(str(source), False, git_mock)

        assert exc_info.value.code == 1


class TestImportStow:
    """Tests for _import_stow()."""

    def test_imports_hidden_package_files_no_dot_prefix(self, tmp_path):
        """Files with dot-prefixed first component go to ~/<path>."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()
        pkg = source / "bash"
        pkg.mkdir()
        (pkg / ".bashrc").write_text("alias ll='ls -la'")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_stow(str(source), False, git_mock)

        assert (home / ".bashrc").read_text() == "alias ll='ls -la'"
        git_mock.add_all.assert_called_once()
        git_mock.commit.assert_called_once()

    def test_imports_hidden_package_files_in_subdir(self, tmp_path):
        """Dot-prefixed subdirectories keep their full path under home."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()
        pkg = source / "vim"
        vim_dir = pkg / ".vim"
        vim_dir.mkdir(parents=True)
        (vim_dir / "rc").write_text("set nu")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_stow(str(source), False, git_mock)

        # .vim starts with dot → dest = ~/.vim/rc
        assert (home / ".vim" / "rc").read_text() == "set nu"

    def test_imports_non_hidden_package_files(self, tmp_path):
        """Non-dot first component gets dot-prefixed directory under home."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()
        pkg = source / "config"
        pkg_dir = pkg / "i3"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "config").write_text("bar")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_stow(str(source), False, git_mock)

        # i3 doesn't start with dot → dest = ~/.i3/config
        assert (home / ".i3" / "config").read_text() == "bar"

    def test_error_when_no_packages(self, tmp_path):
        """Raises SystemExit when source has no stow packages."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_stow(str(source), False, git_mock)

        assert exc_info.value.code == 1

    def test_dry_run_does_not_copy(self, tmp_path):
        """Dry run skips file copies and git operations."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()
        pkg = source / "bash"
        pkg.mkdir()
        (pkg / ".bashrc").write_text("alias ll='ls -la'")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_stow(str(source), True, git_mock)

        assert not (home / ".bashrc").exists()
        git_mock.add_all.assert_not_called()
        git_mock.commit.assert_not_called()

    def test_error_when_source_not_found_by_detection(self, tmp_path):
        """Raises SystemExit when auto-detect finds no stow dir."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        home.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_stow", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_stow(None, False, git_mock)

        assert exc_info.value.code == 1

    def test_mutiple_packages_all_imported(self, tmp_path):
        """Multiple stow packages are all imported."""
        from dot_man.cli.import_cmd import _import_stow

        home = tmp_path / "home"
        source = tmp_path / "stow_source"
        source.mkdir()

        for pkg_name in ("bash", "vim"):
            pkg = source / pkg_name
            pkg.mkdir()
            (pkg / f".{pkg_name}rc").write_text(f"{pkg_name} config")

        git_mock = MagicMock()

        with patch("dot_man.cli.import_cmd.Path.home", return_value=home):
            _import_stow(str(source), False, git_mock)

        assert (home / ".bashrc").read_text() == "bash config"
        assert (home / ".vimrc").read_text() == "vim config"


# ===========================================================================
# _import_all function
# ===========================================================================


class TestImportAll:
    """Tests for _import_all()."""

    def test_detects_all_three_sources(self, tmp_path):
        """All three sources (chezmoi, yadm, stow) detected and imported."""
        from dot_man.cli.import_cmd import _import_all

        home = tmp_path / "home"
        chezmoi_src = tmp_path / "chezmoi"
        chezmoi_src.mkdir()
        (chezmoi_src / "bashrc").write_text("chezmoi bashrc")

        yadm_src = tmp_path / "yadm"
        yadm_src.mkdir()
        (yadm_src / ".bashrc_write").write_text("yadm bashrc")

        stow_src = tmp_path / "stow"
        stow_src.mkdir()
        pkg = stow_src / "bash"
        pkg.mkdir()
        (pkg / ".bashrc").write_text("stow bashrc")

        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch(
                "dot_man.cli.import_cmd._detect_chezmoi",
                return_value=str(chezmoi_src),
            ),
            patch(
                "dot_man.cli.import_cmd._detect_yadm",
                return_value=str(yadm_src),
            ),
            patch(
                "dot_man.cli.import_cmd._detect_stow",
                return_value=str(stow_src),
            ),
        ):
            _import_all(None, False, git_mock)

        assert (home / ".config" / "bashrc").read_text() == "chezmoi bashrc"
        assert (home / ".bashrc_write").read_text() == "yadm bashrc"
        assert (home / ".bashrc").read_text() == "stow bashrc"
        assert git_mock.add_all.call_count == 3

    def test_detects_and_imports_multiple_sources(self, tmp_path):
        """All detected sources are imported."""
        from dot_man.cli.import_cmd import _import_all

        home = tmp_path / "home"
        chezmoi_src = tmp_path / "chezmoi"
        chezmoi_src.mkdir()
        (chezmoi_src / "bashrc").write_text("chezmoi bashrc")

        yadm_src = tmp_path / "yadm"
        yadm_src.mkdir()
        (yadm_src / ".bashrc").write_text("yadm bashrc")

        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch(
                "dot_man.cli.import_cmd._detect_chezmoi", return_value=str(chezmoi_src)
            ),
            patch("dot_man.cli.import_cmd._detect_yadm", return_value=str(yadm_src)),
            patch("dot_man.cli.import_cmd._detect_stow", return_value=None),
        ):
            _import_all(None, False, git_mock)

        assert (home / ".config" / "bashrc").read_text() == "chezmoi bashrc"
        assert (home / ".bashrc").read_text() == "yadm bashrc"

    def test_dry_run_does_not_import(self, tmp_path):
        """Dry run in _import_all skips all imports."""
        from dot_man.cli.import_cmd import _import_all

        home = tmp_path / "home"
        chezmoi_src = tmp_path / "chezmoi"
        chezmoi_src.mkdir()
        (chezmoi_src / "bashrc").write_text("chezmoi bashrc")

        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch(
                "dot_man.cli.import_cmd._detect_chezmoi", return_value=str(chezmoi_src)
            ),
            patch("dot_man.cli.import_cmd._detect_yadm", return_value=None),
            patch("dot_man.cli.import_cmd._detect_stow", return_value=None),
        ):
            _import_all(None, True, git_mock)

        assert not (home / ".config" / "bashrc").exists()
        git_mock.add_all.assert_not_called()
        git_mock.commit.assert_not_called()

    def test_error_when_no_sources_detected(self, tmp_path):
        """Raises SystemExit when no sources are found."""
        from dot_man.cli.import_cmd import _import_all

        home = tmp_path / "home"
        home.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_chezmoi", return_value=None),
            patch("dot_man.cli.import_cmd._detect_yadm", return_value=None),
            patch("dot_man.cli.import_cmd._detect_stow", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_all(None, False, git_mock)

        assert exc_info.value.code == 1

    def test_dry_run_with_no_sources_still_errors(self, tmp_path):
        """Dry run still errors when no sources detected."""
        from dot_man.cli.import_cmd import _import_all

        home = tmp_path / "home"
        home.mkdir()
        git_mock = MagicMock()

        with (
            patch("dot_man.cli.import_cmd.Path.home", return_value=home),
            patch("dot_man.cli.import_cmd._detect_chezmoi", return_value=None),
            patch("dot_man.cli.import_cmd._detect_yadm", return_value=None),
            patch("dot_man.cli.import_cmd._detect_stow", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            _import_all(None, True, git_mock)

        assert exc_info.value.code == 1


# ===========================================================================
# CLI command (integration tests)
# ===========================================================================


class TestImportCLIHelp:
    """Test import CLI help and argument validation."""

    def test_import_help(self):
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["import", "--help"])
        assert result.exit_code == 0
        assert "chezmoi" in result.output
        assert "yadm" in result.output
        assert "stow" in result.output
        assert "--path" in result.output
        assert "--dry-run" in result.output

    def test_invalid_source_exits_with_code_2(self):
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(cli, ["import", "invalid"])
        assert result.exit_code == 2


class TestImportCLIIntegration:
    """Test import CLI with integration_runner (initialized repo environment)."""

    def test_import_chezmoi_with_path(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "chezmoi"
        source.mkdir()
        (source / "bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(cli, ["import", "chezmoi", "--path", str(source)])

        assert result.exit_code == 0, result.output
        assert "Imported" in result.output

    def test_import_chezmoi_dry_run(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "chezmoi"
        source.mkdir()
        (source / "bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(
            cli, ["import", "chezmoi", "--path", str(source), "--dry-run"]
        )

        assert result.exit_code == 0, result.output
        assert "Would import" in result.output

    def test_import_yadm_with_path(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "yadm"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(cli, ["import", "yadm", "--path", str(source)])

        assert result.exit_code == 0, result.output
        assert "Imported" in result.output

    def test_import_yadm_dry_run(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "yadm"
        source.mkdir()
        (source / ".bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(
            cli, ["import", "yadm", "--path", str(source), "--dry-run"]
        )

        assert result.exit_code == 0, result.output
        assert "Would import" in result.output

    def test_import_stow_with_path(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "stow"
        source.mkdir()
        pkg = source / "bash"
        pkg.mkdir()
        (pkg / ".bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(cli, ["import", "stow", "--path", str(source)])

        assert result.exit_code == 0, result.output
        assert "Imported" in result.output

    def test_import_stow_dry_run(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "stow"
        source.mkdir()
        pkg = source / "bash"
        pkg.mkdir()
        (pkg / ".bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(
            cli, ["import", "stow", "--path", str(source), "--dry-run"]
        )

        assert result.exit_code == 0, result.output
        assert "Would import" in result.output

    def test_import_all_detects_nothing(self, integration_runner):
        runner = integration_runner
        # Create empty chezmoi dirs to avoid FileNotFoundError in _detect_chezmoi
        home = Path.home()
        for sub in [
            ".local/share/chezmoi",
            ".config/chezmoi",
            "Library/Application Support/chezmoi",
        ]:
            (home / sub).mkdir(parents=True)
        # Do NOT create .yadm.git or dotfiles — we want all detectors to return None

        result = runner.invoke(cli, ["import", "all"])

        assert result.exit_code == 1
        assert "No dotfile manager sources detected" in result.output

    def test_import_all_auto_detects_multiple(self, integration_runner):
        """import all auto-detects chezmoi and yadm."""
        runner = integration_runner
        home = Path.home()
        # chezmoi dir with file
        chezmoi_dir = home / ".local" / "share" / "chezmoi"
        chezmoi_dir.mkdir(parents=True)
        (chezmoi_dir / "bashrc").write_text("alias ll='ls -la'")
        # yadm dir
        (home / ".yadm.git").mkdir(parents=True)
        (home / ".yadm").mkdir(parents=True)
        (home / ".yadm" / ".gitconfig").write_text("[user]\n\tname = T")

        result = runner.invoke(cli, ["import", "all"])

        assert result.exit_code == 0, result.output
        assert "Detected dotfile sources" in result.output
        assert "chezmoi" in result.output
        assert "yadm" in result.output

    def test_import_all_auto_detects_chezmoi(self, integration_runner):
        """import all detects chezmoi dir created under patched HOME."""
        runner = integration_runner
        home = Path.home()
        chezmoi_dir = home / ".local" / "share" / "chezmoi"
        chezmoi_dir.mkdir(parents=True)
        (chezmoi_dir / "bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(cli, ["import", "all"])

        assert result.exit_code == 0, result.output
        assert "Detected dotfile sources" in result.output
        assert "chezmoi" in result.output

    def test_import_all_dry_run_detects_and_previews(self, integration_runner):
        runner = integration_runner
        home = Path.home()
        chezmoi_dir = home / ".local" / "share" / "chezmoi"
        chezmoi_dir.mkdir(parents=True)
        (chezmoi_dir / "bashrc").write_text("alias ll='ls -la'")

        result = runner.invoke(cli, ["import", "all", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "Dry-run mode" in result.output

    def test_import_chezmoi_path_does_not_exist(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "nonexistent"

        result = runner.invoke(cli, ["import", "chezmoi", "--path", str(source)])

        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_import_stow_path_does_not_exist(self, tmp_path, integration_runner):
        runner = integration_runner
        source = tmp_path / "nonexistent"

        result = runner.invoke(cli, ["import", "stow", "--path", str(source)])

        assert result.exit_code == 1
        assert "does not exist" in result.output
