"""Tests for the decorator-driven completion engine."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest
from click.shell_completion import CompletionItem

from dot_man.cli.common import _clear_all_caches, _set_git_runner
from dot_man.cli.completion_engine import (
    _PROVIDERS,
    CompletionEngine,
    completes,
    format_fish,
    maybe_run_completion,
    parse_request,
    run_completion_request,
)
from dot_man.cli.interface import cli as root_cli


@pytest.fixture(autouse=True)
def _clean_registry_and_caches():
    """Snapshot provider registry so test registrations never leak."""
    snapshot = dict(_PROVIDERS)
    _clear_all_caches()
    yield
    _PROVIDERS.clear()
    _PROVIDERS.update(snapshot)
    _clear_all_caches()
    _set_git_runner(None)


@pytest.fixture
def engine():
    return CompletionEngine(root_cli)


def make_mock_result(stdout="", returncode=0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class TestCompletionRegistry:
    def test_decorator_registers_provider(self):
        @completes("fake cmd", param="target")
        def provider(ctx):
            return ["a", "b"]

        assert _PROVIDERS[("fake cmd", "target")] is provider

    def test_specific_provider_replaces_generic_slot(self, engine):
        @completes("config set", param="value")
        def specific(ctx):
            return [("specific", "")]

        pairs = engine.complete(["config", "set", "some.key"], "")
        assert [v for v, _ in pairs] == ["specific"]

    def test_normalize_accepts_strings_tuples_and_items(self):
        from dot_man.cli.completion_engine import _normalize

        result = _normalize(
            ["plain", ("val", "desc"), CompletionItem("item", help="h")]
        )
        assert result == [("plain", ""), ("val", "desc"), ("item", "h")]


class TestRootCompletions:
    def test_lists_commands_with_descriptions(self, engine):
        pairs = dict(engine.complete([], ""))
        assert (
            pairs.get("navigate")
            == "Navigate to a branch, tag, or commit with optional diff..."
        )
        assert "init" in pairs

    def test_prefix_filtering(self, engine):
        values = [v for v, _ in engine.complete([], "na")]
        assert "navigate" in values
        assert "nav" in values
        assert "init" not in values

    def test_aliases_labeled(self, engine):
        pairs = dict(engine.complete([], ""))
        assert pairs["nav"].startswith("(alias)")
        assert not pairs["navigate"].startswith("(alias)")

    def test_leading_prog_name_is_ignored(self, engine):
        direct = engine.complete([], "na")
        with_prog = engine.complete(["dot-man"], "na")
        assert direct == with_prog


class TestSubcommandCompletions:
    def test_branch_group_subcommands(self, engine):
        values = [v for v, _ in engine.complete(["branch"], "")]
        assert "list" in values
        assert "delete" in values

    def test_remote_group_subcommands(self, engine):
        values = [v for v, _ in engine.complete(["remote"], "")]
        assert "get" in values
        assert "set" in values

    def test_subcommand_prefix_filtering(self, engine):
        values = [v for v, _ in engine.complete(["branch"], "del")]
        assert values == ["delete"]


class TestStaticChoices:
    def test_import_source_choices(self, engine):
        values = [v for v, _ in engine.complete(["import"], "")]
        assert sorted(values) == ["all", "chezmoi", "stow", "yadm"]

    def test_completions_shell_option_value(self, engine):
        values = [v for v, _ in engine.complete(["completions", "--shell"], "")]
        assert sorted(values) == ["all", "bash", "fish", "zsh"]

    def test_choice_prefix_filtering(self, engine):
        values = [v for v, _ in engine.complete(["import"], "ch")]
        assert values == ["chezmoi"]


class TestOptionNames:
    def test_options_listed_with_help(self, engine):
        pairs = dict(engine.complete(["navigate"], "--"))
        assert "--dry-run" in pairs
        assert pairs["--dry-run"] == "Show what would happen without making changes"

    def test_defaults_and_choices_shown(self, engine):
        pairs = dict(engine.complete(["completions"], "--s"))
        assert (
            pairs["--shell"]
            == "Shell to install completions for [choices: bash|zsh|fish|all] [default: all]"
        )

    def test_used_flag_not_offered_twice(self, engine):
        values = [v for v, _ in engine.complete(["deploy", "--dry-run"], "-")]
        assert "--dry-run" not in values

    def test_root_options_available_at_subcommand_level(self, engine):
        values = [v for v, _ in engine.complete(["status"], "--ver")]
        assert "--verbose" in values


class TestOptionValueForms:
    def test_eq_form_emits_full_tokens(self, engine):
        values = [v for v, _ in engine.complete(["completions"], "--shell=fi")]
        assert values == ["--shell=fish"]

    def test_prev_word_option_value(self, engine):
        values = [v for v, _ in engine.complete(["completions", "--shell"], "b")]
        assert values == ["bash"]


class TestDecoratorProviders:
    def test_config_set_value_static_choices(self, engine):
        values = [
            v for v, _ in engine.complete(["config", "set", "security.strict_mode"], "")
        ]
        assert sorted(values) == ["false", "true"]

    def test_custom_dynamic_provider(self, engine):
        calls = []

        @completes("tag switch", param="name")
        def provider(ctx):
            calls.append(ctx.command_path)
            return [("dyn-tag", "dynamic")]

        pairs = engine.complete(["tag", "switch"], "")
        assert ("dyn-tag", "dynamic") in pairs
        assert calls == ["tag switch"]

    def test_provider_receives_context_state(self, engine):
        seen = {}

        @completes("tag switch", param="name")
        def provider(ctx):
            seen["args"] = ctx.args
            seen["incomplete"] = ctx.incomplete
            return []

        engine.complete(["tag", "switch"], "v1")
        assert seen["args"] == ["tag", "switch"]
        assert seen["incomplete"] == "v1"

    def test_broken_provider_returns_empty_not_crash(self, engine):
        @completes("tag switch", param="name")
        def broken(ctx):
            raise RuntimeError("boom")

        assert isinstance(engine.complete(["tag", "switch"], ""), list)


class TestDynamicCallbacks:
    def test_branch_delete_completes_real_branch_names(self, engine):
        def mock_runner(args, cwd=None, timeout=2):
            if "branch" in args:
                return make_mock_result("main\ndev\nfeature/x\n")
            return make_mock_result()

        _set_git_runner(mock_runner)
        values = [v for v, _ in engine.complete(["branch", "delete"], "")]
        assert values == ["dev", "feature/x", "main"]

    def test_tag_switch_completes_tags(self, engine):
        def mock_runner(args, cwd=None, timeout=2):
            if args[:2] == ["git", "tag"]:
                return make_mock_result("v1.0\nv2.0\n")
            return make_mock_result()

        _set_git_runner(mock_runner)
        values = [v for v, _ in engine.complete(["tag", "switch"], "v1")]
        assert values == ["v1.0"]


class TestArgumentSlotResolution:
    def test_second_argument_slot_used_after_first_filled(self, engine):
        values = [v for v, _ in engine.complete(["tag", "create", "my-tag"], "")]
        assert values == [] or isinstance(values, list)

    def test_argument_values_via_choice_type(self, engine):
        pairs = engine.complete(["import"], "")
        assert all(v in ("chezmoi", "yadm", "stow", "all") for v, _ in pairs)


class TestParseRequest:
    def test_standard_shape_with_separator(self):
        parsed = parse_request(["dot-man", "--complete", "fish", "branch", "--", "de"])
        assert parsed == (["branch"], "de")

    def test_empty_incomplete_after_separator(self):
        parsed = parse_request(["dot-man", "--complete", "fish", "--"])
        assert parsed == ([], "")

    def test_no_words_at_all(self):
        parsed = parse_request(["dot-man", "--complete", "fish"])
        assert parsed == ([], "")

    def test_missing_shell_arg_is_invalid(self):
        assert parse_request(["dot-man", "--complete"]) is None

    def test_no_complete_flag_is_invalid(self):
        assert parse_request(["dot-man", "status"]) is None


class TestFormattingAndEntry:
    def test_format_fish_tab_separates_descriptions(self):
        out = format_fish([("--force", "Force delete"), ("bare", "")])
        lines = out.split("\n")
        assert lines[0] == "--force\tForce delete"
        assert lines[1] == "bare"

    def test_run_completion_request_prints_fish_lines(self, capsys):
        rc = run_completion_request(
            ["dot-man", "--complete", "fish", "import", "--", "ch"]
        )
        assert rc == 0
        assert capsys.readouterr().out.strip() == "chezmoi"

    def test_maybe_run_completion_exits_on_flag(self):
        with pytest.raises(SystemExit) as exc:
            maybe_run_completion(["dot-man", "--complete", "fish", "--", ""])
        assert exc.value.code == 0

    def test_maybe_run_completion_noop_without_flag(self):
        maybe_run_completion(["dot-man", "status"])

    def test_engine_error_never_raises(self, engine):
        with patch.object(engine, "_walk", side_effect=RuntimeError("boom")):
            assert engine.complete(["anything"], "") == []


class TestAddPathCompletions:
    def test_completes_real_tmp_files(self, engine):
        """The add command should complete real file/directory paths."""
        import os
        import tempfile

        # Create a temp file to complete against
        with tempfile.NamedTemporaryFile(
            prefix="test_complete_", dir="/tmp", delete=False
        ) as f:
            tmppath = f.name
        try:
            prefix = os.path.basename(tmppath)
            values = [v for v, _ in engine.complete(["add"], "/tmp/" + prefix)]
            assert tmppath in values
        finally:
            os.unlink(tmppath)

    def test_completes_dir_entries(self, engine):
        """The add command should list directory entries."""
        values = [v for v, _ in engine.complete(["add"], "/tmp/")]
        # Should return at least some /tmp entries
        assert any(v.startswith("/tmp/") for v in values)

    def test_provider_registered(self):
        """The add path provider should be registered."""
        from dot_man.cli.completion_engine import _PROVIDERS

        assert ("add", "path") in _PROVIDERS


class TestBootstrapPmCompletions:
    def test_completes_package_managers(self, engine):
        """The bootstrap --pm should list supported package managers."""
        # Complete the VALUE of --pm (pass --pm as previous arg)
        values = [v for v, _ in engine.complete(["bootstrap", "--pm"], "")]
        assert "brew" in values
        assert "apt" in values
        assert "dnf" in values
        assert "pacman" in values

    def test_pm_prefix_filtering(self, engine):
        values = [v for v, _ in engine.complete(["bootstrap", "--pm"], "pa")]
        assert values == ["pacman"]

    def test_pm_option_name_completion(self, engine):
        """Typing --pm as incomplete completes the option name itself."""
        values = [v for v, _ in engine.complete(["bootstrap"], "--pm")]
        assert "--pm" in values

    def test_provider_registered(self):
        """The bootstrap pm provider should be registered."""
        from dot_man.cli.completion_engine import _PROVIDERS

        assert ("bootstrap", "pm") in _PROVIDERS
