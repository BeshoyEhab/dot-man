"""Tests for dot_man/hook_engine.py resolve pipeline."""

import shlex
from unittest.mock import patch

import pytest

from dot_man.exceptions import ConfigurationError
from dot_man.hook_engine import HookContext, resolve_hook


@pytest.fixture
def hook_dirs(tmp_path):
    repo_hooks = tmp_path / "repo" / "hooks"
    global_hooks = tmp_path / "global-hooks"
    repo_hooks.mkdir(parents=True)
    global_hooks.mkdir(parents=True)
    with (
        patch("dot_man.hook_engine.REPO_DIR", tmp_path / "repo"),
        patch("dot_man.hook_engine.HOOKS_DIR", global_hooks),
    ):
        yield repo_hooks, global_hooks


def test_alias_resolves():
    ctx = HookContext(section_name="nvim")
    assert resolve_hook("shell_reload", ctx) != "shell_reload"


def test_placeholders_resolve_from_context():
    ctx = HookContext(section_name="qs", config_name="ii")
    assert resolve_hook("qs -c {config_name}", ctx) == "qs -c ii"


def test_unknown_placeholder_passes_through_literally():
    ctx = HookContext(section_name="qs")
    assert resolve_hook("echo {branch}", ctx) == "echo {branch}"


def test_file_token_resolves(hook_dirs):
    repo_hooks, _ = hook_dirs
    script = repo_hooks / "log.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o755)
    ctx = HookContext(section_name="nvim")
    assert resolve_hook("file:log.sh 'hi'", ctx) == f"{shlex.quote(str(script))} 'hi'"


def test_escaped_file_token_stays_literal(hook_dirs):
    ctx = HookContext(section_name="nvim")
    assert (
        resolve_hook("echo run \\file:log.sh for details", ctx)
        == "echo run file:log.sh for details"
    )


def test_missing_script_raises(hook_dirs):
    ctx = HookContext(section_name="nvim")
    with pytest.raises(ConfigurationError):
        resolve_hook("file:nope.sh", ctx)


def test_none_passes_through():
    assert resolve_hook(None, HookContext()) is None
