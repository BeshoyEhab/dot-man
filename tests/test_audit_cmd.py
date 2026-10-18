"""Tests for cli/audit_cmd.py — audit command."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir


class TestAuditHelp:
    def test_audit_help(self, runner):
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "audit" in result.output.lower()


class TestAuditWithoutInit:
    def test_audit_runs_without_init(self, uninitialized_runner):
        result = uninitialized_runner.invoke(cli, ["audit"])
        assert result.exit_code == 1, result.output


class TestAuditOptions:
    def test_audit_strict_option(self, runner):
        """Test --strict option is recognized."""
        result = runner.invoke(cli, ["audit", "--help"])
        assert "--strict" in result.output

    def test_audit_fix_option(self, runner):
        """Test --fix option is recognized."""
        result = runner.invoke(cli, ["audit", "--help"])
        assert "--fix" in result.output

    def test_audit_dry_run_option(self, runner):
        """Test --dry-run option is recognized."""
        result = runner.invoke(cli, ["audit", "--help"])
        assert "--dry-run" in result.output


class TestAuditFixDryRun:
    """--fix --dry-run previews redactions without touching anything."""

    def _repo_with_secret(self, tmp_path):
        from dot_man.secrets import SecretMatch, Severity

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        secret_file = repo / "creds.txt"
        secret_file.write_text("token = 'super-secret-value'\n")
        match = SecretMatch(
            file=secret_file,
            line_number=1,
            line_content="token = 'super-secret-value'",
            pattern_name="Generic Secret",
            severity=Severity.MEDIUM,
            matched_text="super-secret-value",
        )
        return repo, secret_file, match

    def test_dry_run_leaves_files_and_history_untouched(self, tmp_path):
        from dot_man.cli import audit_cmd

        repo, secret_file, match = self._repo_with_secret(tmp_path)

        with (
            patch("dot_man.constants.DOT_MAN_DIR", repo),
            patch("dot_man.constants.REPO_DIR", repo),
            patch("dot_man.cli.audit_cmd.get_custom_scanner") as MockScanner,
            patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard,
            patch("dot_man.cli.audit_cmd.PermanentRedactGuard") as MockPerm,
            patch("dot_man.cli.audit_cmd.GitManager") as MockGit,
        ):
            MockScanner.return_value.scan_directory.return_value = [match]
            MockGuard.return_value.is_allowed.return_value = False
            MockPerm.return_value.should_redact.return_value = False

            result = CliRunner().invoke(audit_cmd.audit, ["--fix", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert secret_file.read_text() == "token = 'super-secret-value'\n"
        MockScanner.return_value.redact_content.assert_not_called()
        MockGit.return_value.commit.assert_not_called()
        assert "dry-run" in result.output.lower()
