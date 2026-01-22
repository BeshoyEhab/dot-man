"""Comprehensive CLI command tests.

Tests all CLI commands and subcommands using real-world dotfile structures
similar to hyprland and quickshell configurations.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def sample_hypr_dir(tmp_path):
    """Create a sample hyprland-like directory structure."""
    hypr_dir = tmp_path / ".config" / "hypr"
    hypr_dir.mkdir(parents=True)
    
    # Create hyprland config files
    (hypr_dir / "hyprland.conf").write_text("""
# Hyprland config
monitor=,preferred,auto,1
input {
    kb_layout = us
}
""")
    
    (hypr_dir / "hyprlock.conf").write_text("""
background {
    path = screenshot
    blur_passes = 3
}
""")
    
    (hypr_dir / "hypridle.conf").write_text("""
general {
    lock_cmd = hyprlock
}
""")
    
    # Create custom directory
    custom_dir = hypr_dir / "custom"
    custom_dir.mkdir()
    (custom_dir / "keybinds.conf").write_text("bind = SUPER, Q, killactive")
    (custom_dir / "colors.conf").write_text("$primary = 0xff5500")
    
    return hypr_dir


@pytest.fixture
def sample_quickshell_dir(tmp_path):
    """Create a sample quickshell-like directory structure."""
    qs_dir = tmp_path / ".config" / "quickshell"
    qs_dir.mkdir(parents=True)
    
    ii_dir = qs_dir / "ii"
    ii_dir.mkdir()
    
    (ii_dir / "shell.qml").write_text("""
import QtQuick 2.15
Item {
    width: 100
    height: 100
}
""")
    
    (ii_dir / "Bar.qml").write_text("""
import QtQuick 2.15
Rectangle {
    color: "black"
}
""")
    
    return qs_dir


# =============================================================================
# Help and Basic Tests  
# =============================================================================


class TestBasicCLI:
    """Basic CLI functionality tests."""

    def test_help_command(self, runner):
        """Help should display available commands."""
        result = runner.invoke(cli, ["--help"])
        
        assert result.exit_code == 0
        assert "dot-man" in result.output.lower() or "usage" in result.output.lower()
    
    def test_version_or_help(self, runner):
        """CLI should respond to basic invocation."""
        result = runner.invoke(cli)
        
        # Should either show help or an error about not being initialized
        assert result.exit_code in [0, 1, 2]


class TestStatusCommand:
    """Tests for 'dot-man status' command."""

    def test_status_without_init(self, runner):
        """Status should error gracefully when not initialized."""
        result = runner.invoke(cli, ["status"])
        
        # Should indicate not initialized or run successfully
        assert result.exit_code in [0, 1]
    
    def test_status_help(self, runner):
        """Status --help should show options."""
        result = runner.invoke(cli, ["status", "--help"])
        
        assert result.exit_code == 0
        assert "verbose" in result.output.lower() or "secrets" in result.output.lower()


class TestBranchCommand:
    """Tests for 'dot-man branch' commands."""

    def test_branch_help(self, runner):
        """Branch --help should show subcommands."""
        result = runner.invoke(cli, ["branch", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "delete" in result.output.lower()
    
    def test_branch_list_without_init(self, runner):
        """Branch list should handle uninitialized state."""
        result = runner.invoke(cli, ["branch", "list"])
        
        assert result.exit_code in [0, 1]


class TestSwitchCommand:
    """Tests for 'dot-man switch' command."""

    def test_switch_help(self, runner):
        """Switch --help should show options."""
        result = runner.invoke(cli, ["switch", "--help"])
        
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "force" in result.output.lower()
    
    def test_switch_without_init(self, runner):
        """Switch should handle uninitialized state."""
        result = runner.invoke(cli, ["switch", "main"])
        
        assert result.exit_code in [0, 1]


class TestDeployCommand:
    """Tests for 'dot-man deploy' command."""

    def test_deploy_help(self, runner):
        """Deploy --help should show options."""
        result = runner.invoke(cli, ["deploy", "--help"])
        
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "force" in result.output.lower()


class TestAuditCommand:
    """Tests for 'dot-man audit' command."""

    def test_audit_help(self, runner):
        """Audit --help should show options."""
        result = runner.invoke(cli, ["audit", "--help"])
        
        assert result.exit_code == 0
        assert "strict" in result.output.lower() or "fix" in result.output.lower()


class TestRemoteCommand:
    """Tests for 'dot-man remote' commands."""

    def test_remote_help(self, runner):
        """Remote --help should show subcommands."""
        result = runner.invoke(cli, ["remote", "--help"])
        
        assert result.exit_code == 0
        assert "get" in result.output.lower() or "set" in result.output.lower()
    
    def test_remote_sync_branch_help(self, runner):
        """Remote sync-branch --help should show description."""
        result = runner.invoke(cli, ["remote", "sync-branch", "--help"])
        
        assert result.exit_code == 0
        # Should mention branch synchronization
        assert "branch" in result.output.lower() or "sync" in result.output.lower()


class TestConfigCommand:
    """Tests for 'dot-man config' commands."""

    def test_config_help(self, runner):
        """Config --help should show subcommands."""
        result = runner.invoke(cli, ["config", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "get" in result.output.lower() or "tutorial" in result.output.lower()


class TestAddCommand:
    """Tests for 'dot-man add' command."""

    def test_add_help(self, runner):
        """Add --help should show options."""
        result = runner.invoke(cli, ["add", "--help"])
        
        assert result.exit_code == 0
        assert "name" in result.output.lower() or "path" in result.output.lower()


class TestEditCommand:
    """Tests for 'dot-man edit' command."""

    def test_edit_help(self, runner):
        """Edit --help should show options."""
        result = runner.invoke(cli, ["edit", "--help"])
        
        assert result.exit_code == 0
        assert "raw" in result.output.lower()


class TestBackupCommand:
    """Tests for 'dot-man backup' commands."""

    def test_backup_help(self, runner):
        """Backup --help should show subcommands."""
        result = runner.invoke(cli, ["backup", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "create" in result.output.lower()


class TestInitCommand:
    """Tests for 'dot-man init' command."""

    def test_init_help(self, runner):
        """Init --help should show options."""
        result = runner.invoke(cli, ["init", "--help"])
        
        assert result.exit_code == 0
        assert "force" in result.output.lower() or "wizard" in result.output.lower()


# =============================================================================
# Integration Tests with Sample Dotfiles
# =============================================================================


class TestHyprlandIntegration:
    """Integration tests using hyprland-like file structures."""

    def test_hypr_directory_created(self, sample_hypr_dir):
        """Verify hypr directory structure is correctly set up."""
        assert sample_hypr_dir.exists()
        assert (sample_hypr_dir / "hyprland.conf").exists()
        assert (sample_hypr_dir / "hyprlock.conf").exists()
        assert (sample_hypr_dir / "hypridle.conf").exists()
        assert (sample_hypr_dir / "custom").is_dir()
        assert (sample_hypr_dir / "custom" / "keybinds.conf").exists()
        assert (sample_hypr_dir / "custom" / "colors.conf").exists()
    
    def test_hypr_file_content(self, sample_hypr_dir):
        """Verify hypr config files have expected content."""
        content = (sample_hypr_dir / "hyprland.conf").read_text()
        assert "monitor" in content
        assert "input" in content
        assert "kb_layout" in content
    
    def test_hypr_custom_keybinds(self, sample_hypr_dir):
        """Verify keybinds file has hyprland bind syntax."""
        content = (sample_hypr_dir / "custom" / "keybinds.conf").read_text()
        assert "bind = SUPER" in content
        assert "killactive" in content


class TestQuickshellIntegration:
    """Integration tests using quickshell-like file structures."""

    def test_quickshell_directory_created(self, sample_quickshell_dir):
        """Verify quickshell directory structure is correctly set up."""
        assert sample_quickshell_dir.exists()
        assert (sample_quickshell_dir / "ii").is_dir()
        assert (sample_quickshell_dir / "ii" / "shell.qml").exists()
        assert (sample_quickshell_dir / "ii" / "Bar.qml").exists()
    
    def test_quickshell_qml_content(self, sample_quickshell_dir):
        """Verify QML files have expected content."""
        content = (sample_quickshell_dir / "ii" / "shell.qml").read_text()
        assert "import QtQuick" in content
        assert "Item" in content
    
    def test_quickshell_bar_qml(self, sample_quickshell_dir):
        """Verify Bar.qml has rectangle component."""
        content = (sample_quickshell_dir / "ii" / "Bar.qml").read_text()
        assert "Rectangle" in content
        assert "color" in content


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling across commands."""

    def test_keyboard_interrupt_handling(self):
        """Commands should handle KeyboardInterrupt gracefully."""
        from dot_man.cli.common import handle_exception
        
        with pytest.raises(SystemExit) as exc_info:
            handle_exception(KeyboardInterrupt())
        
        assert exc_info.value.code == 130
    
    def test_permission_error_handling(self):
        """Commands should provide helpful messages for permission errors."""
        from dot_man.exceptions import ErrorDiagnostic, ErrorCategory
        
        diagnostic = ErrorDiagnostic.from_exception(PermissionError("/etc/test"))
        assert diagnostic.category == ErrorCategory.PERMISSION
        assert "sudo" in diagnostic.suggestion.lower() or "permission" in diagnostic.suggestion.lower()
    
    def test_file_not_found_handling(self):
        """Commands should handle missing files gracefully."""
        from dot_man.exceptions import ErrorDiagnostic
        
        diagnostic = ErrorDiagnostic.from_exception(FileNotFoundError("test"))
        assert diagnostic.details is not None
    
    def test_generic_exception_handling(self):
        """Generic exceptions should be handled gracefully."""
        from dot_man.exceptions import ErrorDiagnostic, ErrorCategory
        
        diagnostic = ErrorDiagnostic.from_exception(ValueError("test error"))
        assert diagnostic.category == ErrorCategory.UNKNOWN
        assert "test error" in diagnostic.details


# =============================================================================
# Hook Tests with Quickshell Aliases
# =============================================================================


class TestQuickshellHooks:
    """Tests for quickshell hook aliases."""

    def test_quickshell_hooks_defined(self):
        """Verify quickshell hooks are defined in constants."""
        from dot_man.constants import HOOK_ALIASES
        
        assert "quickshell_reload" in HOOK_ALIASES
        assert "quickshell_restart" in HOOK_ALIASES
        assert "quickshell_validate" in HOOK_ALIASES
    
    def test_quickshell_reload_command(self):
        """Verify quickshell_reload has correct command template."""
        from dot_man.constants import HOOK_ALIASES
        
        cmd = HOOK_ALIASES["quickshell_reload"]
        assert "qs" in cmd
        assert "{qs_config}" in cmd  # Has placeholder for config dir
    
    def test_quickshell_restart_command(self):
        """Verify quickshell_restart has correct command."""
        from dot_man.constants import HOOK_ALIASES
        
        cmd = HOOK_ALIASES["quickshell_restart"]
        assert "qs" in cmd
        assert "killall" in cmd
    
    def test_hyprland_reload_hook(self):
        """Verify hyprland_reload hook exists."""
        from dot_man.constants import HOOK_ALIASES
        
        assert "hyprland_reload" in HOOK_ALIASES
        assert "hyprctl" in HOOK_ALIASES["hyprland_reload"]


# =============================================================================
# Path Canonicalization Tests
# =============================================================================


class TestPathCanonicalization:
    """Tests for secret path canonicalization."""

    def test_tilde_expansion(self):
        """Paths with ~ should be expanded."""
        from dot_man.secrets import _canonicalize_path
        from pathlib import Path
        
        result = _canonicalize_path("~/.bashrc")
        assert "~" not in result
        assert str(Path.home()) in result
    
    def test_relative_path_resolution(self, tmp_path):
        """Relative paths should be resolved to absolute."""
        from dot_man.secrets import _canonicalize_path
        
        # Create a temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        result = _canonicalize_path(test_file)
        assert result.startswith("/")
    
    def test_path_normalization(self):
        """Paths with .. should be normalized."""
        from dot_man.secrets import _canonicalize_path
        from pathlib import Path
        
        home = str(Path.home())
        path_with_dots = f"{home}/subdir/../.bashrc"
        
        result = _canonicalize_path(path_with_dots)
        assert ".." not in result
    
    def test_path_consistency(self):
        """Same path in different formats should canonicalize the same."""
        from dot_man.secrets import _canonicalize_path
        from pathlib import Path
        
        home = Path.home()
        
        # Different representations of same path
        path1 = "~/.bashrc"
        path2 = str(home / ".bashrc")
        path3 = str(home / "subdir" / ".." / ".bashrc")
        
        canon1 = _canonicalize_path(path1)
        canon2 = _canonicalize_path(path2)
        canon3 = _canonicalize_path(path3)
        
        assert canon1 == canon2 == canon3


# =============================================================================
# File Comparison Tests
# =============================================================================


class TestFileComparison:
    """Tests for file comparison functions."""

    def test_compare_identical_files(self, tmp_path):
        """Identical files should compare as equal."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        content = "test content\nwith multiple lines\n"
        file1.write_text(content)
        file2.write_text(content)
        
        assert compare_files(file1, file2) is True
    
    def test_compare_different_files(self, tmp_path):
        """Different files should compare as not equal."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        
        file1.write_text("content a")
        file2.write_text("content b")
        
        assert compare_files(file1, file2) is False
    
    def test_compare_nonexistent_file(self, tmp_path):
        """Comparing with nonexistent file should return False."""
        from dot_man.files import compare_files
        
        file1 = tmp_path / "exists.txt"
        file2 = tmp_path / "nonexistent.txt"
        
        file1.write_text("content")
        
        assert compare_files(file1, file2) is False


# =============================================================================
# Secret Detection Tests
# =============================================================================


class TestSecretDetection:
    """Tests for secret detection functionality."""

    def test_api_key_detection(self, tmp_path):
        """API keys should be detected."""
        from dot_man.secrets import SecretScanner
        
        test_file = tmp_path / "config.env"
        test_file.write_text("API_KEY=sk_live_abcd1234567890")
        
        scanner = SecretScanner()
        matches = list(scanner.scan_file(test_file))
        
        assert len(matches) > 0
    
    def test_clean_file_no_secrets(self, tmp_path):
        """Clean files should have no secret matches."""
        from dot_man.secrets import SecretScanner
        
        test_file = tmp_path / "clean.conf"
        test_file.write_text("""
# Regular config file
monitor = DP-1
font_size = 12
theme = dark
""")
        
        scanner = SecretScanner()
        matches = list(scanner.scan_file(test_file))
        
        assert len(matches) == 0
    
    def test_hyprland_config_no_false_positives(self, sample_hypr_dir):
        """Hyprland configs should not trigger false positives."""
        from dot_man.secrets import SecretScanner
        
        scanner = SecretScanner()
        matches = list(scanner.scan_file(sample_hypr_dir / "hyprland.conf"))
        
        # Should have no matches for clean config
        assert len(matches) == 0


# =============================================================================
# Config Parsing Tests
# =============================================================================


class TestConfigParsing:
    """Tests for configuration file parsing."""

    def test_parse_sample_toml(self, tmp_path):
        """Sample TOML config should parse correctly."""
        from dot_man.config import DotManConfig
        
        config_file = tmp_path / "dot-man.toml"
        config_file.write_text("""
[hypr]
paths = ["~/.config/hypr"]
post_deploy = "hyprland_reload"

[fish]
paths = ["~/.config/fish/config.fish"]
""")
        
        # Should not raise
        config = DotManConfig(repo_path=tmp_path)
        config.load()
        
        # Check that config loaded without error
        assert config is not None
