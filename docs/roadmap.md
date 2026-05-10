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

## v0.8.0 - History & Tags + Performance (Released: 2026-05-10)

- [x] `dot-man log` - Show commit history with optional diffs
- [x] `dot-man log --stat` - Show file change statistics
- [x] `dot-man checkout <sha|tag>` - Checkout specific commit or tag
- [x] `dot-man tag create/list/delete/switch` - Tag management
- [x] `switch branch@tag` - Switch to branch at tag position
- [x] `switch <commit>` - Switch to specific commit
- [x] `switch --save/--no-save` - Override save behavior
- [x] `switch.default_behavior` config option
- [x] Flexible argument order (branch can be before/after flags)
- [x] Shell completion for tags and commits

### Performance (v0.8.x)

- [x] Batch file operations - Group reads/writes for faster switching
- [x] Parallel secret scanning - Use `concurrent.futures` for large directories
- [x] Lazy loading - Only load SecretGuard when secrets detected
- [x] `dot-man diff` - Show changes between branches/files
- [x] `dot-man revert --commit` - Restore file from specific commit
- [ ] Content-addressable storage - Deferred to v1.1.0

### TUI Status

- [x] TUI temporarily removed for redesign (CLI provides full functionality)

---

## v0.9.0 - Diff & Restore (Completed)

- [x] `dot-man diff` - Show changes between branches
- [x] `dot-man diff --branch <branch>` - Compare branches
- [x] `dot-man diff <file>` - Show specific file changes
- [x] `dot-man diff --staged` - Show staged changes
- [x] `dot-man revert --commit` - Restore from history

---

## v0.10.0 - Template Variables ✅

- [x] `dot-man template set <key> <value>` - Set template variable
- [x] `dot-man template get <key>` - Get template value
- [x] `dot-man template list` - List all templates
- [x] `dot-man template system` - Show auto-detected system variables
- [x] System variables: {{HOSTNAME}}, {{USER}}, {{SHELL}}, {{OS}}, etc.

---

## v0.11.0 - Multi-Machine Profiles ✅

- [x] `dot-man profile create/list/switch` - Profile management
- [x] Automatic profile detection based on hostname
- [x] Profile inheritance
- [x] Shell completions for profiles

---

## v1.0.0 - Production Ready

- [ ] `dot-man profile create/list/switch`
- [ ] Automatic profile detection based on hostname
- [ ] Profile inheritance

---

## v0.12.0 - Import/Migration

- [ ] Import from chezmoi, yadm, GNU Stow
- [ ] Export to portable format

---

## v1.0.0 - Production Ready

- [ ] 80%+ test coverage (currently 60%)
- [ ] Full documentation site (mkdocs/sphinx)
- [ ] PyPI publication
- [ ] Stable API guarantee

---

## v1.1.0 - Plugin System

- [ ] Custom secret detection patterns via config
- [ ] User-defined hook scripts directory
- [ ] Plugin API for extensions
- [ ] Content-addressable storage for deduplication

---

## v2.0+ - Future Ideas

- [ ] `dot-man template --set KEY=VALUE`
- [ ] Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- [ ] System variable auto-population

---

## v0.15.0 - Multi-Machine Profiles

- [ ] `dot-man profile create/list/switch`
- [ ] Automatic profile detection based on hostname
- [ ] Profile inheritance

---

## v0.16.0 - Import/Migration

- [ ] Import from chezmoi, yadm, GNU Stow
- [ ] Export to portable format

---

## v1.0.0 - Production Ready

- [ ] 80%+ test coverage (currently 44%)
- [ ] Full documentation site (mkdocs/sphinx)
- [ ] PyPI publication
- [ ] Stable API guarantee

---

## v1.1.0 - Plugin System

- Custom secret detection patterns via config
- User-defined hook scripts directory
- Plugin API for extensions

---

## v2.0+ - Future Ideas

- Encrypted files support (GPG/age)
- Symlink mode
- Web dashboard for configuration management
- Dotfile sharing/marketplace
- CI/CD integration for dotfile testing
- Cloud sync backends (S3, Dropbox, etc.)

---

## Success Metrics

| Metric        | Current                  | v1.0.0 Target         |
| ------------- | ------------------------ | --------------------- |
| Test Coverage | 60% (423 tests)          | 80%+                  |
| Core Commands | 25+ commands ✅         | All commands stable   |
| TUI           | Removed for redesign    | Redesign in v1.x      |
| Documentation | README + specs ✅        | Full docs site        |
| Performance   | Batch ops + parallel ✅ | 500+ files in <5s     |
| Distribution  | GitHub only              | PyPI published        |
