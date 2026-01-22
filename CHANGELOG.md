# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-01-23

### Added

- **Atomic File Operations**: New `atomic_write_text` ensures files are written to a temp file (`.tmp`) first and then renamed, preventing data corruption during save/deploy.
- **Ignored Secret Persistence**: Secrets in the ignore list are now correctly preserved in the local file (unredacted) without trigger warnings.
- **Smart Save Strategy**: Unified file saving logic (`smart_save_file`) that performs content comparison, secret checking, and atomic writing in a single efficient pass.
- **File Locking**: New `FileLock` context manager prevents concurrent `dot-man` operations to avoid race conditions.
- **Strict Typing**: Achieved 100% type safety with strict `mypy` checks.

### Changed

- **Performance**: Optimized file saving by reducing redundant file reads and writes; destination files are now only written to if content actually differs.
- **Code Quality**: Consolidated duplicated secret checking logic from `check_file_save_status` and `copy_file` into a single source of truth.
- **Robustness**: Enforced `newline=""` in all file I/O to guarantee consistent line ending preservation across operations.

## [0.5.1] - 2026-01-22

### Added

- **Branch Name Sync**: New `dot-man remote sync-branch` command to synchronize local/remote branch names (fixes main vs master mismatch)
- **Quickshell Hooks**: Added `quickshell_reload`, `quickshell_restart`, `quickshell_validate` hook aliases with `{qs_config}` auto-detection for config directory
- **Error Categorization**: New `ErrorCategory` enum and `ErrorDiagnostic` class for user-friendly error messages with suggestions
- **Comprehensive CLI Tests**: New `test_cli_commands.py` with 42 tests covering all commands, hyprland/quickshell file structures, path canonicalization, and error handling

### Fixed

- **File Comparison**: Removed unreliable mtime-based optimization in `compare_files()` that caused false "files changed" after git checkout
- **Secret Ignore List**: Added path canonicalization so `~/file` and `/home/user/file` are treated as the same path
- **Switch Command Errors**: Now shows categorized errors with helpful suggestions (e.g., "Permission denied → Try sudo")
- **KeyboardInterrupt Handling**: Graceful handling of Ctrl+C during switch operations
- **PermissionError Detection**: Fixed error categorization to properly detect built-in PermissionError
- **Deploy Error Reporting**: Fixed missing error messages when file copy fails during deploy; added check to skip non-existent repo paths
- **Secret IGNORE Action**: Fixed "IGNORE" action being treated as a replacement string instead of skipping redaction; now only reports actually redacted secrets in log message
- **Binary File Handling**: Skip binary files (.jpg, .pyc, etc.) when restoring secrets during deploy to prevent UTF-8 decode errors

## [0.5.0] - 2026-01-21

### Added

- **Encrypted Secret Vault**: Redacted secrets are now securely encrypted (Fernet) and stashed locally. They are automatically restored when you switch back to a branch.
- **Pre-Push Audit**: `dot-man sync` now automatically scans for secrets before pushing to remote, preventing accidental leaks.
- **"Did you mean?"**: CLI now suggests commands for typos (e.g., `swtich` -> `switch`).
- **Interactive Tutorial**: Revamped `dot-man config tutorial` with colorful interactive examples.
- **Config Validation**: Strict validation for `dot-man.toml` to catch misspelled keys or invalid options.

### Changed

- **CLI Modularization**: Refactored monolithic CLI into a modular package structure (`dot_man/cli/`) for better maintainability and extensibility.
- **UI Overhaul**: Consistent, colorful CLI output using Rich.
- **Performance**: Optimized file comparison and secret scanning (streaming processing) for large files and directories.
- **TUI Responsiveness**: TUI now loads heavy data asynchronously to prevent freezing.

### Fixed

- **CLI Imports**: Resolves circular import issues and improves startup time.
- **Remote URL Persistence**: `dot-man setup` and `dot-man remote set` now correctly save the remote URL to `global.conf`
- **Install Script PATH**: `install.sh` now auto-detects the installation directory and offers to add it to your shell config (bash, zsh, fish)
- **TUI Command Palette**: Selected command now scrolls into view when navigating with arrow keys

## [0.3.0] - 2025-12-26

### Added

- **Remote Sync**: `dot-man sync` command to push/pull dotfiles with remote repository
- **Remote Management**: `dot-man remote set/get` commands for configuring remote URL
- **Interactive TUI**: `dot-man tui` for visual branch management (optional, install with `[tui]` extra)
- **TUI Command Palette**: Press `c` in TUI to access all commands with search/filter
- **TUI Quick Keys**: `e` (edit), `a` (audit), `?` (help) for fast access
- **Setup Wizard**: `dot-man setup` guides you through GitHub repo creation (supports `gh` CLI)
- **Repo Access**: `dot-man repo` shows repo path, `dot-man shell` opens shell in repo directory

### Changed

- TUI is now an optional dependency (install with `pip install dot-man[tui]`)
- TUI now shows files with dirty status, switch preview, and actions

## [0.2.0] - 2025-12-26

### Added

- **Hooks**: `pre_deploy` and `post_deploy` commands for automated tasks (e.g. reload config)
- **Shell Completion**: Tab completion for branch names in `switch`, `deploy`, and `branch delete` commands
- **Interactive Deletion**: `branch delete` now prompts to force delete unmerged branches

### Changed

- **Optimization**: Deployment now skips copying files if content is identical, improving performance and avoiding unnecessary hook execution
- **Directory Sync**: Recursively compares directory contents to prevent false positives when syncing directories like `~/.config/hypr`

## [0.1.0] - 2025-12-25

### Added

- Initial release
- Core CLI with Click framework
- Git operations using GitPython
- Commands: `init`, `status`, `switch`, `edit`, `deploy`, `audit`
- Branch management: `branch list`, `branch delete`
- Secret detection with 10 default patterns:
  - Private keys (SSH, GPG)
  - AWS credentials
  - GitHub tokens
  - Generic API keys
  - Password assignments
  - Bearer tokens
  - JWT tokens
- Automatic secret redaction during save
- `--dry-run` mode for switch and deploy
- `--strict` mode for audit (CI/CD integration)
- `--fix` mode for auto-redacting secrets
- Install script with shell completions (bash, zsh, fish)
- Unit tests with pytest
- MIT License

### Security

- Built-in secret detection prevents accidental credential commits
- Secrets are redacted before saving to repository
- `secrets_filter` can be enabled/disabled per file
