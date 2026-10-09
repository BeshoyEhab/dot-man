"""Tests for the restore command."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    """Return a Click CLI runner."""
    return CliRunner()


def test_restore_help(runner):
    """Test restore help command."""
    result = runner.invoke(cli, ["restore", "--help"])
    assert result.exit_code == 0
    assert "Restore a file from history" in result.output


@patch("dot_man.operations.get_operations")
@patch("dot_man.ui.confirm")
def test_restore_commit(mock_confirm, mock_get_ops, integration_runner, tmp_path):
    """Test restoring a commit."""
    runner = integration_runner

    # Mock ops
    mock_ops = mock_get_ops.return_value
    mock_ops.get_sections.return_value = ["mysection"]

    class MockSection:
        paths = [tmp_path / "test.txt"]

        def get_repo_path(self, p, r):
            return r / "mysection/test.txt"

    mock_ops.get_section.return_value = MockSection()
    mock_ops.git.repo.git.show.return_value = "restored content"

    mock_confirm.return_value = True

    target_file = tmp_path / "test.txt"
    target_file.write_text("old content")

    result = runner.invoke(cli, ["restore", str(target_file), "abc1234"])

    assert result.exit_code == 0, result.output
    assert target_file.read_text() == "restored content"
    assert (
        tmp_path / "home/.config/dot-man/repo/mysection/test.txt"
    ).read_text() == "restored content"


def test_restore_without_init(runner, tmp_path):
    """Test restore without initialization."""
    with patch("dot_man.cli.common.REPO_DIR", tmp_path / "norepo"):
        result = runner.invoke(cli, ["restore", "~/.bashrc", "HEAD"])
        assert result.exit_code != 0
        assert "not initialized" in result.output.lower()


# ---------------------------------------------------------------------------
# Coverage floor: real restore flows + error handlers
# ---------------------------------------------------------------------------


def _track_and_commit(runner, target, name):
    """Add target via the CLI, then commit it (add alone does not commit)."""
    from dot_man.core import GitManager
    from dot_man.operations import reset_operations

    res = runner.invoke(cli, ["add", str(target), "--section", name])
    assert res.exit_code == 0, res.output
    reset_operations()
    git = GitManager()
    git.add_all()
    git.commit(f"Track {name}")
    return git.repo.head.commit.hexsha


def test_restore_real_force_overwrites(integration_runner):
    from pathlib import Path

    from dot_man.operations import reset_operations

    target = Path.home() / ".restorerc"
    target.write_text("repo v1")
    sha = _track_and_commit(integration_runner, target, "restorerc")

    target.write_text("local v2")
    reset_operations()

    result = integration_runner.invoke(cli, ["restore", str(target), sha, "--force"])
    assert result.exit_code == 0, result.output
    assert target.read_text() == "repo v1"
    assert "Restored:" in result.output


def test_restore_declined_keeps_local(integration_runner):
    from pathlib import Path
    from unittest.mock import patch as _patch

    target = Path.home() / ".restorerc"
    target.write_text("repo v1")
    sha = _track_and_commit(integration_runner, target, "restorerc")
    target.write_text("local v2")

    with _patch("dot_man.ui.confirm", return_value=False):
        result = integration_runner.invoke(cli, ["restore", str(target), sha])

    assert result.exit_code == 0, result.output
    assert target.read_text() == "local v2"


def test_restore_untracked_file_errors(integration_runner):
    from pathlib import Path

    target = Path.home() / ".nottrackedrc"
    target.write_text("loose")

    result = integration_runner.invoke(
        cli, ["restore", str(target), "abc1234", "--force"]
    )
    assert result.exit_code == 1, result.output
    assert "File not tracked:" in result.output


def test_restore_invalid_commit_reports(integration_runner):
    from pathlib import Path

    target = Path.home() / ".restorerc"
    target.write_text("repo v1")
    _track_and_commit(integration_runner, target, "restorerc")
    target.write_text("local v2")

    result = integration_runner.invoke(
        cli,
        ["restore", str(target), "0000000000000000000000000000000000000000", "--force"],
    )
    assert result.exit_code == 1, result.output
    assert "Could not restore from commit:" in result.output


def test_restore_dotman_error_uses_exit_code(integration_runner):
    from pathlib import Path
    from unittest.mock import patch as _patch

    from dot_man.exceptions import DotManError

    target = Path.home() / ".restorerc"
    target.write_text("repo v1")

    with _patch(
        "dot_man.operations.get_operations",
        side_effect=DotManError("boom", exit_code=3),
    ):
        result = integration_runner.invoke(
            cli, ["restore", str(target), "abc1234", "--force"]
        )

    assert result.exit_code == 3, result.output
    assert "boom" in result.output


def test_restore_unexpected_error_reported(integration_runner):
    from pathlib import Path
    from unittest.mock import MagicMock
    from unittest.mock import patch as _patch

    target = Path.home() / ".restorerc"
    target.write_text("repo v1")

    fake_ops = MagicMock()
    fake_ops.get_sections.side_effect = ValueError("weird failure")

    with _patch("dot_man.operations.get_operations", return_value=fake_ops):
        result = integration_runner.invoke(
            cli, ["restore", str(target), "abc1234", "--force"]
        )

    assert result.exit_code == 1, result.output
    assert "Unexpected error: weird failure" in result.output
