"""Tests for 'dot-man clean' command."""

from pathlib import Path

from dot_man.cli.interface import cli


def test_clean_backups(integration_runner):
    """Test cleaning backups."""
    from dot_man.operations import reset_operations

    # Create some dummy backups
    # We need to create some tracked files first to backup
    home = Path.home()
    (home / "testfile").write_text("data")

    res = integration_runner.invoke(cli, ["add", str(home / "testfile")], input="y\n")
    assert res.exit_code == 0
    reset_operations()

    res = integration_runner.invoke(cli, ["switch", "main"])  # Commit initial state
    reset_operations()

    integration_runner.invoke(cli, ["backup", "create", "b1"])
    reset_operations()

    integration_runner.invoke(cli, ["backup", "create", "b2"])
    reset_operations()
    integration_runner.invoke(cli, ["backup", "create", "b3"])
    reset_operations()

    # Check list
    result = integration_runner.invoke(cli, ["backup", "list"])
    assert "b1" in result.output
    assert "b3" in result.output
    reset_operations()

    # Clean keeping 1
    result = integration_runner.invoke(
        cli, ["clean", "--backups", "--keep", "1", "--force"]
    )
    assert result.exit_code == 0
    # Rich wraps text, so check substring without looking for newline match exactly
    assert "Deleted 2 old" in result.output
    assert "backups" in result.output

    # Verify only 1 left (b3 is newest)
    result = integration_runner.invoke(cli, ["backup", "list"])
    assert "b3" in result.output
    assert "b1" not in result.output
    assert "b2" not in result.output


def test_clean_orphans(integration_runner):
    from dot_man.constants import REPO_DIR
    from dot_man.operations import reset_operations

    # Create a tracked file
    home = Path.home()
    (home / "tracked.txt").write_text("tracked content")

    # Use explicit section name to know repo path
    result = integration_runner.invoke(
        cli, ["add", str(home / "tracked.txt"), "-s", "tracked"], input="y\n"
    )
    assert result.exit_code == 0
    reset_operations()

    integration_runner.invoke(cli, ["switch", "main"])
    reset_operations()

    # Create an orphaned file in repo manually
    repo_dir = REPO_DIR
    (repo_dir / "orphan.txt").write_text("I am lost")
    (repo_dir / "orphan_dir").mkdir()
    (repo_dir / "orphan_dir" / "lost.txt").write_text("lost inside")

    # Verify tracked exists
    # With section "tracked", path is repo/tracked/tracked.txt
    assert (repo_dir / "tracked" / "tracked.txt").exists()

    # Dry run
    result = integration_runner.invoke(cli, ["clean", "--orphans", "--dry-run"])
    assert result.exit_code == 0
    assert "orphan.txt" in result.output
    assert "orphan_dir/lost.txt" in result.output or "lost.txt" in result.output
    assert "tracked.txt" not in result.output  # Should not list tracked file

    # Real run
    result = integration_runner.invoke(cli, ["clean", "--orphans", "--force"])
    assert result.exit_code == 0
    assert "Deleted" in result.output

    assert not (repo_dir / "orphan.txt").exists()
    assert (repo_dir / "tracked" / "tracked.txt").exists()

    # Check if empty dir removed
    assert not (repo_dir / "orphan_dir").exists()


def test_clean_all(integration_runner):
    """Test cleaning both orphans and backups."""
    from dot_man.operations import reset_operations

    home = Path.home()
    (home / "data").write_text("data")
    integration_runner.invoke(
        cli, ["add", str(home / "data"), "-s", "data"], input="y\n"
    )
    reset_operations()
    integration_runner.invoke(cli, ["switch", "main"])
    reset_operations()

    # Backup
    integration_runner.invoke(cli, ["backup", "create", "b1"])
    reset_operations()

    # Orphan
    from dot_man.constants import REPO_DIR

    (REPO_DIR / "orphan.txt").touch()

    result = integration_runner.invoke(cli, ["clean", "--all", "--force"])
    assert result.exit_code == 0
    assert "Deleted 1 old" in result.output
    assert "Deleted 1 orphaned" in result.output


# ---------------------------------------------------------------------------
# Coverage floor: dry-run previews, delete failures, error handler
# ---------------------------------------------------------------------------


def _make_backups(runner, ids):
    """Tracked file + initial state + one backup per id (existing pattern)."""
    from dot_man.operations import reset_operations

    home = Path.home()
    (home / "baketest").write_text("data")
    res = runner.invoke(cli, ["add", str(home / "baketest"), "-s", "baketest"])
    assert res.exit_code == 0, res.output
    reset_operations()

    res = runner.invoke(cli, ["switch", "main"])
    reset_operations()

    for backup_id in ids:
        res = runner.invoke(cli, ["backup", "create", backup_id])
        assert res.exit_code == 0, res.output
        reset_operations()


def test_clean_backups_dry_run_previews_and_keeps(integration_runner):
    """Dry-run lists deletable backups and skips when nothing exceeds keep."""
    _make_backups(integration_runner, ["b1", "b2", "b3"])

    result = integration_runner.invoke(
        cli, ["clean", "--backups", "--dry-run", "--keep", "1"]
    )
    assert result.exit_code == 0, result.output
    assert "Backups to be deleted (2):" in result.output

    # Nothing was actually deleted
    listing = integration_runner.invoke(cli, ["backup", "list"])
    assert "b1" in listing.output

    result = integration_runner.invoke(
        cli, ["clean", "--backups", "--dry-run", "--keep", "5"]
    )
    assert result.exit_code == 0, result.output
    assert "No backups to clean." in result.output


def test_clean_backups_delete_failure_reports_none(integration_runner, tmp_path):
    """clean_backups returning 0 despite eligible backups -> info message."""
    from unittest.mock import patch as _patch

    _make_backups(integration_runner, ["b1", "b2"])

    with _patch("dot_man.backups.shutil.rmtree", side_effect=OSError("backups locked")):
        result = integration_runner.invoke(
            cli, ["clean", "--backups", "--keep", "1", "--force"]
        )

    assert result.exit_code == 0, result.output
    assert "No backups cleaned." in result.output
    listing = integration_runner.invoke(cli, ["backup", "list"])
    assert "b1" in listing.output


def test_clean_exception_reported(integration_runner):
    from unittest.mock import patch as _patch

    with _patch(
        "dot_man.operations.get_operations", side_effect=Exception("clean boom")
    ):
        result = integration_runner.invoke(cli, ["clean", "--backups", "--force"])

    assert result.exit_code == 1, result.output
    assert "Failed to clean: clean boom" in result.output
