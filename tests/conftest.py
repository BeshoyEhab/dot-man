"""Pytest configuration and fixtures."""

import pytest


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
def integration_runner(tmp_path):
    """Setup runner with initialized repo context."""
    import os
    from contextlib import ExitStack
    from unittest.mock import patch

    from click.testing import CliRunner

    from dot_man.cli.interface import cli

    runner = CliRunner()

    # Setup home and repo env
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    # Patch constants everywhere they are used
    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.init_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.init_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.add_cmd.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.backups.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.switch_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        # We need to manually reset operations singleton to ensure it picks up new config
        from dot_man.operations import reset_operations
        reset_operations()

        # Force init to see if it works with force
        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        if result.exit_code != 0:
            print(f"Init failed: {result.output}")
            print(f"Exception: {result.exception}")
        assert result.exit_code == 0

        # Configure user/email for git to avoid errors
        from dot_man.core import GitManager
        git = GitManager(repo_dir)
        with git.repo.config_writer() as config:
            config.set_value("user", "name", "Tester")
            config.set_value("user", "email", "test@example.com")

        yield runner


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with initial commit."""
    from git import Repo

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")

    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial commit")

    return repo_dir


@pytest.fixture
def git_repo_with_branches(git_repo):
    """Create a git repo with multiple branches."""
    from git import Repo

    repo = Repo(git_repo)

    # Rename default branch to main
    repo.active_branch.rename("main")

    # Create additional branches
    repo.create_head("work")
    repo.create_head("personal")

    return git_repo


@pytest.fixture
def git_repo_with_tags(git_repo):
    """Create a git repo with tags."""
    from git import Repo

    repo = Repo(git_repo)
    repo.create_tag("v1.0", message="Version 1.0")
    repo.create_tag("v2.0", message="Version 2.0")

    return git_repo


@pytest.fixture
def git_repo_with_commits(git_repo):
    """Create a git repo with multiple commits."""
    from git import Repo

    repo = Repo(git_repo)

    for i in range(3):
        (git_repo / f"file_{i}.txt").write_text(f"content {i}")
        repo.index.add([f"file_{i}.txt"])
        repo.index.commit(f"Commit {i}")

    return git_repo
