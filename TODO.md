# TODO

**Status:** v1.4.0 · 1832 tests passing · coverage 86% · docs site live

---

## 🔜 Next Up

### Simplification & Real-World Usability

> Lots of features, most unused or overwhelming. Goal: a normal user
> productive in 5 minutes without reading reference docs.

- [x] **Define the 5-minute happy path** — `init` → `add` → `status` → `navigate`; stated in quickstart intro, encoded in every command's hints
- [x] **Trim the command surface** — two-level help: `help` shows happy-path commands only, `help-all` shows everything, plus a man page (`docs/man/dot-man.1`, `help --install-man`); `switch`/`checkout` shims stay until v2.0 (`navigate` is canonical)
- [x] **Sensible defaults over configuration** — minimal config already works; default `dot-man.toml` slimmed to header + 2 examples, `config list` hides internals and points at `config defaults`
- [x] **One guided onboarding** — a single `init` wizard path that ends with a working tracked file (no tutorial-vs-wizard-vs-manual confusion); suggests `post_deploy`/`on_activate` hooks when popular tools are detected and shows a hook example with the first section
- [x] **Every command teaches the next step** — shared `ui.next_steps()` after `init`/`add`/`deploy` and dirty `status` (silent when clean or `--json`); no dead ends
- [x] **Docs: real-world-first** — "Start in 5 minutes" guide first in Getting Started nav; per-page example rewrite deferred as a separate pass

### Shell Completions

- [x] **`add` command** — complete local file paths
- [x] **`bootstrap` command** — complete package-manager names

### User Experience

- [x] **Consistent exit codes** — `ExitCode` enum (`OK=0`, `ERROR=1`, `USAGE=2`, `CONFIG=7`, `INTERRUPTED=130`); all `sys.exit()` replaced with `raise SystemExit(...)`
- [x] **Centered error handling** — `DotManGroup.invoke()` routes all commands through `handle_exception()` from `common.py`

### Extensibility

- [x] **Hook scripts directory** — `file:<script> [args]` tokens in any section hook resolve from `<repo>/hooks/` (versioned) with `~/.config/dot-man/hooks/` fallback
- [ ] **Plugin API** — ⏸️ parked for now (too big); revisit after the simplification track
- [x] **Template variables in config values** — `{{section_name}}`/`{{config_name}}`/`{{branch}}`/`{{paths}}` + machine vars + conditionals render at load; hook `{x}` stays as shell-friendly spelling

---

## 🧪 Coverage Focus (overall 86%, target: raise the floor)

Lowest-covered modules (regenerated 2026-09-27):

| Module | Coverage |
|--------|----------|
| `cli/completions.py` | 62% |
| `cli/watch_cmd.py` | 65% |
| `core.py` | 66% |
| `cli/navigate_cmd.py` | 68% |
| `cli/navigate_preview.py` | 69% |
| `backups.py` | 71% |
| `cli/init_cmd.py` | 71% |
| `cli/backup_cmd.py` | 72% |

---

## 🏗️ Refactoring & Architecture

- [ ] **Break up `_handle_branch_navigate`** (`navigate_cmd.py`, 233 lines)
- [ ] **Split long functions in `files.py`** — `copy_directory` (95 lines), `smart_save_file` (90 lines)
- [ ] **Reduce nesting in `save_deploy_ops.py`** — `deploy_section`/`deploy_item` at 7 levels each
- [ ] **Remove deprecated `switch` + `checkout` shims** (`switch_cmd.py`, `log_cmd.py`) in v2.0 — policy: majors remove/change APIs, minors only add deprecation notices; `navigate` is canonical
- [ ] **Reduce `type: ignore` count** — some mask real typing issues

---

## 📚 Documentation

- [x] **Full docs site** — mkdocs Material hosted on GitHub Pages
- [x] **Global hook schema first** — one engine (`dot_man/hook_engine.py`) unifying section hooks, `file:` scripts, global `pre_<cmd>`/`post_<cmd>` scripts, aliases, and placeholders; docs rewritten from it
- [x] **Fire global hook scripts in more commands** — `pre_<cmd>`/`post_<cmd>` now fire for `deploy`, `save`, and `add` (warn-and-continue; skipped when idle)
- [ ] **Migration guides** — detailed chezmoi/yadm/stow import walkthroughs
- [ ] **Architecture deep-dive** — how mixins work, how config loading works

---

## ✅ Recently Completed

### Unreleased

- [x] **Happy path guidance** — `next_steps` in `add`/`deploy`/dirty `status`/wizard; fixed `add` test isolation leak (`add_cmd.REPO_DIR` now patched)
- [x] **Sensible defaults surface** — slim default template, curated `config list`
- [x] **Template variables in config values** — section + machine vars + conditionals render at load
- [x] **Hook scripts directory** — `file:` tokens in section hooks, repo `hooks/` + global fallback
- [x] **Consistent exit codes** — `ExitCode` enum; zero `sys.exit()` calls left in `dot_man/`
- [x] **Centralized error handling** — `DotManGroup.invoke()` routes every command through `handle_exception()`; `navigate`/`bootstrap`/`config get`/`doctor` fixed to use shared helpers
- [x] **New suites** — `test_exit_codes`, `test_hook_scripts`, `test_help_cmd`, `test_hook_engine`, `test_config_template_vars`; suite 1811 passed, coverage 84% → 86%

### v1.4.0

- [x] **Decorator-driven completion engine** — `@completes(path, param=...)` registry gathers commands, subcommands, static/dynamic values and defaults from the CLI itself
- [x] **Fish completions rebuilt** — fully dynamic delegating script; invalid/stale entries impossible
- [x] **Defaults & choices surfaced** in option completions; aliases labeled `(alias)`
- [x] **Stale install fix** — completion scripts overwrite outdated installed copies

### Earlier

- [x] Symlink deploy mode + interactive symlink handling (v1.2.x)
- [x] Template substitution & conditionals, vault key rotation (v1.3.0)
- [x] Deduplicated deploy logic, unified config loading, silent-`except` cleanup (v1.2.1)
- [x] Long-function breakdowns: `_run_interactive_tutorial`, `run_setup_wizard`, remote `setup`
