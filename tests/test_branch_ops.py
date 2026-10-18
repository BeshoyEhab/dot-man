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

    def save_all(self, secret_handler=None, symlink_ignore=None):
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
        with patch("dot_man.constants.REPO_DIR", tmp_path):
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

        with patch("dot_man.constants.REPO_DIR", tmp_path):
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

        with patch("dot_man.constants.REPO_DIR", tmp_path):
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

        with patch("dot_man.constants.REPO_DIR", tmp_path):
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

        with patch("dot_man.constants.REPO_DIR", tmp_path):
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
        from git import GitCommandError

        git = MagicMock()
        git.repo.git.diff.side_effect = GitCommandError("diff", "git error")
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

    def test_auto_detected_alias_resolves_placeholders(self):
        """Auto-detected aliases must not ship raw {config_name}."""
        from dot_man.config import Section

        section = Section(name="qs", paths=[Path("/home/user/.config/quickshell/ii")])
        ops = FakeOps(sections={"qs": section})

        with patch(
            "dot_man.constants.HOOK_ALIASES",
            {"qs_reload": "qs -c {config_name} &"},
        ):
            with patch.dict(
                "dot_man.branch_ops.FILE_TO_HOOK_MAP",
                {".config/quickshell": "qs_reload"},
            ):
                hooks = ops.detect_hooks_for_changed_files(
                    ["/home/user/.config/quickshell/ii"]
                )
        assert hooks == ["qs -c ii &"]


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
        """All 31 entries should be mapped."""
        assert len(FILE_TO_HOOK_MAP) == 31
