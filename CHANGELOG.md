# Changelog

All notable changes to dot-man will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-05-10

### Added
- **First-time onboarding flow** (`dot_man/cli/onboarding.py`) — automatically
  launches on the very first `dot-man` invocation:
  - Welcome banner with ASCII logo
  - 2-section interactive tutorial (Architecture + Manual / How To Use)
  - ASCII diagrams for file flow, branch model, components, and typical workflow
  - Auto-runs `dot-man init` with the interactive setup wizard after the tutorial
  - Prompts the user to create their first branch and switches to it automatically
  - Sentinel file (`~/.config/dot-man/.onboarded`) prevents the tutorial from
    repeating on subsequent launches
  - Ctrl-C exits cleanly without writing the sentinel (tutorial re-appears next time)
- **Pre-push quality checklist** in AGENTS.md — mandatory black, ruff, mypy, and pytest before every commit
- **Pre-commit hooks** via `.pre-commit-config.yaml` — automatic enforcement of formatting, linting, and type checking
- **Ruff configuration** in `pyproject.toml` — rules E, F, W, I with per-file E402 suppression
- **Missing test fixtures** — `git_repo`, `git_repo_with_branches`, `git_repo_with_tags`, `git_repo_with_commits`

### Changed
- **CI workflow** — Black now runs with `--check` (was silently reformatting), added ruff lint step
- **Test quality audit** — replaced 15+ weak tests (callable/hasattr/import checks) with functional tests:
  - Secret scanning tests now exercise real file scanning
  - Completion function tests use mocked GitManager with real invocations
  - Operations singleton test verifies identity, not just callability
- Black target-version updated from py38 to py39

### Fixed
- **6 mypy errors** resolved across 4 files:
  - `global_config.py` — `no-any-return` on `current_profile` property
  - `core.py` — `delete_tag` now uses `repo.git.tag("-d", name)` instead of `Repo.delete_tag(str)`
  - `cli/log_cmd.py` — removed invalid `.path` attribute access on Diff objects
  - `cli/profile_cmd.py` — fixed `getattr` misuse and `no-any-return` in `_detect_profile`
- **137 ruff lint errors** fixed (unused imports, unused variables, bool comparison style, trailing whitespace)
- Removed unused `socket` import in profile_cmd.py
- Fixed 26 pre-existing test fixture errors (missing `git_repo`/`git_repo_with_tags` fixtures)
- **SHA-keyed deduplication** - Consolidated three duplicate `hashlib.sha256` implementations (`files.get_content_hash`, `BaseSecretGuard._compute_hash`, `SecretVault._perform_stash`) into a single `utils.sha256_hex` helper

## [0.8.0] - 2026-05-10

### Removed
- **TUI** - Temporarily removed for redesign. CLI provides full functionality.

### Added
- `dot-man diff` - Show changes between branches or files
  - `dot-man diff` - Show uncommitted changes
  - `dot-man diff --branch main` - Compare branches
  - `dot-man diff <file>` - Show specific file changes
  - `dot-man diff --staged` - Show staged changes
- `dot-man revert` - Enhanced with `--commit` to restore from specific commit
- `dot-man template` - Template variable management
  - `dot-man template set <key> <value>` - Set template variable
  - `dot-man template get <key>` - Get template value
  - `dot-man template list` - List all templates
  - `dot-man template system` - Show auto-detected system variables
  - System variables: {{HOSTNAME}}, {{USER}}, {{SHELL}}, {{OS}}, etc.
- `dot-man profile` - Multi-machine profiles
  - `dot-man profile create <name>` - Create profile
  - `dot-man profile list` - List profiles
  - `dot-man profile switch <name>` - Switch to profile
  - `dot-man profile detect` - Auto-detect by hostname
  - Profile inheritance support
- **Performance optimizations:**
  - Batch file operations for faster branch switching
  - Parallel secret scanning using `concurrent.futures`
  - Lazy loading for `SecretGuard` - only loaded when secrets detected
  - Content hash function for future deduplication
  - Thread-safe vault operations with batch mode
- `dot-man log` - Show commit history with optional diffs and stats
  - `-n, --count` - Number of commits to show
  - `--diff, -d` - Show diff for each commit
  - `--stat` - Show file change statistics
- `dot-man checkout <sha|tag>` - Checkout specific commit or tag (creates detached HEAD)
- `dot-man tag` - Tag management
  - `tag create <name> [commit]` - Create tag at current or specific commit
  - `tag list` - List all tags
  - `tag delete <name>` - Delete a tag
  - `tag switch <name>` - Switch to tag
- Enhanced `dot-man switch` command:
  - `branch@tag` syntax - Switch to branch at tag position
  - `commit` syntax - Switch to specific commit (e.g., `switch abc1234`)
  - `--save` - Force save current changes
  - `--no-save` - Discard current changes
  - Flexible argument order (branch can be before or after flags)
- `switch.default_behavior` config option - Set default save/no-save preference
- Shell completions for tags and commits in switch command

### Changed
- Updated documentation with new commands
- Updated roadmap to reflect completed features
- Version bumped to 0.8.0 (Beta)

### Fixed
- Tag detection in branch parsing
- Proper checkout for tags

## [0.7.0] - 2026-02-28

### Added
- `dot-man verify` - Validate repository integrity
- `dot-man clean` - Remove stale backups and orphaned files
- `dot-man doctor` - Diagnostics and health checks
- `--verbose` / `-v` global flag
- GitHub Actions CI with Black and mypy

### Fixed
- Various stability improvements

## [0.6.0] - 2024

### Added
- Atomic file operations
- File locking mechanism
- Complete type hints
- Consolidated secret checking

## [0.5.0] - 2024

### Added
- `dot-man backup create/list/restore`
- Auto-backup before destructive operations
- Backup rotation (max 5)
- `dot-man stash` / `dot-man stash pop`
- `dot-man switch --stash` and `--save-to`

## [0.4.0] - 2024

### Added
- TOML config format with sections and templates
- Template inheritance (`inherits = ["template1"]`)
- Include/exclude patterns for files
- Modular `operations.py` for business logic
- `dot-man add` command
- Auto-migration from INI to TOML

## [0.3.0] - 2024

### Added
- `dot-man sync` - Push/pull with remote
- `dot-man remote get/set` - Remote configuration
- `dot-man setup` - Guided GitHub remote setup
- Interactive TUI (`dot-man tui`)
- TUI Command Palette
- Shell completions (bash, zsh, fish)

## [0.2.0] - 2024

### Added
- Pre/post deploy hooks
- Smart deployment (skip identical files)
- Interactive branch deletion
- Shell completions for branch names

## [0.1.0] - 2023

### Added
- Core functionality
- `dot-man init` - Initialize repository
- `dot-man status` - Display current state
- `dot-man switch <branch>` - Save/deploy configurations
- `dot-man edit` - Open config in editor
- `dot-man audit` - Scan for secrets
- `dot-man deploy <branch>` - One-way deploy for new machines

---

## Roadmap to V1.0

| Feature | Status |
|---------|--------|
| Core commands | ✅ Complete |
| Remote sync | ✅ Complete |
| TUI | ✅ Complete |
| Tags & History (0.8.0) | ✅ Complete |
| Test Coverage (80%+) | 🔄 In Progress |
| PyPI Publication | ⏳ Pending |
| Full Documentation | ⏳ Pending |
| Stable API | ⏳ Pending |

## Future Ideas (Post V1.0)

- Encrypted files support (GPG/age)
- Symlink mode
- Web dashboard for configuration management
- Dotfile sharing/marketplace
- CI/CD integration for dotfile testing
- Cloud sync backends (S3, Dropbox, etc.)
- Plugin system