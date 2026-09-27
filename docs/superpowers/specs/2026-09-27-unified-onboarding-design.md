# Unified Onboarding — Design Spec

Date: 2026-09-27 · Status: approved design, awaiting implementation plan
Approach: init wizard becomes the only flow (no new wizard, no router).

## 1. Problem

Three learning surfaces confuse new users: the first-run tutorial menu
(Architecture / Manual / Skip in `onboarding.py`), the init setup
wizard (`run_setup_wizard` in `init_cmd.py`, also invoked by first-run),
and the expert quick-start (`show_quick_start` behind `--no-wizard`) —
plus the 705-line `config tutorial` reference. The finale panel teaches
the deprecated `switch` command and mislabels `--help` as the full list.

## 2. Scope

**In:** one interactive path (`run_setup_wizard` for first-run and
`init`); teach-by-doing insertions; finale staleness fixes; deletion of
tutorial sections and menu scaffolding.

**Out (explicit):** `config_tutorial.py` untouched (opt-in reference);
`--no-wizard` quick-start kept for experts/scripting; first-run gating,
sentinel logic, and branch offer unchanged; no new flags.

## 3. The single flow

First run: welcome banner → `run_setup_wizard` → branch offer →
finale. `dot-man init`: wizard directly (unchanged entry). Wizard
phase structure unchanged: detect → confirm per file → optional custom
files → save + commit → optional remote → next steps, ending with a
real `status` run so the user sees their tracked file live.

## 4. Teach-by-doing insertions

Only new behavior, all inline, no new required prompts:

- Detected tool with a known hook (`get_auto_hooks_for_config`): the
  confirm prompt gains one line, e.g. ``Will reload with
  `quickshell_reload` after deploy. OK?``
- First tracked section prints a one-line hook example.
- Each phase gets a one-line "why" (e.g. snapshots enable `navigate`).

## 5. Deletions and staleness fixes

Delete from `onboarding.py`: `_section_architecture`,
`_section_manual`, the choice menu, `_confirm_next` scaffolding
(~250 lines). Finale panel: `switch` → `navigate`; `--help` "full
command list" → `help-all`.

## 6. Entry points and flags

`main.py` gating unchanged. `init --no-wizard` unchanged. Interrupt
semantics unchanged (no sentinel → wizard reruns). No new flags.

## 7. Testing

TDD: new tests for hook-suggestion lines and finale text; existing
wizard/onboarding tests updated only where they pin deleted paths
(menu choices, tutorial sections); `config_tutorial` tests untouched.
Full quality gate (black, ruff, mypy, pytest, coverage must not
decrease).
