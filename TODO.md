# TODO

**Status:** v1.4.0 · 1683 tests passing · coverage 84% · docs site live

---

## 🔜 Next Up

### Shell Completions

- [x] **`add` command** — complete local file paths
- [x] **`bootstrap` command** — complete package-manager names

### Init Wizard Hook Suggestions

- [ ] When init wizard detects popular tools, suggest appropriate `post_deploy` hooks
- [ ] For shell configs — suggest `on_activate`/`on_deactivate` hooks
- [ ] Show example of how hooks work when adding the first section

### User Experience

- [ ] **Consistent exit codes** — replace the `sys.exit(1)` / `raise SystemExit(1)` mix
- [ ] **Centered error handling** — route all commands through `handle_exception()` from `common.py`

### Extensibility

- [ ] **Hook scripts directory** — support executing custom hook scripts from a folder
- [ ] **Plugin API** — extension mechanism for third-party tools
- [ ] **Make placeholders available as template variables** — `{{config_name}}` in config values

---

## 🧪 Coverage Focus (overall 84%, target: raise the floor)

Lowest-covered modules:

| Module | Coverage |
|--------|----------|
| `cli/bootstrap_cmd.py` | 15% |
| `cli/export_cmd.py` | 25% |
| `cli/completions.py` | 62% |
| `cli/watch_cmd.py` | 65% |
| `core.py` | 66% |
| `cli/audit_cmd.py` | 68% |
| `cli/navigate_cmd.py` | 68% |
| `cli/revert_cmd.py` | 68% |

---

## 🏗️ Refactoring & Architecture

- [ ] **Break up `_handle_branch_navigate`** (`navigate_cmd.py`, 211 lines)
- [ ] **Split long functions in `files.py`** — `copy_directory` (92 lines), `smart_save_file` (88 lines)
- [ ] **Reduce nesting in `save_deploy_ops.py`** — `deploy_section`/`deploy_item` at 7 levels each
- [ ] **Remove deprecated `checkout`** (`log_cmd.py`) once the deprecation window ends
- [ ] **Reduce `type: ignore` count** — some mask real typing issues

---

## 📚 Documentation

- [x] **Full docs site** — mkdocs Material hosted on GitHub Pages
- [ ] **Hook system docs** — document all hook aliases, placeholders, and examples
- [ ] **Migration guides** — detailed chezmoi/yadm/stow import walkthroughs
- [ ] **Architecture deep-dive** — how mixins work, how config loading works

---

## ✅ Recently Completed

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
