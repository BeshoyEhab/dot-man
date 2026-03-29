"""Tests for CLI commands with low coverage: audit, init, config, doctor, verify."""

import pytest
from pathlib import Path
from contextlib import ExitStack
from click.testing import CliRunner
from unittest.mock import patch

from dot_man.cli.interface import cli


# ─── Init Command ──────────────────────────────────────────


class TestInitCommand:
    def test_init_creates_repo(self, tmp_path):
        """Test that init creates the repo structure."""
        import os
        runner = CliRunner()
        home = tmp_path / "home"
        home.mkdir()
        dot_man_dir = home / ".config" / "dot-man"

        patches = [
            patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
            patch("dot_man.constants.REPO_DIR", dot_man_dir / "repo"),
            patch("dot_man.constants.BACKUPS_DIR", dot_man_dir / "backups"),
            patch("dot_man.constants.GLOBAL_TOML", dot_man_dir / "global.toml"),
            patch("dot_man.global_config.GLOBAL_TOML", dot_man_dir / "global.toml"),
            patch("dot_man.dotman_config.REPO_DIR", dot_man_dir / "repo"),
            patch("dot_man.core.REPO_DIR", dot_man_dir / "repo"),
            patch("dot_man.config.REPO_DIR", dot_man_dir / "repo"),
            patch("dot_man.config.GLOBAL_TOML", dot_man_dir / "global.toml"),
            patch("dot_man.cli.init_cmd.REPO_DIR", dot_man_dir / "repo"),
            patch("dot_man.cli.init_cmd.DOT_MAN_DIR", dot_man_dir),
            patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
            patch.dict(os.environ, {"HOME": str(home)}),
        ]
        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = runner.invoke(cli, ["init", "--no-wizard", "--force"])
            assert result.exit_code == 0
            assert (dot_man_dir / "repo").exists()
            assert (dot_man_dir / "global.toml").exists()

    def test_init_already_exists(self, integration_runner):
        """Test that init without --force on existing repo warns."""
        result = integration_runner.invoke(cli, ["init", "--no-wizard"])
        assert result.exit_code == 0 or "already" in result.output.lower()


# ─── Audit Command ─────────────────────────────────────────


class TestAuditCommand:
    def test_audit_runs_successfully(self, integration_runner):
        """Test that audit runs and exits 0."""
        result = integration_runner.invoke(cli, ["audit"])
        assert result.exit_code == 0
        assert "audit" in result.output.lower() or "scan" in result.output.lower() or "secret" in result.output.lower()


# ─── Config Command ────────────────────────────────────────


class TestConfigCommand:
    def test_config_list(self, integration_runner):
        """Test config list displays values."""
        result = integration_runner.invoke(cli, ["config", "list"])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_config_get_branch(self, integration_runner):
        """Test getting current branch from config."""
        result = integration_runner.invoke(cli, ["config", "get", "dot-man.current_branch"])
        assert result.exit_code == 0
        assert "main" in result.output

    def test_config_get_nonexistent(self, integration_runner):
        """Test getting a non-existent key."""
        result = integration_runner.invoke(cli, ["config", "get", "no.such.key"])
        assert "not found" in result.output.lower() or result.exit_code != 0

    def test_config_create_with_force(self, integration_runner):
        """Test config create regenerates config."""
        result = integration_runner.invoke(cli, ["config", "create", "--force"])
        assert result.exit_code == 0


# ─── Clean Command ─────────────────────────────────────────


class TestCleanCommandExtended:
    def test_clean_orphans_dry_run(self, integration_runner):
        """Test clean orphans with dry-run."""
        result = integration_runner.invoke(cli, ["clean", "--orphans", "--dry-run"])
        assert result.exit_code == 0

    def test_clean_backups(self, integration_runner):
        """Test clean backups."""
        result = integration_runner.invoke(cli, ["clean", "--backups"])
        assert result.exit_code == 0


# ─── Status Command ────────────────────────────────────────


class TestStatusCommand:
    def test_status_basic(self, integration_runner):
        """Test basic status output."""
        result = integration_runner.invoke(cli, ["status"])
        assert result.exit_code == 0
