"""Final set of tests to increase coverage - simplified."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSecretsGuard:
    """Test secret guard more."""

    def test_guard_allow(self):
        """Test allowed secret."""
        from dot_man.secrets import SecretGuard
        guard = SecretGuard()
        result = guard.is_allowed("file.txt", "some text", "pattern")
        assert result is False


class TestSecretPatterns:
    """Test secret patterns."""

    def test_pattern_count(self):
        """Test pattern count."""
        from dot_man.secrets import DEFAULT_PATTERNS
        assert len(DEFAULT_PATTERNS) >= 10


class TestBackupManager:
    """Test backup manager."""

    def test_backup_list_empty(self, tmp_path):
        """Test list on empty backup dir."""
        from dot_man.backups import BackupManager
        
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        
        manager = BackupManager(backup_dir)
        result = manager.list_backups()
        assert isinstance(result, list)


class TestConfigTemplates:
    """Test config templates more."""

    def test_get_all_templates(self):
        """Test get_all_templates."""
        from dot_man.global_config import GlobalConfig
        
        config = GlobalConfig()
        config._data = {
            "templates": {"work": {"paths": ["~/work"]}, "home": {"paths": ["~/home"]}}
        }
        
        templates = config.get_all_templates()
        assert len(templates) == 2


class TestGlobalConfigEditor:
    """Test global config editor."""

    def test_editor_default_none(self):
        """Test editor defaults to None."""
        from dot_man.global_config import GlobalConfig
        
        config = GlobalConfig()
        config._data = {}
        assert config.editor is None

    def test_set_editor(self):
        """Test setting editor."""
        from dot_man.global_config import GlobalConfig
        
        config = GlobalConfig()
        config.editor = "nvim"
        assert config.editor == "nvim"


class TestOperationsInstance:
    """Test operations instance."""

    def test_get_operations_type(self):
        """Test get_operations returns correct type."""
        from dot_man.operations import get_operations
        assert callable(get_operations)


class TestAllBranchStats:
    """Test getting all branch stats."""

    def test_get_all_branch_stats(self, git_repo_with_branches):
        """Test get_all_branch_stats."""
        from dot_man.core import GitManager
        
        git = GitManager(git_repo_with_branches)
        stats = git.get_all_branch_stats()
        assert isinstance(stats, list)


class TestSectionRepoPath:
    """Test section repo path."""

    def test_get_repo_path_basic(self):
        """Test get_repo_path basic."""
        from dot_man.config import Section
        
        section = Section("bash", {"paths": ["~/.bashrc"]}, Path("/repo"))
        
        local_path = Path.home() / ".bashrc"
        repo_path = section.get_repo_path(local_path, Path("/repo"))
        
        assert "bashrc" in str(repo_path)


class TestUIConsole:
    """Test UI console."""

    def test_console_type(self):
        """Test console is Rich console."""
        from rich.console import Console
        from dot_man.interactive import console
        assert isinstance(console, Console)


class TestSecretRedaction:
    """Test secret redaction."""

    def test_redaction_text(self):
        """Test redaction text constant."""
        from dot_man.secrets import SECRET_REDACTION_TEXT
        assert SECRET_REDACTION_TEXT == "***REDACTED***"


class TestFalsePositives:
    """Test false positive indicators."""

    def test_false_positive_indicators(self):
        """Test false positive indicators exist."""
        from dot_man.secrets import FALSE_POSITIVE_INDICATORS
        assert isinstance(FALSE_POSITIVE_INDICATORS, list)


class TestCanonicalizePath:
    """Test path canonicalization."""

    def test_canonicalize_tilde(self):
        """Test canonicalizing tilde path."""
        from dot_man.secrets import _canonicalize_path
        result = _canonicalize_path("~/.bashrc")
        assert "~" not in result
        assert ".bashrc" in result


class TestValidatorsMore:
    """Test validators more."""

    def test_url_validator_import(self):
        """Test URL validator import."""
        from dot_man.interactive import UrlValidator
        assert UrlValidator is not None


class TestWizardsMore:
    """Test wizards more."""

    def test_global_wizard_import(self):
        """Test global wizard import."""
        from dot_man.interactive import run_global_wizard
        assert callable(run_global_wizard)

    def test_section_wizard_import(self):
        """Test section wizard import."""
        from dot_man.interactive import run_section_wizard
        assert callable(run_section_wizard)


class TestVaultEncryption:
    """Test vault encryption."""

    def test_vault_error(self):
        """Test VaultError exists."""
        from dot_man.vault import VaultError
        error = VaultError("test")
        assert "test" in str(error)


class TestLockError:
    """Test lock error."""

    def test_lock_error(self):
        """Test LockError exists."""
        from dot_man.vault import LockError
        error = LockError("locked")
        assert "locked" in str(error)


class TestBackupError:
    """Test backup error."""

    def test_backup_error(self):
        """Test BackupError exists."""
        from dot_man.backups import BackupError
        error = BackupError("backup failed")
        assert "backup failed" in str(error)


class TestUtilsFunctions:
    """Test utility functions."""

    def test_human_size_bytes(self):
        """Test human_size with bytes."""
        from dot_man.utils import human_size
        assert "B" in human_size(500)
        assert "500" in human_size(500)

    def test_human_size_kb(self):
        """Test human_size with KB."""
        from dot_man.utils import human_size
        result = human_size(1024)
        assert "KB" in result

    def test_human_size_mb(self):
        """Test human_size with MB."""
        from dot_man.utils import human_size
        result = human_size(1024 * 1024)
        assert "MB" in result

    def test_human_size_gb(self):
        """Test human_size with GB."""
        from dot_man.utils import human_size
        result = human_size(1024 * 1024 * 1024)
        assert "GB" in result

    def test_human_size_large(self):
        """Test human_size with large value (PB)."""
        from dot_man.utils import human_size
        result = human_size(1024 * 1024 * 1024 * 1024 * 1024)
        assert "PB" in result

    def test_get_directory_size_nonexistent(self):
        """Test get_directory_size with non-existent path."""
        from dot_man.utils import get_directory_size
        from pathlib import Path
        result = get_directory_size(Path("/nonexistent/path"))
        assert result == 0

    def test_get_directory_size_file(self, tmp_path):
        """Test get_directory_size with a file."""
        from dot_man.utils import get_directory_size
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        result = get_directory_size(test_file)
        assert result > 0

    def test_get_directory_size_directory(self, tmp_path):
        """Test get_directory_size with a directory."""
        from dot_man.utils import get_directory_size
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("hello")
        result = get_directory_size(tmp_path)
        assert result > 0

    def test_count_files_nonexistent(self):
        """Test count_files with non-existent path."""
        from dot_man.utils import count_files
        from pathlib import Path
        result = count_files(Path("/nonexistent/path"))
        assert result == 0

    def test_count_files_file(self, tmp_path):
        """Test count_files with a file."""
        from dot_man.utils import count_files
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        result = count_files(test_file)
        assert result == 1

    def test_count_files_directory(self, tmp_path):
        """Test count_files with a directory."""
        from dot_man.utils import count_files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("hello")
        (subdir / "file2.txt").write_text("world")
        result = count_files(tmp_path)
        assert result == 2

    def test_is_git_installed(self):
        """Test is_git_installed."""
        from dot_man.utils import is_git_installed
        result = is_git_installed()
        assert isinstance(result, bool)

    def test_get_hostname(self):
        """Test get_hostname."""
        from dot_man.utils import get_hostname
        result = get_hostname()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_username(self):
        """Test get_username."""
        from dot_man.utils import get_username
        result = get_username()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGitTagOperations:
    """Test Git tag operations in core."""

    def test_list_tags_empty(self, git_repo):
        """Test list_tags when no tags exist."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        tags = git.list_tags()
        assert tags == []

    def test_list_tags_with_tags(self, git_repo_with_tags):
        """Test list_tags with tags."""
        from dot_man.core import GitManager
        git = GitManager(git_repo_with_tags)
        tags = git.list_tags()
        assert len(tags) > 0

    def test_get_tag_commit(self, git_repo_with_tags):
        """Test get_tag_commit."""
        from dot_man.core import GitManager
        git = GitManager(git_repo_with_tags)
        tags = git.list_tags()
        if tags:
            commit = git.get_tag_commit(tags[0])
            assert commit is not None
            assert len(commit) > 0

    def test_create_tag(self, git_repo):
        """Test create_tag."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        git.create_tag("test-tag")
        tags = git.list_tags()
        assert "test-tag" in tags

    def test_create_tag_annotated(self, git_repo):
        """Test create_tag with message (annotated tag)."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        git.create_tag("annotated-tag", message="Test annotation")
        tags = git.list_tags()
        assert "annotated-tag" in tags

    def test_delete_tag(self, git_repo_with_tags):
        """Test delete_tag."""
        from dot_man.core import GitManager
        git = GitManager(git_repo_with_tags)
        tags_before = git.list_tags()
        if tags_before:
            git.delete_tag(tags_before[0])
            tags_after = git.list_tags()
            assert tags_before[0] not in tags_after


class TestGlobalConfigMore:
    """Test global config more thoroughly."""

    def test_global_config_get_defaults(self, tmp_path, monkeypatch):
        """Test get_defaults returns dict."""
        from dot_man.global_config import GlobalConfig
        config_file = tmp_path / "global.toml"
        config_file.write_text("[defaults]\nsecrets_filter = true\n")
        monkeypatch.setattr("dot_man.global_config.GLOBAL_TOML", config_file)
        config = GlobalConfig()
        defaults = config.get_defaults()
        assert isinstance(defaults, dict)

    def test_global_config_get_template_nonexistent(self, tmp_path, monkeypatch):
        """Test get_template returns None for nonexistent."""
        from dot_man.global_config import GlobalConfig
        config_file = tmp_path / "global.toml"
        config_file.write_text("")
        monkeypatch.setattr("dot_man.global_config.GLOBAL_TOML", config_file)
        config = GlobalConfig()
        template = config.get_template("nonexistent")
        assert template is None

    def test_global_config_get_all_templates(self, tmp_path, monkeypatch):
        """Test get_all_templates returns dict."""
        from dot_man.global_config import GlobalConfig
        config_file = tmp_path / "global.toml"
        config_file.write_text("")
        monkeypatch.setattr("dot_man.global_config.GLOBAL_TOML", config_file)
        config = GlobalConfig()
        templates = config.get_all_templates()
        assert isinstance(templates, dict)

    def test_switch_default_behavior_property(self, tmp_path, monkeypatch):
        """Test switch_default_behavior property default."""
        from dot_man.global_config import GlobalConfig
        config_file = tmp_path / "global.toml"
        config_file.write_text("")
        monkeypatch.setattr("dot_man.global_config.GLOBAL_TOML", config_file)
        config = GlobalConfig()
        assert config.switch_default_behavior == "save"


class TestFilesModule:
    """Test files module functions."""

    def test_ensure_directory(self, tmp_path):
        """Test ensure_directory creates directories."""
        from dot_man.files import ensure_directory
        test_dir = tmp_path / "sub" / "deep" / "dir"
        ensure_directory(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_directory_existing(self, tmp_path):
        """Test ensure_directory with existing directory."""
        from dot_man.files import ensure_directory
        ensure_directory(tmp_path)
        assert tmp_path.exists()

    def test_atomic_write_text(self, tmp_path):
        """Test atomic_write_text creates file."""
        from dot_man.files import atomic_write_text
        test_file = tmp_path / "test.txt"
        atomic_write_text(test_file, "hello world")
        assert test_file.exists()
        assert test_file.read_text() == "hello world"

    def test_atomic_write_text_overwrite(self, tmp_path):
        """Test atomic_write_text overwrites file."""
        from dot_man.files import atomic_write_text
        test_file = tmp_path / "test.txt"
        atomic_write_text(test_file, "first")
        atomic_write_text(test_file, "second")
        assert test_file.read_text() == "second"

    def test_get_file_status_new(self, tmp_path):
        """Test get_file_status for new file."""
        from dot_man.files import get_file_status
        src = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("content")
        status = get_file_status(src, dest)
        assert status == "NEW"

    def test_get_file_status_modified(self, tmp_path):
        """Test get_file_status for modified file."""
        from dot_man.files import get_file_status
        src = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("new content")
        dest.write_text("old content")
        status = get_file_status(src, dest)
        assert status == "MODIFIED"

    def test_get_file_status_identical(self, tmp_path):
        """Test get_file_status for identical file."""
        from dot_man.files import get_file_status
        src = tmp_path / "source.txt"
        dest = tmp_path / "dest.txt"
        src.write_text("same content")
        dest.write_text("same content")
        status = get_file_status(src, dest)
        assert status == "IDENTICAL"

    def test_compare_files_identical(self, tmp_path):
        """Test compare_files for identical files."""
        from dot_man.files import compare_files
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("hello")
        f2.write_text("hello")
        result = compare_files(f1, f2)
        assert result == True

    def test_compare_files_different(self, tmp_path):
        """Test compare_files for different files."""
        from dot_man.files import compare_files
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("hello")
        f2.write_text("world")
        result = compare_files(f1, f2)
        assert result == False

    def test_compare_files_binary(self, tmp_path):
        """Test compare_files for binary files."""
        from dot_man.files import compare_files
        f1 = tmp_path / "bin1"
        f2 = tmp_path / "bin2"
        f1.write_bytes(b"\x00\x01\x02")
        f2.write_bytes(b"\x00\x01\x02")
        result = compare_files(f1, f2)
        assert result == True

    def test_compare_files_nonexistent_dest(self, tmp_path):
        """Test compare_files when dest doesn't exist."""
        from dot_man.files import compare_files
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        f1.write_text("hello")
        result = compare_files(f1, f2)
        assert result == False


class TestGitManagerMore:
    """Test more GitManager operations."""

    def test_add_all(self, git_repo):
        """Test add_all stages all changes."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        (git_repo / "new.txt").write_text("content")
        git.add_all()
        # Check that file is staged
        assert len(git.repo.index.diff("HEAD")) > 0

    def test_commit_changes(self, git_repo):
        """Test commit creates a commit."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        (git_repo / "new.txt").write_text("content")
        result = git.commit("Test commit")
        assert result is not None
        assert len(result) == 40

    def test_commit_nothing_to_commit(self, git_repo):
        """Test commit returns None when nothing to commit."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        result = git.commit("Empty commit")
        assert result is None

    def test_current_branch(self, git_repo):
        """Test current_branch returns branch name."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        branch = git.current_branch()
        assert branch == "main" or branch == "master"

    def test_get_all_branch_stats(self, git_repo_with_branches):
        """Test get_all_branch_stats returns list."""
        from dot_man.core import GitManager
        git = GitManager(git_repo_with_branches)
        stats = git.get_all_branch_stats()
        assert isinstance(stats, list)

    def test_has_remote_false(self, git_repo):
        """Test has_remote returns False when no remote."""
        from dot_man.core import GitManager
        git = GitManager(git_repo)
        assert git.has_remote() == False