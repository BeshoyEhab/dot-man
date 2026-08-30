"""Extended tests for cli/audit_cmd.py — security audit command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.secrets import SecretMatch


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_repo(tmp_path):
    """Create a minimal repo structure for testing."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    return repo_dir


def make_match(
    repo_dir=None,
    filename="test.txt",
    line=1,
    content="api_key = 'sk-12345'",
    pattern="API Key",
    severity="HIGH",
):
    """Create a SecretMatch for testing."""
    match = MagicMock(spec=SecretMatch)
    if repo_dir:
        match.file = repo_dir / filename
    else:
        match.file = Path("/repo/test.txt")
    match.line_number = line
    match.line_content = content
    match.pattern_name = pattern
    match.severity = MagicMock()
    match.severity.value = severity
    return match


class TestAuditClean:
    """Test audit with no secrets found."""

    def test_no_secrets_found(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = []
                result = runner.invoke(cli, ["audit"])
        assert result.exit_code == 0
        assert "No secrets detected" in result.output

    def test_allowed_secrets_filtered(self, runner, clean_repo):
        """Secrets in the allow-list should not be reported."""
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                match = make_match(repo_dir=clean_repo, filename="test.txt")
                mock_scanner.return_value.scan_directory.return_value = [match]
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = True
                    result = runner.invoke(cli, ["audit"])
            assert result.exit_code == 0
            assert "No secrets detected" in result.output


class TestAuditWithSecrets:
    """Test audit when secrets are found."""

    def test_secrets_grouped_by_severity(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                critical = make_match(
                    repo_dir=clean_repo,
                    severity="CRITICAL",
                    pattern="Private Key",
                    content="-----BEGIN RSA",
                )
                high = make_match(
                    repo_dir=clean_repo,
                    severity="HIGH",
                    pattern="API Key",
                    content="api_key = 'sk-123'",
                )
                mock_scanner.return_value.scan_directory.return_value = [
                    critical,
                    high,
                ]
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = False
                    with patch(
                        "dot_man.cli.audit_cmd.PermanentRedactGuard"
                    ) as MockPerm:
                        MockPerm.return_value.should_redact.return_value = False
                        result = runner.invoke(cli, ["audit"])
        assert result.exit_code == 0
        assert "CRITICAL" in result.output
        assert "HIGH" in result.output
        assert "2 secrets" in result.output

    def test_recommendations_shown(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = [
                    make_match(repo_dir=clean_repo)
                ]
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = False
                    with patch(
                        "dot_man.cli.audit_cmd.PermanentRedactGuard"
                    ) as MockPerm:
                        MockPerm.return_value.should_redact.return_value = False
                        result = runner.invoke(cli, ["audit"])
        assert "Recommendations" in result.output


class TestAuditStrict:
    """Test --strict flag."""

    def test_strict_exits_with_error(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = [
                    make_match(repo_dir=clean_repo)
                ]
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = False
                    with patch(
                        "dot_man.cli.audit_cmd.PermanentRedactGuard"
                    ) as MockPerm:
                        MockPerm.return_value.should_redact.return_value = False
                        result = runner.invoke(cli, ["audit", "--strict"])
        assert result.exit_code == 50
        assert "strict mode" in result.output.lower()

    def test_strict_clean_exits_zero(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = []
                result = runner.invoke(cli, ["audit", "--strict"])
        assert result.exit_code == 0


class TestAuditFix:
    """Test --fix flag."""

    def test_fix_redacts_secrets(self, runner, clean_repo):
        (clean_repo / "config.txt").write_text("api_key = 'sk-secret123'")
        match = make_match(
            repo_dir=clean_repo,
            filename="config.txt",
            content="api_key = 'sk-secret123'",
        )

        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = [match]
                mock_scanner.return_value.redact_content.return_value = (
                    "api_key = '***REDACTED***'",
                    1,
                )
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = False
                    with patch(
                        "dot_man.cli.audit_cmd.PermanentRedactGuard"
                    ) as MockPerm:
                        MockPerm.return_value.should_redact.return_value = False
                        with patch("dot_man.cli.audit_cmd.ui") as mock_ui:
                            mock_ui.confirm.return_value = True
                            with patch("dot_man.cli.audit_cmd.GitManager"):
                                result = runner.invoke(cli, ["audit", "--fix"])
        assert result.exit_code == 0

    def test_fix_aborted_by_user(self, runner, clean_repo):
        with patch("dot_man.cli.audit_cmd.REPO_DIR", clean_repo):
            with patch("dot_man.cli.audit_cmd.get_custom_scanner") as mock_scanner:
                mock_scanner.return_value.scan_directory.return_value = [
                    make_match(repo_dir=clean_repo)
                ]
                with patch("dot_man.cli.audit_cmd.SecretGuard") as MockGuard:
                    MockGuard.return_value.is_allowed.return_value = False
                    with patch(
                        "dot_man.cli.audit_cmd.PermanentRedactGuard"
                    ) as MockPerm:
                        MockPerm.return_value.should_redact.return_value = False
                        with patch("dot_man.cli.audit_cmd.ui") as mock_ui:
                            mock_ui.confirm.return_value = False
                            result = runner.invoke(cli, ["audit", "--fix"])
        assert result.exit_code == 0
        # ui.info is called with "Aborted." — check it was called
        mock_ui.info.assert_called_once()


class TestAuditExceptions:
    """Test exception handling."""

    def test_dotman_error(self, runner):
        with patch(
            "dot_man.cli.audit_cmd.get_custom_scanner",
            side_effect=Exception("scanner error"),
        ):
            result = runner.invoke(cli, ["audit"])
        assert result.exit_code != 0

    def test_keyboard_interrupt(self, runner):
        with patch(
            "dot_man.cli.audit_cmd.get_custom_scanner",
            side_effect=KeyboardInterrupt(),
        ):
            result = runner.invoke(cli, ["audit"])
        assert result.exit_code != 0
