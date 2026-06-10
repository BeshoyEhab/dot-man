"""Tests for cli/doctor_cmd.py — doctor command.

These tests use the integration_runner fixture from conftest.py which
runs ``init --force --no-wizard`` to create a fully initialised dot-man
repository.  Additional patches are applied where needed to exercise
specific failure / warning branches.
"""

import os
import shutil
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Simple Click test runner (no patches)."""
    return CliRunner()


@pytest.fixture
def doctor_env(tmp_path):
    """Set up a complete dot-man environment with doctor_cmd patches.

    This is similar to ``integration_runner`` but additionally patches
    the module-level constants inside ``doctor_cmd`` so that the doctor
    command uses the temporary paths.

    Yields (runner, dot_man_dir, repo_dir, global_toml).
    """
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"
    dotman_toml = repo_dir / "dot-man.toml"

    patches = [
        # --- constants layer ---
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        # --- layer that every sub-module might re-bind ---
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        # --- CLI-layer patches ---
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.init_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.init_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.add_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.navigate_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        # --- critical: doctor_cmd gets its own copies ---
        patch("dot_man.cli.doctor_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.doctor_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.doctor_cmd.GLOBAL_TOML", global_toml),
        # DOT_MAN_TOML is a plain string in constants → patch to a Path
        # so that .exists() works as intended.
        patch("dot_man.cli.doctor_cmd.DOT_MAN_TOML", dotman_toml),
        # --- env ---
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        _runner = CliRunner()
        result = _runner.invoke(cli, ["init", "--force", "--no-wizard"])
        if result.exit_code != 0:
            raise RuntimeError(f"init failed: {result.output}")
        assert result.exit_code == 0

        # Configure git user so commit operations don't warn
        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        with git.repo.config_writer() as cw:
            cw.set_value("user", "name", "Tester")
            cw.set_value("user", "email", "test@example.com")

        yield _runner, dot_man_dir, repo_dir, global_toml


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants — **no** init.

    Yields (runner, dot_man_dir, repo_dir, global_toml).
    """
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"
    dotman_toml = repo_dir / "dot-man.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.doctor_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.doctor_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.doctor_cmd.GLOBAL_TOML", global_toml),
        patch("dot_man.cli.doctor_cmd.DOT_MAN_TOML", dotman_toml),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestDoctorHelp:
    def test_doctor_help(self, runner):
        """--help shows diagnostics and health keywords."""
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "diagnostics" in result.output.lower()
        assert "health" in result.output.lower()

    def test_doctor_alias(self, runner):
        """'doc' alias resolves to the same command."""
        result = runner.invoke(cli, ["doc", "--help"])
        assert result.exit_code == 0
        assert "diagnostics" in result.output.lower()


# ---------------------------------------------------------------------------
# Without init
# ---------------------------------------------------------------------------


class TestDoctorWithoutInit:
    def test_doctor_fails_without_init(self, runner):
        """Doctor without init should exit with code 1."""
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "init" in result.output.lower() or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Healthy repo
# ---------------------------------------------------------------------------


class TestDoctorHealthy:
    def test_all_checks_pass(self, doctor_env):
        """All checks pass on a healthy initialised repo."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0, result.output
        assert "dot-man is healthy" in result.output

    def test_system_section(self, doctor_env):
        """System checks (git, python) are shown."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert "Git installed" in result.output
        assert "Python" in result.output

    def test_repo_section(self, doctor_env):
        """Repository checks all pass."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert "Config directory exists" in result.output
        assert "Repository directory exists" in result.output
        assert "Git repository initialized" in result.output
        assert "Repository permissions" in result.output

    def test_config_section(self, doctor_env):
        """Global config and dot-man.toml are validated."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert "Global config exists" in result.output
        assert "Config is valid" in result.output
        assert "section" in result.output.lower()

    def test_branch_section(self, doctor_env):
        """Current branch and available branches are reported."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert "Current branch" in result.output
        assert "Available branches" in result.output

    def test_summary_healthy(self, doctor_env):
        """Summary shows 0 failures and 'dot-man is healthy'."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert "0 failed" in result.output
        assert "dot-man is healthy" in result.output

    def test_exit_code_zero(self, doctor_env):
        """Exit code is 0 when all checks pass."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "dot-man is healthy" in result.output


# ---------------------------------------------------------------------------
# Git issues
# ---------------------------------------------------------------------------


class TestDoctorGitIssues:
    def test_git_not_found(self, doctor_env):
        """When git is not installed, the check fails."""
        runner, *_ = doctor_env
        with patch("shutil.which", return_value=None):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Git not found" in result.output

    def test_no_dot_git(self, clean_env):
        """Missing .git directory causes failure."""
        runner, dot_man_dir, repo_dir, _ = clean_env
        # Mimic partial structure without a git repo
        dot_man_dir.mkdir(parents=True, exist_ok=True)
        repo_dir.mkdir(parents=True, exist_ok=True)
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()


# ---------------------------------------------------------------------------
# Config issues
# ---------------------------------------------------------------------------


class TestDoctorConfigIssues:
    def test_missing_global_toml(self, doctor_env):
        """Missing global.toml triggers a warning and config parse fails."""
        runner, _, _, global_toml = doctor_env
        global_toml.unlink()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "No global config" in result.output
        assert "Config parse error" in result.output
        assert "Global config not found" in result.output

    def test_corrupted_dotman_toml(self, doctor_env):
        """Invalid TOML content triggers a parse error."""
        runner, _, repo_dir, _ = doctor_env
        dotman = repo_dir / "dot-man.toml"
        dotman.write_text("<<<<< NOT VALID TOML >>>>>")
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Config parse error" in result.output

    def test_empty_dotman_toml(self, doctor_env):
        """Empty dot-man.toml is valid and shows 0 sections."""
        runner, _, repo_dir, _ = doctor_env
        dotman = repo_dir / "dot-man.toml"
        dotman.write_text("")
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Config is valid" in result.output
        assert "0 section" in result.output


# ---------------------------------------------------------------------------
# Tracked files
# ---------------------------------------------------------------------------


class TestDoctorTrackedFiles:
    def test_no_paths_tracked(self, doctor_env):
        """When no files are tracked, a warning is shown."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "No paths tracked" in result.output

    def test_all_tracked_paths_exist(self, doctor_env):
        """When every tracked path exists, check passes."""
        runner, _, repo_dir, _ = doctor_env
        dotman = repo_dir / "dot-man.toml"
        tracked_file = repo_dir / "testfile.txt"
        tracked_file.write_text("hello")
        dotman.write_text(f'[test-section]\npaths = ["{tracked_file}"]\n')
        from dot_man.operations import reset_operations

        reset_operations()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "All tracked paths exist" in result.output

    def test_missing_tracked_path(self, doctor_env):
        """Missing tracked path triggers a warning."""
        runner, _, repo_dir, _ = doctor_env
        dotman = repo_dir / "dot-man.toml"
        dotman.write_text('[test-section]\npaths = ["nonexistent-file.txt"]\n')
        from dot_man.operations import reset_operations

        reset_operations()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Missing" in result.output


# ---------------------------------------------------------------------------
# Orphaned files
# ---------------------------------------------------------------------------


class TestDoctorOrphanedFiles:
    def test_orphaned_files_warning(self, doctor_env):
        """Orphaned files inside the repo trigger a warning."""
        runner, _, repo_dir, _ = doctor_env
        orphan = repo_dir / "orphaned-file.txt"
        orphan.write_text("I am not tracked")
        repo_dir.joinpath(".git").mkdir(parents=True, exist_ok=True)

        # Stage the orphan so there's a committed file that doesn't
        # match any section.
        from git import Repo as GitRepo

        grepo = GitRepo(repo_dir)
        grepo.index.add(["orphaned-file.txt"])
        grepo.index.commit("Add orphan")

        from dot_man.operations import reset_operations

        reset_operations()

        result = runner.invoke(cli, ["doctor"])
        assert "orphaned" in result.output.lower()

    def test_no_orphaned_files(self, doctor_env):
        """Clean repo shows no orphan warning."""
        result = doctor_env[0].invoke(cli, ["doctor"])
        assert "No orphaned files" in result.output


# ---------------------------------------------------------------------------
# Remote
# ---------------------------------------------------------------------------


class TestDoctorRemote:
    def test_no_remote_warning(self, doctor_env):
        """No remote configured shows a warning."""
        runner, *_ = doctor_env
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "No remote configured" in result.output

    def test_remote_configured(self, doctor_env):
        """When a remote is set, it is shown."""
        runner, _, repo_dir, _ = doctor_env
        global_toml = doctor_env[3]
        global_toml.write_text(
            '[dot-man]\ncurrent_branch = "main"\n'
            '[remote]\nurl = "https://github.com/user/dotfiles.git"\n'
        )
        from dot_man.operations import reset_operations

        reset_operations()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Remote configured" in result.output
        assert "github.com" in result.output


# ---------------------------------------------------------------------------
# Directory / permission issues (unreachable via normal flow)
# ---------------------------------------------------------------------------


class TestDoctorDirectoryIssues:
    def test_config_dir_missing_body_check(self, doctor_env):
        """When DOT_MAN_DIR is missing inside doctor body (require_init already
        passed because it uses common's binding), the check should fail."""
        runner, dot_man_dir, _, _ = doctor_env
        # Patch the class-level method; for DOT_MAN_DIR we need it to
        # be True for require_init (which uses common.DOT_MAN_DIR) and
        # False for the body check (which uses doctor_cmd.DOT_MAN_DIR).
        # The simplest way: change which path doctor_cmd sees.
        with patch(
            "dot_man.cli.doctor_cmd.DOT_MAN_DIR",
            dot_man_dir / "nonexistent",
        ):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Config directory missing" in result.output

    def test_repo_dir_missing_body_check(self, doctor_env):
        """When REPO_DIR is missing inside doctor body, check fails."""
        runner, _, repo_dir, _ = doctor_env
        with patch(
            "dot_man.cli.doctor_cmd.REPO_DIR",
            repo_dir / "nonexistent",
        ):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Repository directory missing" in result.output

    def test_no_dot_git_body_check(self, doctor_env):
        """When .git is missing inside doctor body, check fails.

        ``require_init`` uses ``common.REPO_DIR`` while the doctor body uses
        ``doctor_cmd.REPO_DIR``.  We point the former at a fake init tree
        (with ``.git``) and keep the latter at the real repo (without any
        ``.git`` after we remove it).
        """
        runner, dot_man_dir, repo_dir, _ = doctor_env

        # Remove .git from the real repo so the doctor body sees it missing
        git_dir = repo_dir / ".git"
        shutil.rmtree(git_dir)

        # Create a fake init structure that has .git for require_init
        fake_dir = repo_dir.parent / "fake-dot-man"
        fake_repo = fake_dir / "repo"
        fake_repo.mkdir(parents=True)
        (fake_repo / ".git").mkdir()

        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", fake_repo),
        ):
            result = runner.invoke(cli, ["doctor"])

        assert result.exit_code == 1
        assert "No .git directory" in result.output

    def test_repo_permissions_denied(self, doctor_env):
        """When REPO_DIR lacks read/write permissions, check fails."""
        runner, _, _, _ = doctor_env
        with patch("os.access", return_value=False):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Cannot read/write" in result.output


# ---------------------------------------------------------------------------
# Missing dot-man.toml (DOT_MAN_TOML is a simple string in constants)
# ---------------------------------------------------------------------------


class TestDoctorNoDotManToml:
    def test_warning_when_dotman_missing(self, doctor_env):
        """When DOT_MAN_TOML does not exist, a warning is shown."""
        runner, _, _, _ = doctor_env
        with patch(
            "dot_man.cli.doctor_cmd.DOT_MAN_TOML",
            Path("/nonexistent/dot-man.toml"),
        ):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "No dot-man.toml" in result.output


# ---------------------------------------------------------------------------
# Exception handlers (get_operations / sub-calls raise)
# ---------------------------------------------------------------------------


class TestDoctorExceptionHandlers:
    def test_branch_check_exception(self, doctor_env):
        """When get_operations raises, a failure is reported (all handlers)."""
        runner, _, _, _ = doctor_env
        with patch(
            "dot_man.operations.get_operations",
            side_effect=RuntimeError("ops boom"),
        ):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        # Every get_operations call fails -> multiple failures
        assert "Config parse error" in result.output
        assert "Branch check failed" in result.output
        assert "File check failed" in result.output
        # Remote/orphan/backup use check_warn, not check_fail
        assert "Could not check remote" in result.output
        assert "Could not check orphans" in result.output
        assert "Could not check backups" in result.output

    def test_orphan_check_exception(self, doctor_env):
        """When get_orphaned_files raises, a warning is shown."""
        runner, _, _, _ = doctor_env
        from dot_man.operations import get_operations as real_get_ops

        real_ops = real_get_ops()
        with patch.object(real_ops, "get_orphaned_files") as mock_orph:
            mock_orph.side_effect = RuntimeError("orphan boom")
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Could not check orphans" in result.output

    def test_backup_check_exception(self, doctor_env):
        """When backup check raises, a warning is shown."""
        runner, _, _, _ = doctor_env
        from dot_man.operations import get_operations as real_get_ops

        real_ops = real_get_ops()
        with patch.object(real_ops.backups, "list_backups") as mock_bkp:
            mock_bkp.side_effect = RuntimeError("backup boom")
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Could not check backups" in result.output

    def test_backups_available(self, doctor_env):
        """When backups exist, the check passes."""
        runner, _, _, _ = doctor_env
        from dot_man.operations import get_operations as real_get_ops

        real_ops = real_get_ops()
        with patch.object(real_ops.backups, "list_backups") as mock_bkp:
            mock_bkp.return_value = [{"id": "bkp1", "timestamp": "now"}]
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Backups available" in result.output


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------


class TestDoctorBackups:
    def test_backups_section_appears(self, doctor_env):
        """Backups section is always present in output."""
        result = doctor_env[0].invoke(cli, ["doctor"])
        assert "Backups" in result.output


# ---------------------------------------------------------------------------
# Summary / exit code
# ---------------------------------------------------------------------------


class TestDoctorSummary:
    def test_summary_format(self, doctor_env):
        """Summary line shows passed / warned / failed / total counts."""
        result = doctor_env[0].invoke(cli, ["doctor"])
        assert "passed" in result.output
        assert "warnings" in result.output
        assert "failed" in result.output
        assert "checks" in result.output.lower()

    def test_failure_summary(self, doctor_env):
        """When a check fails, summary shows the failure count."""
        runner, *_ = doctor_env
        with patch("shutil.which", return_value=None):
            result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "failed" in result.output
        assert "check(s) failed" in result.output

    def test_healthy_summary(self, doctor_env):
        """Healthy repo summary shows 'dot-man is healthy'."""
        result = doctor_env[0].invoke(cli, ["doctor"])
        assert "dot-man is healthy" in result.output
        assert "0 failed" in result.output
