# TODO

### main idea v0.0.0

- [x] make it more simple for user, by UX and tutorial and the starting initialize (init after start then offer make first branch). ✅
- [] after switching it should kill the qs then open it to start and make hyperctl reload

## Completed Releases

### v0.1.0 ✅ - Core Foundation

- [x] Core CLI with Click
- [x] Git operations with GitPython
- [x] Secret detection (10 patterns)
- [x] Commands: init, status, switch, edit, deploy, audit
- [x] Branch management (list, delete)
- [x] Install script with shell completions
- [x] Unit tests

### v0.2.0 ✅ - Hooks & Smart Deploy

- [x] Hooks: `pre_deploy` and `post_deploy`
- [x] Smart deployment (skip identical files)
- [x] Directory recursion fix
- [x] Interactive branch deletion
- [x] Shell completions for branches

### v0.3.0 ✅ - Remote Sync & TUI

- [x] `dot-man sync` - Push/pull with remote
- [x] `dot-man remote get/set` - Configure remote URL
- [x] `dot-man setup` - Guided GitHub remote setup
- [x] Interactive TUI (`dot-man tui`)
- [x] TUI Command Palette (access all commands)
- [x] `dot-man repo` and `dot-man shell` utilities

### v0.4.0 ✅ - Config Refactor & Modular Architecture

- [x] TOML config format with sections and templates
- [x] Template inheritance (`inherits = ["template1"]`)
- [x] Include/exclude patterns for files
- [x] Modular `operations.py` for business logic
- [x] `dot-man add` command
- [x] Auto-migration from INI to TOML
- [x] Branch-specific file preview in TUI
- [x] Refactored all commands to use new Section API

### v0.5.0 ✅ - Backup & Stash System

- [x] `dot-man backup create` - Manual backups
- [x] `dot-man backup list` - Show available backups
- [x] `dot-man backup restore` - Restore from backup
- [x] Auto-backup before destructive operations
- [x] Backup rotation (max 5)
- [x] `dot-man stash` - Temporarily stash current changes
- [x] `dot-man stash pop` - Restore stashed changes
- [x] `dot-man switch --stash` - Stash changes instead of committing
- [x] `dot-man switch --save-to <branch>` - Save to new branch before switching

### v0.5.1 ✅ - Bug Fixes & Stability

- [x] Fix file comparison false positives after git checkout
- [x] Fix secret ignore list path matching (canonicalize paths)
- [x] Add error categorization with user-friendly suggestions
- [x] Add `dot-man remote sync-branch` for main/master mismatch
- [x] Add quickshell hook aliases
- [x] Graceful KeyboardInterrupt handling

---

### v0.6.0 ✅ - Code Quality & Robustness

- [x] **Atomic file operations** - Write to temp file, then rename (prevents corruption)
- [x] **Consistent file I/O** - Use `newline=""` everywhere for line ending preservation
- [x] **Consolidate secret checking** - Reduce duplicate code in `has_unhandled_secrets()` and `check_file_save_status()`
- [x] **Complete type hints** - Add missing type annotations throughout codebase
- [x] **File locking** - Prevent concurrent `dot-man` operations from conflicting

---

## Currently In Progress

### v0.8.0 - Performance ✅

- [x] **Batch file operations** - Group reads/writes for faster switching
- [x] **Parallel secret scanning** - Use `concurrent.futures` for large directories
- [x] **Lazy loading** - Only load `SecretGuard` when secrets detected
- [x] **Content-addressable storage** - SHA-keyed deduplication (consolidated `sha256_hex` into `utils.py`)

### v0.9.0 - TUI Core Actions (DEPRECATED)

- [x] TUI temporarily removed for redesign (v1.x)
- [x] CLI provides full functionality for all operations

---

### v0.12.0 - Diff & History ✅

- [x] `dot-man diff` - Show changes between branches
- [x] `dot-man diff <file>` - Show local vs repo diff
- [x] `dot-man log` - Show commit history with files changed (existing)
- [x] `dot-man checkout` - Checkout specific commit/tag (existing)
- [x] `dot-man revert --commit` - Restore from history

---

## Test Coverage (Current: ~46%, Target: 80%)

Priority files needing tests:

- [x] **`cli/remote_cmd.py`** - 10% → 60%+
- [x] **`cli/edit_cmd.py`** - 16% → 60%+
- [x] **`cli/init_cmd.py`** - 30% → 60%+

---

## Feature Roadmap

### v0.12.0 - Git Wrapper CLI Commands ✅

- [x] `dot-man diff` - Show uncommitted changes
- [x] `dot-man diff --branch <name>` - Compare branches
- [x] `dot-man diff <file>` - Compare specific file
- [x] `dot-man log` - Show commit history
- [x] `dot-man log --diff` - Show log with patch
- [x] `dot-man log --interactive` - TUI Log viewer
- [x] `dot-man show <commit>` - View full diff for a specific commit
- [x] `dot-man restore <file> <commit>` - Restore from history

### v0.13.0 - Template Variables ✅

- [x] `dot-man template set KEY=VALUE`
- [x] `dot-man template list`
- [x] Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- [x] System variable auto-population

### v0.14.0 - Multi-Machine Profiles ✅

- [x] `dot-man profile create <name>` - Create machine-specific profiles
- [x] `dot-man profile list` - List available profiles
- [x] `dot-man profile switch <name>` - Switch between profiles
- [x] Automatic profile detection based on hostname
- [x] Profile inheritance (e.g., `server` extends `minimal`)

### v0.15.0 - Import/Migration

- [ ] `dot-man import chezmoi` - Import from chezmoi
- [ ] `dot-man import yadm` - Import from yadm
- [ ] `dot-man import stow` - Import from GNU Stow
- [ ] `dot-man export` - Export to portable format

---

## v1.0.0 - Production Ready

- [ ] 80%+ test coverage
- [ ] Full documentation site (mkdocs/sphinx)
- [ ] PyPI publication
- [ ] Stable API guarantee

## v1.1.0 - Plugin System

- [ ] Custom secret detection patterns via config
- [ ] User-defined hook scripts directory
- [ ] Plugin API for extensions
- [ ] Built-in plugin: pro-mgr integration

---

## Implemented in Recent Releases

### v0.10.0 - Config System Improvements

- [x] YAML configuration support (.yaml, .yml alongside .toml)
- [x] Environment variable expansion in paths ($HOME, $USER, etc.)
- [x] Config file conflict detection (warns when both .toml and .yaml exist)
- [x] Removed legacy INI migration code
- [x] Removed unused LegacyConfigLoader class
- [x] Consolidated LOCK_FILE to constants.py
- [x] Import from chezmoi/yadm/stow
- [x] Export to tar/zip/json
- [x] Encrypt/decrypt sensitive files (GPG/AGE)
- [x] Auto-discover dotfiles
- [x] Rich diff output

---

## Future Ideas (v2.0+)

### Storage & Sync

- [ ] **Symlink mode** - Option to symlink files instead of copying (instant sync, saves space)
- [ ] **Encrypted files** - GPG/age support for sensitive configs (basic done, needs more)
- [ ] **Cloud sync backends** - S3, Dropbox, Google Drive
- [ ] **Per-branch config inheritance** - `inherits_branch = "main"` in dot-man.toml
- [ ] **Configurable backup rotation** - Make MAX_BACKUPS configurable via global.toml
- [ ] **Deploy rollback** - Transaction-style deploy with automatic rollback on failure
- [ ] **Configurable thread pool** - `max_workers` setting in global.toml

### User Experience

- [ ] **Web dashboard** - Browser-based configuration management
- [ ] **JSON output** - `--json` option for scripting (status, log, show, audit)
- [ ] **Universal Setup Wizard** - Interactive menu: remote, dotfiles, secrets, hooks
- [ ] **File watcher** - `dot-man watch` for auto-sync on file changes

### CLI Improvements

- [ ] **YAML save support** - Preserve YAML format when saving
- [ ] **Section priority/ordering** - Control deploy order with `priority` key
- [ ] **Enhanced shell completions** - Add for all commands

### Architecture

- [ ] **Profile system expansion** - Profile-specific configs and switching
- [ ] **Template multiple inheritance** - True inheritance chain with override priority
- [ ] **Abstract method enforcement** - Use protocol-based typing for mixins

### Ecosystem

- [ ] **Dotfile sharing/marketplace** - Share configs with community
- [ ] **CI/CD integration** - Test dotfiles before deployment

---

## Known Issues

- Shell completions may show stale branch names (restart shell to refresh)
- TUI cannot fully preview files for other branches without git checkout
- YAML config files are saved as TOML (format is converted on save)

---

## Architecture

```
cli/ ────┐
         ├──> operations.py ─┬─> config.py (re-exports)
tui.py ──┘    (orchestrator)  │    ├─> global_config.py
              ├ SaveDeployMixin│    ├─> section.py
              ├ BranchMixin   │    └─> dotman_config.py
              └ StatusMixin   ├─> core.py (Git)
                              ├─> files.py
                              ├─> secrets.py
                              ├─> vault.py
                              ├─> backups.py
                              └─> lock.py
```

`operations.py` is the single source of truth for all business logic.

---

## Current Test Coverage Inventory

Our primary target is **80%+ overall coverage** for the `v1.0.0` release.

**Overall Progress:** 60% (4231 statements, 1706 missing)

### Modules Below 50% Coverage (High Priority)

| Module                        | Current Coverage | Missing Lines |
| ----------------------------- | ---------------- | ------------- |
| `dot_man/tui_log.py`          | 0%               | 48            |
| `dot_man/cli/profile_cmd.py`  | 17%              | 134           |
| `dot_man/cli/template_cmd.py` | 20%              | 105           |
| `dot_man/cli/audit_cmd.py`    | 32%              | 55            |
| `dot_man/cli/log_cmd.py`      | 34%              | 97            |
| `dot_man/cli/tag_cmd.py`      | 35%              | 55            |
| `dot_man/interactive.py`      | 46%              | 109           |
| `dot_man/cli/switch_cmd.py`   | 47%              | 111           |
| `dot_man/cli/common.py`       | 47%              | 94            |
| `dot_man/cli/branch_cmd.py`   | 48%              | 37            |

### Modules 50% - 79% Coverage (Medium Priority)

| Module                       | Current Coverage | Missing Lines |
| ---------------------------- | ---------------- | ------------- |
| `dot_man/branch_ops.py`      | 53%              | 58            |
| `dot_man/dotman_config.py`   | 53%              | 106           |
| `dot_man/cli/deploy_cmd.py`  | 54%              | 46            |
| `dot_man/core.py`            | 58%              | 110           |
| `dot_man/cli/tui_cmd.py`     | 60%              | 4             |
| `dot_man/cli/revert_cmd.py`  | 61%              | 16            |
| `dot_man/backups.py`         | 65%              | 37            |
| `dot_man/status_ops.py`      | 65%              | 43            |
| `dot_man/global_config.py`   | 67%              | 58            |
| `dot_man/cli/main.py`        | 67%              | 1             |
| `dot_man/files.py`           | 68%              | 62            |
| `dot_man/operations.py`      | 68%              | 36            |
| `dot_man/save_deploy_ops.py` | 68%              | 67            |
| `dot_man/section.py`         | 68%              | 30            |
| `dot_man/cli/add_cmd.py`     | 69%              | 24            |
| `dot_man/cli/backup_cmd.py`  | 69%              | 20            |
| `dot_man/cli/interface.py`   | 73%              | 8             |
| `dot_man/cli/status_cmd.py`  | 76%              | 24            |
| `dot_man/cli/clean_cmd.py`   | 77%              | 13            |
| `dot_man/lock.py`            | 79%              | 7             |

### Modules 80%+ Coverage (Target Achieved / Low Priority)

| Module                       | Current Coverage | Missing Lines |
| ---------------------------- | ---------------- | ------------- |
| `dot_man/ui.py`              | 81%              | 6             |
| `dot_man/cli/restore_cmd.py` | 82%              | 9             |
| `dot_man/vault.py`           | 85%              | 23            |
| `dot_man/cli/show_cmd.py`    | 86%              | 2             |
| `dot_man/utils.py`           | 87%              | 8             |
| `dot_man/exceptions.py`      | 88%              | 9             |
| `dot_man/secrets.py`         | 88%              | 20            |
| `dot_man/cli/init_cmd.py`    | 92%              | 14            |
| `dot_man/cli/__init__.py`    | 100%             | 0             |
| `dot_man/config.py`          | 100%             | 0             |
| `dot_man/constants.py`       | 100%             | 0             |
| `dot_man/__init__.py`        | 100%             | 0             |
