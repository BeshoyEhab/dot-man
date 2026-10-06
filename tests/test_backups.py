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

    def test_create_backup_skips_missing_paths(self, tmp_backups_dir, tmp_path):
        """Missing paths are skipped; real files still back up."""
        import json

        from dot_man.backups import BackupManager

        real_file = tmp_path / "real.txt"
        real_file.write_text("real content")
        missing = tmp_path / "ghost.txt"

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.create_backup([real_file, missing], note="mixed")

        assert result != ""
        manifest = json.loads(
            (tmp_backups_dir / result / "manifest.json").read_text(encoding="utf-8")
        )
        assert len(manifest) == 1
        assert list(manifest.values()) == [str(real_file)]

    def test_create_backup_all_missing_returns_empty(self, tmp_backups_dir, tmp_path):
        """All-missing paths leave no empty backup directory behind."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.create_backup([tmp_path / "ghost.txt"], note="empty")

        assert result == ""
        assert list(tmp_backups_dir.iterdir()) == []

    def test_create_backup_failure_cleans_up(self, tmp_backups_dir, tmp_path):
        """OSError mid-backup raises BackupError with no leftover directory."""
        from dot_man.backups import BackupManager
        from dot_man.exceptions import BackupError

        real_file = tmp_path / "real.txt"
        real_file.write_text("real content")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        with patch("shutil.copy2", side_effect=OSError("disk full")):
            with pytest.raises(BackupError):
                bm.create_backup([real_file], note="boom")

        assert list(tmp_backups_dir.iterdir()) == []

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

    def test_list_backups_missing_dir(self, tmp_backups_dir):
        """list_backups returns [] when the backups dir itself is gone."""
        import shutil

        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        shutil.rmtree(tmp_backups_dir)

        assert bm.list_backups() == []

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

    def test_restore_missing_manifest(self, tmp_backups_dir):
        """Backup dir without manifest.json raises corrupt-backup error."""
        from dot_man.backups import BackupManager
        from dot_man.exceptions import BackupError

        bm = BackupManager(backups_dir=tmp_backups_dir)
        (tmp_backups_dir / "20240101_120000_manual").mkdir(parents=True)

        with pytest.raises(BackupError, match="corrupt"):
            bm.restore_backup("20240101_120000_manual")

    def test_restore_invalid_manifest(self, tmp_backups_dir):
        """Backup with unparseable manifest raises BackupError."""
        from dot_man.backups import BackupManager
        from dot_man.exceptions import BackupError

        bm = BackupManager(backups_dir=tmp_backups_dir)
        broken = tmp_backups_dir / "20240101_120000_broken"
        broken.mkdir(parents=True)
        (broken / "manifest.json").write_text("not json {{{")

        with pytest.raises(BackupError):
            bm.restore_backup("20240101_120000_broken")

    def test_restore_file_roundtrip(self, tmp_backups_dir, tmp_path):
        """Modified file is restored to backed-up content."""
        from dot_man.backups import BackupManager

        target = tmp_path / "settings.conf"
        target.write_text("original")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        backup_id = bm.create_backup([target], note="snap")
        assert backup_id != ""

        target.write_text("modified")
        assert bm.restore_backup(backup_id) is True
        assert target.read_text() == "original"

    def test_restore_directory_roundtrip(self, tmp_backups_dir, tmp_path):
        """Directory restored over a modified copy regains its files."""
        from dot_man.backups import BackupManager

        target_dir = tmp_path / "confdir"
        target_dir.mkdir()
        (target_dir / "inner.txt").write_text("inner content")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        backup_id = bm.create_backup([target_dir], note="snap")
        assert backup_id != ""

        (target_dir / "inner.txt").write_text("changed")
        (target_dir / "extra.txt").write_text("extra")
        assert bm.restore_backup(backup_id) is True
        assert (target_dir / "inner.txt").read_text() == "inner content"
        assert not (target_dir / "extra.txt").exists()


class TestBackupManagerDelete:
    def test_delete_nonexistent(self, tmp_backups_dir):
        """Test delete with nonexistent backup."""
        from dot_man.backups import BackupManager

        bm = BackupManager(backups_dir=tmp_backups_dir)
        result = bm.delete_backup("nonexistent_backup_id")
        assert result is False or result is None

    def test_delete_failure_returns_false(self, tmp_backups_dir, tmp_path):
        """OSError during delete returns False instead of raising."""
        from dot_man.backups import BackupManager

        target = tmp_path / "f.txt"
        target.write_text("x")

        bm = BackupManager(backups_dir=tmp_backups_dir)
        backup_id = bm.create_backup([target], note="snap")
        assert backup_id != ""

        with patch("shutil.rmtree", side_effect=OSError("locked")):
            assert bm.delete_backup(backup_id) is False


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
