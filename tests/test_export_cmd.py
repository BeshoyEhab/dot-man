"""Tests for cli/export_cmd.py — export dotfiles to tar, zip, json."""

import json
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from git import Repo

from dot_man.cli.interface import cli
from dot_man.core import GitManager
from dot_man.section import Section


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def initialized(tmp_path):
    """Pretend dot-man is initialized so require_init passes."""
    dotman_dir = tmp_path / "config"
    dotman_dir.mkdir()
    with patch("dot_man.constants.DOT_MAN_DIR", dotman_dir):
        yield dotman_dir


def _init_empty_repo(tmp_path: Path) -> Path:
    """Create an empty-but-valid repo tree so ``require_init`` passes."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


def _make_repo(tmp_path: Path) -> tuple[Path, GitManager, str]:
    """Create a real repo with a default and a divergent work branch."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")

    (repo_dir / "a.txt").write_text("main-content")
    repo.index.add(["a.txt"])
    repo.index.commit("initial")
    default = repo.active_branch.name

    repo.git.checkout("-b", "work")
    (repo_dir / "a.txt").write_text("work-content")
    repo.index.add(["a.txt"])
    repo.index.commit("work change")
    repo.git.checkout(default)

    return repo_dir, GitManager(repo_dir), default


def _ops_with(gm: GitManager, branch: str = "main") -> MagicMock:
    ops = MagicMock()
    ops.git = gm
    ops.current_branch = branch
    return ops


class TestExportArchive:
    """tar/zip must export the requested branch's committed tree."""

    def test_tar_exports_requested_branch(self, runner, tmp_path, initialized):
        repo_dir, gm, default = _make_repo(tmp_path)
        output = tmp_path / "backup.tar.gz"
        ops = _ops_with(gm)

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", repo_dir),
        ):
            result = runner.invoke(
                cli, ["export", "tar", str(output), "--branch", "work"]
            )

        assert result.exit_code == 0, result.output
        with tarfile.open(output) as tar:
            content = tar.extractfile("dotman-export/a.txt").read().decode()
        assert content == "work-content"

    def test_zip_exports_current_branch_by_default(self, runner, tmp_path, initialized):
        repo_dir, gm, default = _make_repo(tmp_path)
        output = tmp_path / "dots.zip"
        ops = _ops_with(gm, branch=default)

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", repo_dir),
        ):
            result = runner.invoke(cli, ["export", "zip", str(output)])

        assert result.exit_code == 0, result.output
        with zipfile.ZipFile(output) as zipf:
            assert zipf.read("dotman-export/a.txt").decode() == "main-content"

    def test_tar_adds_suffix(self, runner, tmp_path, initialized):
        repo_dir, gm, default = _make_repo(tmp_path)
        ops = _ops_with(gm, branch=default)

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", repo_dir),
        ):
            result = runner.invoke(cli, ["export", "tar", str(tmp_path / "backup")])

        assert result.exit_code == 0, result.output
        assert (tmp_path / "backup.tar.gz").exists()

    def test_archive_error_handling(self, runner, tmp_path, initialized):
        ops = MagicMock()
        ops.current_branch = "main"
        ops.git.repo.git.archive.side_effect = OSError("disk full")

        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(
                cli, ["export", "tar", str(tmp_path / "backup.tar.gz")]
            )

        assert result.exit_code == 1


class TestExportJson:
    """JSON manifest contents and metadata."""

    def test_manifest_has_iso_timestamp_and_repo_path(
        self, runner, tmp_path, initialized
    ):
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("export EDITOR=vim")

        section = Section(name="shell", paths=[str(bashrc)], repo_base="shell")
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = ["shell"]
        ops.get_section.return_value = section

        output = tmp_path / "manifest.json"
        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", _init_empty_repo(tmp_path)),
        ):
            result = runner.invoke(cli, ["export", "json", str(output)])

        assert result.exit_code == 0, result.output
        data = json.loads(output.read_text())
        assert data["branch"] == "main"
        # Real ISO-8601 timestamp, not a path.
        datetime.fromisoformat(data["exported_at"])
        assert data["files"][0]["repo_path"] == "shell/.bashrc"

    def test_no_content_without_include_secrets(self, runner, tmp_path, initialized):
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("secret")

        section = Section(name="shell", paths=[str(bashrc)], repo_base="shell")
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = ["shell"]
        ops.get_section.return_value = section

        output = tmp_path / "manifest.json"
        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", _init_empty_repo(tmp_path)),
        ):
            runner.invoke(cli, ["export", "json", str(output)])

        data = json.loads(output.read_text())
        assert "content" not in data["files"][0]

    def test_include_secrets_embeds_content_and_is_private(
        self, runner, tmp_path, initialized
    ):
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("export EDITOR=vim")

        section = Section(name="shell", paths=[str(bashrc)], repo_base="shell")
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = ["shell"]
        ops.get_section.return_value = section

        output = tmp_path / "manifest.json"
        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("dot_man.constants.REPO_DIR", _init_empty_repo(tmp_path)),
        ):
            result = runner.invoke(
                cli, ["export", "json", str(output), "--include-secrets"]
            )

        assert result.exit_code == 0, result.output
        data = json.loads(output.read_text())
        assert data["files"][0]["content"] == "export EDITOR=vim"
        assert (output.stat().st_mode & 0o777) == 0o600

    def test_json_adds_suffix(self, runner, tmp_path, initialized):
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = []

        with patch("dot_man.operations.get_operations", return_value=ops):
            result = runner.invoke(cli, ["export", "json", str(tmp_path / "manifest")])

        assert result.exit_code == 0, result.output
        assert (tmp_path / "manifest.json").exists()

    def test_json_write_error(self, runner, tmp_path, initialized):
        ops = MagicMock()
        ops.current_branch = "main"
        ops.get_sections.return_value = []

        with (
            patch("dot_man.operations.get_operations", return_value=ops),
            patch("pathlib.Path.write_text", side_effect=OSError("read only")),
        ):
            result = runner.invoke(
                cli, ["export", "json", str(tmp_path / "manifest.json")]
            )

        assert result.exit_code == 1


def test_invalid_format_rejected(runner):
    result = runner.invoke(cli, ["export", "xml", "output.xml"])
    assert result.exit_code != 0
