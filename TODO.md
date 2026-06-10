# TODO

---

## ✅ Completed (v1.2.0)

### Bugs
- [x] Missing f-string prefix in `dotman_config.py:96` — fixed
- [x] Stale `"dot-man.ini"` reference in `status_ops.py:158` — removed
- [x] `assert` in production code — all replaced with proper `if/error()` checks across `navigate_cmd.py`, `encrypt_cmd.py`, `import_cmd.py`

### Refactoring & Code Quality

- [x] **Consolidate `switch_cmd.py` → `navigate_cmd.py`** — `switch_cmd` is now a 17-line thin wrapper delegating to `_navigate_impl()`
- [x] **Remove duplicate `BranchParamType`** — moved from `switch_cmd.py`/`navigate_cmd.py` to `common.py`
- [x] **Deduplicate schema keys** — `VALID_SECTION_KEYS` defined once in `dotman_config.py`
- [x] **Unify `HOOK_ALIASES` and `UNIVERSAL_HOOKS`** — `constants.py` is canonical; `merge.py` imports it
- [x] **Silent `except: pass` cleanup** — added `logging.debug()`/`logging.warning()` to 11+ bare exceptions across `common.py`, `navigate_cmd.py`, `rollback_cmd.py`, `core.py`, `files.py`, `init_cmd.py`
- [x] **Generalized placeholder system** — `{qs_config}` → `{config_name}`, `{config_root}`, `{section_name}`, `{paths}`, `{branch}` in `Section._resolve_hook()`

### Features
- [x] **Symlink deploy mode** — `deploy_method = "symlink"` per section
- [x] **Symlink warning on save** — warns user when saving to symlinked paths
- [x] **Quickshell hook aliases** — `quickshell_reload`, `quickshell_restart`, `quickshell_validate` with `{qs_config}` → `{config_name}` placeholder
- [x] **Migration onboarding** — init wizard shows import hints for chezmoi/yadm/stow
- [x] **Removed hard-coded quickshell kill/restart** — lifecycle now handled via user-defined hooks
- [x] **Shell completions** — `complete_sections` for `encrypt`, `complete_branches` for `export --branch`, `complete_commits` for `rollback`

### Test Coverage Improvements

| Module | Before | After | Gain |
|--------|--------|-------|------|
| `files.py` | 73% | **94%** | +21pp |
| `branch_ops.py` | 40% | **97%** | +57pp |
| `encryption.py` | 33% | **100%** | +67pp |
| `completions_cmd.py` | 12% | **94%** | +82pp |
| `section.py` | 70% | **95%** | +25pp |
| `save_deploy_ops.py` | 52% | **75%** | +23pp |
| `status_ops.py` | 59% | **89%** | +30pp |
| `core.py` | 58% | **66%** | +8pp |

New test files added: `test_files_comprehensive.py` (55), `test_branch_ops.py` (39), `test_encryption.py` (32), `test_completions_cmd.py` (10), `test_shell_completions.py` (7), `test_section.py` (39), `test_save_deploy_ops.py` (26), `test_status_ops.py` (17), `test_core_extended.py` (46)

---

## 🔥 Refactoring & Code Quality (Remaining)

### Eliminate Duplication

- [x] **Deduplicate deploy logic** — `deploy_section()` and `deploy_item()` in `save_deploy_ops.py` duplicate symlink/copy/secret-restore code. Extract shared helpers.
- [x] **Unify config loading** — `dotman_config.py` and `global_config.py` have nearly identical YAML/TOML loading patterns. Extract base class or utility.

### Clean Up Silent `except: pass`

- [x] **Cache ops** — `common.py:230-280` silently swallows all cache save/load errors
- [x] **Git operations** — `core.py:330,441,456` silently swallows errors in diff/stash operations
- [x] **Remote operations** — `init_cmd.py:104,117,130` silently swallows clone/fetch errors

### Break Up Long Functions

- [x] **`config_cmd.py`** — `_run_interactive_tutorial` (301 lines), `_show_section_examples` (290 lines)
- [x] **`init_cmd.py`** — `run_setup_wizard` (250 lines)
- [x] **`remote_cmd.py`** — `setup` (253 lines)
- [ ] **`navigate_cmd.py`** — `_handle_branch_navigate` (211 lines)
- [ ] **`files.py`** — `copy_directory` (92 lines), `smart_save_file` (88 lines)

### Deep Nesting

- [x] **`config_cmd.py`** — `config_tutorial` has 12 levels of nesting
- [x] **`remote_cmd.py`** — `setup` has 11 levels
- [x] **`edit_cmd.py`** — `edit` has 9 levels
- [ ] **`save_deploy_ops.py`** — `deploy_section` and `deploy_item` have 7 levels each — reduced via helper extraction

---

## 🧪 Test Coverage (Current ~83%, Target 80%+)

### Lowest coverage modules (below 70%)

| Module | Coverage |
|--------|----------|
| `navigate_cmd.py` | 59% |
| `core.py` | 66% |
| `common.py` | 66% |
| `init_cmd.py` | 70% |
| `watch_cmd.py` | 67% |

### At 80%+ coverage

| Module | Coverage |
|--------|----------|
| `interactive.py` | **100%** |
| `branch_cmd.py` | **100%** |
| `deploy_cmd.py` | **100%** |
| `config_cmd.py` | 97% |
| `doctor_cmd.py` | 99% |
| `encrypt_cmd.py` | 91% |
| `log_cmd.py` | 78% → rising

---

## 🚀 Features

### Shell Completions

- [ ] **`add` command** — complete local file paths
- [ ] **`import` command** — complete source tools (chezmoi, yadm, stow)

### Init Wizard Hook Suggestions

- [ ] When init wizard detects popular tools, suggest appropriate `post_deploy` hooks
- [ ] For shell configs — suggest `on_activate`/`on_deactivate` hooks
- [ ] Show example of how hooks work when adding the first section

### User Experience

- [ ] **`--json` output** — for `status`, `log`, `show`, `audit`
- [ ] **Centered error handling** — all commands use `handle_exception()` from `common.py`
- [ ] **Consistent exit codes** — replace `sys.exit(1)` / `raise SystemExit(1)` mix

### Extensibility (v1.2.0+)

- [ ] **Hook scripts directory** — support executing custom hook scripts from a folder
- [ ] **Plugin API** — extension mechanism for third-party tools
- [ ] **Make placeholders available in template variables** — `{{config_name}}` in config values

---

## 📚 Documentation

- [ ] **Full docs site** — mkdocs/sphinx hosted on GitHub Pages
- [ ] **Hook system docs** — document all hook aliases, placeholders, and examples
- [ ] **Migration guides** — detailed chezmoi/yadm/stow import walkthroughs
- [ ] **Architecture docs** — how mixins work, how config loading works

---

## 🏗️ Architecture

- [ ] **Remove old `log_cmd` checkout** (already deprecated)
- [ ] **Reduce `type: ignore` count** — currently some mask real typing issues

---

## Coverage Inventory (as of last run, 83% overall)

| Module | Coverage | Module | Coverage |
|--------|----------|--------|----------|
| `__init__.py` | 100% | `backups.py` | 71% |
| `branch_ops.py` | **97%** | `cli/__init__.py` | 100% |
| `cli/add_cmd.py` | 82% | `cli/audit_cmd.py` | 70% |
| `cli/backup_cmd.py` | 72% | `cli/branch_cmd.py` | **100%** |
| `cli/clean_cmd.py` | 81% | `cli/common.py` | 66% |
| `cli/completions_cmd.py` | **94%** | `cli/config_cmd.py` | 97% |
| `cli/deploy_cmd.py` | **100%** | `cli/discover_cmd.py` | 100% |
| `cli/doctor_cmd.py` | 99% | `cli/edit_cmd.py` | 72% |
| `cli/encrypt_cmd.py` | 91% | `cli/export_cmd.py` | 82% |
| `cli/import_cmd.py` | 93% | `cli/init_cmd.py` | 70% |
| `cli/log_cmd.py` | 78% | `cli/navigate_cmd.py` | 59% |
| `cli/onboarding.py` | 100% | `cli/profile_cmd.py` | 94% |
| `cli/remote_cmd.py` | 93% | `cli/restore_cmd.py` | 82% |
| `cli/revert_cmd.py` | 68% | `cli/rollback_cmd.py` | 90% |
| `cli/show_cmd.py` | 86% | `cli/status_cmd.py` | 76% |
| `cli/switch_cmd.py` | 94% | `cli/tag_cmd.py` | 68% |
| `cli/template_cmd.py` | 90% | `cli/verify_cmd.py` | 70% |
| `cli/watch_cmd.py` | 67% | `config.py` | 100% |
| `config_detector.py` | 87% | `constants.py` | 100% |
| `core.py` | 66% | `dotman_config.py` | 78% |
| `encryption.py` | **100%** | `exceptions.py` | 89% |
| `files.py` | **94%** | `global_config.py` | 89% |
| `hooks.py` | 80% | `interactive.py` | **100%** |
| `lock.py` | 79% | `merge.py` | 80% |
| `operations.py` | 82% | `save_deploy_ops.py` | 75% |
| `secrets.py` | 86% | `section.py` | **95%** |
| `status_ops.py` | **89%** | `ui.py` | 78% |
| `utils.py` | 81% | `vault.py` | 85% |
| **TOTAL** | **83%** | **(7443 lines)** | |
