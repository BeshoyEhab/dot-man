"""Tests for cli/branch_cmd.py — branch command."""

import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Simple Click test runner (no patches)."""
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated dot-man environment with a real git repo & global config.

    Creates and initialises a git repository (branch renamed to ``main``),
    writes a valid ``global.toml`` that points to ``main``, and patches
    every module-level constant so that all commands operate inside the
    temporary tree.

    Yields (runner, dot_man_dir, repo_dir, global_toml).
    """
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    global_toml.parent.mkdir(parents=True, exist_ok=True)
    global_toml.write_text('[dot-man]\ncurrent_branch = "main"\n')

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
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        # Create the git repository — Repo.init creates branch "master",
        # so we rename it to "main" to match global config.
        from git import Repo

        repo_dir.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(repo_dir)
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Tester")
            cw.set_value("user", "email", "test@example.com")

        (repo_dir / "initial.txt").write_text("initial")
        repo.index.add(["initial.txt"])
        repo.index.commit("Initial commit")

        # Rename master → main
        if repo.heads and repo.heads[0].name != "main":
            repo.git.branch("-m", "master", "main")

        yield CliRunner(), dot_man_dir, repo_dir, global_toml


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestBranchHelp:
    def test_branch_help(self, runner):
        """--help on the branch group shows subcommands."""
        result = runner.invoke(cli, ["branch", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "delete" in result.output

    def test_branch_list_help(self, runner):
        """branch list --help shows description."""
        result = runner.invoke(cli, ["branch", "list", "--help"])
        assert result.exit_code == 0
        assert "List" in result.output

    def test_branch_delete_help(self, runner):
        """branch delete --help shows argument and force option."""
        result = runner.invoke(cli, ["branch", "delete", "--help"])
        assert result.exit_code == 0
        assert "NAME" in result.output
        assert "--force" in result.output


# ---------------------------------------------------------------------------
# Without init
# ---------------------------------------------------------------------------


class TestBranchWithoutInit:
    def test_list_fails_without_init(self, runner):
        """branch list without init shows welcome banner."""
        with patch(
            "dot_man.cli.common.DOT_MAN_DIR",
            Path("/tmp/nonexistent-dot-man"),
        ):
            result = runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 1
        assert "Welcome" in result.output

    def test_delete_fails_without_init(self, runner):
        """branch delete without init shows welcome banner."""
        with patch(
            "dot_man.cli.common.DOT_MAN_DIR",
            Path("/tmp/nonexistent-dot-man"),
        ):
            result = runner.invoke(cli, ["branch", "delete", "x"])
        assert result.exit_code == 1
        assert "Welcome" in result.output


# ---------------------------------------------------------------------------
# Branch list
# ---------------------------------------------------------------------------


class TestBranchList:
    def test_list_shows_branches(self, clean_env):
        """branch list shows available branches."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("work")
        grepo.create_head("personal")

        result = runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 0
        assert "main" in result.output
        assert "work" in result.output
        assert "personal" in result.output

    def test_list_marks_current_branch(self, clean_env):
        """branch list marks the active branch with a checkmark."""
        runner, _, repo_dir, global_toml = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("work")

        global_toml.write_text('[dot-man]\ncurrent_branch = "work"\n')
        from dot_man.operations import reset_operations

        reset_operations()

        result = runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 0
        assert "work" in result.output
        assert "✓" in result.output

    def test_list_no_branches(self, clean_env):
        """branch list when no branches exist shows dim message."""
        runner, _, _, _ = clean_env

        with patch(
            "dot_man.cli.branch_cmd.GitManager.list_branches",
            return_value=[],
        ):
            result = runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 0
        assert "No branches found" in result.output

    def test_list_exception_handled(self, clean_env):
        """branch list handles GlobalConfig.load failure gracefully."""
        runner, _, _, _ = clean_env
        with patch(
            "dot_man.global_config.GLOBAL_TOML",
            Path("/nonexistent/global.toml"),
        ):
            result = runner.invoke(cli, ["branch", "list"])
        # ConfigurationError has exit_code=7
        assert result.exit_code == 7
        assert "Error" in result.output or "error" in result.output

    def test_list_keyboard_interrupt(self, clean_env):
        """branch list handles KeyboardInterrupt in list_branches."""
        runner, _, _, _ = clean_env
        with patch(
            "dot_man.cli.branch_cmd.GitManager.list_branches",
            side_effect=KeyboardInterrupt,
        ):
            result = runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 130
        assert "cancelled" in result.output.lower()


# ---------------------------------------------------------------------------
# Branch delete — active / not found
# ---------------------------------------------------------------------------


class TestBranchDeleteBasic:
    def test_delete_active_branch_fails(self, clean_env):
        """Deleting the active branch shows an error and suggestions."""
        runner, _, _, _ = clean_env
        result = runner.invoke(cli, ["branch", "delete", "main"])
        assert result.exit_code == 1
        assert "Cannot delete the active branch" in result.output
        assert "Switch to another branch" in result.output

    def test_delete_active_branch_lists_alternatives(self, clean_env):
        """Deleting the active branch when other branches exist lists them."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("work")

        result = runner.invoke(cli, ["branch", "delete", "main"])
        assert result.exit_code == 1
        assert "Cannot delete the active branch" in result.output
        assert "work" in result.output

    def test_delete_nonexistent_branch_fails(self, clean_env):
        """Deleting a branch that doesn't exist prints an error."""
        runner, _, _, _ = clean_env
        result = runner.invoke(cli, ["branch", "delete", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_delete_non_existent_no_branches_shows_none(self, clean_env):
        """Deleting the active branch shows (none) when it's the only one."""
        runner, _, _, _ = clean_env
        result = runner.invoke(cli, ["branch", "delete", "main"])
        assert result.exit_code == 1
        assert "(none)" in result.output


# ---------------------------------------------------------------------------
# Branch delete — force / confirm
# ---------------------------------------------------------------------------


class TestBranchDeleteConfirm:
    def test_delete_force_success(self, clean_env):
        """Force deleting a non-active branch succeeds."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("feature-x")

        result = runner.invoke(cli, ["branch", "delete", "feature-x", "--force"])
        assert result.exit_code == 0
        assert "Deleted branch" in result.output
        assert "feature-x" not in [h.name for h in grepo.heads]

    def test_delete_without_force_confirmed(self, clean_env):
        """Deleting without --force but confirming succeeds."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("feature-y")

        with patch("dot_man.ui.confirm", return_value=True):
            result = runner.invoke(cli, ["branch", "delete", "feature-y"])

        assert result.exit_code == 0
        assert "Deleted branch" in result.output
        assert "feature-y" not in [h.name for h in grepo.heads]

    def test_delete_without_force_not_confirmed(self, clean_env):
        """Deleting without --force and declining prints Aborted."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("feature-z")

        with patch("dot_man.ui.confirm", return_value=False):
            result = runner.invoke(cli, ["branch", "delete", "feature-z"])

        assert result.exit_code == 0
        assert "Aborted" in result.output
        assert "feature-z" in [h.name for h in grepo.heads]


# ---------------------------------------------------------------------------
# Branch delete — BranchNotMergedError handling
# ---------------------------------------------------------------------------


class TestBranchDeleteUnmerged:
    def test_unmerged_confirmed_force_ok(self, clean_env):
        """BranchNotMergedError, user confirms force, succeeds."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("unmerged-1")

        from dot_man.exceptions import BranchNotMergedError

        def delete_side_effect(name, force=False):
            if not force:
                raise BranchNotMergedError(f"Branch '{name}' is not fully merged")
            return None

        with (
            patch(
                "dot_man.cli.branch_cmd.GitManager.delete_branch",
                side_effect=delete_side_effect,
            ),
            patch("dot_man.ui.confirm", return_value=True),
        ):
            result = runner.invoke(cli, ["branch", "delete", "unmerged-1"])

        assert result.exit_code == 0
        assert "Deleted branch" in result.output

    def test_unmerged_confirmed_force_fails(self, clean_env):
        """BranchNotMergedError, user confirms, but force delete fails."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("unmerged-2")

        from dot_man.exceptions import BranchNotMergedError

        call_count = 0

        def delete_side_effect(name, force=False):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise BranchNotMergedError(f"Branch '{name}' is not fully merged")
            raise RuntimeError("force delete failed")

        with (
            patch(
                "dot_man.cli.branch_cmd.GitManager.delete_branch",
                side_effect=delete_side_effect,
            ),
            patch("dot_man.ui.confirm", return_value=True),
        ):
            result = runner.invoke(cli, ["branch", "delete", "unmerged-2"])

        assert result.exit_code == 1
        assert "Failed to force delete" in result.output

    def test_unmerged_not_confirmed(self, clean_env):
        """BranchNotMergedError, user declines force, prints Aborted."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("unmerged-3")

        from dot_man.exceptions import BranchNotMergedError

        with (
            patch(
                "dot_man.cli.branch_cmd.GitManager.delete_branch",
                side_effect=BranchNotMergedError(
                    "Branch 'unmerged-3' is not fully merged"
                ),
            ),
            patch("dot_man.ui.confirm", return_value=False),
        ):
            result = runner.invoke(cli, ["branch", "delete", "unmerged-3", "--force"])

        assert result.exit_code == 0
        assert "Aborted" in result.output


# ---------------------------------------------------------------------------
# Branch delete — other exceptions
# ---------------------------------------------------------------------------


class TestBranchDeleteExceptions:
    def test_delete_dotman_error(self, clean_env):
        """Delete with a non-BranchNotMerged DotManError shows the error."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("error-branch")

        from dot_man.exceptions import DotManError

        with patch(
            "dot_man.cli.branch_cmd.GitManager.delete_branch",
            side_effect=DotManError("Something bad happened", exit_code=7),
        ):
            result = runner.invoke(
                cli,
                ["branch", "delete", "error-branch", "--force"],
            )

        assert result.exit_code == 7
        assert "Something bad happened" in result.output

    def test_delete_keyboard_interrupt(self, clean_env):
        """Delete with KeyboardInterrupt shows cancellation message."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("interrupt-branch")

        with patch(
            "dot_man.cli.branch_cmd.GitManager.delete_branch",
            side_effect=KeyboardInterrupt,
        ):
            result = runner.invoke(
                cli,
                ["branch", "delete", "interrupt-branch", "--force"],
            )

        assert result.exit_code == 130
        assert "cancelled" in result.output.lower()

    def test_delete_generic_exception(self, clean_env):
        """Delete with a generic exception shows diagnostic."""
        runner, _, repo_dir, _ = clean_env

        from git import Repo

        grepo = Repo(repo_dir)
        grepo.create_head("crash-branch")

        with patch(
            "dot_man.cli.branch_cmd.GitManager.delete_branch",
            side_effect=ValueError("oops"),
        ):
            result = runner.invoke(
                cli,
                ["branch", "delete", "crash-branch", "--force"],
            )

        assert result.exit_code == 1
        # handle_exception prints the ErrorDiagnostic details
        assert "Unexpected error" in result.output
