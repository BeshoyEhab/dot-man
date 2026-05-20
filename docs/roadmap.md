# Development Roadmap

## MVP (v0.1.0) - Core Functionality ✅

**Goal:** Basic dotfile management with git-backed branches.

### Phase 1: Foundation ✅

- ✅ Project setup (pyproject.toml, package structure)
- ✅ Core modules: constants, exceptions, config parsing
- ✅ File operations and secret detection patterns

### Phase 2: Core Commands ✅

- ✅ `dot-man init` - Initialize repository structure
- ✅ `dot-man status` - Display current state
- ✅ `dot-man switch <branch>` - Save/deploy configurations
- ✅ `dot-man edit` - Open config in editor
- ✅ `dot-man audit` - Scan for secrets
- ✅ `dot-man deploy <branch>` - One-way deploy for new machines

### Phase 3: Polish ✅

- ✅ Test suite with pytest
- ✅ Error handling and user feedback
- ✅ Documentation and examples

---

## v0.2.0 - Hooks & Optimization ✅

- ✅ Pre/post deploy hooks
- ✅ Smart deployment (skip identical files)
- ✅ Interactive branch deletion
- ✅ Shell completions for branch names

---

## v0.3.0 - Remote Sync & TUI ✅

- ✅ `dot-man sync` - Push/pull with remote
- ✅ `dot-man remote get/set` - Remote configuration
- ✅ `dot-man setup` - Guided GitHub remote setup
- ✅ Interactive TUI (`dot-man tui`)
- ✅ TUI Command Palette
- ✅ Shell completions (bash, zsh, fish)

---

## v0.4.0 - Config Refactor & Modular Architecture ✅

- ✅ TOML config format with sections and templates
- ✅ Template inheritance (`inherits = ["template1"]`)
- ✅ Include/exclude patterns for files
- ✅ Modular `operations.py` for business logic
- ✅ `dot-man add` command
- ✅ Auto-migration from INI to TOML
- ✅ Refactored all commands to use new Section API

---

## v0.5.0 - Backup & Stash System ✅

- ✅ `dot-man backup create/list/restore`
- ✅ Auto-backup before destructive operations
- ✅ Backup rotation (max 5)
- ✅ `dot-man stash` / `dot-man stash pop`
- ✅ `dot-man switch --stash` and `--save-to`
- ✅ Bug fixes & stability (v0.5.1)

---

## v0.6.0 - Code Quality & Robustness ✅

- ✅ Atomic file operations
- ✅ Consistent file I/O
- ✅ Consolidate secret checking
- ✅ Complete type hints
- ✅ File locking

---

## v0.7.0 - New Commands ✅ (Released: 2026-02-28)

- ✅ `dot-man verify` - Validate repo integrity
- ✅ `dot-man clean` - Remove stale backups, orphaned files
- ✅ `dot-man doctor` - Diagnostics and health checks
- ✅ `--verbose` / `-v` global flag
- ✅ GitHub Actions CI with Black and mypy

---

## v0.8.0 - History & Tags + Performance ✅ (Released: 2026-05-10)

- ✅ `dot-man log` - Show commit history with optional diffs
- ✅ `dot-man log --stat` - Show file change statistics
- ✅ `dot-man checkout <sha|tag>` - Checkout specific commit or tag
- ✅ `dot-man tag create/list/delete/switch` - Tag management
- ✅ `switch branch@tag` - Switch to branch at tag position
- ✅ `switch <commit>` - Switch to specific commit
- ✅ `switch --save/--no-save` - Override save behavior
- ✅ `switch.default_behavior` config option
- ✅ Flexible argument order (branch can be before/after flags)
- ✅ Shell completion for tags and commits
- ✅ Batch file operations - Group reads/writes for faster switching
- ✅ Parallel secret scanning - Use `concurrent.futures` for large directories
- ✅ Lazy loading - Only load SecretGuard when secrets detected
- ✅ `dot-man diff` - Show changes between branches/files
- ✅ `dot-man revert --commit` - Restore file from specific commit
- ✅ `dot-man template set/get/list/system` - Template variable management
- ✅ `dot-man profile create/list/switch/detect` - Multi-machine profiles
- ✅ TUI temporarily removed for redesign (CLI provides full functionality)

---

## v0.9.0 - Quality Gates & Test Audit ✅ (Released: 2026-05-10)

- ✅ Pre-push quality checklist (black, ruff, mypy, pytest)
- ✅ Pre-commit hooks (.pre-commit-config.yaml)
- ✅ Ruff configuration in pyproject.toml
- ✅ 6 mypy type errors fixed
- ✅ 137 ruff lint errors fixed
- ✅ 15+ weak tests replaced with functional tests
- ✅ 26 fixture errors fixed (missing git_repo fixtures)
- ✅ CI updated: Black --check, ruff check added
- ✅ Updated stale documentation

---

## v0.9.0 - Enhanced Testing & Features ✅

### Testing Improvements

- ✅ 627 tests (from 418)
- ✅ 56% coverage (from 57%)
- ✅ All CLI commands have test coverage
- ✅ Added tests for: backups, config, remote, profile, template, deploy, add, backup
- ✅ Updated coverage omit list

### New Features

- ✅ `dot-man init --import` - Import from existing git repos
- ✅ `dot-man navigate` - Unified command (replaces switch/checkout)
- ✅ `dot-man hooks` - Manage global hooks
- ✅ Auto-detect hooks on branch switch
- ✅ Universal file merge system
- ✅ Config auto-detection (Quickshell, etc.)

---

## v1.1.1 - Command Aliases ✅

- ✅ Short command aliases (3 letters where possible):
  - ✅ `nav` = navigate, `doc` = doctor, `dep` = deploy
  - ✅ `enc` = encrypt, `exp` = export, `imp` = import
  - ✅ `dis` = discover, `aud` = audit, `cln` = clean
  - ✅ `ver` = verify, `rev` = revert, `rol` = rollback
  - ✅ `wat` = watch, `cpl` = completions, `rst` = restore
  - ✅ `edt` = edit, `sta` = status, `ini` = init
  - ✅ `syn` = sync, `log` = log, `dif` = diff
  - ✅ `hks` = hooks
- ✅ Updated license with additional copyright holder (ZVAXEROWS)
- ✅ Updated copyright years to 2025, 2026

---

## v1.0.0 - Production Ready

- [ ] 80%+ test coverage (currently 56%)
- [ ] Full documentation site (mkdocs/sphinx)
- [x] PyPI publication ✅
- [ ] Stable API guarantee

---

## v1.1.0 - Plugin System

- [ ] Custom secret detection patterns via config
- [ ] User-defined hook scripts directory
- [ ] Plugin API for extensions
- [ ] Built-in plugin: pro-mgr integration

---

## v2.0+ - Future Ideas

### Implemented in v0.10.0

- ✅ Import from chezmoi, yadm, GNU Stow (`dot-man import`)
- ✅ Export to portable formats (`dot-man export tar/zip/json`)
- ✅ Encrypt/decrypt sensitive files (`dot-man encrypt`)
- ✅ Auto-discover dotfiles (`dot-man discover`)
- ✅ YAML configuration support
- ✅ Environment variable expansion in paths
- ✅ Rich diff output (`dot-man diff --rich`)

### Implemented in v1.0.1

- ✅ `dot-man watch` - Auto-save tracked dotfiles on change (watchdog/polling)
- ✅ `dot-man rollback` - Transaction-style rollback to previous commits/tags

### Storage & Sync (Future)

- [ ] Symlink mode - Option to symlink files instead of copying
- [ ] Encrypted files - More advanced GPG/age support
- [ ] Cloud sync backends - S3, Dropbox, Google Drive
- [ ] Per-branch config inheritance - `inherits_branch = "main"` in config

### User Experience (Future)

- [ ] Web dashboard - Browser-based configuration management
- [ ] JSON output - `--json` option for scripting
- [x] File watcher - `dot-man watch` for auto-sync
- [x] Deploy rollback - Transaction-style with automatic undo
- [ ] Configurable backup rotation - `max_backups` in global.toml

### Ecosystem (Future)

- [ ] Dotfile sharing/marketplace - Share configs with community
- [ ] CI/CD integration - Test dotfiles before deployment

---

## Success Metrics

| Metric        | Current                 | v1.0.0 Target       |
| ------------- | ----------------------- | ------------------- |
| Test Coverage | 59% (872 tests) ✅      | 80%+                |
| Core Commands | 30+ commands ✅         | All commands stable |
| Lint Errors   | 0 (ruff + mypy) ✅      | 0                   |
| TUI           | Removed for redesign    | Redesign in v1.x    |
| Documentation | README + specs ✅       | Full docs site      |
| Performance   | Batch ops + parallel ✅ | 500+ files in <5s   |
| Distribution  | Published to PyPI ✅    | PyPI published      |
