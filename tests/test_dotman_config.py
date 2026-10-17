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
        """VALID_UPDATE_STRATEGIES is canonical in constants (used by Section)."""
        from dot_man.constants import VALID_UPDATE_STRATEGIES

        assert VALID_UPDATE_STRATEGIES == ["replace", "rename_old", "ignore"]


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


def _load(tmp_path, text):
    """Write dot-man.toml and return a loaded DotManConfig."""
    from dot_man.dotman_config import DotManConfig

    (tmp_path / "dot-man.toml").write_text(text)
    cfg = DotManConfig(tmp_path)
    cfg.load()
    return cfg


class TestConfigDiscovery:
    """Multiple config files resolve by TOML-over-YAML priority."""

    def test_toml_wins_over_yaml(self, tmp_path):
        from dot_man.dotman_config import DotManConfig

        (tmp_path / "dot-man.toml").write_text('[a]\npaths = ["~/a"]\n')
        (tmp_path / "dot-man.yaml").write_text("b:\n  paths: ['~/b']\n")

        cfg = DotManConfig(tmp_path)

        assert cfg._path.name == "dot-man.toml"


class TestTemplateInheritance:
    """Local and global templates resolve into sections."""

    def test_inherits_single_string(self, tmp_path):
        """A bare `inherits = \"base\"` string behaves like a one-list."""
        cfg = _load(
            tmp_path,
            "[bashrc]\npaths = ['~/.bashrc']\ninherits = 'base'\n"
            "[templates.base]\nupdate_strategy = 'rename_old'\n",
        )

        section = cfg.get_section("bashrc")

        assert section.update_strategy == "rename_old"

    def test_resolve_template_from_global(self, tmp_path):
        """Templates missing locally fall back to the global config."""
        from dot_man.dotman_config import DotManConfig
        from dot_man.global_config import GlobalConfig

        (tmp_path / "dot-man.toml").write_text(
            "[bashrc]\npaths = ['~/.bashrc']\ninherits = ['base']\n"
        )
        gc = GlobalConfig()
        gc._data = {"templates": {"base": {"update_strategy": "rename_old"}}}

        cfg = DotManConfig(tmp_path, global_config=gc)
        cfg.load()

        assert cfg.get_section("bashrc").update_strategy == "rename_old"


class TestGetSectionCaching:
    """Resolved sections are memoized and invalidated on mutation (A10)."""

    def test_repeated_get_section_returns_cached_instance(self, tmp_path):
        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")

        first = cfg.get_section("bashrc")

        assert cfg.get_section("bashrc") is first

    def test_update_section_invalidates_cache(self, tmp_path):
        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")
        first = cfg.get_section("bashrc")

        cfg.update_section("bashrc", deploy_method="symlink")
        second = cfg.get_section("bashrc")

        assert second is not first
        assert second.deploy_method == "symlink"

    def test_add_section_invalidates_cache(self, tmp_path):
        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")

        cfg.add_section("nvim", ["~/.config/nvim"])
        section = cfg.get_section("nvim")

        assert section.name == "nvim"


class TestGetSectionValidation:
    """get_section rejects bad shapes and bad values."""

    def test_paths_single_string(self, tmp_path):
        """A bare `paths = \"...\"` string is a schema error, not a one-list.

        Silently wrapping it hides a typo (`paths = \"~/a ~/b\"` becomes one
        bogus path) behind a confusing not-found later; reject it loudly.
        """
        import pytest

        from dot_man.exceptions import ConfigValidationError

        cfg = _load(tmp_path, "[bashrc]\npaths = '~/.bashrc'\n")

        with pytest.raises(ConfigValidationError, match=r"\[bashrc\].*paths"):
            cfg.get_section("bashrc")

    def test_invalid_deploy_method(self, tmp_path):
        import pytest

        from dot_man.exceptions import ConfigValidationError

        cfg = _load(
            tmp_path, "[bashrc]\npaths = ['~/.bashrc']\ndeploy_method = 'teleport'\n"
        )

        with pytest.raises(ConfigValidationError, match="teleport"):
            cfg.get_section("bashrc")

    def test_missing_section_raises(self, tmp_path):
        import pytest

        from dot_man.exceptions import ConfigurationError

        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")

        with pytest.raises(ConfigurationError, match="ghost"):
            cfg.get_section("ghost")


class TestAddSectionErrors:
    """add_section rejects empty, blank, and reserved inputs."""

    def test_no_paths_rejected(self, tmp_path):
        import pytest

        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        cfg = DotManConfig(tmp_path)

        with pytest.raises(ConfigurationError, match="at least one path"):
            cfg.add_section("empty", [])

    def test_blank_path_rejected(self, tmp_path):
        import pytest

        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        cfg = DotManConfig(tmp_path)

        with pytest.raises(ConfigurationError, match="non-empty strings"):
            cfg.add_section("bad", ["   "])

    def test_templates_name_reserved(self, tmp_path):
        import pytest

        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        cfg = DotManConfig(tmp_path)

        with pytest.raises(ConfigurationError, match="reserved"):
            cfg.add_section("templates", ["~/x"])


class TestReservedTables:
    """Top-level reserved tables must never be treated as tracked sections."""

    def test_secrets_table_is_not_a_section(self, tmp_path):
        cfg = _load(
            tmp_path,
            "[secrets]\npatterns = ['CUSTOM_[A-Z]+']\n\n"
            "[bashrc]\npaths = ['~/.bashrc']\n",
        )

        assert cfg.get_section_names() == ["bashrc"]

    def test_secrets_name_reserved(self, tmp_path):
        from dot_man.dotman_config import DotManConfig
        from dot_man.exceptions import ConfigurationError

        cfg = DotManConfig(tmp_path)
        with pytest.raises(ConfigurationError, match="reserved"):
            cfg.add_section("secrets", ["~/x"])


class TestSectionEncryptionFields:
    """Per-section encryption config must reach the resolved Section."""

    def test_encryption_fields_forwarded(self, tmp_path):
        cfg = _load(
            tmp_path,
            "[creds]\n"
            "paths = ['~/.creds']\n"
            "encrypted = true\n"
            "encryption_method = 'age'\n"
            "encryption_recipient = 'me@example.com'\n",
        )

        section = cfg.get_section("creds")

        assert section.encrypted is True
        assert section.encryption_method == "age"
        assert section.encryption_recipient == "me@example.com"


class TestUpdateSection:
    """update_section edits keys and removes them on None."""

    def test_missing_section_rejected(self, tmp_path):
        import pytest

        from dot_man.exceptions import ConfigurationError

        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")

        with pytest.raises(ConfigurationError, match="ghost"):
            cfg.update_section("ghost", update_strategy="rename_old")

    def test_unknown_key_rejected(self, tmp_path):
        import pytest

        from dot_man.exceptions import ConfigurationError

        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\n")

        with pytest.raises(ConfigurationError, match="Unknown key"):
            cfg.update_section("bashrc", bogus_key="x")

    def test_none_removes_key(self, tmp_path):
        cfg = _load(
            tmp_path,
            "[bashrc]\npaths = ['~/.bashrc']\nupdate_strategy = 'rename_old'\n",
        )

        cfg.update_section("bashrc", update_strategy=None)

        assert "update_strategy" not in cfg._data["bashrc"]
        assert cfg.get_section("bashrc").update_strategy == "replace"


class TestValidate:
    """validate() reports problems instead of raising."""

    def test_missing_path_warns(self, tmp_path):
        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/definitely-not-here-xyz']\n")

        warnings = cfg.validate()

        assert any("does not exist" in w for w in warnings)

    def test_unresolved_template_warns(self, tmp_path):
        cfg = _load(
            tmp_path,
            "[bashrc]\npaths = ['~/.bashrc']\ninherits = ['ghost-template']\n",
        )

        warnings = cfg.validate()

        assert any("Template not found" in w for w in warnings)

    def test_unknown_key_warns(self, tmp_path):
        cfg = _load(tmp_path, "[bashrc]\npaths = ['~/.bashrc']\nbogus = 1\n")

        warnings = cfg.validate()

        assert any("Unknown key" in w for w in warnings)

    def test_broken_section_warns(self, tmp_path):
        """A section that cannot resolve becomes a warning, not an error."""
        cfg = _load(tmp_path, "[empty]\nupdate_strategy = 'replace'\n")

        warnings = cfg.validate()

        assert any("empty" in w for w in warnings)

    def test_clean_config_is_quiet(self, tmp_path):
        real = tmp_path / ".bashrc"
        real.write_text("x")
        cfg = _load(tmp_path, f"[bashrc]\npaths = ['{real}']\n")

        assert cfg.validate() == []
