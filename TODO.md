# TODO

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

## Next Up

### v0.6.0 - Code Quality & Robustness

- [x] **Atomic file operations** - Write to temp file, then rename (prevents corruption)
- [x] **Consistent file I/O** - Use `newline=""` everywhere for line ending preservation
- [x] **Consolidate secret checking** - Reduce duplicate code in `has_unhandled_secrets()` and `check_file_save_status()`
- [ ] **Complete type hints** - Add missing type annotations throughout codebase
- [ ] **File locking** - Prevent concurrent `dot-man` operations from conflicting

### v0.7.0 - New Commands

- [ ] **`dot-man verify`** - Validate repo integrity, check orphaned files, verify permissions
- [ ] **`dot-man clean`** - Remove stale backups, orphaned files in repo
- [ ] **`dot-man doctor`** - Diagnostics and health checks
- [ ] **Dry-run for all commands** - `--dry-run` flag for deploy, save, etc.

### v0.8.0 - Performance

- [ ] **Batch file operations** - Group reads/writes for faster switching
- [ ] **Parallel secret scanning** - Use `concurrent.futures` for large directories
- [ ] **Lazy loading** - Only load `SecretGuard` when secrets detected
- [ ] **Content-addressable storage** - SHA-keyed deduplication for identical files

### v0.9.0 - TUI Core Actions

- [ ] **Sync from TUI** - Pull/push with remote directly from TUI
- [ ] **Switch from TUI** - Full branch switching with confirmation
- [ ] **Delete branch from TUI** - Delete branches with confirmation dialog
- [ ] **Edit config from TUI** - Open config in editor, reload on save
- [ ] **Create new branch from TUI** - Modal to create and switch to new branch

### v0.10.0 - TUI Per-Branch Management

- [ ] **Edit any branch config** - View/edit dot-man.toml for any branch
- [ ] **Add files to any branch** - Add tracked paths without switching
- [ ] **Remove files from any branch** - Remove sections/paths from config
- [ ] **Copy section between branches** - Duplicate config from one branch to another
- [ ] **Expandable TUI Audit Panel** - Collapsible tree view of secrets
- [ ] **First-run welcome modal** - Help new users in TUI

### v0.11.0 - TUI Polish

- [ ] **Keyboard shortcuts help overlay** - Show all keybindings
- [ ] **Status bar** - Show current operation, branch, sync status
- [ ] **Notification toasts** - Non-blocking success/error messages
- [ ] **Progress indicators** - Show progress for long operations

---

## Feature Roadmap

### v0.12.0 - Diff & History

- [ ] `dot-man diff` - Show changes between branches
- [ ] `dot-man diff <file>` - Show local vs repo diff
- [ ] `dot-man log` - Show commit history with files changed
- [ ] `dot-man log <file>` - Show file-specific history
- [ ] `dot-man log --interactive` - Interactive log browser
- [ ] `dot-man restore <file> <commit>` - Restore from history
- [ ] TUI: Log viewer with commit list, file changes, and diff preview
- [ ] CLI: `dot-man show <commit>` - View full diff for a specific commit

### v0.13.0 - Template Variables

- [ ] `dot-man template --set KEY=VALUE`
- [ ] `dot-man template --list`
- [ ] Template substitution (`{{HOSTNAME}}`, `{{EMAIL}}`)
- [ ] System variable auto-population
- [ ] Default value syntax (`{{VAR:default}}`)

### v0.14.0 - Multi-Machine Profiles

- [ ] `dot-man profile create <name>` - Create machine-specific profiles
- [ ] `dot-man profile list` - List available profiles
- [ ] `dot-man profile switch <name>` - Switch between profiles
- [ ] Automatic profile detection based on hostname
- [ ] Profile inheritance (e.g., `server` extends `minimal`)

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

## Future Ideas (v2.0+)

### Storage & Sync

- [ ] **Symlink mode** - Option to symlink files instead of copying (instant sync, saves space)
- [ ] **Encrypted files** - GPG/age support for sensitive configs
- [ ] **Cloud sync backends** - S3, Dropbox, Google Drive
- [ ] **Per-branch config inheritance** - `inherits_branch = "main"` in dot-man.toml

### User Experience

- [ ] **Web dashboard** - Browser-based configuration management
- [ ] **Universal Setup Wizard** - Interactive menu: remote, dotfiles, secrets, hooks
  - Auto-scan common dotfile locations
  - Import from existing repos (`--from github.com/user/dotfiles`)
  - Branch structure scaffolding (work/home/minimal)

### Ecosystem

- [ ] **Dotfile sharing/marketplace** - Share configs with community
- [ ] **CI/CD integration** - Test dotfiles before deployment

---

## Known Issues

- Shell completions may show stale branch names (restart shell to refresh)
- TUI cannot fully preview files for other branches without git checkout
- Old INI configs are auto-migrated on first run

---

## Architecture

```
cli.py ─┐
        ├──> operations.py ─┬─> config.py (TOML)
tui.py ─┘                   ├─> core.py (Git)
                            ├─> files.py
                            └─> secrets.py
```

`operations.py` is the single source of truth for all business logic.
