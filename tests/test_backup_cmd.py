"""Tests for cli/backup_cmd.py — backup command."""

import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

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

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


def _init_repo(repo_dir):
    """Initialize a real git repo with initial commit, branch 'main'."""
    from git import Repo

    repo = Repo.init(repo_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "test@test.com")
    (repo_dir / ".gitkeep").write_text("")
    repo.index.add([".gitkeep"])
    repo.index.commit("Initial")
    repo.git.branch("-m", "main")
    return repo


def _setup_global_toml(global_toml, branch="main"):
    """Write a minimal global.toml."""
    global_toml.parent.mkdir(parents=True, exist_ok=True)
    global_toml.write_text(f'[dot-man]\ncurrent_branch = "{branch}"\n')


def _setup_bashrc_section(repo_dir, home, content='alias ll="ls -la"\n'):
    """dot-man.toml with a bashrc section plus a real ~/.bashrc to track."""
    from git import Repo

    (repo_dir / "dot-man.toml").write_text('[bashrc]\npaths = ["~/.bashrc"]\n')
    bashrc = home / ".bashrc"
    bashrc.write_text(content)

    repo_file = repo_dir / "bashrc" / ".bashrc"
    repo_file.parent.mkdir(parents=True)
    repo_file.write_text(content)

    repo = Repo(repo_dir)
    repo.index.add(["dot-man.toml", "bashrc/.bashrc"])
    repo.index.commit("Add bashrc section")


class TestBackupHelp:
    def test_backup_help(self, runner):
        """Backup help."""
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0


class TestBackupWithoutInit:
    def test_backup_without_init(self, uninitialized_runner):
        """Backup without init fails with the not-initialized exit code."""
        result = uninitialized_runner.invoke(cli, ["backup", "create"])
        assert result.exit_code == 1, result.output


class TestBackupCreate:
    def test_backup_create_help(self, runner):
        """Backup create help."""
        result = runner.invoke(cli, ["backup", "create", "--help"])
        assert result.exit_code in [0, 2]

    def test_backup_create_runs(self, integration_runner):
        """Backup create succeeds in an initialized environment."""
        result = integration_runner.invoke(cli, ["backup", "create"])

        assert result.exit_code == 0, result.output
        assert "backup" in result.output.lower()


class TestBackupList:
    def test_backup_list_help(self, runner):
        """Backup list help."""
        result = runner.invoke(cli, ["backup", "list", "--help"])
        assert result.exit_code in [0, 2]

    def test_backup_list_runs(self, clean_env):
        """Backup list runs."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        config_writer = repo.config_writer()
        config_writer.set_value("user", "name", "Test")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (repo_dir / "test.txt").write_text("test")
        repo.index.add(["test.txt"])
        repo.index.commit("Initial")

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 0, result.output


class TestBackupRestore:
    def test_backup_restore_help(self, runner):
        """Deprecated `backup restore --help` points at `rollback --backup`."""
        result = runner.invoke(cli, ["backup", "restore", "--help"])
        assert result.exit_code == 0
        assert "DEPRECATED" in result.output
        assert "rollback --backup" in result.output

    def test_backup_restore_without_id(self, runner):
        """Backup restore without backup id."""
        result = runner.invoke(cli, ["backup", "restore"])
        assert result.exit_code in [0, 1, 2]


class TestBackupCreateWithFiles:
    def test_create_warns_without_tracked_files(self, clean_env):
        """Empty config means nothing to back up."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        (repo_dir / "dot-man.toml").write_text("# no sections yet\n")

        result = runner.invoke(cli, ["backup", "create"])

        assert result.exit_code == 0
        assert "No tracked files found" in result.output

    def test_create_backs_up_tracked_files(self, clean_env):
        """Tracked ~/.bashrc ends up in a real backup snapshot."""
        import json

        runner, dot_man_dir, repo_dir, global_toml = clean_env
        home = dot_man_dir.parent.parent
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, home)

        result = runner.invoke(cli, ["backup", "create", "testnote"])

        assert result.exit_code == 0
        assert "Backup created" in result.output

        from dot_man.backups import BackupManager

        backups = BackupManager().list_backups()
        assert len(backups) == 1
        manifest = json.loads(
            (backups[0]["path"] / "manifest.json").read_text(encoding="utf-8")
        )
        assert list(manifest.values()) == [str(home / ".bashrc")]


class TestBackupListWithData:
    def test_list_empty_reports_none(self, clean_env):
        """No backups prints the empty message."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 0
        assert "No backups found" in result.output

    def test_list_shows_created_backup(self, clean_env):
        """Created backup appears in the table with its id."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        home = dot_man_dir.parent.parent
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, home)

        from dot_man.backups import BackupManager

        backup_id = BackupManager().create_backup([home / ".bashrc"], note="snap")
        assert backup_id != ""

        result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 0
        assert backup_id in result.output
        assert "snap" in result.output


class TestBackupRestoreFlow:
    def test_restore_force_roundtrip(self, clean_env):
        """--force restore brings back the backed-up content."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        home = dot_man_dir.parent.parent
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, home)

        from dot_man.backups import BackupManager

        backup_id = BackupManager().create_backup([home / ".bashrc"], note="snap")

        (home / ".bashrc").write_text("modified content\n")
        result = runner.invoke(cli, ["backup", "restore", backup_id, "--force"])

        assert result.exit_code == 0
        assert "restored successfully" in result.output
        assert (home / ".bashrc").read_text() == 'alias ll="ls -la"\n'
        # Deprecated alias still warns about the replacement.
        assert "deprecated" in result.output.lower()
        assert "rollback --backup" in result.output

    def test_restore_confirm_abort_keeps_files(self, clean_env):
        """Answering 'no' at the prompt leaves local files alone."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        home = dot_man_dir.parent.parent
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)
        _setup_bashrc_section(repo_dir, home)

        from dot_man.backups import BackupManager

        backup_id = BackupManager().create_backup([home / ".bashrc"], note="snap")

        (home / ".bashrc").write_text("modified content\n")
        result = runner.invoke(cli, ["backup", "restore", backup_id], input="n\n")

        assert result.exit_code == 0
        assert (home / ".bashrc").read_text() == "modified content\n"

    def test_restore_missing_id_fails(self, clean_env):
        """Unknown backup id reports the BackupError (exit 41), not a bare 1."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        result = runner.invoke(cli, ["backup", "restore", "nope", "--force"])

        assert result.exit_code == 41
        assert "Backup 'nope' not found" in result.output


class TestBackupErrorBranches:
    """Error and empty-result paths for backup create/list/restore."""

    def test_create_empty_result_warns(self, clean_env):
        """A snapshot returning no id warns instead of reporting success."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        tracked = repo_dir / "tracked.txt"
        tracked.write_text("x")
        ops = MagicMock()
        ops.get_sections.return_value = ["s"]
        ops.get_section.return_value.paths = [tracked]
        ops.backups.create_backup.return_value = ""

        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(cli, ["backup", "create"])

        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_create_failure_reports(self, clean_env):
        """A raising create path is reported, not swallowed."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        with patch(
            "dot_man.operations.get_operations",
            side_effect=RuntimeError("boom"),
        ):
            result = runner.invoke(cli, ["backup", "create"])

        assert result.exit_code == 1
        assert "Failed to create backup: boom" in result.output

    def test_list_failure_reports(self, clean_env):
        """A raising list path is reported."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        ops = MagicMock()
        ops.backups.list_backups.side_effect = RuntimeError("bad list")
        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(cli, ["backup", "list"])

        assert result.exit_code == 1
        assert "Failed to list backups: bad list" in result.output

    def test_restore_unexpected_error_reports(self, clean_env):
        """A non-DotManError from restore hits the generic handler (exit 1)."""
        runner, dot_man_dir, repo_dir, global_toml = clean_env
        _init_repo(repo_dir)
        _setup_global_toml(global_toml)

        ops = MagicMock()
        ops.backups.restore_backup.side_effect = RuntimeError("disk gone")
        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(cli, ["backup", "restore", "any", "--force"])

        assert result.exit_code == 1
        assert "Failed to restore backup: disk gone" in result.output
