"""Tests for config command."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestConfigCommand:
    """Tests for dot-man config command."""

    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage global configuration" in result.output

    def test_config_list_help(self, runner):
        result = runner.invoke(cli, ["config", "list", "--help"])
        assert result.exit_code == 0

    def test_config_get_help(self, runner):
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self, runner):
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code == 0


class TestBranchCommand:
    """Tests for branch command."""

    def test_branch_help(self, runner):
        result = runner.invoke(cli, ["branch", "--help"])
        assert result.exit_code == 0

    def test_branch_list_help(self, runner):
        result = runner.invoke(cli, ["branch", "list", "--help"])
        assert result.exit_code == 0

    def test_branch_delete_help(self, runner):
        result = runner.invoke(cli, ["branch", "delete", "--help"])
        assert result.exit_code == 0


class TestRemoteCommand:
    """Tests for remote command."""

    def test_remote_help(self, runner):
        result = runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0


class TestBackupCommand:
    """Tests for backup command."""

    def test_backup_help(self, runner):
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0


class TestVerifyCommand:
    """Tests for verify command."""

    def test_verify_help(self, runner):
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0


class TestCleanCommand:
    """Tests for clean command."""

    def test_clean_help(self, runner):
        result = runner.invoke(cli, ["clean", "--help"])
        assert result.exit_code == 0


class TestDoctorCommand:
    """Tests for doctor command."""

    def test_doctor_help(self, runner):
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0


class TestOtherCommands:
    """Tests for other commands."""

    def test_edit_help(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0

    def test_revert_help(self, runner):
        result = runner.invoke(cli, ["revert", "--help"])
        assert result.exit_code == 0

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_audit_help(self, runner):
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
