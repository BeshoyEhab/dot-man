"""Tests for git-history secret scanning (S8)."""

import os
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from git import Repo

from dot_man.secrets import SecretScanner


@pytest.fixture
def runner_with_home(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), repo_dir


def _init_repo(path):
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")
    return repo


class TestScanGitHistory:
    def test_finds_committed_then_removed_secret(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = _init_repo(repo_dir)
        secret_file = repo_dir / "creds.txt"
        secret_file.write_text("aws = AKIA1234567890ABCDEF\n")
        repo.index.add(["creds.txt"])
        repo.index.commit("add secret")
        secret_file.unlink()
        repo.index.remove(["creds.txt"])
        repo.index.commit("remove secret")

        scanner = SecretScanner()
        matches = list(scanner.scan_git_history(repo))

        assert any(m.matched_text == "AKIA1234567890ABCDEF" for m in matches)
        history = [m for m in matches if m.history_ref]
        assert history and history[0].file == Path("creds.txt")
        # The working tree is clean, so a directory scan must find nothing.
        assert list(scanner.scan_directory(repo_dir)) == []

    def test_finds_staged_but_uncommitted_secret(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = _init_repo(repo_dir)
        (repo_dir / ".gitkeep").write_text("")
        repo.index.add([".gitkeep"])
        repo.index.commit("init")

        staged = repo_dir / "staged.txt"
        staged.write_text("key = AKIA1234567890ABCDEF\n")
        repo.index.add(["staged.txt"])

        scanner = SecretScanner()
        matches = list(scanner.scan_git_history(repo))

        assert any(
            m.matched_text == "AKIA1234567890ABCDEF" and m.history_ref == "index"
            for m in matches
        )

    def test_no_matches_in_clean_history(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo = _init_repo(repo_dir)
        (repo_dir / "readme.txt").write_text("nothing sensitive here\n")
        repo.index.add(["readme.txt"])
        repo.index.commit("init")

        scanner = SecretScanner()
        assert list(scanner.scan_git_history(repo)) == []


class TestAuditHistoryOption:
    def test_help_lists_history(self, runner_with_home):
        from dot_man.cli.interface import cli

        runner, _ = runner_with_home
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0
        assert "--history" in result.output
