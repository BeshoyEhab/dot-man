"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_home(tmp_path):
    """Create a temporary home directory."""
    home = tmp_path / "home"
    home.mkdir()
    return home


@pytest.fixture
def mock_dot_man_dir(tmp_path):
    """Create a mock dot-man directory structure."""
    dot_man = tmp_path / ".config" / "dot-man"
    repo = dot_man / "repo"
    backups = dot_man / "backups"
    
    dot_man.mkdir(parents=True)
    repo.mkdir()
    backups.mkdir()
    
    # Create minimal git repo
    (repo / ".git").mkdir()
    
    return dot_man
