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

## v0.7.0 - New Commands (Current)

- `dot-man verify` - Validate repo integrity
- `dot-man clean` - Remove stale backups, orphaned files
- `dot-man doctor` - Diagnostics and health checks
- `--dry-run` flag for all commands

---

## v0.8.0 - Performance

- Batch file operations
- Parallel secret scanning
- Lazy loading
- Content-addressable storage

---

## v0.9.0 - TUI Core Actions

- Sync, switch, delete branch from TUI
- Edit config from TUI
- Create new branch from TUI

---

## v0.10.0-0.11.0 - TUI Management & Polish

- Per-branch config editing
- Keyboard shortcuts overlay
- Status bar, notifications, progress indicators

---

## v0.12.0 - Diff & History

- `dot-man diff` - Show changes between branches
- `dot-man log` - Show commit history
- `dot-man restore <file> <commit>` - Restore from history

---

## v0.13.0 - Template Variables

- `dot-man template --set KEY=VALUE`
- Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- System variable auto-population

---

## v0.14.0 - Multi-Machine Profiles

- `dot-man profile create/list/switch`
- Automatic profile detection based on hostname
- Profile inheritance

---

## v0.15.0 - Import/Migration

- Import from chezmoi, yadm, GNU Stow
- Export to portable format

---

## v1.0.0 - Production Ready

- 80%+ test coverage
- Full documentation site (mkdocs/sphinx)
- PyPI publication
- Stable API guarantee

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

| Metric        | Current              | v1.0.0 Target         |
| ------------- | -------------------- | --------------------- |
| Test Coverage | ~41% (98 tests)      | 80%+                  |
| Core Commands | 14+ commands ✅      | All commands stable   |
| TUI           | Full-featured ✅     | Polished & responsive |
| Documentation | README + specs ✅    | Full docs site        |
| Performance   | ~100 files in <5s ✅ | 500+ files in <5s     |
| Distribution  | GitHub only          | PyPI published        |
