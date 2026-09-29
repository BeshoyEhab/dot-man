"""Tests for dotman_config module."""

from unittest.mock import patch

import pytest


class TestDotManConfigInit:
    """Test DotManConfig initialization."""

    def test_dotman_config_init_default(self, tmp_path):
        """Test DotManConfig with default path."""
        from dot_man.dotman_config import DotManConfig

        with patch("dot_man.dotman_config.REPO_DIR", tmp_path):
            config = DotManConfig()
            assert config.repo_path == tmp_path

    def test_dotman_config_init_custom(self, tmp_path):
        """Test DotManConfig with custom path."""
        from dot_man.dotman_config import DotManConfig

        config = DotManConfig(tmp_path)
        assert config.repo_path == tmp_path


class TestDotManConfigProperties:
    """Test DotManConfig properties."""

    def test_repo_path_property(self, tmp_path):
        """Test repo_path property."""
        from dot_man.dotman_config import DotManConfig

        config = DotManConfig(tmp_path)
        assert config.repo_path == tmp_path


class TestDotManConfigLoad:
    """Test DotManConfig load method."""

    def test_load_no_config(self, tmp_path):
        """Test load raises error when config doesn't exist."""
        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        with patch("dot_man.dotman_config.REPO_DIR", tmp_path):
            config = DotManConfig()
            with pytest.raises(ConfigurationError):
                config.load()


class TestDotManConfigSave:
    """Test DotManConfig save method."""

    def test_save_no_doc(self, tmp_path):
        """Test save with no document."""
        from dot_man.dotman_config import DotManConfig

        with patch("dot_man.dotman_config.REPO_DIR", tmp_path):
            config = DotManConfig()
            config.save()  # Should not raise


class TestConfigConstants:
    """Test config module constants."""

    def test_config_file_priority(self):
        """Test CONFIG_FILE_PRIORITY exists."""
        from dot_man.dotman_config import CONFIG_FILE_PRIORITY

        assert isinstance(CONFIG_FILE_PRIORITY, list)
        assert len(CONFIG_FILE_PRIORITY) > 0

    def test_valid_update_strategies(self):
        """Test VALID_UPDATE_STRATEGIES exists."""
        from dot_man.dotman_config import VALID_UPDATE_STRATEGIES

        assert isinstance(VALID_UPDATE_STRATEGIES, (list, tuple))


class TestDefaultTemplateSlim:
    """Default dot-man.toml is short and teaches current commands."""

    def _default_content(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        DotManConfig(tmp_path).create_default()
        return (tmp_path / "dot-man.toml").read_text()

    def test_default_template_is_short(self, tmp_path):
        assert len(self._default_content(tmp_path).splitlines()) < 40

    def test_default_template_has_two_examples(self, tmp_path):
        content = self._default_content(tmp_path)
        assert "[bashrc]" in content
        assert "[nvim]" in content

    def test_default_template_teaches_current_commands(self, tmp_path):
        content = self._default_content(tmp_path)
        assert "dot-man switch" not in content
        assert "navigate" in content
        assert "github.com" not in content
