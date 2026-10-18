"""Tests for the CLI entry point (dot_man/cli/main.py)."""

import importlib
import sys
from types import SimpleNamespace

import pytest

from dot_man import constants

# `dot_man.cli.main` is shadowed by the `main` function on the package, so
# fetch the module object from importlib rather than attribute access.
main_mod = importlib.import_module("dot_man.cli.main")


class _Tty:
    def isatty(self) -> bool:
        return True


class _NotTty:
    def isatty(self) -> bool:
        return False


def _patch_sys(monkeypatch, main_mod, argv, stdout):
    monkeypatch.setattr(main_mod, "sys", SimpleNamespace(argv=argv, stdout=stdout))


class TestShouldAutoOnboard:
    """First-run onboarding must not hijack help/version or non-interactive runs."""

    def test_skips_help_and_version(self):
        from dot_man.cli.main import _should_auto_onboard

        assert _should_auto_onboard(["--help"]) is False
        assert _should_auto_onboard(["--version"]) is False
        assert _should_auto_onboard(["-h"]) is False

    def test_skips_when_explicitly_disabled(self, monkeypatch):
        _patch_sys(monkeypatch, main_mod, ["dot-man", "--no-onboarding"], _Tty())

        assert main_mod._should_auto_onboard(["--no-onboarding"]) is False

    def test_skips_when_not_a_tty(self, monkeypatch):
        _patch_sys(monkeypatch, main_mod, ["dot-man"], _NotTty())

        assert main_mod._should_auto_onboard([]) is False

    def test_onboards_bare_invocation_and_init(self, monkeypatch):
        _patch_sys(monkeypatch, main_mod, ["dot-man"], _Tty())

        assert main_mod._should_auto_onboard([]) is True
        assert main_mod._should_auto_onboard(["init"]) is True

    def test_skips_other_subcommands(self, monkeypatch):
        _patch_sys(monkeypatch, main_mod, ["dot-man"], _Tty())

        assert main_mod._should_auto_onboard(["add", "~/.bashrc"]) is False

    def test_isatty_failure_is_treated_as_non_interactive(self, monkeypatch):
        class _Boom:
            def isatty(self) -> bool:
                raise ValueError("no tty info")

        _patch_sys(monkeypatch, main_mod, ["dot-man"], _Boom())

        assert main_mod._should_auto_onboard([]) is False


class TestMainVersion:
    """`dot-man --version` on a fresh machine must print the version only."""

    def test_version_does_not_onboard_or_create_dir(
        self, tmp_path, monkeypatch, capsys
    ):
        import dot_man.cli.completion_engine as completion_engine
        import dot_man.cli.completions_cmd as completions_cmd
        import dot_man.cli.onboarding as onboarding

        fresh = tmp_path / "dot-man"
        monkeypatch.setattr(constants, "DOT_MAN_DIR", fresh)
        monkeypatch.setattr(onboarding, "SENTINEL", fresh / ".onboarded")
        monkeypatch.setattr(completion_engine, "maybe_run_completion", lambda: None)
        monkeypatch.setattr(completions_cmd, "run_install", lambda: None)
        monkeypatch.setattr(sys, "argv", ["dot-man", "--version"])

        with pytest.raises(SystemExit) as exc:
            main_mod.main()

        assert exc.value.code == 0
        assert "1.5.0" in capsys.readouterr().out
        assert not fresh.exists()


class TestMainFlow:
    """`main()` routes first-run onboarding and swallows install failures."""

    def test_first_run_runs_onboarding_and_skips_cli(self, monkeypatch):
        import dot_man.cli.completion_engine as completion_engine
        import dot_man.cli.onboarding as onboarding

        calls: dict[str, bool] = {}
        monkeypatch.setattr(completion_engine, "maybe_run_completion", lambda: None)
        monkeypatch.setattr(onboarding, "is_first_run", lambda: True)
        monkeypatch.setattr(
            onboarding, "run_onboarding", lambda: calls.setdefault("onboard", True)
        )
        monkeypatch.setattr(main_mod, "_should_auto_onboard", lambda argv: True)
        monkeypatch.setattr(main_mod, "cli", lambda: calls.setdefault("cli", True))

        main_mod.main()

        assert calls == {"onboard": True}

    def test_completion_install_failure_is_swallowed(self, monkeypatch):
        import dot_man.cli.completion_engine as completion_engine
        import dot_man.cli.completions_cmd as completions_cmd
        import dot_man.cli.onboarding as onboarding

        def _boom() -> None:
            raise RuntimeError("cannot install completions")

        calls: dict[str, bool] = {}
        monkeypatch.setattr(completion_engine, "maybe_run_completion", lambda: None)
        monkeypatch.setattr(onboarding, "is_first_run", lambda: False)
        monkeypatch.setattr(completions_cmd, "run_install", _boom)
        monkeypatch.setattr(main_mod, "cli", lambda: calls.setdefault("cli", True))

        main_mod.main()

        assert calls == {"cli": True}
