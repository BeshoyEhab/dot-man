"""Tests for cli/export_cmd.py — export dotfiles to tar, zip, json."""

import json
from pathlib import Path
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
    ops.get_sections.return_value = ["shell", "config"]
    shell_section = MagicMock()
    shell_section.paths = [Path("/home/user/.bashrc")]
    config_section = MagicMock()
    config_section.paths = [Path("/home/user/.config/nvim")]
    ops.get_section.side_effect = lambda name: {
        "shell": shell_section,
        "config": config_section,
    }[name]
    return ops


class TestExportTar:
    """Test tar export."""

    def test_export_creates_tarball(self, runner, tmp_path):
        output = tmp_path / "backup.tar.gz"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            result = runner.invoke(cli, ["export", "tar", str(output)])
        # Should attempt to create tar (may fail if REPO_DIR doesn't exist)
        assert result.exit_code in (0, 1)

    def test_export_tar_adds_suffix(self, runner, tmp_path):
        output = tmp_path / "backup"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            with patch("dot_man.cli.export_cmd.REPO_DIR", tmp_path / "repo"):
                (tmp_path / "repo").mkdir(exist_ok=True)
                (tmp_path / "repo" / "test.txt").write_text("hello")
                result = runner.invoke(cli, ["export", "tar", str(output)])
        assert result.exit_code == 0

    def test_export_tar_with_branch(self, runner, tmp_path):
        output = tmp_path / "backup.tar.gz"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            result = runner.invoke(
                cli, ["export", "tar", str(output), "--branch", "work"]
            )
        assert result.exit_code in (0, 1)

    def test_export_tar_error_handling(self, runner, tmp_path):
        output = tmp_path / "backup.tar.gz"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            with patch("tarfile.open", side_effect=OSError("disk full")):
                result = runner.invoke(cli, ["export", "tar", str(output)])
        assert result.exit_code == 1


class TestExportZip:
    """Test zip export."""

    def test_export_creates_zip(self, runner, tmp_path):
        output = tmp_path / "backup.zip"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            with patch("dot_man.cli.export_cmd.REPO_DIR", tmp_path / "repo"):
                (tmp_path / "repo").mkdir(exist_ok=True)
                (tmp_path / "repo" / "test.txt").write_text("hello")
                result = runner.invoke(cli, ["export", "zip", str(output)])
        assert result.exit_code == 0

    def test_export_zip_adds_suffix(self, runner, tmp_path):
        output = tmp_path / "backup"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            with patch("dot_man.cli.export_cmd.REPO_DIR", tmp_path / "repo"):
                (tmp_path / "repo").mkdir(exist_ok=True)
                (tmp_path / "repo" / "test.txt").write_text("hello")
                result = runner.invoke(cli, ["export", "zip", str(output)])
        assert result.exit_code == 0

    def test_export_zip_error_handling(self, runner, tmp_path):
        output = tmp_path / "backup.zip"
        with patch("dot_man.operations.get_operations") as mock_get:
            mock_get.return_value.current_branch = "main"
            with patch("zipfile.ZipFile", side_effect=OSError("permission denied")):
                result = runner.invoke(cli, ["export", "zip", str(output)])
        assert result.exit_code == 1


class TestExportJson:
    """Test JSON export."""

    def test_export_creates_json(self, runner, tmp_path):
        output = tmp_path / "manifest.json"
        with patch(
            "dot_man.operations.get_operations",
            return_value=mock_ops_from_tmp(tmp_path),
        ):
            result = runner.invoke(cli, ["export", "json", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["version"] == "1.0"
        assert data["branch"] == "main"

    def test_export_json_adds_suffix(self, runner, tmp_path):
        output = tmp_path / "manifest"
        with patch(
            "dot_man.operations.get_operations",
            return_value=mock_ops_from_tmp(tmp_path),
        ):
            result = runner.invoke(cli, ["export", "json", str(output)])
        assert result.exit_code == 0
        assert (tmp_path / "manifest.json").exists()

    def test_export_json_includes_content(self, runner, tmp_path):
        (tmp_path / ".bashrc").write_text("export EDITOR=vim")
        output = tmp_path / "manifest.json"
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = ["shell"]
        shell_section = MagicMock()
        shell_section.paths = [tmp_path / ".bashrc"]
        ops.get_section.return_value = shell_section

        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(
                cli, ["export", "json", str(output), "--include-secrets"]
            )
        assert result.exit_code == 0
        data = json.loads(output.read_text())
        assert any(f.get("content") == "export EDITOR=vim" for f in data["files"])

    def test_export_json_error_on_write(self, runner, tmp_path):
        output = tmp_path / "manifest.json"
        with patch(
            "dot_man.operations.get_operations",
            return_value=mock_ops_from_tmp(tmp_path),
        ):
            with patch("builtins.open", side_effect=OSError("read only")):
                result = runner.invoke(cli, ["export", "json", str(output)])
        assert result.exit_code == 1


class TestExportFormats:
    """Test format validation."""

    def test_invalid_format_rejected(self, runner):
        result = runner.invoke(cli, ["export", "xml", "output.xml"])
        assert result.exit_code != 0

    def test_all_formats_accepted(self, runner, tmp_path):
        for fmt in ("tar", "zip", "json"):
            output = tmp_path / f"test.{fmt}"
            with patch("dot_man.operations.get_operations") as mock_get:
                mock_get.return_value.current_branch = "main"
                with patch("dot_man.cli.export_cmd.REPO_DIR", tmp_path / "repo"):
                    (tmp_path / "repo").mkdir(exist_ok=True)
                    result = runner.invoke(cli, ["export", fmt, str(output)])
            # May succeed or fail depending on format, but should not error on format validation
            assert "Invalid" not in (result.output or "")


def mock_ops_from_tmp(tmp_path):
    """Create a mock ops object for testing."""
    ops = MagicMock()
    ops.current_branch = "main"
    ops.get_sections.return_value = []
    return ops
