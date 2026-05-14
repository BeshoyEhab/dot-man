"""Tests for dot_man/backups.py — backup manager."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest


@pytest.fixture
def tmp_backups_dir(tmp_path):
    """Create temporary backups directory."""
    return tmp_path / "backups"


@pytest.fixture
def clean_backups_env(tmp_path):
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

        yield dot_man_dir, repo_dir, backups_dir


class TestBackupManagerInit:
    def test_backup_manager_init(self, tmp_backups_dir):
        """Test BackupManager initialization."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        assert bm.backups_dir == tmp_backups_dir
        assert tmp_backups_dir.exists()

    def test_backup_manager_creates_dir(self, tmp_path):
        """Test BackupManager creates directory if missing."""
        from dot_man.backups import BackupManager

        backups_dir = tmp_path / "nonexistent" / "backups"
        BackupManager(backups_dir=backups_dir)
        assert backups_dir.exists()


class TestBackupManagerCreate:
    def test_create_backup_empty_paths(self, tmp_backups_dir):
        """Test create_backup with empty paths."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.create_backup([], note="test")
        assert result == ""

    def test_create_backup_single_file(self, tmp_backups_dir, tmp_path):
        """Test create_backup with a single file."""
        from dot_man.backups import BackupManager

        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.create_backup([test_file], note="test")

        assert result != ""
        assert result.startswith("20")  # timestamp starts with year

    def test_create_backup_directory(self, tmp_backups_dir, tmp_path):
        """Test create_backup with a directory."""
        from dot_man.backups import BackupManager

        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.create_backup([test_dir], note="backup")

        assert result != ""


class TestBackupManagerList:
    def test_list_backups_empty(self, tmp_backups_dir):
        """Test list_backups when no backups exist."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        backups = bm.list_backups()
        assert backups == []

    def test_list_backups_with_data(self, tmp_backups_dir, tmp_path):
        """Test list_backups with some backups."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        bm.create_backup([test_file], note="first")

        backups = bm.list_backups()
        assert len(backups) >= 1
        assert "id" in backups[0]
        assert "date" in backups[0]


class TestBackupManagerRestore:
    def test_restore_nonexistent(self, tmp_backups_dir):
        """Test restore with nonexistent backup."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        with pytest.raises(Exception):
            bm.restore_backup("nonexistent_backup_id")


class TestBackupManagerDelete:
    def test_delete_nonexistent(self, tmp_backups_dir):
        """Test delete with nonexistent backup."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.delete_backup("nonexistent_backup_id")
        assert result is False or result is None


class TestBackupManagerCleanup:
    def test_cleanup_old_backups(self, tmp_backups_dir, tmp_path):
        """Test cleanup removes old backups beyond MAX_BACKUPS."""
        from dot_man.backups import MAX_BACKUPS, BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)

        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        for i in range(MAX_BACKUPS + 2):
            bm.create_backup([test_file], note=f"backup_{i}")

        backups = bm.list_backups()
        assert len(backups) <= MAX_BACKUPS
