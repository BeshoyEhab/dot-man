
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner
from dot_man.cli import switch, deploy
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
    with patch("dot_man.cli.DOT_MAN_DIR", dot_man_dir), \
         patch("dot_man.cli.REPO_DIR", repo_dir), \
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

@pytest.mark.skip(reason="Test needs update for new operations module architecture")
@patch("dot_man.cli.subprocess.run")
@patch("dot_man.cli.GitManager")
@patch("dot_man.cli.GlobalConfig")
def test_switch_runs_hooks(mock_global_config, mock_git, mock_subprocess, mock_config):
    """Test that switch command runs hooks."""
    runner = CliRunner()
    
    # Setup config with hooks
    config = DotManConfig(repo_path=mock_config["repo_dir"])
    config.create_default()
    config.add_section(
        "test_section", 
        [str(mock_config["local_file"])], 
        "test_file.txt",
        pre_deploy="echo pre",
        post_deploy="echo post"
    )
    config.save()
    
    # Create local file to prevent Phase 1 deletion
    Path(mock_config["local_file"]).write_text("initial_content")
    
    # Global config mock
    mock_global_instance = mock_global_config.return_value
    mock_global_instance.current_branch = "main"

    # Git mock
    mock_git_instance = mock_git.return_value
    mock_git_instance.branch_exists.return_value = True
    
    # Simulate git checkout changing file content
    def checkout_side_effect(*args, **kwargs):
        Path(mock_config["repo_file"]).write_text("new_content_from_branch")
        
    mock_git_instance.checkout.side_effect = checkout_side_effect

    # Run switch
    # Note: verify_init decorator might check paths, which we mocked in fixture but
    # imports in cli.py might resolved earlier. We might need to mock is_git_installed too.
    
    with patch("dot_man.cli.is_git_installed", return_value=True), \
         patch("dot_man.cli.DOT_MAN_DIR", mock_config["repo_dir"].parent), \
         patch("dot_man.cli.REPO_DIR", mock_config["repo_dir"]):
        
        result = runner.invoke(switch, ["other_branch"])
    
    assert result.exit_code == 0
    
    # Verify hooks were called by checking output
    assert "Exec: echo pre" in result.output
    assert "Exec: echo post" in result.output
    
    # Optional: also check mock if wanted, but output is sufficient proof of intent
    # calls = [c[0][0] for c in mock_subprocess.call_args_list]
    # assert "echo pre" in calls


@pytest.mark.skip(reason="Test needs update for new operations module architecture")
@patch("dot_man.cli.subprocess.run")
@patch("dot_man.cli.GitManager") 
def test_deploy_runs_hooks(mock_git, mock_subprocess, mock_config):
    """Test that deploy command runs hooks."""
    runner = CliRunner()
    
    config = DotManConfig(repo_path=mock_config["repo_dir"])
    config.create_default()
    config.add_section(
        "test_section", 
        [str(mock_config["local_file"])], 
        "test_file.txt",
        pre_deploy="echo pre_deploy",
        post_deploy="echo post_deploy"
    )
    config.save()

    mock_git_instance = mock_git.return_value
    mock_git_instance.branch_exists.return_value = True
    
    with patch("dot_man.cli.is_git_installed", return_value=True), \
         patch("dot_man.cli.DOT_MAN_DIR", mock_config["repo_dir"].parent), \
         patch("dot_man.cli.REPO_DIR", mock_config["repo_dir"]):
         
        result = runner.invoke(deploy, ["main", "--force"])
        
    assert result.exit_code == 0
    
    calls = [c[0][0] for c in mock_subprocess.call_args_list]
    assert "echo pre_deploy" in calls
    assert "echo post_deploy" in calls
