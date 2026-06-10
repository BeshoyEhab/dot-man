"""Tests for cli/log_cmd.py — log, diff, checkout commands."""

import os
import subprocess
from contextlib import ExitStack
from unittest.mock import patch

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
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants."""
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
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir


@pytest.fixture
def repo_with_commits(clean_env):
    """Set up an initialized repo with multiple commits + global.toml."""
    runner, dot_man_dir, repo_dir = clean_env

    from git import Repo

    repo = Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")

    commits = []
    for i in range(5):
        (repo_dir / f"file_{i}.txt").write_text(f"content {i}")
        repo.index.add([f"file_{i}.txt"])
        c = repo.index.commit(f"Commit number {i}")
        commits.append(c.hexsha)

    # Create dot-man.toml so config-dependent features work
    (repo_dir / "dot-man.toml").write_text(
        '["_dummy"]\npaths = ["/nonexistent/path/for/dotman/testing"]\n'
    )
    repo.index.add(["dot-man.toml"])
    repo.index.commit("Add minimal config")

    # Create global.toml so checkout can find it
    (dot_man_dir / "global.toml").write_text('[profiles]\ndefault = "default"\n')

    return runner, dot_man_dir, repo_dir, commits


# ---------------------------------------------------------------------------
# Log — Help
# ---------------------------------------------------------------------------


class TestLogHelp:
    def test_log_help_works_without_init(self, runner):
        result = runner.invoke(cli, ["log", "--help"])
        assert result.exit_code == 0
        assert "log" in result.output.lower()

    def test_log_help_contains_options(self, runner):
        result = runner.invoke(cli, ["log", "--help"])
        assert result.exit_code == 0
        assert "-n" in result.output
        assert "--count" in result.output
        assert "--diff" in result.output or "-d" in result.output
        assert "--stat" in result.output
        assert "--interactive" in result.output or "-i" in result.output

    def test_log_help_contains_examples(self, runner):
        result = runner.invoke(cli, ["log", "--help"])
        assert result.exit_code == 0
        assert "dot-man log" in result.output


# ---------------------------------------------------------------------------
# Log — Subprocess argument verification (mocked)
# ---------------------------------------------------------------------------


class TestLogSubprocess:
    def test_log_calls_git_log(self, repo_with_commits):
        """Log invokes git log with --color=always."""
        runner, _, repo_dir, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert args[1] == "log"
            assert "--color=always" in args

    def test_log_count_passes_n(self, repo_with_commits):
        """Log -n adds -n<N> to git args."""
        runner, _, _, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "-n", "3"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "-n3" in args

    def test_log_diff_adds_p(self, repo_with_commits):
        """Log --diff adds -p to git args."""
        runner, _, _, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "--diff", "-n", "1"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "-p" in args

    def test_log_stat_adds_stat(self, repo_with_commits):
        """Log --stat adds --stat to git args."""
        runner, _, _, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "--stat", "-n", "1"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "--stat" in args

    def test_log_count_long_form(self, repo_with_commits):
        """Log --count works as long form of -n."""
        runner, _, _, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "--count", "2"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "-n2" in args

    def test_log_with_diff_shorthand(self, repo_with_commits):
        """Log -d works as shorthand for --diff."""
        runner, _, _, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "-d", "-n", "1"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "-p" in args

    def test_log_calls_subprocess_with_repo_cwd(self, repo_with_commits):
        """Log passes REPO_DIR as cwd to subprocess."""
        runner, _, repo_dir, _ = repo_with_commits
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", "-n", "1"])
            assert result.exit_code == 0
            assert mock_run.call_args[1].get("cwd") == repo_dir

    def test_log_empty_repo(self, clean_env):
        """Log on repo with no commits returns exit code 0 or 1."""
        runner, _, repo_dir = clean_env

        from git import Repo

        repo = Repo.init(repo_dir)
        with repo.config_writer() as config:
            config.set_value("user", "name", "Test")
            config.set_value("user", "email", "test@test.com")

        result = runner.invoke(cli, ["log"])
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Log — Interactive
# ---------------------------------------------------------------------------


class TestLogInteractive:
    def test_log_interactive_starts_viewer(self, repo_with_commits):
        """Log --interactive runs TUI app."""
        runner, _, _, _ = repo_with_commits
        with patch("dot_man.tui_log.LogViewerApp") as MockApp:
            instance = MockApp.return_value
            result = runner.invoke(cli, ["log", "--interactive"])
            assert result.exit_code == 0
            MockApp.assert_called_once()
            instance.run.assert_called_once()

    def test_log_interactive_shorthand(self, repo_with_commits):
        """Log -i works as shorthand for --interactive."""
        runner, _, _, _ = repo_with_commits
        with patch("dot_man.tui_log.LogViewerApp") as MockApp:
            instance = MockApp.return_value
            result = runner.invoke(cli, ["log", "-i"])
            assert result.exit_code == 0
            MockApp.assert_called_once()
            instance.run.assert_called_once()


# ---------------------------------------------------------------------------
# Log — File argument
# ---------------------------------------------------------------------------


class TestLogFile:
    def _setup_tracked_file(self, repo_dir):
        """Helper: create section config and commit a tracked file."""
        tracked_file = repo_dir / "tracked.txt"
        tracked_file.write_text("tracked content")

        config_path = repo_dir / "dot-man.toml"
        config_path.write_text(f'["test-section"]\npaths = ["{tracked_file}"]\n')

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["tracked.txt", "dot-man.toml"])
        repo.index.commit("Add tracked file and config")

        from dot_man.operations import get_operations, reset_operations

        reset_operations()
        ops = get_operations()
        ops.reload_config()

        return tracked_file

    def test_log_with_tracked_file(self, repo_with_commits):
        """Log with a tracked file adds file filter to git args."""
        runner, _, repo_dir, _ = repo_with_commits
        tracked_file = self._setup_tracked_file(repo_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["log", str(tracked_file)])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "--" in args
            idx = args.index("--")
            assert len(args) > idx + 1

    def test_log_with_untracked_file_shows_error(self, repo_with_commits):
        """Log with an untracked file shows error message."""
        runner, _, _, _ = repo_with_commits
        result = runner.invoke(cli, ["log", "/nonexistent/untracked.txt"])
        assert "not tracked" in result.output.lower()


# ---------------------------------------------------------------------------
# Log — Error handling
# ---------------------------------------------------------------------------


class TestLogErrors:
    def test_log_exception_is_caught_and_displayed(self, repo_with_commits):
        """Exception during log is caught and displayed."""
        runner, _, _, _ = repo_with_commits
        with patch(
            "subprocess.run",
            side_effect=Exception("Simulated git error"),
        ):
            result = runner.invoke(cli, ["log", "-n", "1"])
            assert "Simulated git error" in result.output


# ---------------------------------------------------------------------------
# Diff — Help
# ---------------------------------------------------------------------------


class TestDiffHelp:
    def test_diff_help_works(self, runner):
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0
        assert "diff" in result.output.lower()

    def test_diff_help_contains_options(self, runner):
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0
        assert "--branch" in result.output or "-b" in result.output
        assert "--staged" in result.output
        assert "--rich" in result.output or "--no-rich" in result.output


# ---------------------------------------------------------------------------
# Diff — Subprocess argument verification
# ---------------------------------------------------------------------------


class TestDiffSubprocess:
    def test_diff_calls_git_diff(self, repo_with_commits):
        """Diff invokes git diff with --color=always."""
        runner, _, repo_dir, _ = repo_with_commits
        (repo_dir / "file_0.txt").write_text("modified content")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["diff", "--no-rich"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert args[1] == "diff"
            assert "--color=always" in args

    def test_diff_with_staged(self, repo_with_commits):
        """Diff --staged adds --staged to git args."""
        runner, _, repo_dir, _ = repo_with_commits

        from git import Repo

        repo = Repo(repo_dir)
        (repo_dir / "staged_file.txt").write_text("staged content")
        repo.index.add(["staged_file.txt"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["diff", "--staged", "--no-rich"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "--staged" in args

    def test_diff_no_rich_fallback(self, repo_with_commits):
        """Diff --no-rich uses plain git diff subprocess."""
        runner, _, repo_dir, _ = repo_with_commits
        (repo_dir / "file_0.txt").write_text("modified")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["diff", "--no-rich"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "diff" in args

    def test_diff_branch_comparison(self, repo_with_commits):
        """Diff --branch adds branch comparison to git args."""
        runner, _, repo_dir, _ = repo_with_commits

        from git import Repo

        repo = Repo(repo_dir)
        repo.create_head("feature")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["diff", "--branch", "feature", "--no-rich"])
            assert result.exit_code == 0
            args = mock_run.call_args[0][0]
            assert any("..." in a for a in args)


# ---------------------------------------------------------------------------
# Diff — Rich output
# ---------------------------------------------------------------------------


class TestDiffRich:
    def test_diff_rich_on_clean_repo(self, repo_with_commits):
        """Diff on clean repo works."""
        runner, _, _, _ = repo_with_commits

        with patch("subprocess.run") as mock_run:
            mock_result = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            mock_run.return_value = mock_result
            result = runner.invoke(cli, ["diff"])
            assert result.exit_code == 0
            mock_run.assert_called()

    def test_show_rich_diff_works(self, repo_with_commits):
        """_show_rich_diff runs git diff with capture_output."""
        runner, _, repo_dir, _ = repo_with_commits
        (repo_dir / "file_0.txt").write_text("changed")

        from dot_man.cli.log_cmd import _show_rich_diff

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            _show_rich_diff(None, None, False)
            assert mock_run.called
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "diff" in args
            assert mock_run.call_args[1].get("capture_output") is True


# ---------------------------------------------------------------------------
# Diff — File argument
# ---------------------------------------------------------------------------


class TestDiffFile:
    def _setup_tracked_file(self, repo_dir):
        """Helper: create section config and commit a tracked file."""
        tracked_file = repo_dir / "diff_tracked.txt"
        tracked_file.write_text("original")

        config_path = repo_dir / "dot-man.toml"
        config_path.write_text(f'["test-section"]\npaths = ["{tracked_file}"]\n')

        from git import Repo

        repo = Repo(repo_dir)
        repo.index.add(["diff_tracked.txt", "dot-man.toml"])
        repo.index.commit("Add diff tracked file")

        from dot_man.operations import get_operations, reset_operations

        reset_operations()
        ops = get_operations()
        ops.reload_config()

        return tracked_file

    def test_diff_with_tracked_file(self, repo_with_commits):
        """Diff with tracked file calls subprocess with correct args."""
        runner, _, repo_dir, _ = repo_with_commits
        tracked_file = self._setup_tracked_file(repo_dir)
        tracked_file.write_text("modified")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            result = runner.invoke(cli, ["diff", str(tracked_file)])
            assert result.exit_code == 0
            mock_run.assert_called()
            args, kwargs = mock_run.call_args
            assert "diff" in args[0]

    def test_diff_with_untracked_file(self, repo_with_commits):
        """Diff with untracked file shows error."""
        runner, _, _, _ = repo_with_commits
        result = runner.invoke(cli, ["diff", "/nonexistent/untracked.txt"])
        assert "not tracked" in result.output.lower()


# ---------------------------------------------------------------------------
# Checkout — Help
# ---------------------------------------------------------------------------


class TestCheckoutHelp:
    def test_checkout_help_works(self, runner):
        result = runner.invoke(cli, ["checkout", "--help"])
        assert result.exit_code == 0
        assert "checkout" in result.output.lower()


# ---------------------------------------------------------------------------
# Checkout — Deprecation & Basic operation
# ---------------------------------------------------------------------------


class TestCheckoutDeprecation:
    def test_checkout_shows_deprecation_warning(self, repo_with_commits):
        """Checkout shows deprecation warning before proceeding."""
        runner, _, _, _ = repo_with_commits

        with patch("dot_man.cli.common.parse_branch_arg") as mock_parse:
            mock_parse.return_value = {"type": "commit", "target": "abc1234"}
            with patch("dot_man.cli.log_cmd._checkout_commit"):
                result = runner.invoke(cli, ["checkout", "abc1234"])
                assert result.exit_code == 0
                assert (
                    "DEPRECATED" in result.output
                    or "deprecated" in result.output.lower()
                )
                assert "navigate" in result.output

    def test_checkout_with_commit(self, repo_with_commits):
        """Checkout with valid commit calls _checkout_commit."""
        runner, _, _, _ = repo_with_commits

        with patch("dot_man.cli.common.parse_branch_arg") as mock_parse:
            mock_parse.return_value = {"type": "commit", "target": "abc1234"}
            with patch("dot_man.cli.log_cmd._checkout_commit") as mock_cc:
                result = runner.invoke(cli, ["checkout", "abc1234"])
                assert result.exit_code == 0
                mock_cc.assert_called_once()

    def test_checkout_with_tag(self, repo_with_commits):
        """Checkout with tag calls _checkout_tag."""
        runner, _, _, _ = repo_with_commits

        with patch("dot_man.cli.common.parse_branch_arg") as mock_parse:
            mock_parse.return_value = {"type": "tag", "target": "v1.0"}
            with patch("dot_man.cli.log_cmd._checkout_tag") as mock_ct:
                result = runner.invoke(cli, ["checkout", "v1.0"])
                assert result.exit_code == 0
                mock_ct.assert_called_once()

    def test_checkout_unknown_target_falls_through(self, repo_with_commits):
        """Checkout with unknown target tries commit, then tag, then errors."""
        runner, _, _, _ = repo_with_commits

        with patch("dot_man.cli.common.parse_branch_arg") as mock_parse:
            mock_parse.return_value = {"type": "unknown", "target": "bogus"}
            with patch("dot_man.cli.log_cmd._checkout_commit"):
                with patch("dot_man.cli.log_cmd._checkout_tag"):
                    result = runner.invoke(cli, ["checkout", "bogus"])
                    assert result.exit_code != 0
                    assert "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Checkout — Error handling
# ---------------------------------------------------------------------------


class TestCheckoutErrors:
    def test_checkout_exception_is_caught(self, repo_with_commits):
        """Exception during checkout is caught and displayed."""
        runner, _, _, _ = repo_with_commits

        with patch(
            "dot_man.cli.common.parse_branch_arg",
            side_effect=Exception("Checkout boom"),
        ):
            result = runner.invoke(cli, ["checkout", "abc123"])
            assert "Checkout boom" in result.output

    def test_checkout_invalid_commit_sha(self, repo_with_commits):
        """Checkout with invalid commit SHA handled gracefully."""
        runner, _, _, _ = repo_with_commits

        with patch("dot_man.cli.common.parse_branch_arg") as mock_parse:
            mock_parse.return_value = {"type": "commit", "target": "badsha"}
            with patch("dot_man.cli.log_cmd._checkout_commit") as mock_cc:
                mock_cc.side_effect = Exception("Invalid commit")
                result = runner.invoke(cli, ["checkout", "badsha"])
                assert "Invalid commit" in result.output


# ---------------------------------------------------------------------------
# _checkout_commit and _checkout_tag unit tests
# ---------------------------------------------------------------------------


class TestCheckoutHelpers:
    def test_checkout_commit_valid(self, repo_with_commits):
        """_checkout_commit checks out a valid commit."""
        runner, _, repo_dir, commits = repo_with_commits

        from dot_man.cli.log_cmd import _checkout_commit
        from dot_man.operations import get_operations

        ops = get_operations()

        with patch("dot_man.cli.log_cmd.ui.console.print"):
            _checkout_commit(ops, "master", commits[0])

        from git import Repo

        repo = Repo(repo_dir)
        assert repo.head.commit.hexsha.startswith(commits[0][:7])

    def test_checkout_commit_invalid(self, repo_with_commits):
        """_checkout_commit with unresolvable SHA shows error and exits."""
        runner, _, _, _ = repo_with_commits

        from dot_man.cli.log_cmd import _checkout_commit
        from dot_man.operations import get_operations

        ops = get_operations()

        with patch.object(ops.git.repo, "commit", side_effect=ValueError("bad SHA")):
            with patch("dot_man.cli.log_cmd.ui.console.print"):
                with pytest.raises(SystemExit):
                    _checkout_commit(ops, "master", "badsha")

    def test_checkout_tag_valid(self, repo_with_commits):
        """_checkout_tag checks out a valid tag."""
        runner, _, repo_dir, _ = repo_with_commits

        from git import Repo

        repo = Repo(repo_dir)
        repo.create_tag("test-tag", message="Test tag message")

        from dot_man.cli.log_cmd import _checkout_tag
        from dot_man.operations import get_operations

        ops = get_operations()

        with patch.object(ops.git, "checkout") as mock_checkout:
            with patch("dot_man.cli.log_cmd.ui.console.print"):
                with patch("dot_man.cli.log_cmd.success"):
                    _checkout_tag(ops, "master", "test-tag")
                    mock_checkout.assert_called_once_with("test-tag")

    def test_checkout_tag_not_found(self, repo_with_commits):
        """_checkout_tag with non-existent tag shows error."""
        runner, _, _, _ = repo_with_commits

        from dot_man.cli.log_cmd import _checkout_tag
        from dot_man.operations import get_operations

        ops = get_operations()

        with pytest.raises(SystemExit):
            _checkout_tag(ops, "master", "nonexistent-tag")


# ---------------------------------------------------------------------------
# Integration tests (using integration_runner)
# ---------------------------------------------------------------------------


class TestLogIntegration:
    def test_log_after_init(self, integration_runner):
        """Log works after full init with commits."""
        runner = integration_runner

        from git import Repo

        from dot_man.constants import REPO_DIR

        repo = Repo(REPO_DIR)
        (REPO_DIR / "integration.txt").write_text("integration test")
        repo.index.add(["integration.txt"])
        repo.index.commit("Integration test commit")

        result = runner.invoke(cli, ["log", "-n", "1"])
        assert result.exit_code == 0, result.output

    def test_log_with_file_filter_integration(self, integration_runner):
        """Log with file argument works in integration."""
        runner = integration_runner

        from git import Repo

        from dot_man.constants import REPO_DIR

        repo = Repo(REPO_DIR)

        tracked_file = REPO_DIR / "tracked.txt"
        tracked_file.write_text("content")
        repo.index.add(["tracked.txt"])

        config_path = REPO_DIR / "dot-man.toml"
        config_path.write_text(f'["test-section"]\npaths = ["{tracked_file}"]\n')
        repo.index.add(["dot-man.toml"])
        repo.index.commit("Setup tracked file")

        from dot_man.operations import get_operations, reset_operations

        reset_operations()
        ops = get_operations()
        ops.reload_config()

        result = runner.invoke(cli, ["log", str(tracked_file)])
        assert result.exit_code == 0, result.output


class TestDiffIntegration:
    def test_diff_after_init(self, integration_runner):
        """Diff works in full integration."""
        runner = integration_runner

        from git import Repo

        from dot_man.constants import REPO_DIR

        repo = Repo(REPO_DIR)
        (REPO_DIR / "diff_test.txt").write_text("new file")
        repo.index.add(["diff_test.txt"])
        repo.index.commit("Diff test commit")
        (REPO_DIR / "diff_test.txt").write_text("modified")

        result = runner.invoke(cli, ["diff", "--no-rich"])
        assert result.exit_code == 0, result.output

    def test_diff_staged_integration(self, integration_runner):
        """Diff --staged works in integration."""
        runner = integration_runner

        from git import Repo

        from dot_man.constants import REPO_DIR

        repo = Repo(REPO_DIR)
        (REPO_DIR / "staged_test.txt").write_text("staged")
        repo.index.add(["staged_test.txt"])

        result = runner.invoke(cli, ["diff", "--staged", "--no-rich"])
        assert result.exit_code == 0, result.output
