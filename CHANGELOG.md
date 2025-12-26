# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

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
