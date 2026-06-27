"""Shell completion helpers for dot-man CLI."""

import json
import logging
import os
import subprocess
import time

import click

from ..constants import REPO_DIR

COMPLETION_CACHE_TTL = 10
COMPLETION_CACHE_FILE = REPO_DIR / ".dotman" / "completion_cache.json"

_git_runner = None
_memory_cache: dict | None = None
_memory_cache_time: float = 0
_template_cache: list[str] | None = None
_config_keys_cache: list[str] | None = None
_profiles_cache: list[str] | None = None


def _set_git_runner(runner):
    """Set custom git runner for testing."""
    global _git_runner
    _git_runner = runner


def _run_git(args, cwd=REPO_DIR, timeout=2):
    """Run git command, using custom runner if set."""
    if _git_runner is not None:
        return _git_runner(args, cwd, timeout)
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def _get_completion_cache() -> dict:
    """Load completion cache from memory or file."""
    global _memory_cache, _memory_cache_time

    if (
        _memory_cache is not None
        and time.time() - _memory_cache_time < COMPLETION_CACHE_TTL
    ):
        return _memory_cache

    try:
        if not REPO_DIR.exists():
            _memory_cache = {}
            _memory_cache_time = time.time()
            return _memory_cache
        if COMPLETION_CACHE_FILE.exists():
            mtime = os.path.getmtime(COMPLETION_CACHE_FILE)
            if time.time() - mtime < COMPLETION_CACHE_TTL:
                _memory_cache = json.loads(COMPLETION_CACHE_FILE.read_text())
                _memory_cache_time = time.time()
                return _memory_cache
    except Exception:
        logging.debug("Failed to load completion cache from file")

    _memory_cache = {}
    _memory_cache_time = time.time()
    return _memory_cache


def _save_completion_cache(data: dict) -> None:
    """Save completion cache to memory and file."""
    global _memory_cache, _memory_cache_time
    _memory_cache = data
    _memory_cache_time = time.time()

    try:
        if not REPO_DIR.exists():
            return
        COMPLETION_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COMPLETION_CACHE_FILE.write_text(json.dumps(data))
    except Exception:
        logging.debug("Failed to save completion cache to file")


def _clear_completion_cache() -> None:
    """Clear completion cache for testing."""
    global _memory_cache, _memory_cache_time
    _memory_cache = None
    _memory_cache_time = 0

    try:
        if COMPLETION_CACHE_FILE.exists():
            COMPLETION_CACHE_FILE.unlink()
    except Exception:
        logging.debug(
            "Failed to unlink completion cache file in _clear_completion_cache"
        )


def _clear_all_caches() -> None:
    """Clear all completion caches including in-memory."""
    global _memory_cache, _memory_cache_time
    global _template_cache, _config_keys_cache, _profiles_cache

    _memory_cache = None
    _memory_cache_time = 0
    _template_cache = None
    _config_keys_cache = None
    _profiles_cache = None

    try:
        if COMPLETION_CACHE_FILE.exists():
            COMPLETION_CACHE_FILE.unlink()
    except Exception:
        logging.debug("Failed to unlink completion cache file in _clear_all_caches")


def complete_switch_args(ctx, param, incomplete):
    """Shell completion callback for switch (branches, tags, commits)."""
    try:
        return _complete_navigate_items(incomplete)
    except Exception as e:
        logging.debug(f"Completion error: {e}")
        return []


def _complete_navigate_items(
    incomplete: str,
) -> "list[click.shell_completion.CompletionItem]":
    """Get completion items for navigate command with context."""
    from click.shell_completion import CompletionItem

    try:
        cache = _get_completion_cache()
        items: list[CompletionItem] = []

        if "branches" not in cache or "current_branch" not in cache:
            result = _run_git(["git", "branch", "--list", "--format=%(refname:short)"])
            branches = [
                b.strip() for b in result.stdout.strip().split("\n") if b.strip()
            ]

            result = _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            current_branch = result.stdout.strip() or "HEAD"

            cache["branches"] = branches
            cache["current_branch"] = current_branch
        else:
            branches = cache["branches"]
            current_branch = cache["current_branch"]

        branch_items: list[CompletionItem] = []
        other_branches: list[CompletionItem] = []
        for b in branches:
            if b.startswith(incomplete):
                if b == current_branch:
                    branch_items.append(CompletionItem(b, help="current branch"))
                else:
                    other_branches.append(CompletionItem(b, help="branch"))

        other_branches.sort(key=lambda x: x.value.lower())
        items.extend(branch_items)
        items.extend(other_branches)

        if "tags" not in cache:
            result = _run_git(["git", "tag", "-l"])
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
            cache["tags"] = tags
        else:
            tags = cache["tags"]

        tag_items: list[CompletionItem] = []
        for t in tags:
            if t.startswith(incomplete):
                result = _run_git(["git", "rev-parse", f"{t}^{{commit}}"])
                commit_hash = (
                    result.stdout.strip()[:7] if result.returncode == 0 else ""
                )
                tag_items.append(CompletionItem(t, help=f"tag → {commit_hash}"))

        tag_items.sort(key=lambda x: x.value.lower())
        items.extend(tag_items)

        if "commits" not in cache:
            result = _run_git(
                ["git", "log", "--oneline", "-n", "20", "--format=%H %s"], timeout=3
            )
            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({"sha": parts[0][:7], "message": parts[1][:30]})
            cache["commits"] = commits
        else:
            commits = cache["commits"]

        commit_items: list[CompletionItem] = []
        for c in commits:
            if c["sha"].startswith(incomplete):
                commit_items.append(CompletionItem(c["sha"], help=f"{c['message']}..."))

        items.extend(commit_items)

        if "@" in incomplete:
            parts = incomplete.split("@", 1)
            if parts[0] in branches:
                for t in tags:
                    if t.startswith(parts[1] if len(parts) > 1 else ""):
                        result = _run_git(["git", "rev-parse", f"{t}^{{commit}}"])
                        commit_hash = (
                            result.stdout.strip()[:7] if result.returncode == 0 else ""
                        )
                        items.append(
                            CompletionItem(
                                f"{parts[0]}@{t}", help=f"tag at {commit_hash}"
                            )
                        )

        _save_completion_cache(cache)
        return items
    except Exception:
        logging.debug("Failed to complete navigate items")
        return []


def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        cache = _get_completion_cache()
        if "branches" not in cache:
            result = _run_git(["git", "branch", "--list", "--format=%(refname:short)"])
            branches = [
                b.strip() for b in result.stdout.strip().split("\n") if b.strip()
            ]
            cache["branches"] = branches
            _save_completion_cache(cache)
        else:
            branches = cache["branches"]
        return [b for b in branches if b.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete branches")
        return []


def complete_tags(ctx, param, incomplete):
    """Shell completion callback for tags."""
    try:
        cache = _get_completion_cache()
        if "tags" not in cache:
            result = _run_git(["git", "tag", "-l"])
            tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
            cache["tags"] = tags
            _save_completion_cache(cache)
        else:
            tags = cache["tags"]
        return [t for t in tags if t.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete tags")
        return []


def complete_commits(ctx, param, incomplete):
    """Shell completion callback for commits."""
    try:
        cache = _get_completion_cache()
        if "commits_all" not in cache:
            result = _run_git(
                ["git", "log", "--oneline", "-n", "50", "--format=%h"], timeout=3
            )
            commits = [
                c.strip() for c in result.stdout.strip().split("\n") if c.strip()
            ]
            cache["commits_all"] = commits
            _save_completion_cache(cache)
        else:
            commits = cache["commits_all"]
        return [c for c in commits if c.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete commits")
        return []


def complete_template_keys(ctx, param, incomplete):
    """Shell completion callback for template keys."""
    global _template_cache

    if _template_cache is not None:
        return [k for k in _template_cache if k.startswith(incomplete)]

    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        templates = gc.get_all_templates()
        _template_cache = list(templates.keys())
        return [k for k in _template_cache if k.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete template keys")
        return []


def complete_config_keys(ctx, param, incomplete):
    """Shell completion callback for config keys."""
    global _config_keys_cache

    if _config_keys_cache is not None:
        return [k for k in _config_keys_cache if k.startswith(incomplete)]

    try:
        keys = [
            "dot-man.current_branch",
            "remote.url",
            "security.strict_mode",
            "switch.default_behavior",
            "secrets_filter_enabled",
        ]
        _config_keys_cache = keys
        return [k for k in keys if k.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete config keys")
        return []


def complete_profiles(ctx, param, incomplete):
    """Shell completion callback for profiles."""
    global _profiles_cache

    if _profiles_cache is not None:
        return [k for k in _profiles_cache if k.startswith(incomplete)]

    try:
        from ..global_config import GlobalConfig

        gc = GlobalConfig()
        profiles = gc._data.get("profiles", {})
        _profiles_cache = list(profiles.keys())
        return [k for k in _profiles_cache if k.startswith(incomplete)]
    except Exception:
        logging.debug("Failed to complete profiles")
        return []


def complete_sections(ctx, param, incomplete):
    """Shell completion callback for section names."""
    try:
        from ..dotman_config import DotManConfig

        config = DotManConfig()
        config.load()
        return [
            name for name in config.get_section_names() if name.startswith(incomplete)
        ]
    except Exception:
        logging.debug("Failed to complete sections")
        return []
