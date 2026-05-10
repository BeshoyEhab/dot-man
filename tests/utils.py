"""Shared test utilities and fixtures for dot-man tests.

This module provides reusable fixtures and utilities that can be shared
across all test files to reduce duplication and improve test coverage.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import ExitStack
from click.testing import CliRunner
from git import Repo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


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


@pytest.fixture
def git_repo(tmp_path):
    """Create a git repository with initial commit.
    
    Returns:
        Path to the repo directory
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    
    # Configure git
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")
    
    # Create initial commit
    (repo_dir / "test.txt").write_text("test content")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")
    
    return repo_dir


@pytest.fixture
def git_repo_with_branches(tmp_path):
    """Create a git repo with multiple branches.
    
    Returns:
        Path to the repo directory
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")
    
    # Initial commit
    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial")
    
    # Create branches
    repo.create_head("main")
    repo.create_head("work")
    repo.create_head("feature")
    
    return repo_dir


@pytest.fixture
def git_repo_with_tags(tmp_path):
    """Create a git repo with tags.
    
    Returns:
        Path to the repo directory
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")
    
    # Initial commit
    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial")
    
    # Create tags
    repo.create_tag("v1.0")
    repo.create_tag("v2.0")
    repo.create_tag("beta")
    
    return repo_dir


@pytest.fixture
def git_repo_with_commits(tmp_path):
    """Create a git repo with multiple commits.
    
    Returns:
        Path to the repo directory
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")
    
    # Create multiple commits
    for i in range(5):
        (repo_dir / f"file{i}.txt").write_text(f"content {i}")
        repo.index.add([f"file{i}.txt"])
        repo.index.commit(f"Commit {i}")
    
    return repo_dir


@pytest.fixture
def dot_man_dirs(tmp_path):
    """Create complete dot-man directory structure.
    
    Returns:
        dict with paths: home, dot_man_dir, repo_dir, backups_dir, global_toml
    """
    home = tmp_path / "home"
    home.mkdir()
    
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"
    
    dot_man_dir.mkdir(parents=True)
    repo_dir.mkdir()
    backups_dir.mkdir()
    
    # Create minimal git repo
    Repo.init(repo_dir)
    
    # Create global config
    global_toml.write_text("""
[dot-man]
current_branch = "main"
version = "0.8.0"

[defaults]
secrets_filter = true
update_strategy = "replace"

[remote]
url = ""

[switch]
default_behavior = "save"
""")
    
    return {
        "home": home,
        "dot_man_dir": dot_man_dir,
        "repo_dir": repo_dir,
        "backups_dir": backups_dir,
        "global_toml": global_toml,
    }


@pytest.fixture
def mock_git_manager():
    """Create a mock GitManager with common methods.
    
    Returns:
        MagicMock configured as GitManager
    """
    with patch('dot_man.core.GitManager') as mock:
        instance = MagicMock()
        instance.current_branch.return_value = "main"
        instance.list_branches.return_value = ["main", "work", "feature"]
        instance.list_tags.return_value = ["v1", "v2", "beta"]
        instance.branch_exists.return_value = True
        instance.is_dirty.return_value = False
        instance.get_commits.return_value = [
            {"sha": f"{'a'*(7+i)}", "message": f"Commit {i}", "author": "Test", "date": "2026-05-10T10:00:00"}
            for i in range(5)
        ]
        instance.get_tag_commit.return_value = "abc1234"
        
        mock.return_value = instance
        yield instance


@pytest.fixture
def patch_all_dirs(dot_man_dirs):
    """Patch all dot-man directories globally.
    
    Use this fixture to set up the environment for integration tests.
    """
    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dirs["dot_man_dir"]),
        patch("dot_man.constants.REPO_DIR", dot_man_dirs["repo_dir"]),
        patch("dot_man.constants.BACKUPS_DIR", dot_man_dirs["backups_dir"]),
        patch("dot_man.constants.GLOBAL_TOML", dot_man_dirs["global_toml"]),
        patch("dot_man.core.REPO_DIR", dot_man_dirs["repo_dir"]),
        patch("dot_man.config.REPO_DIR", dot_man_dirs["repo_dir"]),
        patch("dot_man.config.GLOBAL_TOML", dot_man_dirs["global_toml"]),
        patch("dot_man.global_config.GLOBAL_TOML", dot_man_dirs["global_toml"]),
        patch("dot_man.dotman_config.REPO_DIR", dot_man_dirs["repo_dir"]),
        patch("dot_man.operations.REPO_DIR", dot_man_dirs["repo_dir"]),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dirs["dot_man_dir"]),
        patch.dict(os.environ, {"HOME": str(dot_man_dirs["home"])}),
    ]
    
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield


# =============================================================================
# Parametrized Test Data
# =============================================================================


BRANCH_NAMES = ["main", "work", "feature", "develop", "release/v1.0"]
TAG_NAMES = ["v1.0", "v2.0", "latest", "beta", "stable"]
COMMIT_SHAS = ["abc1234", "def5678", "abc123456789", "a" * 40]


# =============================================================================
# Utility Functions
# =============================================================================


def create_file(path: Path, content: str = "test") -> None:
    """Create a file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_git_commit(repo_dir: Path, filename: str, content: str, message: str) -> None:
    """Create a git commit with a file."""
    repo = Repo(repo_dir)
    file_path = repo_dir / filename
    file_path.write_text(content)
    repo.index.add([filename])
    repo.index.commit(message)


def assert_cli_help(runner, command: str, expected_keywords: list[str]) -> None:
    """Helper to test CLI command help output."""
    result = runner.invoke(command, ["--help"])
    assert result.exit_code == 0
    for keyword in expected_keywords:
        assert keyword.lower() in result.output.lower()


# =============================================================================
# Reusable Test Classes
# =============================================================================


class TestCLIHelpBase:
    """Base class for testing CLI help commands.
    
    Subclass and define:
        - command: the CLI command to test
        - expected_keywords: list of keywords expected in help
    """
    command = None
    expected_keywords = []
    
    def test_help(self, runner):
        """Test command --help shows expected keywords."""
        assert_cli_help(runner, self.command, self.expected_keywords)


class TestBranchOperationsBase:
    """Base class for testing branch operations.
    
    Subclass and define:
        - get_git_manager(): returns GitManager instance
    """
    
    def test_list_branches(self):
        """Test listing branches."""
        git = self.get_git_manager()
        branches = git.list_branches()
        assert isinstance(branches, list)
    
    def test_branch_exists(self):
        """Test checking branch existence."""
        git = self.get_git_manager()
        git.branch_exists("main")
    
    def test_current_branch(self):
        """Test getting current branch."""
        git = self.get_git_manager()
        branch = git.current_branch()
        assert isinstance(branch, str)


class TestTagOperationsBase:
    """Base class for testing tag operations."""
    
    def test_list_tags(self):
        """Test listing tags."""
        git = self.get_git_manager()
        tags = git.list_tags()
        assert isinstance(tags, list)
    
    def test_get_tag_commit(self):
        """Test getting tag commit SHA."""
        git = self.get_git_manager()
        git.get_tag_commit("v1")


# =============================================================================
# Decorators for Parametrized Tests
# =============================================================================


def parametrize_branch_names(func):
    """Decorator to parametrize tests with branch names."""
    return pytest.mark.parametrize("branch_name", BRANCH_NAMES)(func)


def parametrize_tag_names(func):
    """Decorator to parametrize tests with tag names."""
    return pytest.mark.parametrize("tag_name", TAG_NAMES)(func)


def parametrize_commit_shorts(func):
    """Decorator to parametrize tests with commit SHAs."""
    return pytest.mark.parametrize("commit_sha", COMMIT_SHAS[:3])(func)