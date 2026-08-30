"""Shared-section synchronization across branches.

A section marked ``shared = true`` lives once and edits flow to every
branch. Branches that define their own ``[section]`` are treated as
overrides and never touched — so per-machine customizations stay put.

Propagation runs after a save/commit on the current branch: the shared
blobs are grafted onto each inheriting branch using git plumbing,
leaving the working tree untouched.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .constants import CONFIG_FILE_PRIORITY

__all__ = ["GitPlumbing", "GitPlumbingError", "SharedSectionSync", "SharedSyncReport"]

_RESERVED_KEYS = {"templates", "secrets"}


def _parse_toml(text: str) -> dict | None:
    """Parse TOML text, returning None on failure."""
    try:
        import sys

        if sys.version_info >= (3, 11):
            import tomllib

            result: dict = tomllib.loads(text)
            return result
        import tomli

        return tomli.loads(text)  # type: ignore[no-any-return]
    except Exception:
        return None


def _parse_yaml(text: str) -> dict | None:
    """Parse YAML text if pyyaml is installed, else None."""
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


class GitPlumbingError(RuntimeError):
    """A git plumbing command failed."""


class GitPlumbing:
    """Low-level git plumbing commands scoped to one repository."""

    def __init__(self, worktree: Path):
        self.worktree = Path(worktree)

    def run(self, *args: str, index_file: str | None = None) -> str:
        """Run a plumbing command and return stripped stdout.

        Raises :class:`GitPlumbingError` on failure. When ``index_file``
        is given it is exported as ``GIT_INDEX_FILE`` so index-mutating
        commands operate on a temporary index instead of the real one.
        """
        env = dict(os.environ, GIT_INDEX_FILE=index_file) if index_file else None
        result = subprocess.run(
            ["git", "-C", str(self.worktree), *args],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            raise GitPlumbingError(f"git {' '.join(args)}: {result.stderr.strip()}")
        return result.stdout.strip()

    def rev_parse(self, ref: str) -> str:
        return self.run("rev-parse", ref)

    def ls_tree_blobs(self, ref: str, pathspec: str = "") -> dict[str, tuple[str, str]]:
        """Map path → (mode, blob sha) for all blobs under ``pathspec``."""
        args = ["ls-tree", "-r", ref]
        if pathspec:
            args += ["--", pathspec]
        entries: dict[str, tuple[str, str]] = {}
        for line in self.run(*args).splitlines():
            meta, _, path = line.partition("\t")
            parts = meta.split()
            if len(parts) >= 3 and parts[1] == "blob":
                entries[path] = (parts[0], parts[2])
        return entries

    def read_tree(self, treeish: str, index_file: str) -> None:
        self.run("read-tree", treeish, index_file=index_file)

    def stage_blob(self, mode: str, sha: str, path: str, index_file: str) -> None:
        self.run(
            "update-index",
            "--add",
            "--cacheinfo",
            f"{mode},{sha},{path}",
            index_file=index_file,
        )

    def write_tree(self, index_file: str) -> str:
        return self.run("write-tree", index_file=index_file)

    def commit_tree(self, tree: str, parent: str, message: str) -> str:
        return self.run("commit-tree", tree, "-p", parent, "-m", message)

    def update_branch(self, branch: str, commit: str) -> None:
        self.run("update-ref", f"refs/heads/{branch}", commit)


@dataclass
class SharedSyncReport:
    """Outcome of one propagation pass."""

    shared_sections: list[str] = field(default_factory=list)
    propagated: dict[str, list[str]] = field(default_factory=dict)
    skipped: dict[str, list[str]] = field(default_factory=dict)
    unchanged: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


class SharedSectionSync:
    """Propagates ``shared = true`` sections to non-overriding branches."""

    def __init__(self, ops):
        self.ops = ops
        self.git = ops.git
        self.plumbing = GitPlumbing(ops.git.repo.working_tree_dir)

    # ── public API ──────────────────────────────────────────────

    def get_shared_section_names(self) -> list[str]:
        """Names of sections marked shared=True in the active config."""
        try:
            self.ops.reload_config()
            config = self.ops.dotman_config
            names = []
            for name in config.get_section_names():
                try:
                    section = config.get_section(name)
                except Exception:
                    continue
                if getattr(section, "shared", False):
                    names.append(name)
            return names
        except Exception as e:
            logging.debug("Failed to inspect shared sections: %s", e)
            return []

    def sync(self) -> SharedSyncReport:
        """Graft shared-section blobs from HEAD onto every other branch."""
        report = SharedSyncReport()
        try:
            current = self.git.current_branch
        except Exception as e:
            report.errors["<repo>"] = str(e)
            return report

        shared_names = self.get_shared_section_names()
        report.shared_sections = shared_names
        if not shared_names:
            return report

        blobs = self._head_blobs_for(shared_names)
        if not blobs:
            return report

        for branch in self.git.list_branches():
            if branch != current:
                self._sync_branch(branch, current, shared_names, blobs, report)
        return report

    # ── internals ───────────────────────────────────────────────

    def _section_repo_spec(self, name: str) -> str | None:
        """Repo-relative prefix (or exact file) backing a section."""
        try:
            section = self.ops.dotman_config.get_section(name)
        except Exception as e:
            logging.debug("Skipping unreadable section %s: %s", name, e)
            return None
        spec = section.repo_path or section.repo_base
        return spec.replace("\\", "/").strip("/") or None

    def _head_blobs_for(self, shared_names: list[str]) -> dict[str, tuple[str, str]]:
        """Blobs in HEAD belonging to any shared section."""
        blobs: dict[str, tuple[str, str]] = {}
        for name in shared_names:
            spec = self._section_repo_spec(name)
            if spec:
                blobs.update(self.plumbing.ls_tree_blobs("HEAD", spec))
        return blobs

    def _branch_overrides(self, branch: str) -> set[str]:
        """Section names the branch defines in its own committed config."""
        for filename in CONFIG_FILE_PRIORITY:
            content = self.git.get_file_from_branch(branch, filename)
            if content is None:
                continue
            if filename.endswith((".yaml", ".yml")):
                data = _parse_yaml(content)
            else:
                data = _parse_toml(content)
            if data is None:
                # Unparsable config: assume full customization, stay safe.
                return set(self.get_shared_section_names())
            return {
                key
                for key, value in data.items()
                if key not in _RESERVED_KEYS and isinstance(value, dict)
            }
        return set()

    def _changed_sections(self, specs: dict[str, str], paths: set[str]) -> list[str]:
        """Section names owning at least one of ``paths``."""
        return sorted(
            name
            for name, spec in specs.items()
            if any(p == spec or p.startswith(spec + "/") for p in paths)
        )

    def _sync_branch(
        self,
        branch: str,
        source_branch: str,
        shared_names: list[str],
        head_blobs: dict[str, tuple[str, str]],
        report: SharedSyncReport,
    ) -> None:
        overrides = self._branch_overrides(branch)
        wanted = [n for n in shared_names if n not in overrides]
        skipped = [n for n in shared_names if n in overrides]
        if skipped:
            report.skipped[branch] = skipped
        if not wanted:
            return

        specs = {n: s for n in wanted if (s := self._section_repo_spec(n)) is not None}
        relevant = {
            path: meta
            for path, meta in head_blobs.items()
            if any(path == s or path.startswith(s + "/") for s in specs.values())
        }
        if not relevant:
            report.unchanged.append(branch)
            return

        target_blobs = self.plumbing.ls_tree_blobs(branch)
        diff = {p: m for p, m in relevant.items() if target_blobs.get(p) != m}
        if not diff:
            report.unchanged.append(branch)
            return

        changed = self._changed_sections(specs, set(diff))
        index_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix="dotman-sync-", delete=False
            ) as tmp:
                index_path = tmp.name

            base_tree = self.plumbing.rev_parse(f"{branch}^{{tree}}")
            self.plumbing.read_tree(base_tree, index_path)
            for path, (mode, sha) in diff.items():
                self.plumbing.stage_blob(mode, sha, path, index_path)

            new_tree = self.plumbing.write_tree(index_path)
            if new_tree == base_tree:
                report.unchanged.append(branch)
                return

            preview = ", ".join(changed[:3])
            hidden = len(changed) - 3
            suffix = f" +{hidden} more" if hidden > 0 else ""
            message = (
                f"sync(shared): propagate {preview}{suffix} from '{source_branch}'"
            )
            commit = self.plumbing.commit_tree(new_tree, branch, message)
            self.plumbing.update_branch(branch, commit)
            report.propagated[branch] = changed
        except Exception as e:
            report.errors[branch] = str(e)
        finally:
            if index_path:
                Path(index_path).unlink(missing_ok=True)
