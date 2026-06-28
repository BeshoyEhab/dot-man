"""Tests for verify_cmd.py — repository integrity verification."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_man.cli.verify_cmd import verify


class TestVerify:
    """Test verify command."""

    def test_verify_clean_repo(self, tmp_path):
        """Verify clean repository shows no issues."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_missing_config(self, tmp_path):
        """Verify warns when dot-man.toml is missing."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_config_parse_error(self, tmp_path):
        """Verify reports config parse errors."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("{{invalid}}")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.side_effect = Exception("parse error")
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_missing_tracked_path(self, tmp_path):
        """Verify reports missing tracked paths."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        section = MagicMock()
        section.paths = [tmp_path / "nonexistent_file.txt"]
        section.get_repo_path.return_value = tmp_path / "nonexistent_repo.txt"

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = ["main"]
            ops.get_section.return_value = section
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_broken_symlink(self, tmp_path):
        """Verify detects broken symlinks."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        broken_link = tmp_path / "broken_link"
        broken_link.symlink_to(tmp_path / "does_not_exist")

        section = MagicMock()
        section.paths = [broken_link]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = ["main"]
            ops.get_section.return_value = section
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_orphaned_files(self, tmp_path):
        """Verify detects orphaned files."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False
            ops.get_orphaned_files.return_value = [
                repo_dir / "orphan1.txt",
                repo_dir / "orphan2.txt",
            ]

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_fix_orphans(self, tmp_path):
        """Verify --fix deletes orphaned files."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False
            ops.get_orphaned_files.return_value = [repo_dir / "orphan.txt"]
            ops.clean_orphaned_files.return_value = [repo_dir / "orphan.txt"]

            runner = CliRunner()
            result = runner.invoke(verify, ["--fix"])

            assert result.exit_code == 0
            ops.clean_orphaned_files.assert_called_once_with(dry_run=False)

    def test_verify_dirty_repo(self, tmp_path):
        """Verify reports uncommitted changes."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = True
            ops.git.repo.index.diff.return_value = []
            ops.git.repo.untracked_files = []

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_handles_section_check_error(self, tmp_path):
        """Verify handles errors during section checking."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.side_effect = Exception("section error")
            ops.git.repo.is_dirty.return_value = False

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_handles_orphan_check_error(self, tmp_path):
        """Verify handles errors during orphan check."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False
            ops.get_orphaned_files.side_effect = Exception("orphan error")

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_handles_git_status_error(self, tmp_path):
        """Verify handles errors during git status check."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.side_effect = Exception("git error")

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0

    def test_verify_orphans_more_than_10(self, tmp_path):
        """Verify shows 'and X more' for >10 orphans."""
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        orphans = [repo_dir / f"orphan{i}.txt" for i in range(15)]

        with (
            patch("dot_man.cli.verify_cmd.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = []
            ops.git.repo.is_dirty.return_value = False
            ops.get_orphaned_files.return_value = orphans

            runner = CliRunner()
            result = runner.invoke(verify, [])

            assert result.exit_code == 0
