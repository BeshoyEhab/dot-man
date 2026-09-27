# Unified Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three onboarding paths with the init wizard as the single interactive flow.

**Architecture:** Teach-by-doing insertions into the existing `run_setup_wizard` (already shared by first-run and `init`); delete the tutorial menu/sections from `onboarding.py`; fix staleness (`switch`, `--help`, wrong `init` flags) wherever touched.

**Tech Stack:** Python 3.10+, Click, Rich, pytest.

**Spec:** `docs/superpowers/specs/2026-09-27-unified-onboarding-design.md` — the plan argues from the spec; executors read both.

## Global Constraints

- Python 3.10+ compatible.
- Black line length 88; ruff `E, F, W, I`; mypy `--ignore-missing-imports` zero errors.
- Every command runs under `uv run`.
- Coverage must not decrease (currently 86%).
- Never `sys.exit()`; use `raise SystemExit(ExitCode.X)`, `error()`, or `handle_exception()`.
- `config_tutorial.py` is untouched. `init --no-wizard`, first-run gating, sentinel logic, and `_offer_first_branch` flow are unchanged (only its `switch` wording).

---

## File Map

- Modify `dot_man/cli/onboarding.py` — finale + branch-offer wording (Task 1); delete tutorial menu/sections/scaffolding (Task 3).
- Modify `dot_man/cli/init_cmd.py` — hook-suggestion line, hook-example helper + call, two why-lines, terminal status run (Task 2).
- Modify `tests/test_onboarding.py` — finale test (Task 1); delete/refresh tutorial tests (Task 3).
- Modify `tests/test_init_cmd.py` — update `switch` assertions (Task 1); wizard insertion tests (Task 2).
- Modify `docs/commands/init.md`, `CHANGELOG.md`, `TODO.md` (Task 4).

---

### Task 1: Staleness fixes (`switch`, `--help`, init flags)

**Files:**
- Modify: `dot_man/cli/onboarding.py` (finale panel + 2 branch-offer lines)
- Modify: `tests/test_onboarding.py` (finale test), `tests/test_init_cmd.py` (`switch` assertions)
- Test: same files.

**Interfaces:**
- Consumes: nothing new.
- Produces: corrected user-facing copy for Tasks 2–3.

- [ ] **Step 1: Fix the three `switch` wordings and the finale help line**

In `dot_man/cli/onboarding.py`, make exactly these replacements:

1. Finale panel: `"  [cyan]dot-man switch <name>[/cyan]   — switch branch\n"` → `"  [cyan]dot-man navigate <name>[/cyan] — switch configuration\n"`
2. Finale panel: `"  [cyan]dot-man --help[/cyan]          — full command list",` → `"  [cyan]dot-man help-all[/cyan]        — full command list",`
3. `_offer_first_branch` decline path: `"  [bold cyan]dot-man switch <branch-name>[/bold cyan]\n"` → `"  [bold cyan]dot-man navigate <branch-name>[/bold cyan]\n"`
4. `_offer_first_branch` except path: `f"[dim]Try manually: [bold]dot-man switch {branch_name}[/bold][/dim]"` → `f"[dim]Try manually: [bold]dot-man navigate {branch_name}[/bold][/dim]"`

- [ ] **Step 2: Write the failing finale test** (append to `tests/test_onboarding.py`)

```python
    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="s")
    @patch("dot_man.cli.onboarding._console")
    def test_finale_teaches_navigate_and_help_all(
        self, mock_console, mock_prompt, mock_init, mock_branch, mock_onboarded
    ):
        """Finale panel teaches navigate/help-all, never switch."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "dot-man navigate" in output
        assert "help-all" in output
        assert "dot-man switch" not in output
```

(The menu still exists at this point, so `Prompt.ask` returns `"s"` to skip it.)

- [ ] **Step 3: Run tests to verify the new test fails, then passes**

Run: `uv run pytest tests/test_onboarding.py::TestRunOnboarding::test_finale_teaches_navigate_and_help_all -q`
Expected: FAIL before Step 1, PASS after. (If implementing Step 1 first, verify FAIL by stashing: not needed — the test asserts strings Step 1 introduces.)

- [ ] **Step 4: Update `switch` assertions in init tests**

Run: `rg -n "switch" tests/test_init_cmd.py`
Update every match to `navigate` (e.g. `test_quick_start_shows_switch_command` and its assertions). Then run: `uv run pytest tests/test_init_cmd.py tests/test_onboarding.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add dot_man/cli/onboarding.py tests/test_onboarding.py tests/test_init_cmd.py
git commit -m "fix(onboarding): teach navigate and help-all, not switch"
```

---

### Task 2: Wizard teach-by-doing insertions

**Files:**
- Modify: `dot_man/cli/init_cmd.py` (`_wizard_prompt_for_files`, `_wizard_save_and_summarize`, `run_setup_wizard`, `_wizard_show_next_steps`, new `_format_hook_example` helper)
- Test: `tests/test_init_cmd.py` (append 4 tests)

**Interfaces:**
- Consumes: `get_auto_hooks_for_config(section_name, paths)` from `dot_man.config_detector` (already imported in `init_cmd.py`); status command callback `dot_man.cli.status_cmd.status.callback(verbose, secrets, json_output)`.
- Produces: hook-aware wizard output consumed by Task 3's shrunk first-run (no signature changes).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_init_cmd.py`)

```python
def test_hook_suggestion_shown(tmp_path):
    """Detected tool hooks are announced inline while prompting."""
    from dot_man.cli import init_cmd

    target = tmp_path / ".bashrc"
    target.write_text("export X=1")
    with (
        patch("dot_man.cli.init_cmd.ui") as mock_ui,
        patch(
            "dot_man.cli.init_cmd.get_auto_hooks_for_config",
            return_value={"post_deploy": "echo reloaded"},
        ),
    ):
        mock_ui.confirm.return_value = True
        init_cmd._wizard_prompt_for_files([(str(target), "Bash shell", "bashrc")], [])
    printed = " ".join(str(c) for c in mock_ui.console.print.call_args_list)
    assert "post_deploy" in printed
    assert "echo reloaded" in printed


def test_format_hook_example():
    from dot_man.cli.init_cmd import _format_hook_example

    assert _format_hook_example("bash", None) is None
    line = _format_hook_example("bash", "echo reloaded")
    assert "bash" in line
    assert "echo reloaded" in line


def test_show_next_steps_mentions_navigate():
    from dot_man.cli import init_cmd

    with patch("dot_man.cli.init_cmd.ui") as mock_ui:
        with patch("dot_man.cli.init_cmd.status_cmd") as mock_status:
            init_cmd._wizard_show_next_steps([("~/.bashrc", "bashrc")])
    printed = " ".join(str(c) for c in mock_ui.console.print.call_args_list)
    assert "navigate" in printed
    mock_status.callback.assert_called_once_with(False, False, False)
```

Note for the third test: `_wizard_show_next_steps` must import the
status command as `from . import status_cmd` (module import, so the
patch target `dot_man.cli.init_cmd.status_cmd` resolves). Patching the
module object — not the command — keeps the real `status` callback
out of the unit test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_init_cmd.py -q -k "hook_suggestion or hook_example or next_steps_mentions"`
Expected: FAIL — `_format_hook_example` undefined; no hook line printed; no status call.

- [ ] **Step 3: Write minimal implementation** in `dot_man/cli/init_cmd.py`

(a) In `_wizard_prompt_for_files`, inside the generic `if path.exists():`
branch after the `Found:` print, insert:

```python
            auto_hooks = get_auto_hooks_for_config(section_name, [path_str])
            if auto_hooks:
                for hook_type, hook_cmd in auto_hooks.items():
                    ui.console.print(
                        f"    [dim]Will run {hook_type} hook: {hook_cmd}[/dim]"
                    )
```

(b) Add the pure helper next to the other `_wizard_*` helpers:

```python
def _format_hook_example(section_name: str, hook_cmd: str | None) -> str | None:
    """One-line hook example for the first tracked section."""
    if not hook_cmd:
        return None
    return f"  [dim]Example: [{section_name}] runs '{hook_cmd}' after deploy[/dim]"
```

(c) In `_wizard_save_and_summarize`, after the `success(f"Added ...")`
block inside `if files_to_add:`, insert:

```python
        first_section = files_to_add[0][1]
        try:
            first_hook = dotman_config.get_section(first_section).post_deploy
        except Exception:
            first_hook = None
        example = _format_hook_example(first_section, first_hook)
        if example:
            ui.console.print(example)
```

(d) Why-lines — insert exactly two prints. In `run_setup_wizard`
after the `"Let's get your dotfiles set up! ..."` print:

```python
    ui.console.print(
        "[dim]Each file you track gets snapshotted, so you can `dot-man navigate` between configurations.[/dim]"
    )
```

In `_wizard_show_next_steps`, at the top:

```python
    ui.console.print(
        "[dim]Your files are tracked. `dot-man status` shows them live below.[/dim]"
    )
```

(e) Terminal status run — end of `_wizard_show_next_steps`:

```python
    try:
        from . import status_cmd

        status_cmd.status.callback(False, False, False)
    except Exception as e:
        logging.debug("Closing status display skipped: %s", e)
```

(`logging` is already imported in `init_cmd.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_init_cmd.py -q`
Expected: all PASS (existing end-to-end wizard tests also execute the new print lines, holding coverage).

- [ ] **Step 5: Commit**

```bash
git add dot_man/cli/init_cmd.py tests/test_init_cmd.py
git commit -m "feat(wizard): teach-by-doing insertions and closing status run"
```

---

### Task 3: Delete tutorial paths, shrink first-run

**Files:**
- Modify: `dot_man/cli/onboarding.py` (delete sections/menu/scaffolding, shrink `run_onboarding`)
- Modify: `tests/test_onboarding.py` (delete/refresh tutorial tests)

**Interfaces:**
- Consumes: Task 2's wizard (unchanged signatures).
- Produces: single-path first-run for Task 4 docs.

- [ ] **Step 1: Delete dead code from `dot_man/cli/onboarding.py`**

Delete: `_section_architecture`, `_section_manual`, the `Prompt.ask`
choice menu in `run_onboarding`, `_confirm_next`, and the module
constants used only by deleted sections (`ARCH_OVERVIEW`,
`BRANCH_DIAGRAM`, `INIT_FLOW`, `COMPONENTS`). Rewrite
`run_onboarding` to: welcome (`_show_welcome` minus the Tutorial Menu
panel) → `_run_init_direct()` → `_offer_first_branch()` if init ok →
finale panel (Task 1 text) → `mark_onboarded()`; keep the
`KeyboardInterrupt` handler and sentinel semantics verbatim. Keep
`_show_welcome` (minus menu panel), `_section_rule`, `_run_init_direct`,
`_offer_first_branch`, `mark_onboarded`, `is_first_run`. Delete
`_pause`, `_code_block`, `_ascii_panel` only if ruff reports them
unused afterward (check with `uv run ruff check dot_man/cli/onboarding.py`;
`_section_rule` stays — used by init/branch helpers).

In `_show_welcome`, delete the `menu_text` panel block and change
`"We'll walk you through a short tutorial\n" "before setting
everything up automatically.\n\n"` to `"We'll get your dotfiles
tracked in about a minute.\n\n"` and `"The tutorial has 2 sections
and takes about 2 minutes."` to `"No reading required — just answer
a few prompts."`.

- [ ] **Step 2: Rewrite the tutorial-pinned tests** in `tests/test_onboarding.py`

Delete classes `TestConfirmNext`, `TestSectionArchitecture`,
`TestSectionManual`. Delete `test_choice_architecture`,
`test_choice_manual`, `test_choice_skip`,
`test_confirm_false_skips_manual`. Update
`test_prints_welcome_art_and_menu` → rename to
`test_prints_welcome_art_without_menu`, asserting the Tutorial Menu
panel is gone (assert `"Tutorial Menu" not in output` plus the
existing art assertions). Replace the deleted choice tests with one
straight-through test (no `Prompt.ask` patch — the menu is gone):

```python
    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._console")
    def test_straight_through_runs_wizard_and_branch(
        self, mock_console, mock_init, mock_branch, mock_onboarded
    ):
        """No menu: welcome goes straight to init, branch, sentinel."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()
```

Keep `test_init_failure_skips_branch` and `test_keyboard_interrupt`
but drop their `_confirm_next`/`_section_*` patches (patched names
must exist or `patch()` raises `AttributeError`).

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run pytest tests/test_onboarding.py -q`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add dot_man/cli/onboarding.py tests/test_onboarding.py
git commit -m "refactor(onboarding): single wizard path, drop tutorial sections"
```

---

### Task 4: Docs from the single path plus full gate

**Files:**
- Modify: `docs/commands/init.md`, `CHANGELOG.md`, `TODO.md`
- Test: full suite plus gate.

- [ ] **Step 1: Fix `docs/commands/init.md` flags**

The Options table and Examples list `--yes` and `--verbose`, which
`dot-man init` does not accept (real flags: `--force`,
`--no-wizard`, `--sandbox`, `--import`). Replace the table rows and
the `--yes` example with the real flags:

| Flag | Description |
|------|-------------|
| `--force` | Reinitialize even if already exists |
| `--no-wizard` | Skip interactive setup wizard |
| `--sandbox` | Test init in a temporary sandbox directory |
| `--import` | Import from an existing git repository |

Example block: replace `# Non-interactive setup / dot-man init --yes`
with `# Manual setup without the wizard / dot-man init --no-wizard`.

- [ ] **Step 2: Update `CHANGELOG.md` (Unreleased → Added)**

```markdown
- **Unified onboarding** — the init wizard is the single interactive path (first-run tutorial menu and Architecture/Manual sections removed; `config tutorial` stays as opt-in reference); wizard suggests hooks inline, shows a hook example, and ends with a live `status`; finale teaches `navigate`/`help-all`
```

- [ ] **Step 3: Update `TODO.md`**

Check off the "One guided onboarding" bullet (appending the hook-suggestion and example coverage to its text); update the status line counts to the gate output of Step 4.

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
git add docs/commands/init.md CHANGELOG.md TODO.md
git commit -m "docs: unified onboarding changelog and checklist"
```

---

## Self-Review

**1. Spec coverage:** §3 single flow → Tasks 2–3 (wizard insertions + shrunk first-run with `status` close). §4 insertions → Task 2 (hook line, example, why-lines, status run). §5 deletions → Task 3 (functions, constants, menu); staleness → Task 1 (finale/branch) + Task 4 (`init.md` flags found during exploration). §6 entry points → untouched by design, no task needed. §7 tests/docs → Tasks 1–4. No gaps.

**2. Placeholder scan:** every step names exact strings, functions, and assertions. Two honest investigation-in-miniature spots, both fully specified: Task 1 Step 4 (`rg` + update matches) and Task 3 helper pruning (delete only what ruff flags). No TBDs.

**3. Type consistency:** `status_cmd.status.callback(False, False, False)` matches `status(verbose, secrets, json_output)`; `_format_hook_example(section_name: str, hook_cmd: str | None) -> str | None` used consistently; `get_auto_hooks_for_config(section_name, [path_str])` matches its `(section_name: str, paths: list[str])` signature.
