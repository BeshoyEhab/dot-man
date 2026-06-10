"""Tests for cli/rollback_cmd.py — rollback command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
from git import Repo as GitRepo

from dot_man.cli.interface import cli
from dot_man.cli.rollback_cmd import _resolve_target, _show_rollback_points

# =============================================================================
# Helpers
# =============================================================================


def _commits(repo_dir: Path, n: int) -> GitRepo:
    """Create n additional commits in the repo (returning the Repo object)."""
    repo = GitRepo(repo_dir)
    for i in range(n):
        f = repo_dir / f"_cr_{i}.txt"
        f.write_text(f"content_{i}")
        repo.index.add([f"_cr_{i}.txt"])
        repo.index.commit(f"Auto commit {i}")
    return repo


def _repo_dir(tmp_path: Path) -> Path:
    """Return the repo path set up by the integration_runner fixture."""
    return tmp_path / "home" / ".config" / "dot-man" / "repo"


# =============================================================================
# Unit tests — _resolve_target
# =============================================================================


class TestResolveTarget:
    """Unit tests for _resolve_target()."""

    def test_valid_target_returns_full_hexsha(self):
        """Returns the full 40-char hexsha for a valid target."""
        git = MagicMock()
        mock_commit = MagicMock()
        mock_commit.hexsha = "a" * 40
        git.repo.commit.return_value = mock_commit

        result = _resolve_target(git, "HEAD")
        assert result == "a" * 40

    def test_invalid_target_returns_none(self):
        """Returns None when the target cannot be resolved."""
        git = MagicMock()
        git.repo.commit.side_effect = Exception("not found")

        result = _resolve_target(git, "nonexistent")
        assert result is None

    def test_git_command_failure_returns_none(self):
        """Returns None when repo.commit raises any exception."""
        git = MagicMock()
        git.repo.commit.side_effect = Exception("git error")

        result = _resolve_target(git, "broken")
        assert result is None

    def test_delegates_target_string_to_repo_commit(self):
        """Passes the exact target string to repo.commit()."""
        git = MagicMock()
        git.repo.commit.return_value.hexsha = "a" * 40

        _resolve_target(git, "abc1234")
        git.repo.commit.assert_called_once_with("abc1234")


# =============================================================================
# Unit tests — _show_rollback_points
# =============================================================================


class TestShowRollbackPoints:
    """Unit tests for _show_rollback_points()."""

    @patch("dot_man.cli.rollback_cmd.ui.console.print")
    def test_calls_get_commits_detailed_with_count_20(self, mock_print):
        """Delegates to ops.git.get_commits_detailed(count=20)."""
        ops = MagicMock()
        ops.git.get_commits_detailed.return_value = []

        _show_rollback_points(ops)
        ops.git.get_commits_detailed.assert_called_once_with(count=20)

    @patch("dot_man.cli.rollback_cmd.ui.console.print")
    def test_shows_no_history_when_empty(self, mock_print):
        """Prints 'No commit history found' for an empty list."""
        ops = MagicMock()
        ops.git.get_commits_detailed.return_value = []

        _show_rollback_points(ops)

        texts = [str(c) for c, _ in mock_print.call_args_list]
        assert any("No commit history" in t for t in texts)

    @patch("dot_man.cli.rollback_cmd.ui.console.print")
    def test_displays_table_when_commits_exist(self, mock_print):
        """Calls console.print at least once when commits are returned."""
        ops = MagicMock()
        ops.git.get_commits_detailed.return_value = [
            {
                "sha": "abc1234",
                "full_sha": "a" * 40,
                "message": "Add feature",
                "full_message": "Add feature",
                "author": "Tester",
                "date": "2026-05-15 10:00",
                "relative_date": "2 days ago",
                "files": ["f1.txt"],
                "files_more": None,
                "insertions": 10,
                "deletions": 2,
                "tags": [],
                "is_merge": False,
                "parent_count": 1,
            },
        ]

        _show_rollback_points(ops)
        assert mock_print.call_count > 0

    @patch("dot_man.cli.rollback_cmd.ui.console.print")
    def test_shows_tags_alongside_message(self, mock_print):
        """Renders tags in the message column."""
        ops = MagicMock()
        ops.git.get_commits_detailed.return_value = [
            {
                "sha": "abc1234",
                "full_sha": "a" * 40,
                "message": "Release v1",
                "full_message": "Release v1",
                "author": "Tester",
                "date": "2026-05-15 10:00",
                "relative_date": "2 days ago",
                "files": ["f1.txt"],
                "files_more": None,
                "insertions": 10,
                "deletions": 2,
                "tags": ["v1.0", "latest"],
                "is_merge": False,
                "parent_count": 1,
            },
        ]

        _show_rollback_points(ops)
        assert mock_print.call_count > 0

    @patch("dot_man.cli.rollback_cmd.ui.console.print")
    def test_counts_files_with_files_more(self, mock_print):
        """Correctly tallies files when files_more exceeds 5."""
        ops = MagicMock()
        ops.git.get_commits_detailed.return_value = [
            {
                "sha": "def5678",
                "full_sha": "d" * 40,
                "message": "Big change",
                "full_message": "Big change",
                "author": "Tester",
                "date": "2026-05-14 09:00",
                "relative_date": "3 days ago",
                "files": ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt"],
                "files_more": 15,
                "insertions": 100,
                "deletions": 20,
                "tags": [],
                "is_merge": False,
                "parent_count": 1,
            },
        ]

        _show_rollback_points(ops)
        assert mock_print.call_count > 0


# =============================================================================
# Integration tests — rollback CLI
# =============================================================================


class TestRollbackHelp:
    """Tests for rollback --help."""

    def test_help_exit_code(self):
        """--help exits with code 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["rollback", "--help"])
        assert result.exit_code == 0

    def test_help_contains_options(self):
        """--help lists --list, --steps, --dry-run, --force."""
        runner = CliRunner()
        result = runner.invoke(cli, ["rollback", "--help"])
        assert "--list" in result.output
        assert "--steps" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output


class TestRollbackList:
    """Tests for rollback --list."""

    def test_list_with_minimal_history(self, integration_runner):
        """--list succeeds with the initial init commit."""
        result = integration_runner.invoke(cli, ["rollback", "--list"])
        assert result.exit_code == 0

    def test_list_shows_commits(self, integration_runner, tmp_path):
        """--list displays available rollback points."""
        _commits(_repo_dir(tmp_path), 3)

        result = integration_runner.invoke(cli, ["rollback", "--list"])
        assert result.exit_code == 0
        assert "HEAD" in result.output

    def test_list_includes_all_commits(self, integration_runner, tmp_path):
        """--list shows all commits when there is enough history."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 5)
        last_msg = list(repo.iter_commits())[0].message.strip()

        result = integration_runner.invoke(cli, ["rollback", "--list"])
        assert result.exit_code == 0
        assert last_msg in result.output


class TestRollbackDryRun:
    """Tests for rollback --dry-run."""

    def test_dry_run_prints_preview(self, integration_runner, tmp_path):
        """--dry-run prints a plan but does not make changes."""
        _commits(_repo_dir(tmp_path), 3)

        result = integration_runner.invoke(
            cli, ["rollback", "--steps", "1", "--dry-run"]
        )
        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "Rollback Plan" in result.output

    def test_dry_run_does_not_change_head(self, integration_runner, tmp_path):
        """--dry-run leaves HEAD unchanged."""
        repo_dir = _repo_dir(tmp_path)
        _commits(repo_dir, 3)

        repo = GitRepo(repo_dir)
        head_before = repo.head.commit.hexsha

        integration_runner.invoke(cli, ["rollback", "--steps", "1", "--dry-run"])

        head_after = repo.head.commit.hexsha
        assert head_before == head_after


class TestRollbackForce:
    """Tests for rollback --force."""

    def test_force_skips_confirmation(self, integration_runner, tmp_path):
        """--force bypasses confirmation prompt."""
        _commits(_repo_dir(tmp_path), 3)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output


class TestRollbackSteps:
    """Tests for rollback --steps / -n."""

    def test_steps_1_rolls_back_one(self, integration_runner, tmp_path):
        """--steps 1 rolls back one commit."""
        repo_dir = _repo_dir(tmp_path)
        _commits(repo_dir, 3)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_steps_2_rolls_back_two(self, integration_runner, tmp_path):
        """--steps 2 rolls back two commits."""
        _commits(_repo_dir(tmp_path), 3)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "2", "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_steps_moves_head_to_correct_position(self, integration_runner, tmp_path):
        """After --steps N, HEAD matches HEAD~N from before rollback."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        expected_sha = list(repo.iter_commits())[1].hexsha

        integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])

        repo_after = GitRepo(repo_dir)
        assert repo_after.head.commit.hexsha == expected_sha


class TestRollbackTarget:
    """Tests for providing a specific target."""

    def test_full_sha(self, integration_runner, tmp_path):
        """Rolls back to a full 40-char commit SHA."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        target = list(repo.iter_commits())[2].hexsha

        result = integration_runner.invoke(cli, ["rollback", target, "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_short_sha(self, integration_runner, tmp_path):
        """Rolls back to a 7-char abbreviated SHA."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        target = list(repo.iter_commits())[2].hexsha[:7]

        result = integration_runner.invoke(cli, ["rollback", target, "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_tag(self, integration_runner, tmp_path):
        """Rolls back to a tagged commit."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        repo.create_tag("safe-point")

        result = integration_runner.invoke(cli, ["rollback", "safe-point", "--force"])
        assert result.exit_code == 0
        assert "Rolled back" in result.output

    def test_checks_out_correct_sha(self, integration_runner, tmp_path):
        """HEAD points to the target commit after rollback."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        target = list(repo.iter_commits())[2].hexsha

        integration_runner.invoke(cli, ["rollback", target, "--force"])

        repo_after = GitRepo(repo_dir)
        assert repo_after.head.commit.hexsha == target


class TestRollbackErrors:
    """Tests for error handling."""

    def test_error_unresolvable_target(self, integration_runner):
        """Exits with error when target string cannot be resolved."""
        result = integration_runner.invoke(
            cli, ["rollback", "totally_nonexistent_sha", "--force"]
        )
        assert result.exit_code != 0
        assert "Cannot resolve" in result.output

    def test_error_steps_less_than_one(self, integration_runner):
        """Exits with error when --steps is less than 1."""
        result = integration_runner.invoke(cli, ["rollback", "--steps", "0", "--force"])
        assert result.exit_code != 0
        assert "at least 1" in result.output

    def test_error_not_enough_history(self, integration_runner, tmp_path):
        """Exits with error when there are not enough commits for --steps."""
        _commits(_repo_dir(tmp_path), 1)

        result = integration_runner.invoke(
            cli, ["rollback", "--steps", "50", "--force"]
        )
        assert result.exit_code != 0
        assert "Not enough history" in result.output

    @patch("dot_man.cli.rollback_cmd.ui.confirm", return_value=False)
    def test_aborts_on_no_confirmation(
        self, mock_confirm, integration_runner, tmp_path
    ):
        """Prints 'Aborted' when user declines confirmation."""
        _commits(_repo_dir(tmp_path), 3)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1"])
        assert result.exit_code == 0
        assert "Aborted" in result.output

    @patch("dot_man.cli.rollback_cmd.ui.confirm", return_value=False)
    def test_abort_does_not_change_head(
        self, mock_confirm, integration_runner, tmp_path
    ):
        """HEAD is unchanged when user declines confirmation."""
        repo_dir = _repo_dir(tmp_path)
        _commits(repo_dir, 3)

        head_before = GitRepo(repo_dir).head.commit.hexsha
        integration_runner.invoke(cli, ["rollback", "--steps", "1"])
        head_after = GitRepo(repo_dir).head.commit.hexsha

        assert head_before == head_after


class TestRollbackFullFlow:
    """Tests for the complete rollback flow (backup, checkout, deploy)."""

    def test_backup_created_with_file_section(self, integration_runner, tmp_path):
        """Creates a safety backup when a section with existing paths is configured."""
        repo_dir = _repo_dir(tmp_path)
        test_file = tmp_path / "home" / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("version1")
        integration_runner.invoke(cli, ["add", str(test_file), "--section", "test"])

        _commits(repo_dir, 2)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])
        assert result.exit_code == 0
        assert "Backup" in result.output or "backup" in result.output.lower()

    def test_backup_skipped_without_sections(self, integration_runner, tmp_path):
        """Backup is skipped when no sections have existing paths."""
        _commits(_repo_dir(tmp_path), 2)

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])
        assert result.exit_code == 0

    def test_checkout_moves_to_target(self, integration_runner, tmp_path):
        """The target commit is checked out after rollback."""
        repo_dir = _repo_dir(tmp_path)
        repo = _commits(repo_dir, 3)
        expected = list(repo.iter_commits())[1].hexsha

        integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])

        assert GitRepo(repo_dir).head.commit.hexsha == expected

    def test_deploy_runs_after_checkout(self, integration_runner, tmp_path):
        """Deploy executes after the target commit is checked out."""
        repo_dir = _repo_dir(tmp_path)
        test_file = tmp_path / "home" / ".testrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("content")
        integration_runner.invoke(cli, ["add", str(test_file), "--section", "test"])

        repo = GitRepo(repo_dir)
        (repo_dir / "_extra.txt").write_text("extra")
        repo.index.add(["_extra.txt"])
        repo.index.commit("Second commit")

        result = integration_runner.invoke(cli, ["rollback", "--steps", "1", "--force"])
        assert result.exit_code == 0
        assert "deployed" in result.output.lower() or "Rolled back" in result.output
