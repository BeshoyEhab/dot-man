"""Tests for tag_cmd.py — tag create, list, delete, switch commands."""

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.tag_cmd import tag


def _mock_init():
    """Return context managers for requiring init."""
    return (
        patch("dot_man.cli.common.DOT_MAN_DIR"),
        patch("dot_man.operations.get_operations"),
    )


class TestTagList:
    """Test tag list subcommand."""

    def test_list_no_tags(self):
        """List tags when none exist."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.list_tags.return_value = []

            runner = CliRunner()
            result = runner.invoke(tag, ["list"])

            assert result.exit_code == 0

    def test_list_with_tags(self):
        """List tags shows each tag with commit SHA."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.list_tags.return_value = ["v1.0", "v2.0"]
            ops.git.get_tag_commit.side_effect = lambda t: "abc1234" if t else None

            runner = CliRunner()
            result = runner.invoke(tag, ["list"])

            assert result.exit_code == 0

    def test_list_handles_exception(self):
        """List tags handles errors gracefully (exits with code 1, not crash)."""
        with patch(
            "dot_man.operations.get_operations", side_effect=Exception("repo not found")
        ):
            runner = CliRunner()
            result = runner.invoke(tag, ["list"])

            assert result.exit_code == 1


class TestTagCreate:
    """Test tag create subcommand."""

    def test_create_at_head(self):
        """Create tag at HEAD."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            commit_obj = type("Commit", (), {"hexsha": "abc123" * 7})()
            ops.git.repo.commit.return_value = commit_obj

            runner = CliRunner()
            result = runner.invoke(tag, ["create", "my-tag"])

            assert result.exit_code == 0

    def test_create_annotated_tag(self):
        """Create annotated tag with message."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            commit_obj = type("Commit", (), {"hexsha": "abc123" * 7})()
            ops.git.repo.commit.return_value = commit_obj

            runner = CliRunner()
            result = runner.invoke(tag, ["create", "v1", "-m", "Release v1"])

            assert result.exit_code == 0

    def test_create_invalid_commit(self):
        """Create tag with invalid commit fails."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.repo.commit.side_effect = Exception("bad commit")

            runner = CliRunner()
            result = runner.invoke(tag, ["create", "my-tag", "badsha"])

            assert result.exit_code == 1

    def test_create_handles_exception(self):
        """Create tag handles errors."""
        with patch(
            "dot_man.operations.get_operations", side_effect=Exception("repo error")
        ):
            runner = CliRunner()
            result = runner.invoke(tag, ["create", "my-tag"])

            assert result.exit_code == 1


class TestTagDelete:
    """Test tag delete subcommand."""

    def test_delete_with_force(self):
        """Delete tag with --force skips confirmation."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.list_tags.return_value = ["old-tag"]

            runner = CliRunner()
            result = runner.invoke(tag, ["delete", "old-tag", "--force"])

            assert result.exit_code == 0

    def test_delete_not_found(self):
        """Delete tag that doesn't exist fails."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.list_tags.return_value = []

            runner = CliRunner()
            result = runner.invoke(tag, ["delete", "missing", "--force"])

            assert result.exit_code == 1

    def test_delete_handles_exception(self):
        """Delete tag handles errors."""
        with patch("dot_man.operations.get_operations", side_effect=Exception("error")):
            runner = CliRunner()
            result = runner.invoke(tag, ["delete", "tag", "--force"])

            assert result.exit_code == 1


class TestTagSwitch:
    """Test tag switch subcommand."""

    def test_switch_to_tag(self):
        """Switch to a valid tag."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.get_tag_commit.return_value = "abc1234"

            runner = CliRunner()
            result = runner.invoke(tag, ["switch", "v1.0"])

            assert result.exit_code == 0

    def test_switch_tag_not_found(self):
        """Switch to non-existent tag fails."""
        with (
            patch("dot_man.cli.common.DOT_MAN_DIR") as mock_dir,
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            mock_dir.exists.return_value = True
            ops = mock_ops.return_value
            ops.git.get_tag_commit.return_value = None

            runner = CliRunner()
            result = runner.invoke(tag, ["switch", "missing"])

            assert result.exit_code == 1

    def test_switch_handles_exception(self):
        """Switch tag handles errors."""
        with patch("dot_man.operations.get_operations", side_effect=Exception("error")):
            runner = CliRunner()
            result = runner.invoke(tag, ["switch", "v1"])

            assert result.exit_code == 1
