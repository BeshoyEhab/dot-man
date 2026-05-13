"""Tests for cli/remote_cmd.py — remote set/get, sync-branch, sync, setup."""

import os
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def initialized_runner(tmp_path):
    """Runner with a fully-initialized dot-man repo, git user configured."""
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
        patch("dot_man.cli.init_cmd.BACKUPS_DIR", backups_dir),
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

        from dot_man.operations import reset_operations

        reset_operations()

        r = CliRunner()
        result = r.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, f"Init failed:\n{result.output}"

        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        with git.repo.config_writer() as cfg:
            cfg.set_value("user", "name", "Tester")
            cfg.set_value("user", "email", "test@example.com")

        yield r, repo_dir, dot_man_dir, global_toml


# ---------------------------------------------------------------------------
# Help / Command registration
# ---------------------------------------------------------------------------


class TestRemoteHelp:
    """Verify the remote sub-group and its sub-commands are registered."""

    def test_remote_group_help(self, runner):
        result = runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output
        assert "get" in result.output

    def test_remote_set_help(self, runner):
        result = runner.invoke(cli, ["remote", "set", "--help"])
        assert result.exit_code == 0
        assert "url" in result.output.lower()

    def test_remote_get_help(self, runner):
        result = runner.invoke(cli, ["remote", "get", "--help"])
        assert result.exit_code == 0

    def test_remote_sync_branch_help(self, runner):
        result = runner.invoke(cli, ["remote", "sync-branch", "--help"])
        assert result.exit_code == 0
        assert "branch" in result.output.lower() or "sync" in result.output.lower()

    def test_sync_help(self, runner):
        result = runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "push" in result.output.lower() or "pull" in result.output.lower()

    def test_setup_help(self, runner):
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# require_init guard
# ---------------------------------------------------------------------------


class TestRemoteRequiresInit:
    """Commands protected by @require_init should fail gracefully before init."""

    @pytest.fixture()
    def uninit_runner(self, tmp_path):
        """Runner pointing at a directory that has never been initialized."""
        fake_dir = tmp_path / "nonexistent"
        fake_toml = fake_dir / "global.toml"
        fake_repo = fake_dir / "repo"
        patches = [
            patch("dot_man.constants.DOT_MAN_DIR", fake_dir),
            patch("dot_man.constants.REPO_DIR", fake_repo),
            patch("dot_man.cli.common.DOT_MAN_DIR", fake_dir),
            patch("dot_man.cli.common.REPO_DIR", fake_repo),
            patch("dot_man.global_config.GLOBAL_TOML", fake_toml),
            patch("dot_man.core.REPO_DIR", fake_repo),
        ]
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            yield CliRunner()

    def test_remote_set_without_init(self, uninit_runner):
        result = uninit_runner.invoke(
            cli, ["remote", "set", "https://example.com/repo.git"]
        )
        assert result.exit_code != 0 or "not initialized" in result.output.lower()

    def test_remote_get_without_init(self, uninit_runner):
        result = uninit_runner.invoke(cli, ["remote", "get"])
        assert result.exit_code != 0 or "not initialized" in result.output.lower()

    def test_sync_branch_without_init(self, uninit_runner):
        result = uninit_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0 or "not initialized" in result.output.lower()

    def test_sync_without_init(self, uninit_runner):
        result = uninit_runner.invoke(cli, ["sync"])
        assert result.exit_code != 0 or "not initialized" in result.output.lower()


# ---------------------------------------------------------------------------
# remote set
# ---------------------------------------------------------------------------


class TestRemoteSet:
    """Tests for 'dot-man remote set <url>'."""

    def test_remote_set_saves_url(self, initialized_runner):
        runner, repo_dir, dot_man_dir, global_toml = initialized_runner
        url = "https://github.com/user/dotfiles.git"

        with (
            patch("dot_man.core.GitManager.set_remote") as mock_set,
            patch("dot_man.global_config.GlobalConfig.save"),
        ):
            result = runner.invoke(cli, ["remote", "set", url])

        assert result.exit_code == 0
        mock_set.assert_called_once_with(url)

    def test_remote_set_success_message(self, initialized_runner):
        runner, *_ = initialized_runner
        url = "https://github.com/user/dotfiles.git"

        with (
            patch("dot_man.core.GitManager.set_remote"),
            patch("dot_man.global_config.GlobalConfig.save"),
        ):
            result = runner.invoke(cli, ["remote", "set", url])

        assert result.exit_code == 0
        assert url in result.output

    def test_remote_set_propagates_error(self, initialized_runner):
        runner, *_ = initialized_runner

        from dot_man.exceptions import DotManError

        with patch(
            "dot_man.core.GitManager.set_remote",
            side_effect=DotManError("git error"),
        ):
            result = runner.invoke(cli, ["remote", "set", "bad-url"])

        # Should not raise unhandled; error must be reported
        assert "error" in result.output.lower() or result.exit_code != 0


# ---------------------------------------------------------------------------
# remote get
# ---------------------------------------------------------------------------


class TestRemoteGet:
    """Tests for 'dot-man remote get'."""

    def test_remote_get_shows_url_when_configured(self, initialized_runner):
        runner, *_ = initialized_runner
        url = "https://github.com/user/dotfiles.git"

        with patch("dot_man.core.GitManager.get_remote_url", return_value=url):
            result = runner.invoke(cli, ["remote", "get"])

        assert result.exit_code == 0
        assert url in result.output

    def test_remote_get_shows_message_when_not_configured(self, initialized_runner):
        runner, *_ = initialized_runner

        with patch("dot_man.core.GitManager.get_remote_url", return_value=None):
            result = runner.invoke(cli, ["remote", "get"])

        assert result.exit_code == 0
        # Should prompt user to configure a remote
        assert (
            "no remote" in result.output.lower()
            or "remote set" in result.output.lower()
        )


# ---------------------------------------------------------------------------
# remote sync-branch
# ---------------------------------------------------------------------------


class TestRemoteSyncBranch:
    """Tests for 'dot-man remote sync-branch'."""

    def test_sync_branch_no_remote_exits_early(self, initialized_runner):
        runner, *_ = initialized_runner

        with patch("dot_man.core.GitManager.has_remote", return_value=False):
            result = runner.invoke(cli, ["remote", "sync-branch"])

        # error() calls sys.exit(1), so exit_code is 1
        assert result.exit_code != 0
        assert "no remote" in result.output.lower() or "remote" in result.output.lower()

    def test_sync_branch_matching_branches_reports_ok(self, initialized_runner):
        runner, *_ = initialized_runner

        # Simulate remote HEAD == local branch
        mock_repo_git = MagicMock()
        mock_repo_git.remote.return_value = "HEAD branch: main\nother: foo"

        with (
            patch("dot_man.core.GitManager.has_remote", return_value=True),
            patch("dot_man.core.GitManager.fetch"),
            patch("dot_man.core.GitManager.current_branch", return_value="main"),
            patch(
                "dot_man.core.GitManager.repo",
                new_callable=lambda: property(
                    lambda self: MagicMock(git=mock_repo_git)
                ),
            ),
        ):
            result = runner.invoke(cli, ["remote", "sync-branch"])

        assert result.exit_code == 0
        # "already match" or similar success message
        assert "match" in result.output.lower() or "main" in result.output.lower()


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


class TestSyncCommand:
    """Tests for 'dot-man sync'."""

    def test_sync_no_remote_reports_error(self, initialized_runner):
        runner, *_ = initialized_runner

        with (
            patch("dot_man.core.GitManager.has_remote", return_value=False),
            patch("dot_man.lock.FileLock.__enter__", return_value=None),
            patch("dot_man.lock.FileLock.__exit__", return_value=False),
        ):
            result = runner.invoke(cli, ["sync"])

        assert (
            "no remote" in result.output.lower()
            or "remote" in result.output.lower()
            or result.exit_code != 0
        )

    def test_sync_push_only_flag_skips_pull(self, initialized_runner):
        """With --push-only, fetch/pull should not be called."""
        runner, *_ = initialized_runner

        with (
            patch("dot_man.core.GitManager.has_remote", return_value=True),
            patch("dot_man.core.GitManager.fetch") as mock_fetch,
            patch("dot_man.core.GitManager.pull") as mock_pull,
            patch("dot_man.core.GitManager.push", return_value="pushed"),
            patch(
                "dot_man.operations.DotManOperations.pre_push_audit", return_value=True
            ),
            patch("dot_man.core.GitManager.current_branch", return_value="main"),
            patch("dot_man.lock.FileLock.__enter__", return_value=None),
            patch("dot_man.lock.FileLock.__exit__", return_value=False),
        ):
            runner.invoke(cli, ["sync", "--push-only"])

        mock_fetch.assert_not_called()
        mock_pull.assert_not_called()

    def test_sync_pull_only_flag_skips_push(self, initialized_runner):
        """With --pull-only, push should not be called."""
        runner, *_ = initialized_runner

        with (
            patch("dot_man.core.GitManager.has_remote", return_value=True),
            patch("dot_man.core.GitManager.fetch"),
            patch("dot_man.core.GitManager.pull", return_value="Already up to date."),
            patch("dot_man.core.GitManager.push") as mock_push,
            patch("dot_man.core.GitManager.current_branch", return_value="main"),
            patch("dot_man.lock.FileLock.__enter__", return_value=None),
            patch("dot_man.lock.FileLock.__exit__", return_value=False),
        ):
            runner.invoke(cli, ["sync", "--pull-only"])

        mock_push.assert_not_called()
