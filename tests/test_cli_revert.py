"""Tests for the revert command."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from dot_man.cli.interface import cli as main_cli
from dot_man.core import GitManager
from dot_man.operations import get_operations

def test_revert_file(temp_home, mock_dot_man_dir, monkeypatch):
    """Test reverting a single file."""
    runner = CliRunner()
    
    # 1. Setup Repo and Config
    monkeypatch.setattr("pathlib.Path.home", lambda: temp_home)
    monkeypatch.setattr("dot_man.constants.DOT_MAN_DIR", mock_dot_man_dir)
    monkeypatch.setattr("dot_man.constants.REPO_DIR", mock_dot_man_dir / "repo")
    # Patch consumers of REPO_DIR
    monkeypatch.setattr("dot_man.config.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.operations.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.cli.init_cmd.REPO_DIR", mock_dot_man_dir / "repo")
    
    # Init
    result = runner.invoke(main_cli, ["init", "--no-wizard", "--force"])
    assert result.exit_code == 0
    
    # 2. Create a tracked file in repo
    repo_file = mock_dot_man_dir / "repo" / ".bashrc"
    repo_file.write_text("alias ll='ls -l'", encoding="utf-8")
    
    # 3. Create a local file with different content
    local_file = temp_home / ".bashrc"
    local_file.write_text("alias ll='ls -la'", encoding="utf-8")
    
    # 4. Add section tracking this file
    config_file = mock_dot_man_dir / "repo" / "dot-man.toml"
    config_file.write_text(f"""
    [bash]
    paths = ["{local_file}"]
    repo_path = ".bashrc"
    """, encoding="utf-8")
    
    # Reload config
    get_operations().reload_config()
    
    # 5. Run Revert
    # Using --force to skip confirmation
    result = runner.invoke(main_cli, ["revert", str(local_file), "--force"])
    
    # 6. Verify
    assert result.exit_code == 0
    assert "Reverted" in result.output
    assert local_file.read_text() == "alias ll='ls -l'"

def test_revert_untracked_file(temp_home, mock_dot_man_dir, monkeypatch):
    """Test reverting a file that is not tracked."""
    runner = CliRunner()
    
    monkeypatch.setattr("pathlib.Path.home", lambda: temp_home)
    monkeypatch.setattr("dot_man.constants.DOT_MAN_DIR", mock_dot_man_dir)
    monkeypatch.setattr("dot_man.constants.REPO_DIR", mock_dot_man_dir / "repo")
    # Patch consumers of REPO_DIR
    monkeypatch.setattr("dot_man.config.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.operations.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.cli.init_cmd.REPO_DIR", mock_dot_man_dir / "repo")
    
    # Init
    runner.invoke(main_cli, ["init", "--no-wizard", "--force"])
    
    untracked_file = temp_home / "untracked.txt"
    untracked_file.write_text("foo")
    
    result = runner.invoke(main_cli, ["revert", str(untracked_file), "--force"])
    
    assert result.exit_code == 0 # Command runs successfully but warns
    assert "not tracked" in result.output

def test_revert_interactive_abort(temp_home, mock_dot_man_dir, monkeypatch):
    """Test aborting revert in interactive mode."""
    runner = CliRunner()
    
    monkeypatch.setattr("pathlib.Path.home", lambda: temp_home)
    monkeypatch.setattr("dot_man.constants.DOT_MAN_DIR", mock_dot_man_dir)
    monkeypatch.setattr("dot_man.constants.REPO_DIR", mock_dot_man_dir / "repo")
    # Patch consumers of REPO_DIR
    monkeypatch.setattr("dot_man.config.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.operations.REPO_DIR", mock_dot_man_dir / "repo")
    monkeypatch.setattr("dot_man.cli.init_cmd.REPO_DIR", mock_dot_man_dir / "repo")
    
    runner.invoke(main_cli, ["init", "--no-wizard", "--force"])
    
    # Setup tracked file
    repo_file = mock_dot_man_dir / "repo" / ".vimrc"
    repo_file.write_text("set number")
    
    local_file = temp_home / ".vimrc"
    local_file.write_text("set nonumber")
    
    config_file = mock_dot_man_dir / "repo" / "dot-man.toml"
    config_file.write_text(f"""
    [vim]
    paths = ["{local_file}"]
    """)
    
    get_operations().reload_config()
    
    # Run without force, input 'n'
    result = runner.invoke(main_cli, ["revert", str(local_file)], input="n\n")
    
    assert result.exit_code == 0
    # Should NOT have reverted
    assert local_file.read_text() == "set nonumber"
