"""Tests for dot_man.config — GlobalConfig, Section, DotManConfig."""

import pytest
from pathlib import Path
from unittest.mock import patch

from dot_man.config import GlobalConfig, Section, DotManConfig
from dot_man.exceptions import ConfigurationError, ConfigValidationError
from dot_man.constants import DEFAULT_IGNORED_DIRECTORIES, DEFAULT_BRANCH, HOOK_ALIASES


# ─── GlobalConfig ──────────────────────────────────────────


@pytest.fixture
def global_cfg(tmp_path):
    """Create a GlobalConfig pointing at a temp directory."""
    toml_path = tmp_path / "global.toml"
    with patch("dot_man.global_config.GLOBAL_TOML", toml_path):
        gc = GlobalConfig()
        gc.create_default()
        gc.load()
        yield gc


class TestGlobalConfig:
    def test_load_creates_file(self, global_cfg):
        assert global_cfg.current_branch == DEFAULT_BRANCH

    def test_current_branch_get_set(self, global_cfg):
        global_cfg.current_branch = "work"
        assert global_cfg.current_branch == "work"

    def test_remote_url_get_set(self, global_cfg):
        assert global_cfg.remote_url == ""
        global_cfg.remote_url = "https://github.com/test/repo.git"
        assert global_cfg.remote_url == "https://github.com/test/repo.git"

    def test_editor_get_set(self, global_cfg):
        assert global_cfg.editor is None or isinstance(global_cfg.editor, str)
        global_cfg.editor = "nvim"
        assert global_cfg.editor == "nvim"

    def test_secrets_filter_get_set(self, global_cfg):
        assert global_cfg.secrets_filter_enabled is True
        global_cfg.secrets_filter_enabled = False
        assert global_cfg.secrets_filter_enabled is False

    def test_strict_mode_get_set(self, global_cfg):
        assert global_cfg.strict_mode is False
        global_cfg.strict_mode = True
        assert global_cfg.strict_mode is True

    def test_get_defaults(self, global_cfg):
        defaults = global_cfg.get_defaults()
        assert "secrets_filter" in defaults
        assert "ignored_directories" in defaults
        assert "follow_symlinks" in defaults

    def test_get_template_nonexistent(self, global_cfg):
        assert global_cfg.get_template("nope") is None

    def test_get_all_templates(self, global_cfg):
        templates = global_cfg.get_all_templates()
        assert isinstance(templates, dict)

    def test_save_persistence(self, tmp_path):
        toml_path = tmp_path / "global.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", toml_path):
            gc = GlobalConfig()
            gc.create_default()
            gc.current_branch = "test-persist"
            gc.save(force=True)

            gc2 = GlobalConfig()
            gc2.load()
            assert gc2.current_branch == "test-persist"

    def test_load_missing_raises(self, tmp_path):
        toml_path = tmp_path / "nonexistent.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", toml_path):
            gc = GlobalConfig()
            with pytest.raises(ConfigurationError):
                gc.load()


# ─── Section ───────────────────────────────────────────────


class TestSection:
    def test_basic_creation(self):
        s = Section(name="test", paths=[Path("/home/user/.bashrc")])
        assert s.name == "test"
        assert s.secrets_filter is True
        assert s.update_strategy == "replace"
        assert s.follow_symlinks is False

    def test_defaults(self):
        s = Section(name="s", paths=[Path("/tmp/f")])
        assert s.include == []
        assert s.exclude == []
        assert s.inherits == []
        assert s.ignored_directories == DEFAULT_IGNORED_DIRECTORIES

    def test_repo_base_auto_dotfile(self):
        s = Section(name="bash", paths=[Path("/home/user/.bashrc")])
        assert s.repo_base == "bashrc"

    def test_repo_base_auto_dotdir(self):
        s = Section(name="vim", paths=[Path("/home/user/.vim")])
        assert s.repo_base == "vim"

    def test_repo_base_auto_config_dir(self):
        s = Section(name="nvim", paths=[Path("/home/user/.config/nvim")])
        assert s.repo_base == "nvim"

    def test_repo_base_explicit(self):
        s = Section(name="test", paths=[Path("/tmp/f")], repo_base="custom")
        assert s.repo_base == "custom"

    def test_repo_base_empty_paths(self):
        s = Section(name="empty", paths=[])
        assert s.repo_base == "empty"

    def test_get_repo_path_with_repo_base(self):
        s = Section(name="test", paths=[Path("/tmp/f")], repo_base="mybase")
        result = s.get_repo_path(Path("/tmp/f"), Path("/repo"))
        assert result == Path("/repo/mybase/f")

    def test_get_repo_path_with_repo_path(self):
        s = Section(name="test", paths=[Path("/tmp/f")], repo_path="explicit/dest")
        result = s.get_repo_path(Path("/tmp/f"), Path("/repo"))
        assert result == Path("/repo/explicit/dest")

    def test_to_dict_minimal(self):
        s = Section(name="test", paths=[Path("/tmp/f")])
        d = s.to_dict()
        assert "paths" in d
        # Default values should NOT be in dict
        assert "secrets_filter" not in d
        assert "update_strategy" not in d

    def test_to_dict_non_defaults(self):
        s = Section(
            name="test",
            paths=[Path("/tmp/f")],
            secrets_filter=False,
            update_strategy="rename_old",
            include=["*.conf"],
            exclude=["*.log"],
            pre_deploy="echo pre",
            post_deploy="echo post",
            inherits=["base"],
            follow_symlinks=True,
        )
        d = s.to_dict()
        assert d["secrets_filter"] is False
        assert d["update_strategy"] == "rename_old"
        assert d["include"] == ["*.conf"]
        assert d["exclude"] == ["*.log"]
        assert d["pre_deploy"] == "echo pre"
        assert d["post_deploy"] == "echo post"
        assert d["inherits"] == ["base"]
        assert d["follow_symlinks"] is True

    def test_resolve_hook_none(self):
        s = Section(name="test", paths=[Path("/tmp/f")])
        assert s.pre_deploy is None

    def test_resolve_hook_custom(self):
        s = Section(name="test", paths=[Path("/tmp/f")], post_deploy="echo hello")
        assert s.post_deploy == "echo hello"

    def test_resolve_hook_alias(self):
        s = Section(name="test", paths=[Path("/tmp/f")], post_deploy="shell_reload")
        assert s.post_deploy == HOOK_ALIASES["shell_reload"]

    def test_custom_ignored_directories(self):
        s = Section(name="test", paths=[Path("/tmp/f")], ignored_directories=["custom"])
        assert s.ignored_directories == ["custom"]


# ─── DotManConfig ──────────────────────────────────────────


@pytest.fixture
def dotman_cfg(tmp_path):
    """Create a DotManConfig with a sample toml."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    toml_content = """
[myconfig]
paths = ["/tmp/test.conf"]

[shell]
paths = ["~/.bashrc", "~/.zshrc"]
post_deploy = "shell_reload"
secrets_filter = false

[templates.base]
update_strategy = "rename_old"
"""
    (repo_dir / "dot-man.toml").write_text(toml_content)

    global_toml = tmp_path / "global.toml"
    with patch("dot_man.global_config.GLOBAL_TOML", global_toml), \
         patch("dot_man.config.REPO_DIR", repo_dir):
        gc = GlobalConfig()
        gc.create_default()
        gc.load()

        dc = DotManConfig(repo_path=repo_dir, global_config=gc)
        dc.load()
        yield dc


class TestDotManConfig:
    def test_get_section_names(self, dotman_cfg):
        names = dotman_cfg.get_section_names()
        assert "myconfig" in names
        assert "shell" in names
        assert "templates" not in names

    def test_get_section(self, dotman_cfg):
        s = dotman_cfg.get_section("myconfig")
        assert s.name == "myconfig"
        assert len(s.paths) == 1

    def test_get_section_with_overrides(self, dotman_cfg):
        s = dotman_cfg.get_section("shell")
        assert s.secrets_filter is False
        assert s.post_deploy == HOOK_ALIASES["shell_reload"]
        assert len(s.paths) == 2

    def test_get_section_nonexistent(self, dotman_cfg):
        with pytest.raises(ConfigurationError):
            dotman_cfg.get_section("nope")

    def test_repo_path_property(self, dotman_cfg):
        assert dotman_cfg.repo_path.exists()

    def test_get_local_templates(self, dotman_cfg):
        templates = dotman_cfg.get_local_templates()
        assert "base" in templates

    def test_save_and_reload(self, dotman_cfg):
        dotman_cfg._data["newsection"] = {"paths": ["/tmp/new"]}
        dotman_cfg._dirty = True
        dotman_cfg.save(force=True)

        dc2 = DotManConfig(
            repo_path=dotman_cfg.repo_path,
            global_config=dotman_cfg._global_config,
        )
        dc2.load()
        assert "newsection" in dc2.get_section_names()

    def test_validate_schema_warns(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text(
            '[bad]\npaths = ["/tmp/f"]\nunknown_key = "oops"\n'
        )
        global_toml = tmp_path / "global.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", global_toml), \
             patch("dot_man.config.REPO_DIR", repo_dir):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.load()  # Should print warning but not raise

    def test_invalid_update_strategy(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text(
            '[bad]\npaths = ["/tmp/f"]\nupdate_strategy = "invalid"\n'
        )
        global_toml = tmp_path / "global.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", global_toml), \
             patch("dot_man.config.REPO_DIR", repo_dir):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.load()
            with pytest.raises(ConfigValidationError):
                dc.get_section("bad")

    def test_section_no_paths_raises(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[empty]\n")
        global_toml = tmp_path / "global.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", global_toml), \
             patch("dot_man.config.REPO_DIR", repo_dir):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.load()
            with pytest.raises(ConfigValidationError):
                dc.get_section("empty")

    def test_inheritance(self, dotman_cfg):
        """Test that inherits applies template settings."""
        # Add a section that inherits from 'base' template
        dotman_cfg._data["child"] = {
            "paths": ["/tmp/child"],
            "inherits": ["base"],
        }
        s = dotman_cfg.get_section("child")
        assert s.update_strategy == "rename_old"  # From template

    def test_create_default(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        global_toml = tmp_path / "global.toml"
        with patch("dot_man.global_config.GLOBAL_TOML", global_toml), \
             patch("dot_man.config.REPO_DIR", repo_dir):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.create_default()
            assert (repo_dir / "dot-man.toml").exists()

    def test_load_missing_raises(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("dot_man.config.REPO_DIR", repo_dir):
            dc = DotManConfig(repo_path=repo_dir)
            with pytest.raises(ConfigurationError):
                dc.load()
