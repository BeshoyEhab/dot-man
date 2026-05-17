"""Tests for the navigate command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.core import GitManager


@pytest.fixture
def navigate_integration(tmp_path):
    """Setup runner with initialized repo context for navigate tests."""
    import os
    from contextlib import ExitStack

    from dot_man.cli.interface import cli

    runner = CliRunner()

    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

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
        patch("dot_man.cli.switch_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.navigate_cmd.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch("dot_man.hooks.DOT_MAN_DIR", dot_man_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, f"Init failed: {result.output}"

        git = GitManager(repo_dir)
        with git.repo.config_writer() as config:
            config.set_value("user", "name", "Tester")
            config.set_value("user", "email", "test@example.com")

        yield runner


class TestNavigateHelp:
    """Test navigate command help."""

    def test_navigate_help(self, navigate_integration):
        """Test that navigate --help works."""
        result = navigate_integration.invoke(cli, ["navigate", "--help"])
        assert result.exit_code == 0
        assert "Navigate to a branch" in result.output


class TestNavigatePreview:
    """Test navigate preview functionality."""

    def test_navigate_preview_branch(self, navigate_integration):
        """Test navigating with --preview flag."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        git = GitManager(REPO_DIR)
        git.repo.create_head("preview-test")

        result = navigate_integration.invoke(
            cli, ["navigate", "preview-test", "--preview"]
        )
        assert result.exit_code == 0
        assert "Preview mode" in result.output


class TestNavigateBranchSwitch:
    """Test navigating between branches."""

    def test_navigate_to_existing_branch(self, navigate_integration):
        """Test navigating to an existing branch."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        git = GitManager(REPO_DIR)
        git.repo.create_head("test-branch")

        result = navigate_integration.invoke(
            cli, ["navigate", "test-branch", "--no-save"]
        )
        assert result.exit_code == 0
        assert "Switched to" in result.output

    def test_navigate_creates_new_branch(self, navigate_integration):
        """Test navigating creates a new branch if it doesn't exist."""
        result = navigate_integration.invoke(
            cli, ["navigate", "brand-new-branch", "--no-save", "--force"]
        )
        assert result.exit_code == 0
        assert "Created" in result.output or "Switched" in result.output


class TestNavigateCommit:
    """Test navigating to commits."""

    def test_navigate_preview_commit(self, navigate_integration):
        """Test navigating to a commit with preview."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        git = GitManager(REPO_DIR)
        commits = list(git.repo.iter_commits(max_count=1))
        commit_sha = commits[0].hexsha[:7] if commits else "abc1234"

        result = navigate_integration.invoke(cli, ["navigate", commit_sha, "--preview"])
        assert result.exit_code == 0


class TestNavigateFilesOnly:
    """Test --files-only option."""

    def test_navigate_files_only(self, navigate_integration):
        """Test navigating with --files-only flag."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        git = GitManager(REPO_DIR)
        git.repo.create_head("files-test")

        result = navigate_integration.invoke(
            cli, ["navigate", "files-test", "--preview", "--files-only"]
        )
        assert result.exit_code == 0


class TestHooksCommand:
    """Test the hooks management command."""

    def test_hooks_list(self, navigate_integration, tmp_path):
        """Test listing available hooks."""
        home = tmp_path / "home"
        hooks_dir = home / ".config" / "dot-man" / "hooks"
        hooks_dir.mkdir(parents=True)
        (hooks_dir / "pre_switch").write_text("#!/bin/bash\necho 'test'\n")

        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = navigate_integration.invoke(cli, ["hooks", "list"])
            assert result.exit_code == 0
            assert "Available Hooks" in result.output

    def test_hooks_create(self, navigate_integration, tmp_path):
        """Test creating a hook."""
        home = tmp_path / "home"
        hooks_dir = home / ".config" / "dot-man" / "hooks"
        hooks_dir.mkdir(parents=True)

        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = navigate_integration.invoke(
                cli, ["hooks", "create", "pre", "switch"]
            )
            assert result.exit_code == 0
            assert "Created hook" in result.output

    def test_hooks_delete(self, navigate_integration, tmp_path):
        """Test deleting a hook."""
        home = tmp_path / "home"
        hooks_dir = home / ".config" / "dot-man" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook_file = hooks_dir / "pre_checkout"
        hook_file.write_text("#!/bin/bash\necho 'test'\n")

        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = navigate_integration.invoke(
                cli, ["hooks", "delete", "pre", "checkout"]
            )
            assert result.exit_code == 0
            assert "Deleted hook" in result.output

    def test_hooks_delete_nonexistent(self, navigate_integration, tmp_path):
        """Test deleting a nonexistent hook."""
        home = tmp_path / "home"
        hooks_dir = home / ".config" / "dot-man" / "hooks"
        hooks_dir.mkdir(parents=True)

        with patch("dot_man.hooks.HOOKS_DIR", hooks_dir):
            result = navigate_integration.invoke(
                cli, ["hooks", "delete", "pre", "nonexistent"]
            )
            assert result.exit_code == 0
            assert "not found" in result.output.lower()
