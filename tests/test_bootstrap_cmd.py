"""Tests for cli/bootstrap_cmd.py — package manager detection and installation."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestDetectPackageManager:
    """Test _detect_package_manager helper."""

    def test_detects_apt_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            with patch("shutil.which", side_effect=lambda cmd: cmd == "apt-get"):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "apt"

    def test_detects_brew_on_darwin(self):
        with patch("platform.system", return_value="Darwin"):
            with patch("shutil.which", side_effect=lambda cmd: cmd == "brew"):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "brew"

    def test_detects_dnf_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            with patch(
                "shutil.which",
                side_effect=lambda cmd: cmd == "dnf",
            ):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "dnf"

    def test_detects_pacman_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            with patch("shutil.which", side_effect=lambda cmd: cmd == "pacman"):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "pacman"

    def test_returns_none_when_no_pm_found(self):
        with patch("platform.system", return_value="Linux"):
            with patch("shutil.which", return_value=None):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() is None

    def test_detects_pkg_on_freebsd(self):
        with patch("platform.system", return_value="FreeBSD"):
            with patch("shutil.which", side_effect=lambda cmd: cmd == "pkg"):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "pkg"

    def test_linux_apt_preferred_over_dnf(self):
        """apt is preferred over dnf on Linux."""
        with patch("platform.system", return_value="Linux"):
            with patch(
                "shutil.which",
                side_effect=lambda cmd: cmd in ("apt-get", "dnf"),
            ):
                from dot_man.cli.bootstrap_cmd import _detect_package_manager

                assert _detect_package_manager() == "apt"


class TestLoadBootstrapPackages:
    """Test _load_bootstrap_packages helper."""

    def test_loads_flat_packages_list(self):
        with patch("dot_man.config.DotManConfig") as MockConfig:
            mock_instance = MagicMock()
            mock_instance._data = {"bootstrap": {"packages": ["neovim", "tmux"]}}
            MockConfig.return_value = mock_instance

            from dot_man.cli.bootstrap_cmd import _load_bootstrap_packages

            result = _load_bootstrap_packages()
            assert result == {"default": ["neovim", "tmux"]}

    def test_loads_grouped_packages(self):
        with patch("dot_man.config.DotManConfig") as MockConfig:
            mock_instance = MagicMock()
            mock_instance._data = {
                "bootstrap": {"shells": ["fish", "zsh"], "editors": ["neovim"]}
            }
            MockConfig.return_value = mock_instance

            from dot_man.cli.bootstrap_cmd import _load_bootstrap_packages

            result = _load_bootstrap_packages()
            assert result == {"shells": ["fish", "zsh"], "editors": ["neovim"]}

    def test_returns_empty_when_no_bootstrap_section(self):
        with patch("dot_man.config.DotManConfig") as MockConfig:
            mock_instance = MagicMock()
            mock_instance._data = {}
            MockConfig.return_value = mock_instance

            from dot_man.cli.bootstrap_cmd import _load_bootstrap_packages

            result = _load_bootstrap_packages()
            assert result == {}

    def test_returns_empty_on_exception(self):
        with patch(
            "dot_man.config.DotManConfig",
            side_effect=RuntimeError("boom"),
        ):
            from dot_man.cli.bootstrap_cmd import _load_bootstrap_packages

            result = _load_bootstrap_packages()
            assert result == {}


class TestRunWithPm:
    """Test _run_with_pm helper."""

    def test_returns_true_on_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            with patch("dot_man.cli.bootstrap_cmd.ui"):
                from dot_man.cli.bootstrap_cmd import _run_with_pm

                assert _run_with_pm("brew", "brew install {package}", "git") is True

    def test_returns_false_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="Error: not found\nLine2\nLine3\nLine4"
            )
            with patch("dot_man.cli.bootstrap_cmd.ui"):
                with patch("dot_man.cli.bootstrap_cmd.warn"):
                    from dot_man.cli.bootstrap_cmd import _run_with_pm

                    assert _run_with_pm("apt", "apt install {package}", "fake") is False

    def test_returns_false_on_timeout(self):
        import subprocess as sp

        with patch("subprocess.run", side_effect=sp.TimeoutExpired("cmd", 300)):
            with patch("dot_man.cli.bootstrap_cmd.ui"):
                with patch("dot_man.cli.bootstrap_cmd.warn"):
                    from dot_man.cli.bootstrap_cmd import _run_with_pm

                    assert (
                        _run_with_pm("apt", "apt install {package}", "big-pkg") is False
                    )

    def test_returns_false_on_generic_exception(self):
        with patch("subprocess.run", side_effect=OSError("permission denied")):
            with patch("dot_man.cli.bootstrap_cmd.ui"):
                with patch("dot_man.cli.bootstrap_cmd.warn"):
                    from dot_man.cli.bootstrap_cmd import _run_with_pm

                    assert _run_with_pm("apt", "apt install {package}", "pkg") is False


class TestBootstrapCommand:
    """Test the bootstrap CLI command."""

    def test_no_packages_no_pm_exits(self, runner):
        """Exits when no PM detected and no packages given."""
        with patch(
            "dot_man.cli.bootstrap_cmd._detect_package_manager", return_value=None
        ):
            result = runner.invoke(cli, ["bootstrap"])
            assert result.exit_code != 0

    def test_unknown_pm_exits(self, runner):
        with patch(
            "dot_man.cli.bootstrap_cmd.PACKAGE_MANAGERS",
            {"brew": {"install": "brew install {package}", "detect": "brew"}},
        ):
            result = runner.invoke(cli, ["bootstrap", "--pm", "unknown-pm", "git"])
            assert result.exit_code != 0

    def test_list_mode(self, runner):
        result = runner.invoke(
            cli, ["bootstrap", "--pm", "apt", "--list", "git", "curl"]
        )
        assert result.exit_code == 0
        assert "git" in result.output
        assert "curl" in result.output

    def test_install_packages(self, runner):
        with patch("dot_man.cli.bootstrap_cmd._run_with_pm", return_value=True):
            result = runner.invoke(cli, ["bootstrap", "--pm", "apt", "git", "curl"])
            assert result.exit_code == 0

    def test_install_with_failures(self, runner):
        call_count = 0

        def mock_run_with_pm(pm, template, pkg):
            nonlocal call_count
            call_count += 1
            return call_count != 2  # Second package fails

        with patch(
            "dot_man.cli.bootstrap_cmd._run_with_pm", side_effect=mock_run_with_pm
        ):
            result = runner.invoke(
                cli, ["bootstrap", "--pm", "apt", "git", "fail-pkg", "curl"]
            )
            assert result.exit_code == 0
            assert "1 failed" in result.output

    def test_update_flag(self, runner):
        with patch("dot_man.cli.bootstrap_cmd._run_with_pm", return_value=True):
            result = runner.invoke(cli, ["bootstrap", "--pm", "apt", "--update", "git"])
            assert result.exit_code == 0

    def test_no_packages_shows_usage(self, runner):
        with patch(
            "dot_man.cli.bootstrap_cmd._load_bootstrap_packages", return_value={}
        ):
            result = runner.invoke(cli, ["bootstrap", "--pm", "apt"])
            assert result.exit_code == 0
            assert "No packages" in result.output

    def test_config_packages(self, runner):
        with patch(
            "dot_man.cli.bootstrap_cmd._load_bootstrap_packages",
            return_value={"default": ["neovim", "tmux"]},
        ):
            with patch("dot_man.cli.bootstrap_cmd._run_with_pm", return_value=True):
                result = runner.invoke(cli, ["bootstrap", "--pm", "apt"])
                assert result.exit_code == 0

    def test_config_packages_list_mode(self, runner):
        with patch(
            "dot_man.cli.bootstrap_cmd._load_bootstrap_packages",
            return_value={"shells": ["fish"], "editors": ["neovim"]},
        ):
            result = runner.invoke(cli, ["bootstrap", "--pm", "apt", "--list"])
            assert result.exit_code == 0
            assert "fish" in result.output
            assert "neovim" in result.output

    def test_package_managers_dict_completeness(self):
        """Ensure all expected package managers are defined."""
        from dot_man.cli.bootstrap_cmd import PACKAGE_MANAGERS

        expected = {
            "brew",
            "apt",
            "dnf",
            "pacman",
            "zypper",
            "nix-env",
            "xbps-install",
            "pkg",
        }
        assert set(PACKAGE_MANAGERS.keys()) == expected

        for pm, info in PACKAGE_MANAGERS.items():
            assert "install" in info
            assert "update" in info
            assert "detect" in info
            assert "{package}" in info["install"] or pm in ("nix-env",)
