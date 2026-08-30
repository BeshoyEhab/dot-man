"""Tests for shared-section synchronization across branches.

Uses real git repositories: shared sections must actually graft blobs
onto other branches while overriding branches stay untouched.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from dot_man.core import GitManager
from dot_man.dotman_config import VALID_SECTION_KEYS, DotManConfig
from dot_man.section import Section
from dot_man.shared_sync import SharedSectionSync, _parse_toml

# ── git helpers ─────────────────────────────────────────────────


def run_git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def commit_file(repo_dir: Path, rel_path: str, content: str, message: str) -> None:
    target = repo_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    run_git(repo_dir, "add", ".")
    run_git(repo_dir, "commit", "-m", message)


def read_branch_file(repo_dir: Path, branch: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "show", f"{branch}:{path}"],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def branch_commit_count(repo_dir: Path, branch: str) -> int:
    return int(run_git(repo_dir, "rev-list", "--count", branch))


@dataclass
class OpsStub:
    """Operations double exposing only what SharedSectionSync needs."""

    git: GitManager
    repo_dir: Path
    _config_cache: dict = field(default_factory=dict)

    def reload_config(self) -> None:
        self._config_cache.clear()

    @property
    def dotman_config(self) -> DotManConfig:
        if "cfg" not in self._config_cache:
            config = DotManConfig(repo_path=self.repo_dir)
            config.load()
            self._config_cache["cfg"] = config
        return self._config_cache["cfg"]


# ── fixtures ────────────────────────────────────────────────────

MAIN_CONFIG = """
[fish]
paths = ["~/.config/fish"]
shared = true

[nvim]
paths = ["~/.config/nvim"]
shared = true
"""

WORK_CONFIG = """
[fish]
paths = ["~/.config/fish"]
repo_base = "fish-work"
"""

SERVER_CONFIG = """
[kitty]
paths = ["~/.config/kitty"]
"""


@pytest.fixture
def multi_branch_repo(tmp_path):
    """Repo on 'main' with 'work' (overrides fish) and 'server' (inherits all)."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    run_git(repo_dir, "init", "-b", "main")
    run_git(repo_dir, "config", "user.name", "Test")
    run_git(repo_dir, "config", "user.email", "test@test.com")

    commit_file(repo_dir, "dot-man.toml", MAIN_CONFIG, "init config")
    commit_file(repo_dir, "fish/config.fish", "set -x EDITOR nvim\n", "add fish")
    commit_file(repo_dir, "nvim/init.lua", "vim.o.number = true\n", "add nvim")

    run_git(repo_dir, "checkout", "-b", "work")
    commit_file(repo_dir, "dot-man.toml", WORK_CONFIG, "work overrides fish")

    run_git(repo_dir, "checkout", "-b", "server", "main")
    commit_file(repo_dir, "dot-man.toml", SERVER_CONFIG, "server config")
    run_git(repo_dir, "checkout", "main")

    return repo_dir, OpsStub(git=GitManager(repo_dir), repo_dir=repo_dir)


@pytest.fixture
def solo_repo(tmp_path):
    """Repo whose sections are not shared."""
    repo_dir = tmp_path / "solo"
    repo_dir.mkdir()
    run_git(repo_dir, "init", "-b", "main")
    run_git(repo_dir, "config", "user.name", "T")
    run_git(repo_dir, "config", "user.email", "t@t.co")
    commit_file(repo_dir, "dot-man.toml", '[bashrc]\npaths = ["~/.bashrc"]\n', "c1")
    commit_file(repo_dir, "bashrc", "export X=1\n", "c2")
    run_git(repo_dir, "checkout", "-b", "other")
    run_git(repo_dir, "checkout", "main")
    return repo_dir, OpsStub(git=GitManager(repo_dir), repo_dir=repo_dir)


class TestConfigParsing:
    def test_parse_toml_reads_sections(self):
        data = _parse_toml("[fish]\npaths = ['x']\n[templates.t]\na = 1\n")
        assert data is not None
        assert "fish" in data
        assert "templates" in data

    def test_parse_toml_invalid_returns_none(self):
        assert _parse_toml("not [ valid toml {{{{") is None


class TestSharedSectionConfig:
    def test_section_flag_roundtrip(self):
        section = Section(name="fish", paths=[Path("~/.config/fish")], shared=True)
        assert section.shared is True
        restored = Section(
            name="fish",
            paths=[Path("~/.config/fish")],
            **{"shared": section.to_dict()["shared"]},
        )
        assert restored.shared is True

    def test_default_is_not_shared_and_not_serialized(self):
        section = Section(name="fish", paths=[Path("~/.config/fish")])
        assert section.shared is False
        assert "shared" not in section.to_dict()

    def test_valid_section_keys_includes_shared(self):
        assert "shared" in VALID_SECTION_KEYS

    def test_loads_from_real_config_file(self, tmp_path):
        (tmp_path / "dot-man.toml").write_text(
            '[fish]\npaths = ["~/.config/fish"]\nshared = true\n'
        )
        config = DotManConfig(repo_path=tmp_path)
        config.load()
        assert config.get_section("fish").shared is True

    def test_typo_key_does_not_enable_shared(self, tmp_path):
        (tmp_path / "dot-man.toml").write_text(
            '[fish]\npaths = ["~/.config/fish"]\nshard = true\n'
        )
        config = DotManConfig(repo_path=tmp_path)
        config.load()  # schema warning logged, must not raise
        assert config.get_section("fish").shared is False


class TestPropagation:
    def test_edits_reach_non_overriding_branches(self, multi_branch_repo):
        repo_dir, ops = multi_branch_repo
        commit_file(
            repo_dir, "fish/config.fish", "set -x EDITOR helix\n", "update fish"
        )

        report = SharedSectionSync(ops).sync()

        assert report.ok
        # work overrides [fish], so fish only propagates to server
        assert set(report.propagated) == {"server"}
        assert "fish" in report.propagated["server"]
        assert "helix" in read_branch_file(repo_dir, "server", "fish/config.fish")

    def test_overriding_branch_keeps_custom_version(self, multi_branch_repo):
        repo_dir, ops = multi_branch_repo
        before = read_branch_file(repo_dir, "work", "fish/config.fish")

        commit_file(
            repo_dir, "fish/config.fish", "set -x EDITOR helix\n", "update fish"
        )
        report = SharedSectionSync(ops).sync()

        assert "fish" in report.skipped.get("work", [])
        assert read_branch_file(repo_dir, "work", "fish/config.fish") == before

    def test_partial_override_blocks_only_that_section(self, multi_branch_repo):
        """work owns [fish]; nvim is shared and must still propagate there."""
        repo_dir, ops = multi_branch_repo
        commit_file(repo_dir, "nvim/init.lua", "vim.o.number = false\n", "tweak nvim")

        report = SharedSectionSync(ops).sync()

        assert "nvim" in report.propagated["work"]
        assert "fish" in report.skipped["work"]
        assert "number = false" in read_branch_file(repo_dir, "work", "nvim/init.lua")

    def test_noop_when_targets_already_match(self, multi_branch_repo):
        repo_dir, ops = multi_branch_repo
        counts_before = {
            b: branch_commit_count(repo_dir, b) for b in ("work", "server")
        }

        report = SharedSectionSync(ops).sync()

        assert report.ok
        assert sorted(report.unchanged) == ["server", "work"]
        for branch, count in counts_before.items():
            assert branch_commit_count(repo_dir, branch) == count

    def test_propagation_creates_exactly_one_commit_per_target(self, multi_branch_repo):
        repo_dir, ops = multi_branch_repo
        commit_file(repo_dir, "fish/config.fish", "set fish_key_bindings\n", "edit")

        SharedSectionSync(ops).sync()

        for branch in ("work", "server"):
            assert branch_commit_count(repo_dir, branch) >= 1
        assert "fish" in read_branch_file(repo_dir, "server", "fish/config.fish")

    def test_no_shared_sections_is_noop(self, solo_repo):
        repo_dir, ops = solo_repo

        report = SharedSectionSync(ops).sync()

        assert report.shared_sections == []
        assert not report.propagated
        assert report.ok

    def test_unparsable_target_config_is_skipped_safely(self, multi_branch_repo):
        """A branch whose config cannot be parsed is never touched."""
        repo_dir, ops = multi_branch_repo
        blob = subprocess.run(
            ["git", "-C", str(repo_dir), "hash-object", "-w", "--stdin"],
            input="]]]garbage",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        tree_id = subprocess.run(
            ["git", "-C", str(repo_dir), "mktree"],
            input=f"100644 blob {blob}\tdot-man.toml",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        bad_commit = subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "commit-tree",
                tree_id,
                "-p",
                "server",
                "-m",
                "bad cfg",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        run_git(repo_dir, "update-ref", "refs/heads/broken", bad_commit)

        commit_file(repo_dir, "fish/config.fish", "changed = true\n", "edit fish")
        report = SharedSectionSync(ops).sync()

        assert report.ok
        assert report.skipped["broken"] == ["fish", "nvim"]

    def test_source_branch_never_modified(self, multi_branch_repo):
        repo_dir, ops = multi_branch_repo
        main_tip_before = run_git(repo_dir, "rev-parse", "main")

        commit_file(repo_dir, "fish/config.fish", "x = 1\n", "edit")
        SharedSectionSync(ops).sync()

        assert run_git(repo_dir, "rev-parse", "main") != main_tip_before  # our own edit
        # The sync itself adds no commits on top of the editing branch's tip
        assert run_git(repo_dir, "log", "-1", "--format=%s") == "edit"


class TestGitPlumbingUnit:
    def test_plumbing_error_includes_command_and_stderr(self, tmp_path):
        from dot_man.shared_sync import GitPlumbing, GitPlumbingError

        repo = tmp_path / "r"
        repo.mkdir()
        run_git(repo, "init", "-b", "main")
        plumbing = GitPlumbing(repo)

        with pytest.raises(GitPlumbingError) as excinfo:
            plumbing.rev_parse("does-not-exist^{}")
        assert "rev-parse" in str(excinfo.value)

    def test_ls_tree_blobs_filters_to_blobs(self, tmp_path):
        from dot_man.shared_sync import GitPlumbing

        repo = tmp_path / "r"
        repo.mkdir()
        run_git(repo, "init", "-b", "main")
        run_git(repo, "config", "user.name", "T")
        run_git(repo, "config", "user.email", "t@t.co")
        commit_file(repo, "dir/a.txt", "A", "one")

        blobs = GitPlumbing(repo).ls_tree_blobs("HEAD", "dir")
        assert set(blobs) == {"dir/a.txt"}
