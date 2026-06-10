"""Comprehensive tests for dot_man.files — targeting uncovered lines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetContentHash:
    def test_get_content_hash(self):
        from dot_man.files import get_content_hash

        h1 = get_content_hash("hello")
        h2 = get_content_hash("hello")
        h3 = get_content_hash("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64
        assert len(h3) == 64

    def test_get_content_hash_empty(self):
        from dot_man.files import get_content_hash

        h = get_content_hash("")
        assert len(h) == 64


class TestAtomicWriteTextErrors:
    def test_atomic_write_oserror_cleanup(self, tmp_path):
        """OSError during atomic_write should clean up temp file."""
        from dot_man.files import atomic_write_text

        dest = tmp_path / "atomic.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)

        with patch("os.replace", side_effect=OSError("permission denied")):
            with pytest.raises(OSError):
                atomic_write_text(dest, "content")
            temp_path = dest.with_suffix(".txt.tmp")
            assert not temp_path.exists()


class TestSmartSaveFileEdgeCases:
    def test_smart_save_file_not_found(self, tmp_path):
        """smart_save_file should return (False, []) when source doesn't exist."""
        from dot_man.files import smart_save_file

        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "dest.txt"
        saved, secrets = smart_save_file(src, dst)
        assert not saved
        assert not secrets

    def test_smart_save_binary_file(self, tmp_path):
        """Binary file should fall through to binary copy."""
        from dot_man.files import smart_save_file

        src = tmp_path / "binary.bin"
        dst = tmp_path / "binary_out.bin"
        src.write_bytes(b"\x00\x01\x02\xff")

        saved, secrets = smart_save_file(src, dst)
        assert saved
        assert dst.read_bytes() == b"\x00\x01\x02\xff"

    def test_smart_save_binary_no_change(self, tmp_path):
        """Binary file identical to dest should not re-copy."""
        from dot_man.files import smart_save_file

        src = tmp_path / "binary.bin"
        dst = tmp_path / "binary_out.bin"
        data = b"\x00\x01\x02\xff"
        src.write_bytes(data)
        dst.write_bytes(data)

        saved, secrets = smart_save_file(src, dst)
        assert not saved

    def test_smart_save_secret_allow_list(self, tmp_path):
        """Secrets in the allow list should be ignored (not redacted)."""
        from dot_man.files import smart_save_file
        from dot_man.secrets import SecretGuard

        src = tmp_path / "allowed_secret.txt"
        dst = tmp_path / "dest_allowed.txt"
        content = "password = 'allowed_secret'"
        src.write_text(content)

        guard = SecretGuard(config_dir=tmp_path)
        guard.add_allowed(src, "password = 'allowed_secret'", "Password Assignment")

        with patch("dot_man.files._get_secret_guard", return_value=guard):
            saved, secrets = smart_save_file(src, dst, check_secrets=True)
        assert saved
        allowed_content = dst.read_text()
        assert "allowed_secret" in allowed_content

    def test_smart_save_permission_mismatch_triggers_save(self, tmp_path):
        """Different permissions should trigger re-save even if content is identical."""
        from dot_man.files import smart_save_file

        src = tmp_path / "src_perm.txt"
        dst = tmp_path / "dst_perm.txt"
        content = "same content"
        src.write_text(content)
        dst.write_text(content)
        dst.chmod(0o644)
        src.chmod(0o755)

        saved, secrets = smart_save_file(src, dst)
        assert saved

    def test_smart_save_chmod_oserror(self, tmp_path):
        """chmod failure should not prevent the save."""
        from dot_man.files import smart_save_file

        src = tmp_path / "src_chmod.txt"
        dst = tmp_path / "dst_chmod.txt"
        src.write_text("content")

        with (
            patch("dot_man.files.ensure_directory"),
            patch.object(Path, "chmod", side_effect=OSError("chmod failed")),
        ):
            saved, secrets = smart_save_file(src, dst)
        assert saved

    def test_smart_save_no_secret_check(self, tmp_path):
        """check_secrets=False should skip all secret filtering."""
        from dot_man.files import smart_save_file

        src = tmp_path / "src_nosecret.txt"
        dst = tmp_path / "dst_nosecret.txt"
        content = "password = 'secret'"
        src.write_text(content)

        saved, secrets = smart_save_file(src, dst, check_secrets=False)
        assert saved
        assert not secrets
        assert dst.read_text() == content


class TestHandleBinaryCopy:
    def test_handle_binary_copy_identical(self, tmp_path):
        """Binary copy should skip when files are identical."""
        from dot_man.files import _handle_binary_copy

        src = tmp_path / "src.bin"
        dst = tmp_path / "dst.bin"
        data = b"\xde\xad\xbe\xef"
        src.write_bytes(data)
        dst.write_bytes(data)
        src.chmod(0o644)
        dst.chmod(0o644)

        saved, secrets = _handle_binary_copy(src, dst, check_secrets=True)
        assert not saved
        assert not secrets

    def test_handle_binary_copy_different_permissions(self, tmp_path):
        """Binary copy should re-copy when permissions differ."""
        from dot_man.files import _handle_binary_copy

        src = tmp_path / "src.bin"
        dst = tmp_path / "dst.bin"
        data = b"\xde\xad\xbe\xef"
        src.write_bytes(data)
        dst.write_bytes(data)
        src.chmod(0o755)
        dst.chmod(0o644)

        saved, secrets = _handle_binary_copy(src, dst, check_secrets=True)
        assert saved

    def test_handle_binary_copy_error(self, tmp_path):
        """Binary copy should return (False, []) on OSError."""
        from dot_man.files import _handle_binary_copy

        src = tmp_path / "src.bin"
        dst = tmp_path / "dst.bin"
        src.write_bytes(b"\x01\x02")

        with patch("shutil.copy2", side_effect=OSError("copy failed")):
            saved, secrets = _handle_binary_copy(src, dst, check_secrets=True)
        assert not saved
        assert not secrets


class TestEnsureDirectory:
    def test_ensure_directory_creates(self, tmp_path):
        from dot_man.files import ensure_directory

        d = tmp_path / "new_dir" / "sub"
        ensure_directory(d)
        assert d.is_dir()

    def test_ensure_directory_exists(self, tmp_path):
        from dot_man.files import ensure_directory

        d = tmp_path / "existing"
        d.mkdir()
        ensure_directory(d)
        assert d.is_dir()


class TestMatchesPatterns:
    def test_matches_name(self, tmp_path):
        from dot_man.files import matches_patterns

        f = tmp_path / "test.txt"
        assert matches_patterns(f, ["*.txt"])
        assert not matches_patterns(f, ["*.md"])

    def test_matches_relative_path(self, tmp_path):
        from dot_man.files import matches_patterns

        f = tmp_path / "subdir" / "file.txt"
        assert matches_patterns(f, ["*/subdir/file.txt"])
        assert not matches_patterns(f, ["*/otherdir/*"])

    def test_matches_no_patterns(self, tmp_path):
        from dot_man.files import matches_patterns

        assert not matches_patterns(Path("file.txt"), [])


class TestCopyDirectory:
    def test_copy_directory_basic(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "sub").mkdir(parents=True)
        (src / "a.txt").write_text("a")
        (src / "sub" / "b.txt").write_text("b")

        copied, failed, secrets = copy_directory(src, dst)
        assert copied == 2
        assert failed == 0
        assert (dst / "a.txt").read_text() == "a"
        assert (dst / "sub" / "b.txt").read_text() == "b"

    def test_copy_directory_with_exclude(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "keep.txt").write_text("keep")
        (src / "skip.txt").write_text("skip")

        copied, failed, secrets = copy_directory(
            src, dst, exclude_patterns=["skip.txt"]
        )
        assert copied == 1
        assert (dst / "keep.txt").read_text() == "keep"
        assert not (dst / "skip.txt").exists()

    def test_copy_directory_with_include(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "keep.txt").write_text("keep")
        (src / "skip.py").write_text("skip")

        copied, failed, secrets = copy_directory(src, dst, include_patterns=["*.txt"])
        assert copied == 1
        assert (dst / "keep.txt").read_text() == "keep"
        assert not (dst / "skip.py").exists()

    def test_copy_directory_exclude_dirs(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "node_modules").mkdir(parents=True)
        (src / "node_modules" / "big.txt").write_text("big")
        (src / "keep.txt").write_text("keep")

        copied, failed, secrets = copy_directory(
            src, dst, exclude_patterns=["node_modules/*"]
        )
        assert copied == 1
        assert (dst / "keep.txt").exists()
        assert not (dst / "node_modules").exists()

    def test_copy_directory_no_secrets(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "f.txt").write_text("no secret here")

        copied, failed, secrets = copy_directory(src, dst, filter_secrets_enabled=False)
        assert copied == 1

    def test_copy_directory_copy_error_logged(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "f.txt").write_text("content")

        with patch(
            "dot_man.files.smart_save_file",
            side_effect=Exception("write failed"),
        ):
            copied, failed, secrets = copy_directory(src, dst)
        assert copied == 0
        assert failed == 1

    def test_copy_directory_follow_symlinks(self, tmp_path):
        from dot_man.files import copy_directory

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        target = tmp_path / "target"
        target.write_text("target content")
        src.mkdir()
        (src / "link").symlink_to(target)

        copied, failed, secrets = copy_directory(src, dst, follow_symlinks=True)
        assert copied == 1
        assert (dst / "link").read_text() == "target content"


class TestCompareFiles:
    def test_compare_directories_identical(self, tmp_path):
        from dot_man.files import compare_files

        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        (d1 / "a.txt").write_text("same")
        (d2 / "a.txt").write_text("same")
        (d1 / "sub").mkdir()
        (d2 / "sub").mkdir()
        (d1 / "sub" / "b.txt").write_text("same")
        (d2 / "sub" / "b.txt").write_text("same")

        assert compare_files(d1, d2) is True

    def test_compare_directories_different(self, tmp_path):
        from dot_man.files import compare_files

        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        (d1 / "a.txt").write_text("different")
        (d2 / "a.txt").write_text("content")

        assert compare_files(d1, d2) is False

    def test_compare_directories_missing_subdir(self, tmp_path):
        from dot_man.files import compare_files

        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        (d1 / "sub").mkdir()
        (d1 / "sub" / "a.txt").write_text("content")

        assert compare_files(d1, d2) is False

    def test_compare_file_nonexistent(self, tmp_path):
        from dot_man.files import compare_files

        a = tmp_path / "nonexistent1.txt"
        b = tmp_path / "nonexistent2.txt"
        assert compare_files(a, b) is False

    def test_compare_files_cached(self, tmp_path):
        from dot_man.files import clear_comparison_cache, compare_files

        clear_comparison_cache()
        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("cache test")
        f2.write_text("cache test")

        result1 = compare_files(f1, f2)
        result2 = compare_files(f1, f2)
        assert result1 is True
        assert result2 is True

    def test_compare_files_cache_miss_on_change(self, tmp_path):
        from dot_man.files import clear_comparison_cache, compare_files

        clear_comparison_cache()
        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("version1")
        f2.write_text("version1")

        assert compare_files(f1, f2) is True
        f2.write_text("version2")
        assert compare_files(f1, f2) is False

    def test_compare_files_oserror(self, tmp_path):
        from dot_man.files import compare_files

        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("content")
        f2.write_text("content")

        f1.chmod(0o000)
        result = compare_files(f1, f2)
        f1.chmod(0o644)
        assert result is False


class TestGetFileStatus:
    def test_status_new(self, tmp_path):
        from dot_man.files import get_file_status

        local = tmp_path / "local.txt"
        repo = tmp_path / "repo.txt"
        local.write_text("content")
        assert get_file_status(local, repo) == "NEW"

    def test_status_deleted(self, tmp_path):
        from dot_man.files import get_file_status

        local = tmp_path / "local.txt"
        repo = tmp_path / "repo.txt"
        repo.write_text("content")
        assert get_file_status(local, repo) == "DELETED"

    def test_status_missing(self, tmp_path):
        from dot_man.files import get_file_status

        local = tmp_path / "local.txt"
        repo = tmp_path / "repo.txt"
        assert get_file_status(local, repo) == "MISSING"

    def test_status_identical(self, tmp_path):
        from dot_man.files import get_file_status

        local = tmp_path / "local.txt"
        repo = tmp_path / "repo.txt"
        local.write_text("same")
        repo.write_text("same")
        assert get_file_status(local, repo) == "IDENTICAL"

    def test_status_modified(self, tmp_path):
        from dot_man.files import get_file_status

        local = tmp_path / "local.txt"
        repo = tmp_path / "repo.txt"
        local.write_text("local version")
        repo.write_text("repo version")
        assert get_file_status(local, repo) == "MODIFIED"


class TestCreateSymlink:
    def test_create_symlink_basic(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "target.txt"
        dst = tmp_path / "link.txt"
        src.write_text("content")

        assert create_symlink(src, dst) is True
        assert dst.is_symlink()
        assert dst.read_text() == "content"

    def test_create_symlink_already_correct(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "target.txt"
        dst = tmp_path / "link.txt"
        src.write_text("content")
        dst.symlink_to(src)

        assert create_symlink(src, dst) is True
        assert dst.is_symlink()

    def test_create_symlink_replace_wrong_link(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "target.txt"
        wrong = tmp_path / "wrong.txt"
        dst = tmp_path / "link.txt"
        src.write_text("content")
        wrong.write_text("wrong")
        dst.symlink_to(wrong)

        assert create_symlink(src, dst) is True
        assert dst.resolve() == src.resolve()

    def test_create_symlink_replace_existing_file(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "target.txt"
        dst = tmp_path / "link.txt"
        src.write_text("content")
        dst.write_text("existing file")

        assert create_symlink(src, dst) is True
        assert dst.is_symlink()
        assert dst.read_text() == "content"

    def test_create_symlink_source_not_found(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "nonexistent.txt"
        dst = tmp_path / "link.txt"

        assert create_symlink(src, dst) is False

    def test_create_symlink_oserror(self, tmp_path):
        from dot_man.files import create_symlink

        src = tmp_path / "target.txt"
        dst = tmp_path / "link.txt"
        src.write_text("content")

        with patch.object(Path, "symlink_to", side_effect=OSError("failed")):
            assert create_symlink(src, dst) is False


class TestDeployFileOrSymlink:
    def test_deploy_copy_mode(self, tmp_path):
        from dot_man.files import deploy_file_or_symlink

        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("copy deploy")

        success, secrets = deploy_file_or_symlink(src, dst, deploy_method="copy")
        assert success is True
        assert dst.read_text() == "copy deploy"

    def test_deploy_symlink_mode(self, tmp_path):
        from dot_man.files import deploy_file_or_symlink

        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("symlink deploy")

        success, secrets = deploy_file_or_symlink(src, dst, deploy_method="symlink")
        assert success is True
        assert dst.is_symlink()
        assert dst.read_text() == "symlink deploy"

    def test_deploy_copy_secrets_threshold(self, tmp_path):
        """High-entropy secret threshold should trigger interactive prompt."""
        from dot_man.files import deploy_file_or_symlink

        src = tmp_path / "src_high_entropy.txt"
        dst = tmp_path / "dst_high_entropy.txt"
        src.write_text(
            "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA\n-----END OPENSSH PRIVATE KEY-----\n"
        )

        result, secrets = deploy_file_or_symlink(
            src,
            dst,
            deploy_method="copy",
            filter_secrets_enabled=True,
        )
        assert result is True
        assert len(secrets) == 1


class TestDeployDirectoryWithSymlinks:
    def test_deploy_dir_symlinks_basic(self, tmp_path):
        from dot_man.files import deploy_directory_with_symlinks

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "sub").mkdir(parents=True)
        (src / "a.txt").write_text("a")
        (src / "sub" / "b.txt").write_text("b")

        symlinked, failed = deploy_directory_with_symlinks(src, dst)
        assert symlinked == 2
        assert failed == 0
        assert (dst / "a.txt").is_symlink()
        assert (dst / "sub" / "b.txt").is_symlink()

    def test_deploy_dir_symlinks_with_exclude(self, tmp_path):
        from dot_man.files import deploy_directory_with_symlinks

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "keep.txt").write_text("keep")
        (src / "skip.txt").write_text("skip")

        symlinked, failed = deploy_directory_with_symlinks(
            src, dst, exclude_patterns=["skip.txt"]
        )
        assert symlinked == 1

    def test_deploy_dir_symlinks_with_include(self, tmp_path):
        from dot_man.files import deploy_directory_with_symlinks

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "keep.txt").write_text("keep")
        (src / "skip.py").write_text("skip")

        symlinked, failed = deploy_directory_with_symlinks(
            src, dst, include_patterns=["*.txt"]
        )
        assert symlinked == 1

    def test_deploy_dir_symlinks_exclude_dir(self, tmp_path):
        from dot_man.files import deploy_directory_with_symlinks

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "node_modules").mkdir(parents=True)
        (src / "node_modules" / "big.txt").write_text("big")
        (src / "keep.txt").write_text("keep")

        symlinked, failed = deploy_directory_with_symlinks(
            src, dst, exclude_patterns=["node_modules/*"]
        )
        assert symlinked == 1
        assert not (dst / "node_modules").exists()

    def test_deploy_dir_symlinks_exception_handled(self, tmp_path):
        from dot_man.files import deploy_directory_with_symlinks

        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "f.txt").write_text("content")

        with patch("dot_man.files.create_symlink", side_effect=Exception("fail")):
            symlinked, failed = deploy_directory_with_symlinks(src, dst)
        assert symlinked == 0
        assert failed == 1


class TestBackupFile:
    def test_backup_file_basic(self, tmp_path):
        from dot_man.files import backup_file

        f = tmp_path / "test.txt"
        f.write_text("original")

        backup = backup_file(f)
        assert backup.exists()
        assert backup.read_text() == "original"

    def test_backup_dir(self, tmp_path):
        from dot_man.files import backup_file

        d = tmp_path / "mydir"
        d.mkdir()
        (d / "a.txt").write_text("a")

        backup = backup_file(d)
        assert backup.is_dir()
        assert (backup / "a.txt").read_text() == "a"

    def test_backup_file_not_found(self, tmp_path):
        from dot_man.files import backup_file

        f = tmp_path / "nonexistent.txt"
        assert backup_file(f) is None

    def test_backup_oserror(self, tmp_path):
        from dot_man.files import backup_file

        f = tmp_path / "test.txt"
        f.write_text("content")

        with patch("shutil.copy2", side_effect=OSError("backup failed")):
            assert backup_file(f) is None
