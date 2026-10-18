"""Tests for verify_cmd.py — repository integrity verification."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_man.cli.verify_cmd import verify


class TestVerify:
    """Test verify command."""

    def test_verify_clean_repo(self, tmp_path):
        """Verify clean repository shows no issues."""
        repo_dir = tmp_path / "repo"
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("{{invalid}}")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        section = MagicMock()
        section.paths = [tmp_path / "nonexistent_file.txt"]
        section.get_repo_path.return_value = tmp_path / "nonexistent_repo.txt"

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        broken_link = tmp_path / "broken_link"
        broken_link.symlink_to(tmp_path / "does_not_exist")

        section = MagicMock()
        section.paths = [broken_link]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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
        (repo_dir / ".git").mkdir(parents=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")

        orphans = [repo_dir / f"orphan{i}.txt" for i in range(15)]

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
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


# ─── coverage floor: symlink order bug, permissions, orphan edge,
#     git dirty details, fixed summary ──────────────────────────────


def _verify_run(tmp_path, section, fix=False, orphans=None, repo_files=None):
    """Common harness: patched ops + CliRunner invocation of verify."""
    repo_dir = tmp_path / "repo"
    (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
    (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")
    if repo_files:
        for rel in repo_files:
            target = repo_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x")

    with (
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
        patch("dot_man.operations.get_operations") as mock_ops,
    ):
        ops = mock_ops.return_value
        ops.get_sections.return_value = ["main"]
        ops.get_section.return_value = section
        ops.git.repo.is_dirty.return_value = False
        ops.get_orphaned_files.return_value = orphans or []

        runner = CliRunner()
        result = runner.invoke(verify, ["--fix"] if fix else [])
        return result, repo_dir


class TestVerifyCoverageFloor:
    def test_broken_symlink_reported_as_broken(self, tmp_path):
        """A broken symlink must say 'Broken symlink', not 'Missing'."""
        broken_link = tmp_path / "broken_link"
        broken_link.symlink_to(tmp_path / "does_not_exist")

        section = MagicMock()
        section.paths = [broken_link]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        result, _ = _verify_run(tmp_path, section)

        assert result.exit_code == 0
        assert "Broken symlink" in result.output
        assert "Missing:" not in result.output

    def test_unreadable_path_reported(self, tmp_path):
        guarded = tmp_path / "guarded.conf"
        guarded.write_text("secret")
        guarded.chmod(0o000)

        section = MagicMock()
        section.paths = [guarded]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        try:
            result, _ = _verify_run(tmp_path, section)
        finally:
            guarded.chmod(0o644)

        assert "Cannot read:" in result.output

    def test_readable_path_prints_success(self, tmp_path):
        good = tmp_path / "good.conf"
        good.write_text("ok")

        section = MagicMock()
        section.paths = [good]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        result, _ = _verify_run(tmp_path, section)

        assert "good.conf" in result.output
        assert "section 'main'" in result.output

    def test_orphan_outside_repo_prints_name(self, tmp_path):
        section = MagicMock()
        section.paths = []
        section.get_repo_path.return_value = tmp_path / "repo_path"

        result, _ = _verify_run(tmp_path, section, orphans=[tmp_path / "outside.txt"])

        assert "outside.txt" in result.output

    def test_no_orphaned_files_message(self, tmp_path):
        section = MagicMock()
        section.paths = []
        section.get_repo_path.return_value = tmp_path / "repo_path"

        result, _ = _verify_run(tmp_path, section)

        assert "No orphaned files" in result.output

    def test_dirty_repo_counts_uncommitted_and_untracked(self, tmp_path):
        """Real git repo: modified tracked file + untracked file."""

        from git import Repo

        section = MagicMock()
        section.paths = []
        section.get_repo_path.return_value = tmp_path / "repo_path"

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(exist_ok=True)
        (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")
        repo = Repo.init(repo_dir)
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "Test")
            cw.set_value("user", "email", "t@t.co")
        (repo_dir / "tracked.txt").write_text("v1")
        repo.index.add(["tracked.txt", "dot-man.toml"])
        repo.index.commit("Initial")

        (repo_dir / "tracked.txt").write_text("v2 modified")
        (repo_dir / "untracked.txt").write_text("new")

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            ops = mock_ops.return_value
            ops.get_sections.return_value = ["main"]
            ops.get_section.return_value = section
            ops.git.repo = repo
            ops.get_orphaned_files.return_value = []

            runner = CliRunner()
            result = runner.invoke(verify, [])

        assert result.exit_code == 0
        assert "1 uncommitted" in result.output
        assert "1 untracked" in result.output

    def test_fix_summary_reports_fixed_count(self, tmp_path):
        missing = tmp_path / "missing.conf"

        section = MagicMock()
        section.paths = [missing]
        section.get_repo_path.return_value = tmp_path / "repo_path"

        with (
            patch("dot_man.constants.REPO_DIR", tmp_path / "repo"),
            patch("dot_man.cli.verify_cmd.DOT_MAN_TOML", "dot-man.toml"),
            patch("dot_man.operations.get_operations") as mock_ops,
        ):
            repo_dir = tmp_path / "repo"
            (repo_dir / ".git").mkdir(parents=True, exist_ok=True)
            (repo_dir / "dot-man.toml").write_text("[main]\npaths = []\n")
            orphan = repo_dir / "orphan.txt"
            orphan.write_text("orphan")

            ops = mock_ops.return_value
            ops.get_sections.return_value = ["main"]
            ops.get_section.return_value = section
            ops.git.repo.is_dirty.return_value = False
            ops.get_orphaned_files.return_value = [orphan]

            def _clean(dry_run=False):
                orphan.unlink()
                return [orphan]

            ops.clean_orphaned_files.side_effect = _clean

            runner = CliRunner()
            result = runner.invoke(verify, ["--fix"])

        assert result.exit_code == 0
        assert "Fixed 1 issue(s)" in result.output
        assert not orphan.exists()
