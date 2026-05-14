"""Tests for global_config.py — Global configuration management."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest


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
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield dot_man_dir, repo_dir, global_toml


class TestGlobalConfigBasics:
    def test_global_config_creation(self, clean_env):
        """Test creating global config."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        assert global_toml.exists()

    def test_global_config_load(self, clean_env):
        """Test loading global config."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        gc2 = GlobalConfig()
        assert gc2._data is not None


class TestGlobalConfigProperties:
    def test_current_branch(self, clean_env):
        """Test current branch property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        gc.current_branch = "work"
        assert gc.current_branch == "work"

    def test_remote_url(self, clean_env):
        """Test remote URL property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        gc.remote_url = "https://github.com/user/dotfiles.git"
        assert gc.remote_url == "https://github.com/user/dotfiles.git"

    def test_editor(self, clean_env):
        """Test editor property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        gc.editor = "vim"
        assert gc.editor == "vim"

    def test_secrets_filter_enabled(self, clean_env):
        """Test secrets_filter_enabled property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        assert gc.secrets_filter_enabled is True
        gc.secrets_filter_enabled = False
        assert gc.secrets_filter_enabled is False

    def test_strict_mode(self, clean_env):
        """Test strict_mode property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        assert gc.strict_mode is False
        gc.strict_mode = True
        assert gc.strict_mode is True

    def test_switch_default_behavior(self, clean_env):
        """Test switch_default_behavior property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        assert gc.switch_default_behavior == "save"
        gc.switch_default_behavior = "no-save"
        assert gc.switch_default_behavior == "no-save"


class TestGlobalConfigTemplates:
    def test_get_all_templates(self, clean_env):
        """Test getting all templates."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        templates = gc.get_all_templates()
        assert isinstance(templates, dict)

    def test_get_template(self, clean_env):
        """Test getting a specific template."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        template = gc.get_template("default")
        # Default template might not exist
        assert template is None or isinstance(template, dict)


class TestGlobalConfigProfiles:
    def test_profiles(self, clean_env):
        """Test profiles property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        profiles = gc.profiles
        assert isinstance(profiles, dict)

    def test_current_profile(self, clean_env):
        """Test current_profile property."""
        dot_man_dir, repo_dir, global_toml = clean_env

        from dot_man.global_config import GlobalConfig

        global_toml.parent.mkdir(parents=True, exist_ok=True)
        gc = GlobalConfig()
        gc.create_default()

        # Default should be empty or None
        current = gc.current_profile
        assert current is None or isinstance(current, str)
