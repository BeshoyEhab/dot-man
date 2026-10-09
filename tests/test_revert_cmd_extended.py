"""Extended tests for cli/revert_cmd.py — revert files from repository."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_ops():
    ops = MagicMock()
    ops.current_branch = "main"
    return ops


class TestRevertBasic:
    """Test basic revert functionality."""

    def test_revert_with_force(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = True
            result = runner.invoke(cli, ["revert", str(target), "--force"])
        assert result.exit_code == 0
        assert "Reverted" in result.output

    def test_revert_confirmed(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = True
            with patch("dot_man.cli.revert_cmd.ui") as mock_ui:
                mock_ui.confirm.return_value = True
                result = runner.invoke(cli, ["revert", str(target)])
        assert result.exit_code == 0

    def test_revert_aborted(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            with patch("dot_man.cli.revert_cmd.ui") as mock_ui:
                mock_ui.confirm.return_value = False
                result = runner.invoke(cli, ["revert", str(target)])
        assert result.exit_code == 0
        mock_ops.revert_file.assert_not_called()

    def test_revert_file_returns_false(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        target.write_text("local changes")
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.revert_file.return_value = False
            result = runner.invoke(cli, ["revert", str(target), "--force"])
        assert result.exit_code == 0
        # Should not crash when revert_file returns False


class TestRevertFromCommit:
    """Test revert from specific commit."""

    def test_revert_from_commit_not_found(self, runner, mock_ops, tmp_path):
        target = tmp_path / ".bashrc"
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.repo.git.show.side_effect = Exception("Path not found")
            result = runner.invoke(
                cli, ["revert", str(target), "-c", "deadbeef", "--force"]
            )
        assert result.exit_code == 1

    def test_revert_from_commit_path_error(self, runner, mock_ops, tmp_path):
        """Test that commit revert handles relative_to errors."""
        target = tmp_path / "sub" / ".bashrc"
        with patch("dot_man.operations.get_operations", return_value=mock_ops):
            mock_ops.repo.git.show.side_effect = ValueError("Path not relative")
            result = runner.invoke(
                cli, ["revert", str(target), "-c", "abc123", "--force"]
            )
        assert result.exit_code == 1


class TestRevertExceptions:
    """Test exception handling."""

    def test_dotman_error(self, runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=Exception("no repo"),
        ):
            result = runner.invoke(cli, ["revert", "/tmp/test", "--force"])
        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_keyboard_interrupt(self, runner):
        with patch(
            "dot_man.operations.get_operations",
            side_effect=KeyboardInterrupt(),
        ):
            result = runner.invoke(cli, ["revert", "/tmp/test", "--force"])
        assert result.exit_code != 0


class TestRevertFromCommitReal:
    """``-c`` restore against a real repo (integration env).

    The old implementation built the git path with
    ``relative_to(REPO_DIR.parent)``, which never matched a path inside
    the repo — every real ``-c`` restore died with "Could not restore".
    These tests pin the section-lookup fix end to end.
    """

    @staticmethod
    def _tracked(integration_runner, tmp_path, name: str, content: str):
        """Write a file under HOME, track it, return (file, commit sha)."""
        from dot_man.core import GitManager

        target = tmp_path / "home" / name
        target.write_text(content)
        result = integration_runner.invoke(cli, ["add", str(target), "--section", name])
        assert result.exit_code == 0, result.output
        # add copies + configures only; the tracked blob enters history
        # via a commit (dot-man save does this in the real workflow).
        git = GitManager()
        git.add_all()
        git.commit(f"Track {name}")
        sha = git.repo.head.commit.hexsha
        return target, sha

    def test_commit_restore_force_overwrites_local(self, integration_runner, tmp_path):
        target, sha = self._tracked(integration_runner, tmp_path, ".revrc", "repo v1")
        target.write_text("local junk")

        result = integration_runner.invoke(
            cli, ["revert", str(target), "-c", sha, "--force"]
        )

        assert result.exit_code == 0, result.output
        assert "Restored" in result.output
        assert target.read_text() == "repo v1"

    def test_commit_restore_declined_keeps_local(self, integration_runner, tmp_path):
        target, sha = self._tracked(integration_runner, tmp_path, ".revrc", "repo v1")
        target.write_text("local junk")

        with patch("dot_man.cli.revert_cmd.ui.confirm", return_value=False):
            result = integration_runner.invoke(cli, ["revert", str(target), "-c", sha])

        assert result.exit_code == 0, result.output
        assert target.read_text() == "local junk"

    def test_commit_restore_confirmed_overwrites_local(
        self, integration_runner, tmp_path
    ):
        target, sha = self._tracked(integration_runner, tmp_path, ".revrc", "repo v1")
        target.write_text("local junk")

        with patch("dot_man.cli.revert_cmd.ui.confirm", return_value=True):
            result = integration_runner.invoke(cli, ["revert", str(target), "-c", sha])

        assert result.exit_code == 0, result.output
        assert target.read_text() == "repo v1"

    def test_commit_restore_untracked_file_errors(self, integration_runner, tmp_path):

        _target, sha = self._tracked(integration_runner, tmp_path, ".revrc", "repo v1")
        stray = tmp_path / "home" / "stray.txt"
        stray.write_text("x")

        result = integration_runner.invoke(
            cli, ["revert", str(stray), "-c", sha, "--force"]
        )

        assert result.exit_code == 1, result.output
        assert "File not tracked" in result.output

    def test_commit_without_file_in_history_errors(self, integration_runner, tmp_path):
        from dot_man.core import GitManager

        sha_before_add = GitManager().repo.head.commit.hexsha
        target, _sha = self._tracked(integration_runner, tmp_path, ".revrc", "repo v1")
        target.write_text("local junk")

        result = integration_runner.invoke(
            cli, ["revert", str(target), "-c", sha_before_add, "--force"]
        )

        assert result.exit_code == 1, result.output
        assert "Could not restore from commit" in result.output

    def test_dotman_error_uses_its_exit_code(self, integration_runner):
        from dot_man.exceptions import DotManError

        with patch(
            "dot_man.operations.get_operations",
            side_effect=DotManError("ops exploded", exit_code=3),
        ):
            result = integration_runner.invoke(
                cli, ["revert", "/tmp/somefile", "--force"]
            )

        assert result.exit_code == 3, result.output
        assert "ops exploded" in result.output
