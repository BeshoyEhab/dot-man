"""Pytest configuration and shared fixtures for dot-man tests.

Fixture contract (names are used by many test files — keep them stable):
- ``temp_home`` / ``mock_dot_man_dir``: directory scaffolding
- ``git_repo`` (+ ``_with_branches`` / ``_with_tags`` / ``_with_commits``):
  real git repositories via GitPython
- ``integration_runner``: fully initialized dot-man environment + CliRunner

All constant-patch targets live in ``_dot_man_patches`` so that wiring a
new module that binds dot-man path constants at import time is a one-line
change in one place.
"""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def _reset_ui_global_flags():
    """Reset the process-wide ui flags between tests.

    The root CLI callback calls ``ui.configure`` on every invocation, but
    tests that exercise ``ui`` directly (or a command that set a flag) must
    not leak ``--quiet``/``--yes``/``--no-color`` state into the next test.
    """
    from dot_man import ui

    ui.configure()
    yield
    ui.configure()


# =============================================================================
# Directory scaffolding
# =============================================================================


@pytest.fixture(autouse=True)
def _isolate_dot_man_env(tmp_path, monkeypatch):
    """Give every test a private, initialized-looking dot-man sandbox.

    Without this, commands guarded by ``require_init`` read the developer's
    real ``~/.config/dot-man/repo``; the suite then passes on a machine where
    dot-man is installed and fails in CI (empty ``HOME``). Redirecting every
    path per test makes the result independent of the host.

    The sandbox looks initialized (``repo/.git`` exists) because that is the
    state most tests assert against; tests that need the uninitialized path
    use ``uninitialized_runner``, which overrides these values.
    """
    from dot_man import constants, hooks
    from dot_man.operations import reset_operations

    home = tmp_path / "isolated-home"
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    (repo_dir / ".git").mkdir(parents=True)
    backups_dir.mkdir()

    monkeypatch.setattr(constants, "DOT_MAN_DIR", dot_man_dir)
    monkeypatch.setattr(constants, "REPO_DIR", repo_dir)
    monkeypatch.setattr(constants, "BACKUPS_DIR", backups_dir)
    monkeypatch.setattr(constants, "GLOBAL_TOML", dot_man_dir / "global.toml")
    monkeypatch.setattr(hooks, "HOOKS_DIR", dot_man_dir / "hooks")
    monkeypatch.setenv("HOME", str(home))

    reset_operations()
    yield
    reset_operations()


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


# =============================================================================
# Integration environment
# =============================================================================


def _dot_man_patches(dot_man_dir, repo_dir, backups_dir, global_toml, home):
    """Return every patch that redirects dot-man's global paths to a temp env.

    Consumers read paths at call time through ``constants.get_*()``, so
    patching the source attributes on ``dot_man.constants`` redirects all of
    them at once. Only modules that still bind a path at import time (e.g.
    ``dot_man.hooks.HOOKS_DIR``) need their own entry here.
    """
    return [
        # Single source of truth: every accessor reads these module globals.
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        # Derived at import time by modules that expose their own constant.
        patch("dot_man.hooks.HOOKS_DIR", dot_man_dir / "hooks"),
        # Environment
        patch.dict(os.environ, {"HOME": str(home)}),
        patch(
            "dot_man.config_detector.ConfigDetector.QUICKSHELL_BASE_PATHS",
            [str(home / ".config/quickshell")],
        ),
    ]


@pytest.fixture
def uninitialized_runner(tmp_path):
    """A CliRunner whose dot-man env is empty (no repo, no config).

    Unlike ``integration_runner`` this does NOT run ``init``, so commands
    guarded by ``require_init`` exercise their not-initialized path instead
    of depending on the developer's real ``~/.config/dot-man``.
    """
    runner = CliRunner()

    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    with ExitStack() as stack:
        for p in _dot_man_patches(
            dot_man_dir, repo_dir, backups_dir, global_toml, home
        ):
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield runner


@pytest.fixture
def integration_runner(tmp_path):
    """Setup runner with initialized repo context."""
    from dot_man.cli.interface import cli

    runner = CliRunner()

    # Setup home and repo env
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    with ExitStack() as stack:
        for p in _dot_man_patches(
            dot_man_dir, repo_dir, backups_dir, global_toml, home
        ):
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


# =============================================================================
# Git repositories
# =============================================================================


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
