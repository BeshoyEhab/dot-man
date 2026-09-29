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
        patch("dot_man.cli.navigate_cmd.REPO_DIR", repo_dir),
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


def _add_tracked_file(runner, tmp_path, name=".apprc", content="v1\n"):
    """Add a file to dot-man tracking and return its path."""
    from dot_man.operations import reset_operations

    test_file = tmp_path / "home" / name
    test_file.write_text(content)
    result = runner.invoke(cli, ["add", str(test_file)])
    assert result.exit_code == 0, f"Add failed: {result.output}"
    reset_operations()
    return test_file


def _add_section_hooks(tmp_path):
    """Append pre/post deploy hooks to the single tracked section."""
    from dot_man.constants import REPO_DIR
    from dot_man.operations import reset_operations

    cfg = REPO_DIR / "dot-man.toml"
    assert cfg.exists(), f"Config missing: {list(REPO_DIR.iterdir())}"
    with cfg.open("a") as f:
        f.write('pre_deploy = "echo pre-hook"\n')
        f.write('post_deploy = "echo post-hook"\n')
    reset_operations()


class TestNavigateNoTarget:
    """Test navigate without a target."""

    def test_no_target_errors(self, navigate_integration):
        """Test that navigate with no target exits non-zero."""
        result = navigate_integration.invoke(cli, ["navigate"])
        assert result.exit_code != 0
        assert "No branch" in result.output

    def test_internal_error_handled(self, navigate_integration):
        """Test that unexpected failures exit non-zero with diagnostics."""
        with patch(
            "dot_man.operations.get_operations",
            side_effect=RuntimeError("kablam"),
        ):
            result = navigate_integration.invoke(cli, ["navigate", "whatever"])
        assert result.exit_code != 0


class TestNavigateCommitReal:
    """Test navigating to commits for real (not just preview)."""

    def _head_sha(self):
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        commits = list(GitManager(REPO_DIR).repo.iter_commits(max_count=1))
        assert commits, "seed repo has no commits"
        return commits[0].hexsha[:7]

    def test_navigate_to_commit_detached(self, navigate_integration):
        """Test navigating to a commit checks out detached HEAD."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        sha = self._head_sha()
        result = navigate_integration.invoke(cli, ["navigate", sha, "--no-save"])
        assert result.exit_code == 0
        assert "detached HEAD" in result.output
        assert GitManager(REPO_DIR).repo.head.is_detached

    def test_navigate_commit_dry_run(self, navigate_integration):
        """Test navigating to a commit with --dry-run changes nothing."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        sha = self._head_sha()
        result = navigate_integration.invoke(cli, ["navigate", sha, "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert not GitManager(REPO_DIR).repo.head.is_detached

    def test_navigate_commit_saves_first(self, navigate_integration, tmp_path):
        """Test navigating to a commit saves pending changes."""
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        sha = self._head_sha()
        result = navigate_integration.invoke(cli, ["navigate", sha])
        assert result.exit_code == 0
        assert "Saved 1 file" in result.output
        assert "detached HEAD" in result.output

    def test_navigate_commit_no_commit_message(self, navigate_integration, tmp_path):
        """Test navigating to a commit with -m none skips the commit."""
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        sha = self._head_sha()
        result = navigate_integration.invoke(cli, ["navigate", sha, "-m", "none"])
        assert result.exit_code == 0
        assert "no commit" in result.output

    def test_navigate_commit_custom_message(self, navigate_integration, tmp_path):
        """Test navigating to a commit with a custom message commits it."""
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        sha = self._head_sha()
        result = navigate_integration.invoke(
            cli, ["navigate", sha, "-m", "custom commit words"]
        )
        assert result.exit_code == 0
        assert "Commit: custom commit words" in result.output


class TestNavigateTagReal:
    """Test navigating to tags for real (covers the tag checkout fix)."""

    def _make_tag(self, name="v1.0"):
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        GitManager(REPO_DIR).repo.create_tag(name)

    def test_navigate_tag_preview(self, navigate_integration):
        """Test previewing a tag shows tag info."""
        self._make_tag()
        result = navigate_integration.invoke(cli, ["navigate", "v1.0", "--preview"])
        assert result.exit_code == 0
        assert "Preview mode" in result.output

    def test_navigate_tag_dry_run(self, navigate_integration):
        """Test dry-running a tag navigate changes nothing."""
        self._make_tag()
        result = navigate_integration.invoke(cli, ["navigate", "v1.0", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_navigate_tag_checkout(self, navigate_integration):
        """Test navigating to a tag checks out the tagged commit."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        self._make_tag()
        result = navigate_integration.invoke(cli, ["navigate", "v1.0", "--no-save"])
        assert result.exit_code == 0, f"Tag navigate failed: {result.output}"
        assert "Switched to tag 'v1.0'" in result.output
        assert GitManager(REPO_DIR).repo.head.is_detached

    def test_navigate_tag_saves_first(self, navigate_integration, tmp_path):
        """Test navigating to a tag saves pending changes."""
        self._make_tag()
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(cli, ["navigate", "v1.0"])
        assert result.exit_code == 0, f"Tag navigate failed: {result.output}"
        assert "Saved 1 file" in result.output
        assert "Switched to tag 'v1.0'" in result.output

    def test_navigate_tag_custom_message(self, navigate_integration, tmp_path):
        """Test navigating to a tag with a custom message commits it."""
        self._make_tag()
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(
            cli, ["navigate", "v1.0", "-m", "tagging along"]
        )
        assert result.exit_code == 0, f"Tag navigate failed: {result.output}"
        assert "Commit: tagging along" in result.output
        assert "Switched to tag 'v1.0'" in result.output

    def test_navigate_tag_no_commit_message(self, navigate_integration, tmp_path):
        """Test navigating to a tag with -m none skips the commit."""
        self._make_tag()
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(cli, ["navigate", "v1.0", "-m", "none"])
        assert result.exit_code == 0, f"Tag navigate failed: {result.output}"
        assert "no commit" in result.output
        assert "Switched to tag 'v1.0'" in result.output

    def test_navigate_branch_at_tag(self, navigate_integration):
        """Test branch@tag syntax switches via the base branch."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        self._make_tag()
        current = GitManager(REPO_DIR).current_branch()
        result = navigate_integration.invoke(
            cli, ["navigate", f"{current}@v1.0", "--no-save"]
        )
        assert result.exit_code == 0, f"branch@tag failed: {result.output}"
        assert "Switched to tag 'v1.0'" in result.output

    def test_navigate_missing_tag_errors(self, navigate_integration):
        """Test navigating to a missing tag exits non-zero."""
        result = navigate_integration.invoke(
            cli, ["navigate", "master@v9.9.9", "--no-save"]
        )
        assert result.exit_code != 0
        assert "not found" in result.output


class TestAlreadyOnBranchPreview:
    """Test previewing the current branch."""

    def test_preview_current_branch(self, navigate_integration):
        """Test preview on the current branch lists commits."""
        from dot_man.operations import get_operations

        current = get_operations().current_branch
        result = navigate_integration.invoke(cli, ["navigate", current, "--preview"])
        assert result.exit_code == 0
        assert "Already on branch" in result.output


class TestDryRunPhases:
    """Test dry-run phase reporting with changes and hooks."""

    def test_dry_run_reports_all_phases(self, navigate_integration, tmp_path):
        """Test dry-run shows save, switch, and deploy phases."""
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        test_file = _add_tracked_file(navigate_integration, tmp_path)
        GitManager(REPO_DIR).repo.create_head("dry-target")
        _add_section_hooks(tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(
            cli, ["navigate", "dry-target", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Phase 1" in result.output
        assert "Would save 1 section" in result.output
        assert "Phase 2" in result.output
        assert "Would checkout existing branch" in result.output
        assert "Phase 3" in result.output
        assert str(test_file) in result.output
        assert "pre_deploy" in result.output
        assert "post_deploy" in result.output
        assert "Phase 4" in result.output

    def test_dry_run_new_branch(self, navigate_integration, tmp_path):
        """Test dry-run reports branch creation for unknown branches."""
        _add_tracked_file(navigate_integration, tmp_path)
        result = navigate_integration.invoke(
            cli, ["navigate", "fresh-dry-branch", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "Would create and checkout new branch" in result.output


class TestBranchNavigateSaveFlows:
    """Test branch navigate save/commit message variants."""

    def _make_branch(self, name="feature-x"):
        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        GitManager(REPO_DIR).repo.create_head(name)

    def test_full_save_switch_deploy_with_hooks(self, navigate_integration, tmp_path):
        """Test switch → deploy with hooks deploys target content."""
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        _add_section_hooks(tmp_path)
        self._make_branch("hooked")
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(cli, ["navigate", "hooked", "--no-save"])
        assert result.exit_code == 0, f"Navigate failed: {result.output}"
        assert "Switching to branch" in result.output
        assert "Deployed 1 file" in result.output
        assert "Switched to 'hooked'" in result.output
        assert test_file.read_text() == "v1\n"

    def test_save_reports_secrets(self, navigate_integration, tmp_path):
        """Test save warns when secrets are redacted mid-navigate."""
        self._make_branch("other")
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("key = AKIAIOSFODNN7REALKEY1\n")
        result = navigate_integration.invoke(
            cli, ["navigate", "other", "--save"], input="2\n"
        )
        assert result.exit_code == 0, f"Navigate failed: {result.output}"
        assert "redacted" in result.output

    def test_save_errors_reported(self, navigate_integration, tmp_path):
        """Test save errors surface during navigate."""
        from unittest.mock import patch

        from dot_man.operations import get_operations

        self._make_branch("other")
        _add_tracked_file(navigate_integration, tmp_path)
        ops = get_operations()
        with patch.object(
            ops,
            "save_all",
            return_value={
                "saved": 1,
                "secrets": [],
                "errors": ["copy boom"],
                "symlinks": [],
            },
        ):
            result = navigate_integration.invoke(cli, ["navigate", "other"])
        assert result.exit_code == 1
        assert "errors during save" in result.output
        assert "copy boom" in result.output

    def test_custom_commit_message(self, navigate_integration, tmp_path):
        """Test a custom -m message is used for the auto-save commit."""
        self._make_branch("other")
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(
            cli, ["navigate", "other", "--save", "-m", "my custom msg"]
        )
        assert result.exit_code == 0, f"Navigate failed: {result.output}"
        assert "Commit: my custom msg" in result.output

    def test_no_commit_message_skips_commit(self, navigate_integration, tmp_path):
        """Test -m none saves files without committing."""
        self._make_branch("other")
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.write_text("v2\n")
        result = navigate_integration.invoke(
            cli, ["navigate", "other", "--save", "-m", "none"]
        )
        assert result.exit_code == 0, f"Navigate failed: {result.output}"
        assert "Saved 1 file" in result.output
        assert "no commit created" in result.output


class TestNavigateAbortCreate:
    """Test declining branch creation."""

    def test_decline_create_aborts(self, navigate_integration):
        """Test answering no to creation aborts the navigate."""
        with patch("dot_man.ui.confirm", return_value=False):
            result = navigate_integration.invoke(
                cli, ["navigate", "never-created", "--no-save"]
            )
        assert result.exit_code == 0
        assert "Aborted" in result.output


class TestNavigateDeployErrors:
    """Test deploy failure reporting."""

    def test_deploy_errors_reported(self, navigate_integration, tmp_path):
        """Test undeployable paths surface as deploy errors."""
        import shutil

        from dot_man.constants import REPO_DIR
        from dot_man.core import GitManager

        GitManager(REPO_DIR).repo.create_head("other")
        test_file = _add_tracked_file(navigate_integration, tmp_path)
        test_file.unlink()
        test_file.mkdir()
        (test_file / "nested.txt").write_text("blocks deploy\n")
        try:
            result = navigate_integration.invoke(
                cli, ["navigate", "other", "--no-save"]
            )
        finally:
            shutil.rmtree(test_file, ignore_errors=True)
        assert result.exit_code == 1
        assert "errors during deploy" in result.output


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
