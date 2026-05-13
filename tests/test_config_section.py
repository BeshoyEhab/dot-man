"""Tests for config and section modules."""

from pathlib import Path


class TestSectionClass:
    """Test Section class."""

    def test_section_init(self):
        """Test Section initialization."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            update_strategy="replace",
        )
        assert section.name == "test"
        assert len(section.paths) == 1
        assert section.repo_base == "test"

    def test_section_get_repo_path(self):
        """Test Section.get_repo_path."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            update_strategy="replace",
        )

        repo_dir = Path("/repo")
        result = section.get_repo_path(Path("/home/test"), repo_dir)
        assert "test" in str(result)

    def test_section_with_hooks(self):
        """Test Section with pre/post deploy hooks."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            pre_deploy="echo 'pre'",
            post_deploy="echo 'post'",
        )
        assert section.pre_deploy == "echo 'pre'"
        assert section.post_deploy == "echo 'post'"

    def test_section_secrets_filter(self):
        """Test Section secrets_filter property."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            secrets_filter=True,
        )
        assert section.secrets_filter is True


class TestDotManConfigClass:
    """Test DotManConfig class."""

    def test_dotman_config_init(self, tmp_path):
        """Test DotManConfig initialization."""
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        config = DotManConfig(repo_dir)
        assert config is not None

    def test_dotman_config_load_with_file(self, tmp_path):
        """Test DotManConfig loads from file."""
        from dot_man.dotman_config import DotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        toml_file = repo_dir / "dot-man.toml"
        toml_file.write_text("""
[test_section]
paths = ["/home/test"]
repo_base = "test"
update_strategy = "replace"
""")

        config = DotManConfig(repo_dir)
        config.load()

        assert "test_section" in config._data


class TestGlobalConfigClass:
    """Test GlobalConfig class."""

    def test_global_config_init(self):
        """Test GlobalConfig initialization."""
        from dot_man.config import GlobalConfig

        config = GlobalConfig()
        assert config is not None

    def test_global_config_properties(self):
        """Test GlobalConfig properties."""
        from dot_man.config import GlobalConfig

        config = GlobalConfig()

        # These should return default values
        assert config.current_branch is not None
        assert isinstance(config.current_branch, str)
        assert config.remote_url == ""
        assert config.strict_mode is False

    def test_global_config_defaults(self):
        """Test GlobalConfig default values."""
        from dot_man.config import GlobalConfig

        config = GlobalConfig()

        # These should have default values
        assert config.secrets_filter_enabled is not None
        assert config.switch_default_behavior is not None


class TestSectionUpdateStrategies:
    """Test Section update strategies."""

    def test_section_replace_strategy(self):
        """Test replace strategy."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            update_strategy="replace",
        )
        assert section.update_strategy == "replace"

    def test_section_rename_old_strategy(self):
        """Test rename_old strategy."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            update_strategy="rename_old",
        )
        assert section.update_strategy == "rename_old"

    def test_section_ignore_strategy(self):
        """Test ignore strategy."""
        from dot_man.config import Section

        section = Section(
            name="test",
            paths=[Path("/home/test")],
            repo_base="test",
            update_strategy="ignore",
        )
        assert section.update_strategy == "ignore"
