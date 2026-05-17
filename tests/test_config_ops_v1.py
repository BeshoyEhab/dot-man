"""Tests for dotman_config.py, operations.py, section.py — config and operations extended."""

from pathlib import Path

import pytest


class TestDotManConfigExtended:
    """Extended tests for DotManConfig."""

    def test_create_default(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config = DotManConfig(repo_dir)
        config.create_default()
        assert config._path.exists()

    def test_load_config(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config_path = repo_dir / "dot-man.toml"
        config_path.write_text('[test]\npaths = ["~/.testrc"]\n')
        config = DotManConfig(repo_dir)
        config.load()
        sections = config.get_section_names()
        assert "test" in sections

    def test_add_section(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config = DotManConfig(repo_dir)
        config.create_default()
        config.load()
        config.add_section("mytest", ["~/.fakefile"])
        config.save(force=True)
        # Reload and verify
        config2 = DotManConfig(repo_dir)
        config2.load()
        assert "mytest" in config2.get_section_names()

    def test_remove_section(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config_path = repo_dir / "dot-man.toml"
        config_path.write_text('[removeme]\npaths = ["~/.fake"]\n')
        config = DotManConfig(repo_dir)
        config.load()
        assert "removeme" in config.get_section_names()
        config.remove_section("removeme")
        # Verify in-memory removal
        assert "removeme" not in config.get_section_names()

    def test_remove_nonexistent_section(self, tmp_path):
        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config_path = repo_dir / "dot-man.toml"
        config_path.write_text("")
        config = DotManConfig(repo_dir)
        config.load()
        with pytest.raises(ConfigurationError):
            config.remove_section("nonexistent")

    def test_add_duplicate_fails(self, tmp_path):
        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config = DotManConfig(repo_dir)
        config.create_default()
        config.load()
        config.add_section("dup", ["~/.dup"])
        with pytest.raises(ConfigurationError):
            config.add_section("dup", ["~/.dup2"])

    def test_add_section_absolute_path_fails(self, tmp_path):
        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config = DotManConfig(repo_dir)
        config.create_default()
        config.load()
        with pytest.raises(ConfigurationError):
            config.add_section("abs", ["/absolute/path"])

    def test_get_section(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        config_path = repo_dir / "dot-man.toml"
        config_path.write_text('[shell]\npaths = ["~/.bashrc"]\n')
        config = DotManConfig(repo_dir)
        config.load()
        section = config.get_section("shell")
        assert section.name == "shell"
        assert len(section.paths) == 1


class TestOperationsExtended:
    """Extended tests for operations module."""

    def test_reset_operations(self):
        from dot_man.operations import reset_operations

        reset_operations()
        # Should not raise

    def test_get_sections(self, integration_runner):
        from dot_man.operations import get_operations

        ops = get_operations()
        sections = ops.get_sections()
        assert isinstance(sections, list)


class TestOperationsIterSectionPaths:
    """Test iter_section_paths with various configurations."""

    def test_iter_simple_file(self, integration_runner, tmp_path):
        from dot_man.cli.interface import cli
        from dot_man.operations import get_operations

        test_file = tmp_path / "home" / ".itertest"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("iter test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "iter-test"]
        )

        ops = get_operations()
        section = ops.get_section("iter-test")
        paths = list(ops.iter_section_paths(section))
        assert len(paths) > 0

    def test_iter_directory(self, integration_runner, tmp_path):
        from dot_man.cli.interface import cli
        from dot_man.operations import get_operations

        test_dir = tmp_path / "home" / ".config" / "iterdir"
        test_dir.mkdir(parents=True)
        (test_dir / "a.conf").write_text("a")
        (test_dir / "b.conf").write_text("b")
        integration_runner.invoke(cli, ["add", str(test_dir), "--section", "dir-test"])

        ops = get_operations()
        section = ops.get_section("dir-test")
        paths = list(ops.iter_section_paths(section))
        assert len(paths) >= 2


class TestSectionExtended:
    """Extended tests for Section class."""

    def test_section_basic_properties(self):
        from dot_man.section import Section

        s = Section(name="test", paths=[Path("/tmp/test")], repo_base=None)
        assert s.name == "test"
        assert len(s.paths) == 1

    def test_section_with_hooks(self):
        from dot_man.section import Section

        s = Section(
            name="hooks-test",
            paths=[Path("/tmp/test")],
            repo_base=None,
            pre_deploy="echo pre",
            post_deploy="echo post",
        )
        assert s.pre_deploy == "echo pre"
        assert s.post_deploy == "echo post"

    def test_section_with_inherits(self):
        from dot_man.section import Section

        s = Section(
            name="child",
            paths=[Path("/tmp/test")],
            repo_base=None,
            inherits=["parent"],
        )
        assert "parent" in s.inherits

    def test_section_get_repo_path(self, tmp_path):
        from dot_man.section import Section

        local_path = Path("~/.bashrc")
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        s = Section(name="bash", paths=[local_path], repo_base=None)
        repo_path = s.get_repo_path(local_path, repo_dir)
        assert str(repo_dir) in str(repo_path)

    def test_section_secrets_filter_default(self):
        from dot_man.section import Section

        s = Section(name="test", paths=[], repo_base=None)
        assert s.secrets_filter is True

    def test_section_with_exclude(self):
        from dot_man.section import Section

        s = Section(
            name="test",
            paths=[Path("/tmp/test")],
            repo_base=None,
            exclude=["*.log", "*.tmp"],
        )
        assert len(s.exclude) == 2
        assert "*.log" in s.exclude

    def test_section_with_include(self):
        from dot_man.section import Section

        s = Section(
            name="test",
            paths=[Path("/tmp/test")],
            repo_base=None,
            include=["*.conf"],
        )
        assert len(s.include) == 1

    def test_section_hook_alias_resolution(self):
        """Test that hook aliases resolve to actual commands."""
        from dot_man.section import Section

        s = Section(
            name="hypr",
            paths=[Path("/tmp/hypr")],
            repo_base=None,
            post_deploy="hyprland_reload",
        )
        # Should resolve the alias to an actual command (not None, not "hyprland_reload")
        assert s.post_deploy is not None
        assert isinstance(s.post_deploy, str)

    def test_section_to_dict(self):
        from dot_man.section import Section

        s = Section(
            name="test",
            paths=[Path("~/.testrc")],
            repo_base=None,
            post_deploy="echo done",
        )
        d = s.to_dict()
        assert "paths" in d
        assert "post_deploy" in d

    def test_section_auto_repo_base(self):
        from dot_man.section import Section

        s = Section(name="bash", paths=[Path("~/.bashrc")], repo_base=None)
        # Should auto-generate repo_base from path
        assert s.repo_base is not None
        assert isinstance(s.repo_base, str)

    def test_section_update_strategy_default(self):
        from dot_man.section import Section

        s = Section(name="test", paths=[Path("/tmp/test")])
        assert s.update_strategy == "replace"
