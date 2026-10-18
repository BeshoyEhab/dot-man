"""Tests for operations module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dot_man import constants


def _ops():
    """Plain operations instance (lazy properties, no IO on init)."""
    from dot_man.operations import DotManOperations

    return DotManOperations()


def _section(name, paths, **kwargs):
    """Section with Path objects for the given path strings."""
    from dot_man.section import Section

    return Section(name=name, paths=[Path(p) for p in paths], **kwargs)


class TestDeploymentPlan:
    """Test DeploymentPlan TypedDict."""

    def test_deployment_plan_creation(self):
        """Test creating a DeploymentPlan."""
        from dot_man.operations import DeploymentPlan

        plan: DeploymentPlan = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": [],
        }
        assert "sections_to_deploy" in plan
        assert "errors" in plan


class TestDotManOperationsInit:
    """Test DotManOperations initialization."""

    def test_operations_init(self):
        """Test DotManOperations can be instantiated."""
        from dot_man.operations import DotManOperations

        ops = DotManOperations.__new__(DotManOperations)
        ops._git = MagicMock()
        ops._config = MagicMock()
        ops._vault = MagicMock()
        ops._backups = MagicMock()

        assert ops is not None


class TestDotManOperationsProperties:
    """Test DotManOperations properties."""

    @patch("dot_man.operations.GitManager")
    def test_git_property(self, mock_git):
        """Test git property."""
        from dot_man.operations import DotManOperations

        ops = DotManOperations.__new__(DotManOperations)
        mock_gm = MagicMock()
        mock_git.return_value = mock_gm
        ops._git = None

        result = ops.git
        assert result is not None


class TestReloadConfig:
    """reload_config must drop all branch-derived caches (A13)."""

    def test_clears_global_and_dotman_config(self):
        from dot_man.operations import DotManOperations

        ops = DotManOperations()
        ops._global_config = MagicMock()
        ops._dotman_config = MagicMock()

        ops.reload_config()

        assert ops._global_config is None
        assert ops._dotman_config is None


class TestOperationsModuleExports:
    """Test module exports."""

    def test_file_lock_exported(self):
        """Test FileLock is exported from operations."""
        from dot_man.operations import FileLock

        assert FileLock is not None

    def test_lock_file_exported(self):
        """Test the lock file path comes from constants."""
        from dot_man.constants import get_lock_file

        assert get_lock_file().name == ".lock"

    def test_save_deploy_mixin_exported(self):
        """Test SaveDeployMixin is exported."""
        from dot_man.operations import SaveDeployMixin

        assert SaveDeployMixin is not None


class TestIterSectionPaths:
    """Real traversal, filtering, and deleted-file reporting."""

    def _names(self, results):
        return {local.name for local, _, _ in results}

    def test_exclude_skips_files(self, tmp_path):
        """Excluded globs never yield."""
        target = tmp_path / "cfg"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        (target / "skip.log").write_text("skip")

        section = _section("cfg", [str(target)], exclude=["*.log"])
        results = list(_ops().iter_section_paths(section))

        assert self._names(results) == {"keep.txt"}

    def test_include_filters_files(self, tmp_path):
        """Include globs restrict what yields."""
        target = tmp_path / "cfg"
        target.mkdir()
        (target / "a.txt").write_text("a")
        (target / "b.md").write_text("b")

        section = _section("cfg", [str(target)], include=["*.txt"])
        results = list(_ops().iter_section_paths(section))

        assert self._names(results) == {"a.txt"}

    def test_excluded_dir_pruned(self, tmp_path):
        """Excluded directories are pruned before descent."""
        target = tmp_path / "cfg"
        (target / "skipdir").mkdir(parents=True)
        (target / "keep.txt").write_text("keep")
        (target / "skipdir" / "inner.txt").write_text("inner")

        section = _section("cfg", [str(target)], exclude=["skipdir"])
        results = list(_ops().iter_section_paths(section))

        assert self._names(results) == {"keep.txt"}

    def test_match_by_relative_path(self, tmp_path):
        """Patterns match the full relative path, not just the name."""
        target = tmp_path / "cfg"
        (target / "sub").mkdir(parents=True)
        (target / "sub" / "a.log").write_text("a")
        (target / "top.log").write_text("top")

        section = _section("cfg", [str(target)], exclude=["sub/*.log"])
        results = list(_ops().iter_section_paths(section))

        assert self._names(results) == {"top.log"}
        from dot_man.files import matches_patterns

        assert matches_patterns(Path("sub/a.log"), ["sub/*.log"]) is True
        assert matches_patterns(Path("sub/a.log"), ["*.txt"]) is False

    def test_deleted_reported(self, tmp_path, monkeypatch):
        """Repo files missing locally yield DELETED; filters still apply."""

        repo_root = tmp_path / "repo"
        repo_dir = repo_root / "nvim" / "nvim"
        repo_dir.mkdir(parents=True)
        (repo_dir / "keep.md").write_text("keep")
        (repo_dir / "skip.tmp").write_text("skip")
        (repo_dir / "other.lua").write_text("other")
        monkeypatch.setattr(constants, "REPO_DIR", repo_root)

        missing = tmp_path / "nope" / "nvim"
        missing.mkdir(parents=True)
        section = _section(
            "nvim",
            [str(missing)],
            repo_base="nvim",
            exclude=["*.tmp"],
            include=["*.md"],
        )
        results = list(_ops().iter_section_paths(section))

        assert [(local.name, s) for local, _, s in results] == [("keep.md", "DELETED")]

    def test_outside_tree_root_skipped(self, tmp_path, monkeypatch):
        """A root that escapes the section keeps yielding the rest."""
        target = tmp_path / "cfg"
        (target / "sub").mkdir(parents=True)
        (target / "top.txt").write_text("top")
        (target / "sub" / "sub.txt").write_text("sub")

        real_relative_to = Path.relative_to
        calls = {"n": 0}

        def _once(self, other):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("outside tree")
            return real_relative_to(self, other)

        monkeypatch.setattr(Path, "relative_to", _once)
        section = _section("cfg", [str(target)], exclude=["top*"])
        results = list(_ops().iter_section_paths(section))

        assert self._names(results) == {"sub.txt"}
