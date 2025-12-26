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

## v0.4.0 - Backup System

- `dot-man backup create` - Manual backups
- `dot-man backup list` - Show available backups
- `dot-man backup restore` - Restore from backup
- Auto-backup before destructive operations
- Backup rotation (max 5)

---

## v0.5.0 - Template Variables

- `dot-man template --set KEY=VALUE`
- `dot-man template --list`
- Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- System variable auto-population
- Default value syntax (`{{VAR:default}}`)

---

## v0.6.0 - Diff & History

- `dot-man diff` - Show changes between branches
- `dot-man diff <file>` - Show local vs repo diff
- `dot-man log` - Show commit history
- `dot-man restore <file> <commit>` - Restore from history

---

## v0.7.0 - Multi-Machine Profiles

- `dot-man profile create <name>` - Create machine-specific profiles
- `dot-man profile list` - List available profiles
- `dot-man profile switch <name>` - Switch between profiles
- Automatic profile detection based on hostname
- Profile inheritance (e.g., `server` extends `minimal`)

---

## v0.8.0 - Import/Migration

- `dot-man import chezmoi` - Import from chezmoi
- `dot-man import yadm` - Import from yadm
- `dot-man import stow` - Import from GNU Stow
- `dot-man export` - Export to portable format

---

## v0.9.0 - Polish & Stability

- Comprehensive error messages
- Performance optimization for large repos
- Extended test coverage (60%+)
- Improved TUI responsiveness
- Bug fixes and edge case handling

---

## v1.0.0 - Production Ready

- `dot-man doctor` - Diagnostics and health checks
- 80%+ test coverage
- Full documentation site (mkdocs/sphinx)
- PyPI publication
- Stable API guarantee

---

## v1.1.0 - Plugin System

- Custom secret detection patterns via config
- User-defined hook scripts directory
- Plugin API for extensions
- Built-in plugin: pro-mgr integration

---

## v2.0+ - Future Ideas

- Encrypted files support (GPG/age)
- Web dashboard for configuration management
- Dotfile sharing/marketplace
- CI/CD integration for dotfile testing
- Cloud sync backends (S3, Dropbox, etc.)

---

## Success Metrics

| Metric        | Current              | v1.0.0 Target         |
| ------------- | -------------------- | --------------------- |
| Test Coverage | ~30%                 | 80%+                  |
| Core Commands | 12+ commands ✅      | All commands stable   |
| TUI           | Full-featured ✅     | Polished & responsive |
| Documentation | README + specs ✅    | Full docs site        |
| Performance   | ~100 files in <5s ✅ | 500+ files in <5s     |
| Distribution  | GitHub only          | PyPI published        |
