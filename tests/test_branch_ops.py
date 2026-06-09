"""Tests for dot_man.branch_ops — BranchMixin."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from dot_man.branch_ops import FILE_TO_HOOK_MAP, BranchMixin


class FakeOps(BranchMixin):
    """Minimal BranchMixin subclass for testing."""

    def __init__(self, **kwargs):
        self._current_branch = kwargs.get("current_branch", "main")
        self._git = kwargs.get("git", MagicMock())
        self._sections = kwargs.get("sections", {})
        self._global_config = kwargs.get("global_config", MagicMock())
        self._backups = kwargs.get("backups", MagicMock())
        self._vault = kwargs.get("vault", MagicMock())
        self._save_all_result = kwargs.get(
            "save_all_result", {"saved": 0, "secrets": [], "errors": [], "symlinks": []}
        )
        self._scan_result = kwargs.get(
            "scan_result", {"pre_hooks": [], "post_hooks": [], "errors": []}
        )
        self._deploy_result = kwargs.get("deploy_result", {"deployed": 0, "errors": []})

    @property
    def current_branch(self) -> str:
        return self._current_branch

    def save_all(self, secret_handler=None):
        return self._save_all_result

    @property
    def git(self):
        return self._git

    def reload_config(self):
        pass

    def get_sections(self):
        return list(self._sections.keys())

    def get_section(self, name):
        return self._sections[name]

    @property
    def backups(self):
        return self._backups

    def scan_deployable_changes(self, sections):
        return self._scan_result

    def execute_deployment_plan(self, plan):
        return self._deploy_result

    @property
    def global_config(self):
        return self._global_config

    @property
    def vault(self):
        return self._vault


class TestSwitchBranch:
    def test_switch_same_branch_noop(self):
        ops = FakeOps(current_branch="main")
        result = ops.switch_branch("main")
        assert result["saved_count"] == 0
        assert result["deployed_count"] == 0
        assert result["errors"] == []
        assert result["created_branch"] is False

    def test_switch_dry_run(self):
        ops = FakeOps(current_branch="work")
        result = ops.switch_branch("personal", dry_run=True)
        assert result["saved_count"] == 0
        assert result["deployed_count"] == 0

    def test_switch_normal(self):
        """Normal switch: save, checkout, deploy."""
        from dot_man.config import Section

        section = Section(
            name="bash", paths=[Path("/home/user/.bashrc")], secrets_filter=False
        )
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            sections={"bash": section},
            global_config=gc,
            save_all_result={"saved": 2, "secrets": [], "errors": [], "symlinks": []},
            scan_result={
                "pre_hooks": ["echo pre"],
                "post_hooks": ["echo post"],
                "errors": [],
            },
            deploy_result={"deployed": 3, "errors": []},
        )
        result = ops.switch_branch("personal")
        assert result["saved_count"] == 2
        assert result["deployed_count"] == 3
        assert result["created_branch"] is False
        assert result["pre_hooks"] == ["echo pre"]
        assert result["post_hooks"] == ["echo post"]
        git_mock.commit.assert_called_once()
        git_mock.checkout.assert_called_once_with("personal", create=False)
        gc.save.assert_called_once()
        assert gc.current_branch == "personal"

    def test_switch_new_branch(self):
        """Switching to a new branch should create it."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = False
        gc = MagicMock()
        ops = FakeOps(
            current_branch="main",
            git=git_mock,
            global_config=gc,
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
            scan_result={"pre_hooks": [], "post_hooks": [], "errors": []},
            deploy_result={"deployed": 0, "errors": []},
        )
        result = ops.switch_branch("new-feature")
        assert result["created_branch"] is True
        git_mock.checkout.assert_called_once_with("new-feature", create=True)

    def test_switch_auto_backup_failure(self):
        """Auto-backup failure should be recorded as warning, not crash."""
        from dot_man.config import Section

        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        backups = MagicMock()
        backups.create_backup.side_effect = Exception("disk full")
        section = Section(name="test", paths=[Path("/")], secrets_filter=False)
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            backups=backups,
            sections={"test": section},
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
            scan_result={"pre_hooks": [], "post_hooks": [], "errors": []},
            deploy_result={"deployed": 0, "errors": []},
        )
        result = ops.switch_branch("personal")
        assert any("disk full" in e for e in result["errors"])

    def test_switch_deploy_failure(self):
        """Deploy failure should be recorded as error."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
            deploy_result={"deployed": 0, "errors": ["deploy failed"]},
        )
        with patch.object(
            ops,
            "scan_deployable_changes",
            return_value={"pre_hooks": [], "post_hooks": [], "errors": []},
        ):
            result = ops.switch_branch("personal")
        assert "deploy failed" in result["errors"]

    def test_switch_deploy_critical_error(self):
        """Exception during deployment should be caught and recorded."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
        )
        with (
            patch.object(
                ops,
                "scan_deployable_changes",
                side_effect=Exception("unexpected error"),
            ),
        ):
            result = ops.switch_branch("personal")
        assert "unexpected error" in result["errors"][0]

    def test_switch_symlink_warning(self):
        """Symlinked paths should produce warnings."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={
                "saved": 0,
                "secrets": [],
                "errors": [],
                "symlinks": [Path("/fake/link")],
            },
        )
        result = ops.switch_branch("personal")
        assert any("symlink" in e.lower() for e in result["errors"])

    def test_switch_secrets_redacted_counted(self):
        """Secrets redacted count should be tracked."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={
                "saved": 0,
                "secrets": [MagicMock(), MagicMock()],
                "errors": [],
                "symlinks": [],
            },
        )
        result = ops.switch_branch("personal")
        assert result["secrets_redacted"] == 2

    def test_switch_auto_hooks_detected(self):
        """Changed files should auto-detect hooks."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
            deploy_result={"deployed": 0, "errors": []},
        )

        def fake_changed_files(src, tgt):
            return [".bashrc"]

        with (
            patch.object(ops, "get_changed_files_between_branches", fake_changed_files),
        ):
            result = ops.switch_branch("personal")
        assert any("bash" in h for h in result["post_hooks"])

    def test_switch_dedup_hooks(self):
        """Duplicate pre/post hooks should be deduplicated."""
        git_mock = MagicMock()
        git_mock.branch_exists.return_value = True
        gc = MagicMock()
        ops = FakeOps(
            current_branch="work",
            git=git_mock,
            global_config=gc,
            save_all_result={"saved": 0, "secrets": [], "errors": [], "symlinks": []},
            scan_result={
                "pre_hooks": ["echo same", "echo same"],
                "post_hooks": ["echo same"],
                "errors": [],
            },
            deploy_result={"deployed": 0, "errors": []},
        )
        result = ops.switch_branch("personal")
        assert result["pre_hooks"] == ["echo same"]
        assert result["post_hooks"] == ["echo same"]


class TestRevertFile:
    def test_revert_file_not_tracked(self):
        """Revert should warn when file is not tracked by any section."""
        ops = FakeOps(sections={})
        result = ops.revert_file(Path("/untracked/file.txt"))
        assert result is False

    def test_revert_file_not_in_repo(self, tmp_path):
        """Revert should warn when file is in section but not in repo."""
        from dot_man.config import Section

        local = tmp_path / ".bashrc"
        local.write_text("local version")
        section = Section(
            name="test", paths=[local], repo_base="bashrc", secrets_filter=False
        )
        ops = FakeOps(sections={"test": section})
        with patch("dot_man.branch_ops.REPO_DIR", tmp_path):
            result = ops.revert_file(local)
        assert result is False

    def test_revert_file_success(self, tmp_path):
        """Successful revert should copy from repo to local."""
        from dot_man.config import Section

        local = tmp_path / ".bashrc"
        repo = tmp_path / "bashrc" / ".bashrc"
        repo.parent.mkdir(parents=True)
        repo.write_text("repo version")
        local.write_text("local version")

        section = Section(
            name="bash", paths=[local], repo_base="bashrc", secrets_filter=False
        )
        ops = FakeOps(sections={"bash": section})

        with patch("dot_man.branch_ops.REPO_DIR", tmp_path):
            result = ops.revert_file(local)
        assert result is True
        assert local.read_text() == "repo version"

    def test_revert_file_with_secrets(self, tmp_path):
        """Revert should restore secrets from vault if section has secrets_filter."""
        from dot_man.config import Section

        local = tmp_path / ".bashrc"
        repo = tmp_path / "bashrc" / ".bashrc"
        repo.parent.mkdir(parents=True)
        # File content has a redacted secret placeholder
        repo.write_text("password = ***REDACTED***")
        local.write_text("local version")

        vault = MagicMock()
        vault.restore_secrets_in_content.return_value = "password = real_secret"

        section = Section(
            name="bash", paths=[local], repo_base="bashrc", secrets_filter=True
        )
        ops = FakeOps(sections={"bash": section}, vault=vault)

        with patch("dot_man.branch_ops.REPO_DIR", tmp_path):
            result = ops.revert_file(local)
        assert result is True
        assert local.read_text() == "password = real_secret"

    def test_revert_file_secret_restore_error(self, tmp_path):
        """Revert should succeed even if secret restore fails."""
        from dot_man.config import Section

        local = tmp_path / ".bashrc"
        repo = tmp_path / "bashrc" / ".bashrc"
        repo.parent.mkdir(parents=True)
        repo.write_text("repo content")
        local.write_text("local version")

        vault = MagicMock()
        vault.restore_secrets_in_content.side_effect = OSError("read error")

        section = Section(
            name="bash", paths=[local], repo_base="bashrc", secrets_filter=True
        )
        ops = FakeOps(sections={"bash": section}, vault=vault)

        with patch("dot_man.branch_ops.REPO_DIR", tmp_path):
            result = ops.revert_file(local)
        assert result is True

    def test_revert_file_under_directory(self, tmp_path):
        """Revert should work for files under a tracked directory."""
        from dot_man.config import Section

        local_dir = tmp_path / "config"
        local = local_dir / "settings.ini"
        repo_dir = tmp_path / "config-repo"
        repo = repo_dir / "settings.ini"
        local_dir.mkdir()
        repo_dir.mkdir()
        repo.write_text("repo version")
        local.write_text("local version")

        section = Section(
            name="config",
            paths=[local_dir],
            repo_base="config-repo",
            secrets_filter=False,
        )
        ops = FakeOps(sections={"config": section})

        with patch("dot_man.branch_ops.REPO_DIR", tmp_path):
            result = ops.revert_file(local)
        assert result is True
        assert local.read_text() == "repo version"


class TestGetChangedFilesBetweenBranches:
    def test_changed_files(self):
        """Should return list of changed files."""
        git = MagicMock()
        git.repo.git.diff.return_value = "file1.txt\nfile2.txt\n"
        ops = FakeOps(git=git)
        result = ops.get_changed_files_between_branches("main", "feature")
        assert result == ["file1.txt", "file2.txt"]

    def test_no_changes(self):
        """Should return empty list when no changes."""
        git = MagicMock()
        git.repo.git.diff.return_value = ""
        ops = FakeOps(git=git)
        result = ops.get_changed_files_between_branches("main", "feature")
        assert result == []

    def test_git_error(self):
        """Should return empty list on git error."""
        git = MagicMock()
        git.repo.git.diff.side_effect = Exception("git error")
        ops = FakeOps(git=git)
        result = ops.get_changed_files_between_branches("main", "feature")
        assert result == []


class TestDetectHooksForChangedFiles:
    def test_hook_known_file(self):
        """Changed file matching FILE_TO_HOOK_MAP should produce hook."""
        ops = FakeOps()
        with patch(
            "dot_man.constants.HOOK_ALIASES", {"bash_reload": "source ~/.bashrc"}
        ):
            hooks = ops.detect_hooks_for_changed_files([".bashrc"])
        assert len(hooks) == 1

    def test_hook_unknown_file(self):
        """Changed file not in map should return empty."""
        ops = FakeOps()
        hooks = ops.detect_hooks_for_changed_files(["random_file.txt"])
        # No sections → no hooks
        assert hooks == []

    def test_hook_dedup(self):
        """Same file changed twice should not duplicate hooks."""
        ops = FakeOps()
        with patch(
            "dot_man.constants.HOOK_ALIASES", {"bash_reload": "source ~/.bashrc"}
        ):
            hooks = ops.detect_hooks_for_changed_files([".bashrc", ".bashrc"])
        assert len(hooks) == 1

    def test_hook_with_section_hooks(self):
        """Changed file should also trigger section pre/post_deploy hooks."""
        from dot_man.config import Section

        section = Section(
            name="bash",
            paths=[Path("/home/user/.bashrc")],
            pre_deploy="echo before",
            post_deploy="echo after",
        )
        ops = FakeOps(sections={"bash": section})

        hooks = ops.detect_hooks_for_changed_files(["/home/user/.bashrc"])
        assert "echo before" in hooks
        assert "echo after" in hooks

    def test_hook_all_hooks_combined(self):
        """Both FILE_TO_HOOK_MAP and section hooks should be included."""
        section = type(
            "Section",
            (),
            {
                "paths": [Path("/home/user/.bashrc")],
                "pre_deploy": "echo custom",
                "post_deploy": None,
            },
        )()
        ops = FakeOps(sections={"bash": section})

        with patch(
            "dot_man.constants.HOOK_ALIASES", {"bash_reload": "source ~/.bashrc"}
        ):
            hooks = ops.detect_hooks_for_changed_files(["/home/user/.bashrc"])
        assert "echo custom" in hooks
        assert any("source" in h for h in hooks)


class TestFindSectionForFile:
    def test_find_exact_match(self):
        """Should find section that exactly matches path."""
        from dot_man.config import Section

        section = Section(name="bash", paths=[Path("/home/user/.bashrc")])
        ops = FakeOps(sections={"bash": section})
        result = ops._find_section_for_file("/home/user/.bashrc")
        assert result == "bash"

    def test_find_subpath_match(self, tmp_path):
        """Should find section that is parent of path."""
        from dot_man.config import Section

        config_dir = tmp_path / ".config"
        config_dir.mkdir()
        section = Section(name="config", paths=[config_dir])
        ops = FakeOps(sections={"config": section})
        result = ops._find_section_for_file(str(config_dir / "nvim" / "init.lua"))
        assert result == "config"

    def test_find_no_match(self):
        """Should return None for untracked files."""
        from dot_man.config import Section

        section = Section(name="bash", paths=[Path("/home/user/.bashrc")])
        ops = FakeOps(sections={"bash": section})
        result = ops._find_section_for_file("/untracked/file.txt")
        assert result is None

    def test_find_tilde_expansion(self):
        """Should expand ~ in file paths."""
        from dot_man.config import Section

        section = Section(name="bash", paths=[Path.home() / ".bashrc"])
        ops = FakeOps(sections={"bash": section})
        result = ops._find_section_for_file("~/.bashrc")
        assert result == "bash"

    def test_find_multiple_sections(self, tmp_path):
        """Should find correct section among multiple."""
        from dot_man.config import Section

        bashrc = tmp_path / ".bashrc"
        nvim_dir = tmp_path / ".config" / "nvim"
        nvim_dir.mkdir(parents=True)
        bashrc.write_text("")
        section1 = Section(name="bash", paths=[bashrc])
        section2 = Section(name="nvim", paths=[nvim_dir])
        ops = FakeOps(sections={"bash": section1, "nvim": section2})
        result = ops._find_section_for_file(str(nvim_dir / "init.lua"))
        assert result == "nvim"


class TestIsSubpath:
    def test_is_subpath(self):
        """Should return True when path is under parent."""
        ops = FakeOps()
        parent = Path("/home/user")
        child = Path("/home/user/.config/file.txt")
        assert ops._is_subpath(child, parent) is True

    def test_not_subpath(self):
        """Should return False when path is not under parent."""
        ops = FakeOps()
        parent = Path("/home/user")
        other = Path("/other/path")
        assert ops._is_subpath(other, parent) is False

    def test_same_path(self):
        """Same path should be considered a subpath (resolve() normalizes)."""
        ops = FakeOps()
        p = Path("/home/user")
        assert ops._is_subpath(p, p) is True


class TestFILE_TO_HOOK_MAP:
    """Verify FILE_TO_HOOK_MAP covers all known patterns."""

    def test_bashrc_mapped(self):
        assert FILE_TO_HOOK_MAP[".bashrc"] == "bash_reload"

    def test_zshrc_mapped(self):
        assert FILE_TO_HOOK_MAP[".zshrc"] == "zsh_reload"

    def test_tmux_mapped(self):
        assert FILE_TO_HOOK_MAP[".tmux.conf"] == "tmux_reload"

    def test_nvim_mapped(self):
        assert FILE_TO_HOOK_MAP[".config/nvim"] == "nvim_sync"

    def test_kitty_mapped(self):
        assert FILE_TO_HOOK_MAP[".config/kitty"] == "kitty_reload"

    def test_key_count(self):
        """All 26 entries should be mapped."""
        assert len(FILE_TO_HOOK_MAP) == 26
