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

    res = integration_runner.invoke(cli, ["switch", "main"]) # Commit initial state
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
    result = integration_runner.invoke(cli, ["clean", "--backups", "--keep", "1", "--force"])
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
    result = integration_runner.invoke(cli, ["add", str(home / "tracked.txt"), "-s", "tracked"], input="y\n")
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
    integration_runner.invoke(cli, ["add", str(home / "data"), "-s", "data"], input="y\n")
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
