"""Tests for cli/remote_cmd.py — remote, sync, and setup commands."""

from unittest.mock import MagicMock, patch

from dot_man.cli.interface import cli

# ==============================================================================
# remote set
# ==============================================================================


class TestRemoteSet:
    """Tests for `dot-man remote set <url>`."""

    def test_sets_remote_and_saves_global_config(self, integration_runner):
        """Setting a remote should update git remote and global config."""
        result = integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        assert result.exit_code == 0
        assert "https://github.com/user/dotfiles.git" in result.output
        # Verify git remote was actually set
        from dot_man.core import GitManager

        git = GitManager()
        assert git.get_remote_url() == "https://github.com/user/dotfiles.git"
        # Verify global config was updated
        from dot_man.config import GlobalConfig

        gc = GlobalConfig()
        gc.load()
        assert gc.remote_url == "https://github.com/user/dotfiles.git"

    def test_overwrites_existing_remote(self, integration_runner):
        """Calling remote set again should overwrite the existing remote."""
        integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/old.git"]
        )
        result = integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/new.git"]
        )
        assert result.exit_code == 0
        assert "new.git" in result.output
        from dot_man.core import GitManager

        assert GitManager().get_remote_url() == "https://github.com/user/new.git"

    def test_ssh_remote_url(self, integration_runner):
        """SSH-style remote URLs should work."""
        result = integration_runner.invoke(
            cli, ["remote", "set", "git@github.com:user/dotfiles.git"]
        )
        assert result.exit_code == 0
        assert "git@github.com:user/dotfiles.git" in result.output
        from dot_man.core import GitManager

        assert GitManager().get_remote_url() == "git@github.com:user/dotfiles.git"

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_dot_man_error_handling(self, mock_git_manager, integration_runner):
        """DotManError from GitManager should be caught and printed."""
        from dot_man.exceptions import GitOperationError

        mock_instance = MagicMock()
        mock_instance.set_remote.side_effect = GitOperationError("Permission denied")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        assert result.exit_code != 0
        assert "Permission denied" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_generic_exception_handling(self, mock_git_manager, integration_runner):
        """Any unexpected exception should be caught with a friendly message."""
        mock_instance = MagicMock()
        mock_instance.set_remote.side_effect = RuntimeError("unexpected error")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        assert result.exit_code != 0
        assert "unexpected error" in result.output


# ==============================================================================
# remote get
# ==============================================================================


class TestRemoteGet:
    """Tests for `dot-man remote get`."""

    def test_shows_remote_url_when_configured(self, integration_runner):
        """When a remote is set, get should display its URL."""
        integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        result = integration_runner.invoke(cli, ["remote", "get"])
        assert result.exit_code == 0
        assert "https://github.com/user/dotfiles.git" in result.output

    def test_no_remote_configured(self, integration_runner):
        """When no remote is set, get should show a dim 'No remote' message."""
        result = integration_runner.invoke(cli, ["remote", "get"])
        assert result.exit_code == 0
        assert "No remote configured" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_dot_man_error_handling(self, mock_git_manager, integration_runner):
        """DotManError should be caught and printed."""
        from dot_man.exceptions import GitOperationError

        mock_instance = MagicMock()
        mock_instance.get_remote_url.side_effect = GitOperationError("git error")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "get"])
        assert result.exit_code != 0
        assert "git error" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_generic_exception_handling(self, mock_git_manager, integration_runner):
        """Generic exception should produce a friendly error."""
        mock_instance = MagicMock()
        mock_instance.get_remote_url.side_effect = RuntimeError("boom")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "get"])
        assert result.exit_code != 0
        assert "boom" in result.output


# ==============================================================================
# remote sync-branch
# ==============================================================================


class TestSyncBranch:
    """Tests for `dot-man remote sync-branch`."""

    def test_requires_remote_first(self, integration_runner):
        """When no remote is configured, sync-branch should error."""
        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "No remote configured" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_branches_already_match(self, mock_git_manager, integration_runner):
        """When local and remote branch already match, show success."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.return_value = "HEAD branch: main"
        mock_instance.current_branch.return_value = "main"
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code == 0
        assert "already match" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    @patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True)
    def test_renames_branch_on_user_confirmation(
        self, mock_confirm, mock_git_manager, integration_runner
    ):
        """When branches differ and user confirms, rename the branch."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.return_value = "HEAD branch: main"
        mock_instance.current_branch.return_value = "master"
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code == 0
        mock_instance.repo.git.branch.assert_called_once_with("-m", "master", "main")
        assert "Renamed" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    @patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False)
    def test_user_declines_rename(
        self, mock_confirm, mock_git_manager, integration_runner
    ):
        """When branches differ and user declines, show info message."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.return_value = "HEAD branch: main"
        mock_instance.current_branch.return_value = "master"
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code == 0
        assert "Keeping current branch name" in result.output
        mock_instance.repo.git.branch.assert_not_called()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_could_not_determine_remote_default(
        self, mock_git_manager, integration_runner
    ):
        """If remote show does not contain HEAD branch, show error."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.return_value = "No HEAD branch info"
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "Could not detect" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_remote_show_raises_exception(self, mock_git_manager, integration_runner):
        """If git remote show fails entirely, show error."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.side_effect = Exception("network error")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "network error" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    @patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True)
    def test_rename_failure(self, mock_confirm, mock_git_manager, integration_runner):
        """If git branch -m fails, show error."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.repo.git.remote.return_value = "HEAD branch: main"
        mock_instance.current_branch.return_value = "master"
        mock_instance.repo.git.branch.side_effect = Exception("rename failed")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "rename failed" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_dot_man_error_handling(self, mock_git_manager, integration_runner):
        """DotManError during sync-branch should be caught."""
        from dot_man.exceptions import GitOperationError

        mock_instance = MagicMock()
        mock_instance.has_remote.side_effect = GitOperationError("remote error")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "remote error" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_generic_exception_handling(self, mock_git_manager, integration_runner):
        """Generic exception should produce a friendly error."""
        mock_instance = MagicMock()
        mock_instance.has_remote.side_effect = RuntimeError("unexpected")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["remote", "sync-branch"])
        assert result.exit_code != 0
        assert "Sync branch failed" in result.output or "unexpected" in result.output


# ==============================================================================
# sync
# ==============================================================================


class TestSync:
    """Tests for `dot-man sync`."""

    def test_no_remote_configured(self, integration_runner):
        """Sync without a remote should show error."""
        result = integration_runner.invoke(cli, ["sync"])
        assert result.exit_code != 0
        assert "No remote configured" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_full_sync_success(self, mock_git_manager, integration_runner):
        """Full sync should fetch, pull, audit, and push."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.current_branch.return_value = "main"
        mock_instance.pull.return_value = "Already up to date."
        mock_instance.push.return_value = "Pushed successfully."
        mock_git_manager.return_value = mock_instance

        with patch("dot_man.operations.get_operations") as mock_get_ops:
            mock_ops = MagicMock()
            mock_ops.pre_push_audit.return_value = True
            mock_get_ops.return_value = mock_ops

            result = integration_runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "Sync complete" in result.output
        mock_instance.fetch.assert_called_once()
        mock_instance.pull.assert_called_once_with(rebase=True)
        mock_instance.push.assert_called_once()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_push_only(self, mock_git_manager, integration_runner):
        """With --push-only, skip pull but still push."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.current_branch.return_value = "main"
        mock_instance.push.return_value = "Pushed successfully."
        mock_git_manager.return_value = mock_instance

        with patch("dot_man.operations.get_operations") as mock_get_ops:
            mock_ops = MagicMock()
            mock_ops.pre_push_audit.return_value = True
            mock_get_ops.return_value = mock_ops

            result = integration_runner.invoke(cli, ["sync", "--push-only"])

        assert result.exit_code == 0
        assert "Sync complete" in result.output
        mock_instance.fetch.assert_not_called()
        mock_instance.pull.assert_not_called()
        mock_instance.push.assert_called_once()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_pull_only(self, mock_git_manager, integration_runner):
        """With --pull-only, skip push but still fetch and pull."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.current_branch.return_value = "main"
        mock_instance.pull.return_value = "Already up to date."
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["sync", "--pull-only"])

        assert result.exit_code == 0
        mock_instance.fetch.assert_called_once()
        mock_instance.pull.assert_called_once_with(rebase=True)
        mock_instance.push.assert_not_called()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_pre_push_audit_fails_aborts_push(
        self, mock_git_manager, integration_runner
    ):
        """If pre_push_audit returns False, push should be skipped."""
        mock_instance = MagicMock()
        mock_instance.has_remote.return_value = True
        mock_instance.current_branch.return_value = "main"
        mock_instance.pull.return_value = "Already up to date."
        mock_git_manager.return_value = mock_instance

        with patch("dot_man.operations.get_operations") as mock_get_ops:
            mock_ops = MagicMock()
            mock_ops.pre_push_audit.return_value = False
            mock_get_ops.return_value = mock_ops

            result = integration_runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "aborted" in result.output.lower()
        mock_instance.push.assert_not_called()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_dot_man_error_handling(self, mock_git_manager, integration_runner):
        """DotManError during sync should be caught."""
        from dot_man.exceptions import GitOperationError

        mock_instance = MagicMock()
        mock_instance.has_remote.side_effect = GitOperationError("sync error")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["sync"])
        assert result.exit_code != 0
        assert "sync error" in result.output

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_generic_exception_handling(self, mock_git_manager, integration_runner):
        """Generic exception should produce a friendly error."""
        mock_instance = MagicMock()
        mock_instance.has_remote.side_effect = RuntimeError("unexpected")
        mock_git_manager.return_value = mock_instance

        result = integration_runner.invoke(cli, ["sync"])
        assert result.exit_code != 0
        assert "unexpected" in result.output


# ==============================================================================
# setup
# ==============================================================================


class TestSetup:
    """Tests for `dot-man setup`."""

    def test_already_configured_user_declines_replace(self, integration_runner):
        """If remote is already set and user declines replace, exit early."""
        integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        with patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Remote already configured" in result.output
        # Remote should be unchanged
        from dot_man.core import GitManager

        assert GitManager().get_remote_url() == "https://github.com/user/dotfiles.git"

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_available_create_repo_success(
        self, mock_run, mock_which, integration_runner
    ):
        """When gh is available and user creates a repo, setup should succeed."""
        # gh create returns success
        create_result = MagicMock()
        create_result.returncode = 0
        create_result.stderr = ""

        # gh view (not called on success path)
        mock_run.return_value = create_result

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch("dot_man.cli.remote_cmd.ui.ask", return_value="dotfiles"),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Created and connected" in result.output

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_repo_already_exists_user_connects(
        self, mock_run, mock_which, integration_runner
    ):
        """When repo already exists and user connects, setup should set remote."""
        # First call (gh create) -> exists error
        create_result = MagicMock()
        create_result.returncode = 1
        create_result.stderr = "Repository already exists on github.com"
        create_result.stdout = ""

        # Second call (gh view) -> succeed
        view_result = MagicMock()
        view_result.returncode = 0
        view_result.stdout = "https://github.com/user/dotfiles.git\n"
        view_result.stderr = ""

        mock_run.side_effect = [create_result, view_result]

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch("dot_man.cli.remote_cmd.ui.ask", side_effect=["dotfiles", "skip"]),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Connected to existing repository" in result.output
        from dot_man.core import GitManager

        assert GitManager().get_remote_url() == "https://github.com/user/dotfiles.git"

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_gh_repo_exists_user_force_pushes(
        self, mock_git_mgr, mock_run, mock_which, integration_runner
    ):
        """When repo exists and user chooses push, force push to remote."""
        mock_inst = MagicMock()
        mock_inst.has_remote.return_value = True
        mock_inst.get_remote_url.return_value = "https://github.com/user/dotfiles.git"
        mock_inst.current_branch.return_value = "main"
        mock_git_mgr.return_value = mock_inst

        create_result = MagicMock()
        create_result.returncode = 1
        create_result.stderr = "Repository already exists on github.com"
        create_result.stdout = ""

        view_result = MagicMock()
        view_result.returncode = 0
        view_result.stdout = "https://github.com/user/dotfiles.git\n"
        view_result.stderr = ""

        mock_run.side_effect = [create_result, view_result]

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                side_effect=["dotfiles", "push (overwrite remote)"],
            ),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Force pushed" in result.output
        mock_inst.repo.git.push.assert_called_once_with(
            "--force", "-u", "origin", "main"
        )

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_repo_exists_user_pulls(self, mock_run, mock_which, integration_runner):
        """When repo exists and user chooses pull, fetch and pull."""
        integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )

        create_result = MagicMock()
        create_result.returncode = 1
        create_result.stderr = "Repository already exists on github.com"
        create_result.stdout = ""

        view_result = MagicMock()
        view_result.returncode = 0
        view_result.stdout = "https://github.com/user/dotfiles.git\n"
        view_result.stderr = ""

        mock_run.side_effect = [create_result, view_result]

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                side_effect=["dotfiles", "pull (fetch remote content)"],
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = True
            mock_instance.get_remote_url.return_value = (
                "https://github.com/user/dotfiles.git"
            )
            mock_instance.repo.git.push.return_value = ""
            mock_instance.current_branch.return_value = "main"
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Pulled from remote" in result.output

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_auth_error(self, mock_run, mock_which, integration_runner):
        """When gh returns auth error, show login prompt."""
        create_result = MagicMock()
        create_result.returncode = 1
        create_result.stderr = "not logged in, use gh auth login"
        create_result.stdout = ""

        mock_run.return_value = create_result

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch("dot_man.cli.remote_cmd.ui.ask", return_value="dotfiles"),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "authentication required" in result.output.lower()

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_generic_failure_falls_back_to_manual(
        self, mock_run, mock_which, integration_runner
    ):
        """When gh fails with unknown error, fall back to manual setup."""
        create_result = MagicMock()
        create_result.returncode = 1
        create_result.stderr = "some unknown error"
        create_result.stdout = ""

        mock_run.return_value = create_result

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch("dot_man.cli.remote_cmd.ui.ask", side_effect=["dotfiles", "skip"]),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Manual Setup" in result.output or "Falling back" in result.output

    @patch("shutil.which", return_value=None)
    def test_no_gh_manual_setup_skip(self, mock_which, integration_runner):
        """When gh is not installed and user skips, show hint."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False),
            patch("dot_man.cli.remote_cmd.ui.ask", return_value="skip"),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "GitHub CLI not found" in result.output
        assert "remote set" in result.output

    @patch("shutil.which", return_value=None)
    def test_no_gh_manual_setup_success(self, mock_which, integration_runner):
        """Manual setup with a valid URL should set the remote."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                return_value="https://github.com/user/dotfiles.git",
            ),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Remote set to" in result.output
        from dot_man.core import GitManager

        assert GitManager().get_remote_url() == "https://github.com/user/dotfiles.git"

    @patch("shutil.which", return_value=None)
    def test_manual_setup_with_push(self, mock_which, integration_runner):
        """Manual setup followed by push should work."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                return_value="https://github.com/user/dotfiles.git",
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.current_branch.return_value = "main"
            mock_instance.push.return_value = "Pushed successfully."
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Pushed to remote" in result.output

    @patch("shutil.which", return_value=None)
    def test_manual_setup_push_rejected_force_push(
        self, mock_which, integration_runner
    ):
        """When push is rejected, user can choose force push."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", side_effect=[True, True]),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                side_effect=[
                    "https://github.com/user/dotfiles.git",
                    "force-push (overwrite remote)",
                ],
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.current_branch.return_value = "main"
            mock_instance.push.side_effect = Exception("rejected: non-fast-forward")
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Force pushed" in result.output
        mock_instance.repo.git.push.assert_called_once_with(
            "--force", "-u", "origin", "main"
        )

    @patch("shutil.which", return_value=None)
    def test_manual_setup_push_rejected_pull_first(
        self, mock_which, integration_runner
    ):
        """When push is rejected, user can choose pull first."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", side_effect=[True, True]),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                side_effect=[
                    "https://github.com/user/dotfiles.git",
                    "pull (fetch remote first)",
                ],
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.current_branch.return_value = "main"
            mock_instance.push.side_effect = [
                Exception("rejected: non-fast-forward"),
                "Pushed successfully.",
            ]
            mock_instance.pull.return_value = "Pulled successfully."
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        mock_instance.fetch.assert_called_once()
        mock_instance.pull.assert_called_once()

    @patch("shutil.which", return_value=None)
    def test_manual_setup_push_error_not_rejected(self, mock_which, integration_runner):
        """When push fails with a non-rejection error, show the error."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                return_value="https://github.com/user/dotfiles.git",
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.current_branch.return_value = "main"
            mock_instance.push.side_effect = Exception("connection refused")
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code != 0
        assert "connection refused" in result.output

    @patch("shutil.which", return_value=None)
    def test_dot_man_error_in_manual_setup(self, mock_which, integration_runner):
        """DotManError during manual setup should be caught."""
        from dot_man.exceptions import GitOperationError

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                return_value="https://github.com/user/dotfiles.git",
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.set_remote.side_effect = GitOperationError("bad remote")
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code != 0
        assert "bad remote" in result.output

    @patch("shutil.which", return_value=None)
    def test_generic_exception_in_manual_setup(self, mock_which, integration_runner):
        """Generic exception during manual setup should produce friendly error."""
        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=False),
            patch(
                "dot_man.cli.remote_cmd.ui.ask",
                return_value="https://github.com/user/dotfiles.git",
            ),
            patch("dot_man.cli.remote_cmd.GitManager") as mock_git,
        ):
            mock_instance = MagicMock()
            mock_instance.has_remote.return_value = False
            mock_instance.set_remote.side_effect = RuntimeError("unexpected")
            mock_git.return_value = mock_instance

            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code != 0
        assert "unexpected" in result.output

    @patch("shutil.which", return_value="/usr/bin/gh")
    @patch("subprocess.run")
    def test_gh_raises_exception_falls_back(
        self, mock_run, mock_which, integration_runner
    ):
        """When gh itself raises (not just nonzero exit), fall back gracefully."""
        mock_run.side_effect = Exception("gh crashed")

        with (
            patch("dot_man.cli.remote_cmd.ui.confirm", return_value=True),
            patch("dot_man.cli.remote_cmd.ui.ask", side_effect=["dotfiles", "skip"]),
        ):
            result = integration_runner.invoke(cli, ["setup"])

        assert result.exit_code == 0
        assert "Manual Setup" in result.output or "Falling back" in result.output


# ==============================================================================
# Help
# ==============================================================================


class TestRemoteHelp:
    """Tests for remote command help output."""

    def test_remote_help(self, integration_runner):
        """`dot-man remote --help` should list subcommands."""
        result = integration_runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output
        assert "get" in result.output
        assert "sync-branch" in result.output

    def test_sync_help(self, integration_runner):
        """`dot-man sync --help` should show sync options."""
        result = integration_runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "push-only" in result.output
        assert "pull-only" in result.output

    def test_setup_help(self, integration_runner):
        """`dot-man setup --help` should show setup description."""
        result = integration_runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "Set up remote" in result.output or "setup" in result.output.lower()


# ==============================================================================
# remote set — unit tests with mocked GitManager
# ==============================================================================


class TestRemoteSetUnit:
    """Focused unit tests for `remote set` with error simulation."""

    @patch("dot_man.cli.remote_cmd.GitManager")
    @patch("dot_man.cli.remote_cmd.GlobalConfig")
    def test_persists_remote_url_in_global_config(
        self, mock_gc_cls, mock_git_cls, integration_runner
    ):
        """After GitManager.set_remote, remote URL must be saved in GlobalConfig."""
        mock_gc_instance = MagicMock()
        mock_gc_cls.return_value = mock_gc_instance

        integration_runner.invoke(
            cli, ["remote", "set", "https://example.com/repo.git"]
        )

        assert mock_gc_instance.remote_url == "https://example.com/repo.git"
        mock_gc_instance.save.assert_called_once()

    @patch("dot_man.cli.remote_cmd.GitManager")
    def test_updates_existing_origin(self, mock_git_cls, integration_runner):
        """set_remote should be called on the GitManager."""
        mock_instance = MagicMock()
        mock_git_cls.return_value = mock_instance

        integration_runner.invoke(
            cli, ["remote", "set", "https://example.com/repo.git"]
        )

        mock_instance.set_remote.assert_called_once_with("https://example.com/repo.git")
