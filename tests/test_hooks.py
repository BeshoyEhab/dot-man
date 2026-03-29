
import pytest
from unittest.mock import patch
from dot_man.cli.interface import cli
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


@pytest.mark.skip(reason="Flaky due to GitPython state caching in test environment")
def test_switch_runs_hooks(integration_runner):
    """Test that switch command runs hooks."""
    from pathlib import Path
    home = Path.home()
    (home / "testfile.txt").write_text("content")
    
    # Add with hooks
    result = integration_runner.invoke(cli, [
        "add", str(home / "testfile.txt"), 
        "--section", "hooks_test",
        "--pre-deploy", "echo PRE-HOOK-RUN",
        "--post-deploy", "echo POST-HOOK-RUN"
    ], input="y\n")
    assert result.exit_code == 0
    
    # Create a dev branch and switch to it using git directly
    from dot_man.core import GitManager
    from dot_man.constants import REPO_DIR
    git = GitManager(REPO_DIR)
    git.repo.create_head("dev")
    git.repo.git.checkout("dev")
    
    # Modify file to ensure switch has something to deploy/overwrite
    (home / "testfile.txt").write_text("modified content")
    
    # Reset operations to clean state
    from dot_man.operations import reset_operations
    reset_operations()
    
    branches = git.list_branches()
    default_branch = "main" if "main" in branches else "master"
    
    # Switch back to default branch should trigger hooks
    result = integration_runner.invoke(cli, ["switch", default_branch])
    assert result.exit_code == 0
    assert "PRE-HOOK-RUN" in result.output
    assert "POST-HOOK-RUN" in result.output

def test_deploy_runs_hooks(integration_runner):
    """Test that deploy command runs hooks."""
    from pathlib import Path
    from dot_man.operations import reset_operations
    from dot_man.core import GitManager
    from dot_man.constants import REPO_DIR
    
    home = Path.home()
    local_file = home / "deploy_test.txt"
    local_file.write_text("v1")
    
    # Add with hooks
    result = integration_runner.invoke(cli, [
        "add", str(local_file), 
        "--section", "deploy_hooks",
        "--post-deploy", "echo DEPLOY-HOOK-RUN"
    ], input="y\n")
    assert result.exit_code == 0
    
    # Determine default branch
    git = GitManager(REPO_DIR)
    branches = git.list_branches()
    default_branch = "main" if "main" in branches else "master"
    
    # Switch to default branch to commit
    res = integration_runner.invoke(cli, ["switch", default_branch])
    if res.exit_code != 0:
        print(f"SWITCH TO {default_branch} FAILED: {res.output}")
    assert res.exit_code == 0
    
    # Modify local file to force deploy to have something to do
    local_file.write_text("modified locally")
    result = integration_runner.invoke(cli, ["deploy", default_branch, "--force"])
    
    if result.exit_code != 0:
        print(f"DEPLOY FAILED: {result.output}")
        print(f"EXCEPTION: {result.exception}")
        
    assert result.exit_code == 0
    assert "DEPLOY-HOOK-RUN" in result.output
    assert local_file.read_text() == "v1"
