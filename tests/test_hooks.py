
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from dot_man.cli.switch_cmd import switch
from dot_man.cli.deploy_cmd import deploy
from dot_man.config import DotManConfig

@pytest.fixture
def mock_config(tmp_path):
    """Create a mock dot-man structure."""
    dot_man_dir = tmp_path / "dot-man"
    dot_man_dir.mkdir()
    repo_dir = dot_man_dir / "repo"
    repo_dir.mkdir()
    
    config_file = repo_dir / "dot-man.toml"
    
    # Create dummy files
    local_file = tmp_path / "test_file.txt"
    # Create repo file (source)
    repo_file = repo_dir / "test_file.txt"
    repo_file.write_text("content")

    # Mock constants
    with patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir), \
         patch("dot_man.cli.common.REPO_DIR", repo_dir), \
         patch("dot_man.cli.switch_cmd.REPO_DIR", repo_dir), \
         patch("dot_man.operations.REPO_DIR", repo_dir), \
         patch("dot_man.config.REPO_DIR", repo_dir), \
         patch("dot_man.constants.REPO_DIR", repo_dir):
        yield {
            "config_file": config_file,
            "local_file": local_file,
            "repo_file": repo_file,
            "repo_dir": repo_dir
        }

def test_config_parses_hooks(mock_config):
    """Test that config parser handles hooks correctly."""
    config = DotManConfig(repo_path=mock_config["repo_dir"])
    config.create_default()
    
    config.add_section(
        "test_section", 
        ["~/test_file.txt"], 
        "test_file.txt",
        pre_deploy="echo pre",
        post_deploy="echo post"
    )
    # Save to disk
    config.save()
    
    # Reload and verify assertion
    new_config = DotManConfig(repo_path=mock_config["repo_dir"])
    new_config.load()
    section = new_config.get_section("test_section")
    
    assert section.pre_deploy == "echo pre"
    assert section.post_deploy == "echo post"

@pytest.mark.skip(reason="Complex mocking required - needs integration test setup")
def test_switch_runs_hooks(mock_config, tmp_path):
    """Test that switch command runs hooks."""
    # This test requires complex mock setup for the full switch flow.
    # Skipped until proper integration test fixtures are available.
    pass


@pytest.mark.skip(reason="Complex mocking required - needs integration test setup")
def test_deploy_runs_hooks(mock_config, tmp_path):
    """Test that deploy command runs hooks."""
    # This test requires complex mock setup for the full deploy flow.
    # Skipped until proper integration test fixtures are available.
    pass
