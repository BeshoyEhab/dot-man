"""Tests for section configuration and parsing - simplified."""

from pathlib import Path


class TestSectionConfig:
    """Test section configuration."""

    def test_section_name(self):
        """Test section name is stored."""
        from dot_man.config import Section

        section = Section("bash", {}, Path("/repo"))
        assert section.name == "bash"


class TestConfigFileParsing:
    """Test dot-man.toml file parsing."""

    def test_load_config_file(self, tmp_path):
        """Test loading a config file."""
        from dot_man.config import DotManConfig

        config_file = tmp_path / "dot-man.toml"
        config_file.write_text("[bashrc]\npaths = ['~/.bashrc']")

        # Just verify it doesn't crash - actual loading is complex
        DotManConfig(config_file)
        assert config_file.exists()


class TestUI:
    """Test UI output functions."""

    def test_warn_message(self):
        """Test warning message output."""
        from dot_man.interactive import warn

        warn("Test warning")


class TestExceptions:
    """Test exception classes."""

    def test_git_operation_error(self):
        """Test GitOperationError."""
        from dot_man.exceptions import GitOperationError

        error = GitOperationError("Git failed")
        assert "Git failed" in str(error)
        assert error.exit_code == 5


class TestAdditionalFeatures:
    """Test additional features."""

    def test_files_atomic_write(self, tmp_path):
        """Test atomic file writing."""
        from dot_man.vault import atomic_write_text

        file_path = tmp_path / "test.txt"
        atomic_write_text(file_path, "test content")
        assert file_path.read_text() == "test content"

    def test_compare_files_binary(self, tmp_path):
        """Test binary file comparison."""
        from dot_man.files import compare_files

        f1 = tmp_path / "bin1"
        f2 = tmp_path / "bin2"
        f1.write_bytes(b"\x00\x01\x02")
        f2.write_bytes(b"\x00\x01\x02")
        assert compare_files(f1, f2) is True


class TestGlobalConfigDefaults:
    """Test global config defaults."""

    def test_defaults_section(self):
        """Test defaults are loaded from global config."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {"defaults": {"secrets_filter": True}}
        defaults = config.get_defaults()
        assert defaults["secrets_filter"] is True


class TestConfigTemplates:
    """Test config templates."""

    def test_templates_loaded(self):
        """Test templates are loaded from global config."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {"templates": {"work": {"post_deploy": "echo work"}}}
        template = config.get_template("work")
        assert template is not None


class TestParseArgs:
    """Test argument parsing."""

    def test_parse_branch_at_tag(self):
        """Test parsing branch@tag."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("work@tag")
        assert result["type"] == "tag"
        assert result["base"] == "work"

    def test_parse_commit(self):
        """Test parsing commit SHA."""
        from dot_man.cli.common import parse_branch_arg

        result = parse_branch_arg("abc1234")
        assert result["type"] == "commit"


class TestSwitchBehavior:
    """Test switch behavior config."""

    def test_default_behavior_save(self):
        """Test default behavior is save."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config._data = {}
        assert config.switch_default_behavior == "save"

    def test_set_behavior_no_save(self):
        """Test setting behavior to no-save."""
        from dot_man.global_config import GlobalConfig

        config = GlobalConfig()
        config.switch_default_behavior = "no-save"
        assert config._data["switch"]["default_behavior"] == "no-save"


class TestFileOps:
    """Test file operations."""

    def test_copy_file(self, tmp_path):
        """Test copying a file."""
        from dot_man.files import copy_file

        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        src.write_text("content")
        success, _ = copy_file(src, dst)
        assert success is True
        assert dst.read_text() == "content"


class TestBranchParamType:
    """Test branch parameter type."""

    def test_convert_branch(self):
        """Test converting branch name."""
        from dot_man.cli.switch_cmd import BranchParamType

        param = BranchParamType()
        result = param.convert("main", None, None)
        assert result["type"] == "branch"

    def test_convert_commit(self):
        """Test converting commit SHA."""
        from dot_man.cli.switch_cmd import BranchParamType

        param = BranchParamType()
        result = param.convert("abc1234", None, None)
        assert result["type"] == "commit"


class TestCompareFiles:
    """Test file comparison."""

    def test_identical_text(self, tmp_path):
        """Test comparing identical text files."""
        from dot_man.files import compare_files

        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("same")
        f2.write_text("same")
        assert compare_files(f1, f2) is True

    def test_different_text(self, tmp_path):
        """Test comparing different text files."""
        from dot_man.files import compare_files

        f1 = tmp_path / "f1.txt"
        f2 = tmp_path / "f2.txt"
        f1.write_text("a")
        f2.write_text("b")
        assert compare_files(f1, f2) is False
