# Hook Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three hook executors and three alias-resolution sites with one `hook_engine` module.

**Architecture:** New `dot_man/hook_engine.py` owns `HookContext` + `resolve()` (alias → `{x}` → `file:` with escape) + `run()` (warn-and-continue shell runner). All call sites delegate; `hooks.py` keeps only global script-file machinery (`run_hook`, list/create/delete).

**Tech Stack:** Python 3.10+, Click, pytest, stdlib only (`re`, `shlex`, `subprocess`, `os`).

**Spec:** `docs/superpowers/specs/2026-09-27-hook-engine-design.md` — the plan argues from the spec; executors read both.

## Global Constraints

- Python 3.10+ compatible (no `X | Y` in runtime annotations outside `from __future__ import annotations`).
- Black line length 88; ruff `E, F, W, I`; mypy `--ignore-missing-imports` zero errors.
- Every command runs under `uv run`.
- Coverage must not decrease (currently 86%).
- Never `sys.exit()`; use `raise SystemExit(ExitCode.X)`, `error()`, or `handle_exception()`.

---

## File Map

- Create `dot_man/hook_engine.py` — `HookContext`, `resolve_hook()`, `find_hook_script()`, `run_hooks()` (Tasks 1–2).
- Create `tests/test_hook_engine.py` — engine tests (Tasks 1–2).
- Modify `dot_man/section.py` — `_resolve_hook` delegates to engine (Task 5).
- Modify `dot_man/branch_ops.py` — `detect_hooks_for_changed_files` resolves with section context (Task 4).
- Modify `dot_man/cli/navigate_cmd.py` — `_run_shell_hooks` body moves to engine; `run_branch_hooks` delegates (Task 2).
- Modify `dot_man/cli/deploy_cmd.py` — inline loops delegate to engine (Task 3).
- Modify `dot_man/hooks.py` — delete moved code (`HOOK_FILE_PATTERN`, `find_hook_script`, `resolve_hook_files`, now-unused imports) (Task 6).
- Modify `tests/test_hook_scripts.py` — fixture patches repoint to `dot_man.hook_engine` (Task 6).
- Modify `tests/test_navigate_helpers.py` — three `run_branch_hooks` tests patch `dot_man.hook_engine.subprocess` (Task 2).
- Modify `docs/concepts/hooks.md`, `CHANGELOG.md`, `TODO.md` (Task 7).

---

### Task 1: Engine module with resolve pipeline

**Files:**
- Create: `dot_man/hook_engine.py`
- Test: `tests/test_hook_engine.py`

**Interfaces:**
- Consumes: `HOOK_ALIASES`, `REPO_DIR`, `DOT_MAN_DIR` from `dot_man.constants`; `ConfigurationError` from `dot_man.exceptions`.
- Produces: `HookContext` (frozen dataclass), `resolve_hook(hook, context)`, `find_hook_script(name)` for Tasks 2–6.

- [ ] **Step 1: Write the failing resolve tests**

```python
"""Tests for dot_man/hook_engine.py resolve pipeline."""

import shlex
from pathlib import Path
from unittest.mock import patch

import pytest

from dot_man.exceptions import ConfigurationError
from dot_man.hook_engine import HookContext, find_hook_script, resolve_hook


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hook_engine.py -q`
Expected: FAIL — `dot_man.hook_engine` does not exist (ERROR on collect/import).

- [ ] **Step 3: Write minimal implementation**

```python
"""Unified hook resolution and execution (the executable hook schema)."""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .constants import DOT_MAN_DIR, HOOK_ALIASES, REPO_DIR
from .exceptions import ConfigurationError

HOOKS_DIR = DOT_MAN_DIR / "hooks"

HOOK_FILE_PATTERN = re.compile(r"(?<![\w/:\\])file:([^\s;|&\"']+)")
HOOK_FILE_ESCAPE_PATTERN = re.compile(r"\\(file:[^\s;|&\"']+)")


@dataclass(frozen=True)
class HookContext:
    """Values available to hook placeholder resolution."""

    section_name: str = ""
    config_name: str = ""
    config_root: str = ""
    paths: tuple[str, ...] = field(default_factory=tuple)
    branch: str = ""

    def placeholders(self) -> dict[str, str]:
        """Canonical vocabulary; `{qs_config}` is the deprecated spelling."""
        return {
            "section_name": self.section_name,
            "config_name": self.config_name,
            "config_root": self.config_root,
            "paths": " ".join(self.paths),
            "branch": self.branch,
            "qs_config": self.config_name,
        }


def find_hook_script(name: str) -> Path | None:
    """Find a hook script: `<repo>/hooks/` first, global dir fallback.

    Names escaping the hooks directory never match.
    """
    for hooks_dir in (REPO_DIR / "hooks", HOOKS_DIR):
        if not hooks_dir.is_dir():
            continue
        candidate = hooks_dir / name
        try:
            inside = candidate.resolve().is_relative_to(hooks_dir.resolve())
        except OSError:
            continue
        if inside and candidate.is_file():
            return candidate
    return None


def resolve_hook(hook: str | None, context: HookContext) -> str | None:
    """Resolve one hook string: alias, then `{x}`, then `file:` tokens."""
    if not hook:
        return None
    resolved = HOOK_ALIASES.get(hook, hook)
    for name, value in context.placeholders().items():
        if value:
            resolved = resolved.replace("{" + name + "}", value)
    searched = [REPO_DIR / "hooks", HOOKS_DIR]

    def _replace(match: re.Match[str]) -> str:
        script = match.group(1)
        path = find_hook_script(script)
        if path is None:
            dirs = ", ".join(f"'{d}'" for d in searched)
            raise ConfigurationError(
                f"Hook script '{script}' not found. Searched: {dirs}."
            )
        if not os.access(path, os.X_OK):
            path.chmod(0o755)
        return shlex.quote(str(path))

    resolved = HOOK_FILE_PATTERN.sub(_replace, resolved)
    return HOOK_FILE_ESCAPE_PATTERN.sub(r"\1", resolved)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_hook_engine.py -q`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add dot_man/hook_engine.py tests/test_hook_engine.py
git commit -m "feat(hooks): add hook_engine resolve pipeline"
```

---

### Task 2: Engine runner plus navigate migration

**Files:**
- Modify: `dot_man/hook_engine.py` (append `run_hooks`)
- Modify: `dot_man/cli/navigate_cmd.py` (delete `_run_shell_hooks` body, delegate; `run_branch_hooks` delegates)
- Modify: `tests/test_hook_engine.py` (append run tests)
- Modify: `tests/test_navigate_helpers.py` (repoint three subprocess patches to `dot_man.hook_engine.subprocess`)

**Interfaces:**
- Consumes: `run_hooks(commands, label, env=None)` contract — prints `Exec:` lines, warns and continues on failure, returns True if any hook failed (today's `_run_shell_hooks` contract verbatim).
- Produces: `run_hooks` for Tasks 3–4.

- [ ] **Step 1: Write the failing run tests** (append to `tests/test_hook_engine.py`)

```python
from unittest.mock import MagicMock


def _ctx():
    return HookContext(section_name="nvim")


def test_run_success():
    from dot_man.hook_engine import run_hooks

    with patch("dot_man.hook_engine.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0, stderr="")
        with patch("dot_man.hook_engine.ui"):
            assert run_hooks(["echo hi"], "Label", _ctx()) is False
    mock_sub.run.assert_called_once()


def test_run_failure_warns_and_continues():
    from dot_man.hook_engine import run_hooks

    with patch("dot_man.hook_engine.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=1, stderr="boom")
        with patch("dot_man.hook_engine.ui"):
            assert run_hooks(["false", "echo hi"], "Label", _ctx()) is True
    assert mock_sub.run.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hook_engine.py -q`
Expected: FAIL — `run_hooks` does not exist (AttributeError on import).

- [ ] **Step 3: Write minimal implementation** (append to `dot_man/hook_engine.py`)

```python
def run_hooks(
    commands: list[str],
    label: str,
    context: HookContext,
    env: dict[str, str] | None = None,
) -> bool:
    """Run shell hook commands; warn and continue on failure.

    Returns True if any hook failed (matches legacy contract).
    """
    import subprocess

    from .. import ui  # noqa: F401  (see note below)
```

STOP — wrong import path: `hook_engine.py` lives in `dot_man/`, so the
import is `from . import ui`, and the local `warn` helper lives in
`dot_man.cli.common` (importing it here would cycle: common → interface
→ commands → hook_engine → common). Use `ui.warn`-free plain prints
matching legacy output instead:

```python
def run_hooks(
    commands: list[str],
    label: str,
    context: HookContext,
    env: dict[str, str] | None = None,
) -> bool:
    """Run shell hook commands; warn and continue on failure.

    Returns True if any hook failed (matches legacy contract).
    """
    import subprocess

    from . import ui

    if not commands:
        return False
    ui.console.print()
    ui.console.print(f"[bold]{label}...[/bold]")
    hook_failed = False
    for cmd in commands:
        ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
        try:
            shell = os.environ.get("SHELL", "/bin/sh")
            result = subprocess.run(
                [shell, "-c", cmd],
                capture_output=True,
                text=True,
                env={**os.environ, **(env or {})},
            )
            if result.returncode != 0:
                hook_failed = True
                ui.console.print(
                    f"  [yellow]⚠ Hook failed (exit code {result.returncode})[/yellow]"
                )
                if result.stderr:
                    for line in result.stderr.splitlines()[:3]:
                        ui.console.print(f"    [dim]{line}[/dim]")
        except Exception as e:
            hook_failed = True
            ui.console.print(f"  [yellow]⚠ Failed to run command '{cmd}': {e}[/yellow]")
    if hook_failed:
        ui.console.print("[dim]  Some hooks failed - continuing anyway[/dim]")
    return hook_failed
```

Note: legacy used `warn()` from `cli.common` for the exception path;
engine uses a plain print to avoid a `cli` → engine → `cli` import
cycle. Output text is otherwise identical.

- [ ] **Step 4: Migrate navigate call sites** in `dot_man/cli/navigate_cmd.py`

Replace the body of `_run_shell_hooks(commands, label)` with a
delegating wrapper (name kept so `run_branch_hooks` below is a
one-line change):

```python
def _run_shell_hooks(commands: list[str], label: str) -> bool:
    """Run a list of shell commands as hooks. Returns True if any failed."""
    from ..hook_engine import HookContext, run_hooks

    return run_hooks(commands, label, HookContext())
```

`run_branch_hooks` keeps calling `_run_shell_hooks` — no change needed
there. Delete now-unused imports in `navigate_cmd.py` only if ruff
flags them (`os`, `subprocess`, `warn` may still be used elsewhere —
check with `uv run ruff check`).

- [ ] **Step 5: Repoint the three navigate helper tests**

In `tests/test_navigate_helpers.py`, the `TestRunBranchHooks`
tests patch `dot_man.cli.navigate_cmd.subprocess` — the subprocess
call now lives in the engine. Change exactly the patch target in
`test_runs_hooks`, `test_hook_failure_continues`, and
`test_deduplicates_hooks` from `"dot_man.cli.navigate_cmd.subprocess"`
to `"dot_man.hook_engine.subprocess"`. Assertions are unchanged.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_hook_engine.py tests/test_navigate_helpers.py tests/test_navigate_cmd.py -q`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add dot_man/hook_engine.py dot_man/cli/navigate_cmd.py tests/test_hook_engine.py tests/test_navigate_helpers.py
git commit -m "feat(hooks): unify shell execution in engine run_hooks"
```

---

### Task 3: Migrate deploy loops

**Files:**
- Modify: `dot_man/cli/deploy_cmd.py` (two inline loops delegate)

**Interfaces:**
- Consumes: `run_hooks` from Task 2.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test** (append to `tests/test_hook_engine.py` — documents the spec carve-out)

```python
def test_run_reports_failure_for_deploy_style_hooks():
    """Deploy migration: nonzero exits warn instead of vanishing."""
    from dot_man.hook_engine import run_hooks

    with patch("dot_man.hook_engine.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=2, stderr="denied")
        with patch("dot_man.hook_engine.ui") as mock_ui:
            assert run_hooks(["systemctl stop x"], "Pre", _ctx()) is True
    printed = " ".join(str(c) for c in mock_ui.console.print.call_args_list)
    assert "exit code 2" in printed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_hook_engine.py::test_run_reports_failure_for_deploy_style_hooks -q`
Expected: FAIL — actually it will PASS already (Task 2 built it). This
step is a carve-out guard: if it passes, note that and move on — the
behavior is covered. Do NOT change implementation for a passing test.

- [ ] **Step 3: Migrate both deploy loops**

In `dot_man/cli/deploy_cmd.py`, replace the pre-hooks block:

```python
        # Execute Pre-Hooks
        if pre_hooks:
            ui.console.print("\n[bold]Running pre-deploy hooks...[/bold]")
            for cmd in pre_hooks:
                ui.console.print(f"  Exec: [cyan]{cmd}[/cyan]")
                try:
                    subprocess.run(cmd, shell=True, check=False)
                except Exception as e:
                    warn(f"Failed to run command '{cmd}': {e}")
```

with:

```python
        # Execute Pre-Hooks
        if pre_hooks:
            run_hooks(pre_hooks, "\nRunning pre-deploy hooks")
```

and the post-hooks block identically with `"\nRunning post-deploy hooks"`.
Add the import at the top of `deploy_cmd.py`:

```python
from ..hook_engine import run_hooks
```

A `HookContext()` default is not needed — `context` is required; pass
`HookContext()` explicitly? The signature in Task 2 requires context.
For deploy there is no single section, so pass an empty context:

```python
from ..hook_engine import HookContext, run_hooks
...
            run_hooks(pre_hooks, "\nRunning pre-deploy hooks", HookContext())
```

Check `subprocess`/`warn` still used elsewhere in `deploy_cmd.py`
before removing imports (run ruff after).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_deploy_cmd.py tests/test_hook_engine.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add dot_man/cli/deploy_cmd.py tests/test_hook_engine.py
git commit -m "feat(hooks): route deploy hooks through engine"
```

---

### Task 4: Migrate auto-detect resolution (fixes raw `{config_name}`)

**Files:**
- Modify: `dot_man/branch_ops.py` (`detect_hooks_for_changed_files`)
- Test: `tests/test_branch_ops.py` (append regression test)

**Interfaces:**
- Consumes: `resolve_hook`, `HookContext` from Task 1; `self.get_section()` and `self._find_section_for_file()` already exist in `BranchMixin`.
- Produces: resolved hook strings (placeholders filled when a section matches; literal when none does).

- [ ] **Step 1: Write the failing regression test** (append to the `TestDetectHooksForChangedFiles` class in `tests/test_branch_ops.py`; check the `FakeOps` helper at the top of that file for constructor shape — it takes `sections=` dict)

```python
    def test_auto_detected_alias_resolves_placeholders(self):
        """Auto-detected aliases must not ship raw {config_name}."""
        from dot_man.config import Section

        section = Section(name="qs", paths=[Path("/home/user/.config/quickshell/ii")])
        ops = FakeOps(sections={"qs": section})

        with patch(
            "dot_man.constants.HOOK_ALIASES",
            {"qs_reload": "qs -c {config_name} &"},
        ):
            with patch.dict(
                "dot_man.branch_ops.FILE_TO_HOOK_MAP",
                {".config/quickshell": "qs_reload"},
            ):
                hooks = ops.detect_hooks_for_changed_files(
                    ["/home/user/.config/quickshell/ii"]
                )
        assert hooks == ["qs -c ii &"]
```

First verify `FILE_TO_HOOK_MAP` is a module-level dict in
`dot_man/branch_ops.py` patchable via `patch.dict` (grep it; if it is a
function, patch that instead with `patch()` returning your map).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_branch_ops.py::TestDetectHooksForChangedFiles::test_auto_detected_alias_resolves_placeholders -q`
Expected: FAIL — output contains raw `{config_name}`.

- [ ] **Step 3: Write minimal implementation**

In `dot_man/branch_ops.py`, replace the alias-resolution block inside
`detect_hooks_for_changed_files`:

```python
                for pattern, hook_name in FILE_TO_HOOK_MAP.items():
                    ...
                        if hook_name in HOOK_ALIASES:
                            resolved_cmd: str = HOOK_ALIASES[hook_name]
                            hooks_to_run.add(resolved_cmd)
                        else:
                            ...
```

with engine resolution carrying the matched section's context:

```python
                from .hook_engine import HookContext, resolve_hook

                ...
                    section_name = self._find_section_for_file(file_str)
                    context = HookContext()
                    if section_name:
                        try:
                            section = self.get_section(section_name)
                            first = (
                                str(section.paths[0])
                                if section.paths
                                else ""
                            )
                            context = HookContext(
                                section_name=section_name,
                                config_name=Path(first).name if first else "",
                                config_root=str(Path(first).parent) if first else "",
                                paths=tuple(str(p) for p in section.paths),
                            )
                        except Exception:
                            context = HookContext()
                    for pattern, hook_name in FILE_TO_HOOK_MAP.items():
                        ...
                            resolved = resolve_hook(hook_name, context)
                            if resolved:
                                hooks_to_run.add(resolved)
                            else:
                                fallback...
```

Keep the existing `get_hook_for_config` fallback path unchanged —
only the `HOOK_ALIASES[hook_name]` line goes through the engine.
(`resolve_hook` on a bare alias name performs exactly the old lookup
first, so non-placeholder aliases resolve identically.)

Restructure minimally: hoist the existing `section_name =
self._find_section_for_file(file_path)` lookup above the
`FILE_TO_HOOK_MAP` loop (it already exists below the loop — move it
up, delete the duplicate).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_branch_ops.py -q`
Expected: all PASS, including the pre-existing `TestDetectHooksForChangedFiles` tests (their fixtures use placeholder-free aliases, which resolve identically).

- [ ] **Step 5: Commit**

```bash
git add dot_man/branch_ops.py tests/test_branch_ops.py
git commit -m "fix(hooks): resolve placeholders in auto-detected hooks"
```

---

### Task 5: Section delegates to engine

**Files:**
- Modify: `dot_man/section.py` (`_resolve_hook` builds context, delegates)
- Test: existing `tests/test_section.py`, `tests/test_config.py`, `tests/test_hook_scripts.py` (no new tests — behavior must be identical)

**Interfaces:**
- Consumes: `resolve_hook`, `HookContext` from Task 1.
- Produces: identical `pre_deploy`/`post_deploy`/`on_activate`/`on_deactivate` values as today.

- [ ] **Step 1: Confirm current behavior is pinned** (no new test — run existing suite as the RED baseline)

Run: `uv run pytest tests/test_section.py tests/test_config.py tests/test_hook_scripts.py -q`
Expected: PASS (baseline; any failure after Step 2 is a regression).

- [ ] **Step 2: Rewrite `_resolve_hook` to delegate**

Replace the body of `Section._resolve_hook` (after the `if not hook:
return None` guard) with context construction plus delegation:

```python
        from .hook_engine import HookContext, resolve_hook

        context = HookContext(section_name=self.name)
        if "{" in hook:
            context = HookContext(
                section_name=self.name,
                branch=self._get_current_branch(),
                paths=tuple(str(p) for p in self.paths),
                **self._config_names(),
            )
        return resolve_hook(hook, context)
```

with helper (place next to `_resolve_hook`):

```python
    def _config_names(self) -> dict[str, str]:
        """Derive config_root/config_name from the first tracked path."""
        if not self.paths:
            return {}
        first = self.paths[0]
        if first.exists() and first.is_dir():
            return {"config_root": str(first.parent), "config_name": first.name}
        if first.exists() and first.is_file():
            return {"config_root": str(first.parent), "config_name": first.name}
        expanded = first.expanduser()
        return {"config_root": str(expanded.parent), "config_name": expanded.name}
```

This preserves today's exact derivation (dir → parent+name,
file → parent+name, missing → expanded parent+name) and today's
eager branch lookup. Update the import at the top of `section.py`:
`from .hooks import resolve_hook_files` becomes
`from .hook_engine import HookContext, resolve_hook`.

- [ ] **Step 3: Run tests to verify identical behavior**

Run: `uv run pytest tests/test_section.py tests/test_config.py tests/test_hook_scripts.py tests/test_hook_engine.py -q`
Expected: all PASS. If any fail, the delegation diverged — fix the
engine, not the tests (existing tests encode the contract).

- [ ] **Step 4: Commit**

```bash
git add dot_man/section.py
git commit -m "refactor(hooks): Section delegates resolution to engine"
```

---

### Task 6: Slim down hooks.py plus fixture repoint

**Files:**
- Modify: `dot_man/hooks.py` (delete moved code)
- Modify: `tests/test_hook_scripts.py` (fixture repoint, 2 lines)

**Interfaces:**
- Consumes: engine owns `HOOK_FILE_PATTERN`, `find_hook_script`, `resolve_hook_files` logic now.
- Produces: `hooks.py` keeps `HOOKS_DIR`, `HOOK_COMMANDS`, `run_hook`, `run_switch_hooks`, `run_checkout_hooks`, `list_hooks`, `create_hook`, `delete_hook`, `ensure_hooks_dir` — untouched.

- [ ] **Step 1: Delete moved code from `hooks.py`**

Remove: `HOOK_FILE_PATTERN`, `find_hook_script()`,
`resolve_hook_files()`, and any imports left unused by the removal
(`re`, `shlex`, `ConfigurationError`, `REPO_DIR` — verify each with
`uv run ruff check dot_man/hooks.py` after and delete what it flags).

- [ ] **Step 2: Repoint the test fixture** in `tests/test_hook_scripts.py`

```python
    with (
        patch("dot_man.hook_engine.REPO_DIR", tmp_path / "repo"),
        patch("dot_man.hook_engine.HOOKS_DIR", global_hooks),
    ):
```

(replacing the `dot_man.hooks.*` targets; semantics identical).

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_hook_scripts.py tests/test_hooks_new.py tests/test_hook_engine.py -q`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add dot_man/hooks.py tests/test_hook_scripts.py
git commit -m "refactor(hooks): slim hooks.py to script-file machinery"
```

---

### Task 7: Docs from schema plus full gate

**Files:**
- Modify: `docs/concepts/hooks.md` (rewrite from spec §4)
- Modify: `CHANGELOG.md`, `TODO.md`
- Test: full suite plus gate.

- [ ] **Step 1: Rewrite `docs/concepts/hooks.md`**

Cover exactly the schema: the two hook kinds (section strings vs
global `pre_<cmd>` scripts), the resolve pipeline order, the
vocabulary table, `file:` references with repo/global lookup, the
`\file:` escape, and the warn-and-continue runner. Document the
deferred item in one line (global scripts fire for switch/checkout
only — wider firing is a follow-up).

- [ ] **Step 2: Update `CHANGELOG.md` (Unreleased → Added)**

```markdown
- **Unified hook engine** — new `dot_man/hook_engine.py`: one resolve path (alias → placeholders → `file:`) and one shell runner for all hook shell; auto-detected hooks now resolve `{config_name}`; deploy hook failures warn instead of vanishing
```

- [ ] **Step 3: Update `TODO.md`**

Check off the "Global hook schema first" bullet; add a follow-up
bullet for deferred global firing (deploy/save/add/…) so the
deferral is tracked, not lost.

- [ ] **Step 4: Run the full Pre-Push Quality Checklist**

```bash
uv run black dot_man/ tests/
uv run ruff check dot_man/ tests/
uv run mypy dot_man/ --ignore-missing-imports
uv run pytest tests/ -v
uv run pytest --cov=dot_man --cov-report=term
```

All green with zero errors and coverage not decreased, or fix forward
— never amend a failed commit.

- [ ] **Step 5: Commit**

```bash
git add docs/concepts/hooks.md CHANGELOG.md TODO.md
git commit -m "docs: unified hook engine schema and changelog"
```

---

## Self-Review

**1. Spec coverage:** §1 problem rows → Tasks 1–6 (row 4 global scripts untouched per §2 Out; row 5 `{{ }}` untouched per §2 Out). §3 surface → Task 1. §4 pipeline/vocabulary/escape → Tasks 1, 5 (vocabulary), Task 4 (context rule). §5 migration list → Tasks 2–5 (config_detector correctly absent — verified it returns raw names resolved later at Section load). §6 semantics + deploy carve-out → Tasks 2–3. §7 tests/docs → Tasks 1–7. No gaps.

**2. Placeholder scan:** every step has exact file paths, function names, and code blocks. The two conditional spots are explicit: Task 3 Step 2 (passing test = note-and-move-on, no implementation change) and Task 4 Step 1 (verify `FILE_TO_HOOK_MAP` shape first, with both branches spelled out). No TBDs.

**3. Type consistency:** `resolve_hook(hook: str | None, context: HookContext) -> str | None`, `run_hooks(commands: list[str], label: str, context: HookContext, env: dict[str, str] | None = None) -> bool`, `HookContext` frozen dataclass with `str`/`tuple[str, ...]` fields — identical in Tasks 1–5. `find_hook_script(name: str) -> Path | None` identical in Tasks 1 and 6.
