"""Tests for configuration comment and format preservation (TOML/YAML)."""

from ruamel.yaml import YAML

from dot_man.dotman_config import DotManConfig
from dot_man.global_config import GlobalConfig


def test_toml_comment_and_key_preservation(tmp_path):
    """Test that modifying a TOML config preserves comments and removes deleted keys."""
    config_file = tmp_path / "global.toml"

    # Write a TOML file with comments and a stale section/key
    config_content = """# Global configuration file for dot-man
[dot-man]
# The active configuration branch
current_branch = "master"
version = "1.0.0"

# Stale section to delete
[stale_section]
# Stale key
temp_val = 123
"""
    config_file.write_text(config_content)

    # Load via GlobalConfig
    gc = GlobalConfig()
    gc._path = config_file
    gc.load()

    # Modify current_branch
    gc.current_branch = "work"

    # Delete stale section from data
    if "stale_section" in gc._data:
        del gc._data["stale_section"]
        gc._dirty = True

    gc.save()

    # Read the output text
    output_text = config_file.read_text()

    # Assertions
    assert 'current_branch = "work"' in output_text
    assert "# Global configuration file for dot-man" in output_text
    assert "# The active configuration branch" in output_text
    assert "stale_section" not in output_text
    assert "temp_val" not in output_text
    assert 'version = "1.0.0"' in output_text


def test_yaml_comment_and_key_preservation(tmp_path):
    """Test that modifying a YAML config preserves comments, format, and removes deleted keys."""
    config_file = tmp_path / "global.yaml"

    # Write a YAML file with comments and a stale section/key
    config_content = """# Global configuration file for dot-man
dot-man:
  # The active configuration branch
  current_branch: master
  version: 1.0.0

# Stale section to delete
stale_section:
  # Stale key
  temp_val: 123
"""
    config_file.write_text(config_content)

    # Load via GlobalConfig
    gc = GlobalConfig()
    gc._path = config_file
    gc.load()

    # Modify current_branch
    gc.current_branch = "work"

    # Delete stale section from data
    if "stale_section" in gc._data:
        del gc._data["stale_section"]
        gc._dirty = True

    gc.save()

    # Read the output text
    output_text = config_file.read_text()

    # Assertions
    assert "current_branch: work" in output_text
    assert "# Global configuration file for dot-man" in output_text
    assert "# The active configuration branch" in output_text
    assert "stale_section" not in output_text
    assert "temp_val" not in output_text
    assert "version: 1.0.0" in output_text
    # Ensure it's still valid YAML
    yaml = YAML()
    parsed = yaml.load(output_text)
    assert parsed["dot-man"]["current_branch"] == "work"
    assert "stale_section" not in parsed


def test_dotman_config_yaml_save(tmp_path):
    """Test that DotManConfig loads and saves YAML files correctly without renaming to TOML."""
    config_file = tmp_path / "dot-man.yaml"

    # Write a YAML file with comments
    config_content = """# Dotfile repository config
paths:
  - ~/.bashrc
# Secret settings
secrets_filter: true
"""
    config_file.write_text(config_content)

    # Load via DotManConfig
    config = DotManConfig(repo_path=tmp_path)
    config.load()

    # Modify values
    config._data["secrets_filter"] = False
    config._dirty = True
    config.save()

    # Verify the saved file has correct suffix and contents
    assert config_file.exists()
    # Check that it did NOT create a dot-man.toml file
    assert not (tmp_path / "dot-man.toml").exists()

    output_text = config_file.read_text()
    assert "# Dotfile repository config" in output_text
    assert "# Secret settings" in output_text
    assert "secrets_filter: false" in output_text
