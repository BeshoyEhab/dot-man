"""Tests for dot_man.operations DotManOperations."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from dot_man.operations import DotManOperations


@pytest.fixture
def ops_env(tmp_path):
    """Set up a fully isolated DotManOperations environment."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    dot_man_dir.mkdir(parents=True)
    repo_dir.mkdir()
    backups_dir.mkdir()

    # Init a real git repo
    from git import Repo

    repo = Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Tester")
        config.set_value("user", "email", "test@test.com")

    # Create initial commit
    (repo_dir / ".gitignore").write_text("*.pyc\n")
    repo.index.add([".gitignore"])
    repo.index.commit("Initial commit")

    # Create global config
    global_toml.write_text(
        '[global]\ncurrent_branch = "main"\nremote_url = ""\nstrict_mode = false\n'
    )

    # Create a sample tracked file
    tracked_file = home / "myconfig.conf"
    tracked_file.write_text("key = value\n")

    # Create dot-man.toml with a section
    toml_content = f"""
[myconfig]
paths = ["{tracked_file}"]
"""
    (repo_dir / "dot-man.toml").write_text(toml_content)
    repo.index.add(["dot-man.toml"])
    repo.index.commit("Add config")

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
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.backups.DOT_MAN_DIR", dot_man_dir),
    ]

    for p in patches:
        p.start()

    ops = DotManOperations()

    yield {
        "ops": ops,
        "home": home,
        "repo_dir": repo_dir,
        "dot_man_dir": dot_man_dir,
        "tracked_file": tracked_file,
    }

    for p in patches:
        p.stop()


class TestDotManOperationsProperties:
    """Tests for lazy-loaded properties."""

    def test_global_config_loads(self, ops_env):
        ops = ops_env["ops"]
        gc = ops.global_config
        assert gc is not None

    def test_dotman_config_loads(self, ops_env):
        ops = ops_env["ops"]
        dc = ops.dotman_config
        assert dc is not None

    def test_git_loads(self, ops_env):
        ops = ops_env["ops"]
        assert ops.git is not None

    def test_vault_loads(self, ops_env):
        ops = ops_env["ops"]
        assert ops.vault is not None

    def test_backups_loads(self, ops_env):
        ops = ops_env["ops"]
        assert ops.backups is not None

    def test_current_branch(self, ops_env):
        ops = ops_env["ops"]
        assert ops.current_branch == "main"

    def test_reload_config(self, ops_env):
        ops = ops_env["ops"]
        _ = ops.dotman_config  # force load
        ops.reload_config()
        # Should reload cleanly
        _ = ops.dotman_config


class TestSections:
    """Tests for section operations."""

    def test_get_sections(self, ops_env):
        ops = ops_env["ops"]
        sections = ops.get_sections()
        assert "myconfig" in sections

    def test_get_section(self, ops_env):
        ops = ops_env["ops"]
        section = ops.get_section("myconfig")
        assert section is not None
        assert len(section.paths) >= 1


class TestSaveSection:
    """Tests for save operations."""

    def test_save_section(self, ops_env):
        ops = ops_env["ops"]
        section = ops.get_section("myconfig")
        saved, secrets, errors = ops.save_section(section)
        assert saved >= 1
        assert isinstance(secrets, list)
        assert isinstance(errors, list)

    def test_save_section_missing_file(self, ops_env):
        ops = ops_env["ops"]
        section = ops.get_section("myconfig")
        # Delete the tracked file
        ops_env["tracked_file"].unlink()
        saved, secrets, errors = ops.save_section(section)
        assert saved == 0


class TestDeploySection:
    """Tests for deploy operations."""

    def test_deploy_section(self, ops_env):
        ops = ops_env["ops"]
        section = ops.get_section("myconfig")
        # First save to repo
        ops.save_section(section)
        ops.git.commit("Save for deploy")
        # Now modify local to detect change
        ops_env["tracked_file"].write_text("modified content")
        # Deploy should restore from repo
        deployed, had_changes, errors = ops.deploy_section(section)
        assert deployed >= 0
        assert isinstance(errors, list)


class TestSaveAll:
    """Tests for save_all."""

    def test_save_all(self, ops_env):
        ops = ops_env["ops"]
        result = ops.save_all()
        assert "saved" in result
        assert "secrets" in result
        assert "errors" in result
        assert result["saved"] >= 1


class TestDeployAll:
    """Tests for deploy_all."""

    def test_deploy_all(self, ops_env):
        ops = ops_env["ops"]
        # Save first
        ops.save_all()
        ops.git.commit("Before deploy")
        result = ops.deploy_all()
        assert "deployed" in result
        assert "errors" in result


class TestStatusSummary:
    """Tests for status summary."""

    def test_get_status_summary(self, ops_env):
        ops = ops_env["ops"]
        summary = ops.get_status_summary()
        assert "branch" in summary
        assert "sections" in summary
        assert "total_paths" in summary
        assert summary["branch"] == "main"

    def test_get_detailed_status(self, ops_env):
        ops = ops_env["ops"]
        items = list(ops.get_detailed_status())
        assert len(items) >= 1
        for item in items:
            assert "section" in item
            assert "status" in item
            assert "local_path" in item


class TestOrphanedFiles:
    """Tests for orphaned file detection and cleanup."""

    def test_get_orphaned_files_empty(self, ops_env):
        ops = ops_env["ops"]
        # Save tracked file first
        ops.save_all()
        ops.git.commit("Save tracked")
        orphans = ops.get_orphaned_files()
        # dot-man.toml and .gitignore are internal, should not appear
        assert all("dot-man.toml" not in str(p) for p in orphans)

    def test_get_orphaned_files_detects_orphan(self, ops_env):
        ops = ops_env["ops"]
        repo_dir = ops_env["repo_dir"]
        # Create an actual orphan
        (repo_dir / "stray_file.txt").write_text("I am lost")
        orphans = ops.get_orphaned_files()
        orphan_names = [p.name for p in orphans]
        assert "stray_file.txt" in orphan_names

    def test_clean_orphaned_files_dry_run(self, ops_env):
        ops = ops_env["ops"]
        repo_dir = ops_env["repo_dir"]
        (repo_dir / "orphan.txt").write_text("orphan")
        result = ops.clean_orphaned_files(dry_run=True)
        assert len(result) >= 1
        # File should still exist (dry run)
        assert (repo_dir / "orphan.txt").exists()

    def test_clean_orphaned_files_real(self, ops_env):
        ops = ops_env["ops"]
        repo_dir = ops_env["repo_dir"]
        (repo_dir / "orphan.txt").write_text("orphan")
        result = ops.clean_orphaned_files(dry_run=False)
        assert len(result) >= 1
        assert not (repo_dir / "orphan.txt").exists()


class TestMatchesPatterns:
    """Tests for pattern matching."""

    def test_matches_glob(self, ops_env):
        ops = ops_env["ops"]
        assert ops._matches_patterns(Path("test.pyc"), ["*.pyc"]) is True
        assert ops._matches_patterns(Path("test.py"), ["*.pyc"]) is False

    def test_matches_directory_pattern(self, ops_env):
        ops = ops_env["ops"]
        assert ops._matches_patterns(Path("node_modules"), ["node_modules"]) is True

    def test_no_patterns(self, ops_env):
        ops = ops_env["ops"]
        assert ops._matches_patterns(Path("anything"), []) is False


class TestRestoreFileSecrets:
    """Tests for the shared _restore_file_secrets helper."""

    def test_skips_binary(self, ops_env):
        ops = ops_env["ops"]
        result = ops._restore_file_secrets(
            Path("/fake/file.jpg"), "/original", "main"
        )
        assert result is None

    def test_skips_various_binary_extensions(self, ops_env):
        ops = ops_env["ops"]
        for ext in [".png", ".pdf", ".zip", ".exe", ".woff2"]:
            result = ops._restore_file_secrets(
                Path(f"/fake/file{ext}"), "/original", "main"
            )
            assert result is None

    def test_handles_nonexistent_file(self, ops_env):
        ops = ops_env["ops"]
        result = ops._restore_file_secrets(
            Path("/nonexistent/file.txt"), "/original", "main"
        )
        # Should return an error string
        assert result is not None
        assert "Failed to restore" in result

    def test_handles_text_file(self, ops_env):
        ops = ops_env["ops"]
        # Create a real text file
        test_file = ops_env["home"] / "test_restore.txt"
        test_file.write_text("no secrets here")
        result = ops._restore_file_secrets(
            test_file, str(test_file), "main"
        )
        assert result is None  # No error
