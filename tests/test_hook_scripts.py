"""Tests for `file:` script references in section hooks.

Hook values stay inline shell strings, but any ``file:<script> [args]``
token resolves to an executable script from the hooks folder
(``<repo>/hooks/`` first, ``~/.config/dot-man/hooks/`` as fallback).
"""

import os
import shlex
from pathlib import Path
from unittest.mock import patch

import pytest

from dot_man.section import Section


@pytest.fixture
def hook_dirs(tmp_path):
    """Fake repo hooks dir + global hooks dir, wired into dot_man.hook_engine."""
    repo_hooks = tmp_path / "repo" / "hooks"
    global_hooks = tmp_path / "global-hooks"
    repo_hooks.mkdir(parents=True)
    global_hooks.mkdir(parents=True)
    with (
        patch("dot_man.constants.REPO_DIR", tmp_path / "repo"),
        patch("dot_man.hook_engine.HOOKS_DIR", global_hooks),
    ):
        yield repo_hooks, global_hooks


def _write_script(directory: Path, name: str, executable: bool = True) -> Path:
    script = directory / name
    script.write_text("#!/bin/sh\necho hook-ran\n")
    if executable:
        script.chmod(0o755)
    else:
        script.chmod(0o644)
    return script


class TestInlineHooksUnchanged:
    def test_plain_string_passes_through(self, hook_dirs):
        section = Section(name="nvim", paths=[], post_deploy="echo hello")
        assert section.post_deploy == "echo hello"

    def test_alias_still_resolves(self, hook_dirs):
        section = Section(name="nvim", paths=[], post_deploy="quickshell_validate")
        assert section.post_deploy != "quickshell_validate"
        assert "file:" not in section.post_deploy


class TestFileResolution:
    def test_file_token_resolves_from_repo_hooks(self, hook_dirs):
        repo_hooks, _ = hook_dirs
        script = _write_script(repo_hooks, "log.sh")
        section = Section(
            name="nvim", paths=[], post_deploy="echo 'start'; file:log.sh 'hi'"
        )
        assert section.post_deploy == f"echo 'start'; {shlex.quote(str(script))} 'hi'"

    def test_falls_back_to_global_hooks_dir(self, hook_dirs):
        _, global_hooks = hook_dirs
        script = _write_script(global_hooks, "log.sh")
        section = Section(name="nvim", paths=[], post_deploy="file:log.sh")
        assert section.post_deploy == shlex.quote(str(script))

    def test_repo_wins_over_global(self, hook_dirs):
        repo_hooks, global_hooks = hook_dirs
        repo_script = _write_script(repo_hooks, "log.sh")
        _write_script(global_hooks, "log.sh")
        section = Section(name="nvim", paths=[], post_deploy="file:log.sh")
        assert section.post_deploy == shlex.quote(str(repo_script))

    def test_multiple_file_tokens(self, hook_dirs):
        repo_hooks, _ = hook_dirs
        first = _write_script(repo_hooks, "one.sh")
        second = _write_script(repo_hooks, "two.sh")
        section = Section(
            name="nvim", paths=[], post_deploy="file:one.sh && file:two.sh arg"
        )
        assert section.post_deploy == (
            f"{shlex.quote(str(first))} && {shlex.quote(str(second))} arg"
        )

    def test_all_hook_fields_support_file_tokens(self, hook_dirs):
        repo_hooks, _ = hook_dirs
        script = _write_script(repo_hooks, "s.sh")
        section = Section(
            name="nvim",
            paths=[],
            pre_deploy="file:s.sh pre",
            post_deploy="file:s.sh post",
            on_activate="file:s.sh on",
            on_deactivate="file:s.sh off",
        )
        quoted = shlex.quote(str(script))
        assert section.pre_deploy == f"{quoted} pre"
        assert section.post_deploy == f"{quoted} post"
        assert section.on_activate == f"{quoted} on"
        assert section.on_deactivate == f"{quoted} off"


class TestFileResolutionErrors:
    def test_missing_script_raises_configuration_error(self, hook_dirs):
        from dot_man.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            Section(name="nvim", paths=[], post_deploy="file:nope.sh")
        assert "nope.sh" in str(exc_info.value)

    def test_missing_script_message_names_search_dirs(self, hook_dirs, tmp_path):
        from dot_man.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            Section(name="nvim", paths=[], post_deploy="file:nope.sh")
        message = str(exc_info.value)
        assert "hooks" in message
        assert str(tmp_path) in message

    def test_path_traversal_rejected(self, hook_dirs, tmp_path):
        from dot_man.exceptions import ConfigurationError

        outside = tmp_path / "evil.sh"
        outside.write_text("#!/bin/sh\necho evil\n")
        with pytest.raises(ConfigurationError):
            Section(name="nvim", paths=[], post_deploy="file:../evil.sh")


class TestCompositionWithPlaceholders:
    def test_file_token_combines_with_placeholders(self, hook_dirs, tmp_path):
        repo_hooks, _ = hook_dirs
        script = _write_script(repo_hooks, "deploy.sh")
        target = tmp_path / "myconf"
        target.mkdir()
        section = Section(
            name="nvim",
            paths=[target],
            post_deploy="file:deploy.sh {config_name}",
        )
        assert section.post_deploy == f"{shlex.quote(str(script))} myconf"


class TestScriptExecutability:
    def test_non_executable_script_gains_exec_bit(self, hook_dirs):
        repo_hooks, _ = hook_dirs
        script = _write_script(repo_hooks, "run.sh", executable=False)
        assert not os.access(script, os.X_OK)
        Section(name="nvim", paths=[], post_deploy="file:run.sh")
        assert os.access(script, os.X_OK)
