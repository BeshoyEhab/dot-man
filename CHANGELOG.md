# Changelog

All notable changes to dot-man will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.3] - 2026-06-11

### Added

- **Interactive symlink handling** — `dot-man add`, `navigate`, and `watch` now detect symlinked config paths and prompt the user with three choices: follow the link (save target content), ignore (skip this path), or ignore all. Deploying also warns when overwriting a symlinked local path.

### Fixed

- **Python 3.10 CI compatibility** — `dot_man/cli/__init__.py` no longer shadows module names with same-named function imports.

## [1.2.1] - 2026-06-10

### Refactored

- **Deduplicate deploy logic** — extracted `_build_final_excludes`, `_deploy_repo_path`, `_restore_file_secrets_inplace` from duplicate code in `deploy_section` and `deploy_item` (save_deploy_ops.py)
- **Unify config loading** — extracted `load_config_file()` function in `global_config.py`, removing 30 lines of duplicate YAML/TOML loading from both `DotManConfig` and `GlobalConfig`
- **Clean up silent `except: pass`** — removed 4 redundant `pass` statements after `logging.debug()` in `common.py`, added `logging.debug()` to a bare `except` in `core.py`
- **Break up `_run_interactive_tutorial`** — 302-line function split into 8 discrete step functions (config_cmd.py)
- **Extract `SECTION_EXAMPLES`** — 260-line data dict moved from function body to module-level constant (config_cmd.py)
- **Break up `run_setup_wizard`** — 250-line wizard split into 5 helpers (init_cmd.py)
- **Break up `setup`** — 253-line remote setup split into 17 helpers; deep nesting reduced from 11 to 4 levels (remote_cmd.py)
- **Reduce deep nesting in `edit`** — from 11 to 4-5 levels (edit_cmd.py)

### Test Improvements

- Strengthened loose assertions (24 tests): added output content checks, mock-call assertions, or file-state assertions
- **`interactive.py`** — 47 tests, 47% → 100% coverage
- **`branch_cmd.py`** — 23 tests, 51% → 100% coverage
- **`deploy_cmd.py`** — 25 tests, 59% → 100% coverage
- Overall coverage: 66% → 83%

## [1.2.0] - 2026-05-17

### Added
- **Symlink deploy mode** — `deploy_method = "symlink"` per section
- **Quickshell hook aliases** — `quickshell_reload`, `quickshell_restart`, `quickshell_validate` with `{qs_config}` → `{config_name}` placeholder

### Fixed
- README outdated commands (switch → navigate)
- Test compatibility for Python 3.10

## [1.0.0] - 2026-05-17

### Added
- **Production Release** - Official v1.0.0 stable release
- **YAML configuration support** - Config files now support `.yaml` and `.yml` formats alongside TOML:
  - Automatic format detection
  - Warning when multiple config files exist (TOML takes priority)
  - Environment variable expansion in paths (`$HOME`, `$USER`, `$WORK_DIR`, etc.)
- **`dot-man import`** - Import dotfiles from other dotfile managers:
  - `dot-man import chezmoi` - Import from chezmoi
  - `dot-man import yadm` - Import from yadm
  - `dot-man import stow` - Import from GNU Stow packages
  - `dot-man import all` - Auto-detect and import from any source
  - `--dry-run` to preview what would be imported
- **`dot-man export`** - Export dotfiles to portable formats:
  - `dot-man export tar backup.tar.gz` - Tar archive
  - `dot-man export zip dots.zip` - Zip archive
  - `dot-man export json manifest.json` - JSON manifest
  - `--branch` to export specific branch
- **`dot-man discover`** - Auto-detect existing dotfiles:
  - Scans 30+ common dotfile locations (shells, WMs, terminals, editors)
  - `--add` to automatically add to dot-man.toml
  - `--include-extended/--no-extended` for VS Code, Sublime, etc.
- **`dot-man encrypt`** - Encrypt/decrypt sensitive files:
  - GPG and AGE encryption support
  - `encrypt status` - Show encryption status
  - `encrypt encrypt <section>` - Encrypt section files
  - `encrypt decrypt <section>` - Decrypt section files
- **`dot-man diff --rich`** - Syntax-highlighted diffs using rich library:
  - Monokai theme with line numbers
  - `--no-rich` to use plain git diff (default: enabled)
- **PyPI packaging** - Ready for `pip install dot-man`

### Changed
- **Version bump to 1.0.0** - Production stable release
- **Removed legacy code**:
  - Removed INI migration (TOML/YAML only)
  - Removed unused `LegacyConfigLoader` class
  - Consolidated `LOCK_FILE` to constants.py
  - Removed `GLOBAL_CONF` and `DOT_MAN_INI` constants
- **Config file priority**: TOML (.toml) > YAML (.yaml/.yml)
- **`switch` command** - Marked as DEPRECATED, shows warning and points to `navigate`
- **`checkout` command** - Marked as DEPRECATED, shows warning and points to `navigate`

### Deprecated
- `switch` → Use `navigate` instead
- `checkout` → Use `navigate` instead

### Fixed
- Type annotations for shell completion
- Import assertions for type safety
- Various lint and type checking issues

## [0.10.0] - 2026-05-17

### Added
- **YAML configuration support** - Config files now support `.yaml` and `.yml` formats alongside TOML:
  - Automatic format detection
  - Warning when multiple config files exist (TOML takes priority)
  - Environment variable expansion in paths (`$HOME`, `$USER`, `$WORK_DIR`, etc.)
- **`dot-man import`** - Import dotfiles from other dotfile managers:
  - `dot-man import chezmoi` - Import from chezmoi
  - `dot-man import yadm` - Import from yadm
  - `dot-man import stow` - Import from GNU Stow packages
  - `dot-man import all` - Auto-detect and import from any source
  - `--dry-run` to preview what would be imported
- **`dot-man export`** - Export dotfiles to portable formats:
  - `dot-man export tar backup.tar.gz` - Tar archive
  - `dot-man export zip dots.zip` - Zip archive
  - `dot-man export json manifest.json` - JSON manifest
  - `--branch` to export specific branch
- **`dot-man discover`** - Auto-detect existing dotfiles:
  - Scans 30+ common dotfile locations (shells, WMs, terminals, editors)
  - `--add` to automatically add to dot-man.toml
  - `--include-extended/--no-extended` for VS Code, Sublime, etc.
- **`dot-man encrypt`** - Encrypt/decrypt sensitive files:
  - GPG and AGE encryption support
  - `encrypt status` - Show encryption status
  - `encrypt encrypt <section>` - Encrypt section files
  - `encrypt decrypt <section>` - Decrypt section files
- **`dot-man diff --rich`** - Syntax-highlighted diffs using rich library:
  - Monokai theme with line numbers
  - `--no-rich` to use plain git diff (default: enabled)

### Changed
- **Removed legacy code**:
  - Removed INI migration (TOML/YAML only)
  - Removed unused `LegacyConfigLoader` class
  - Consolidated `LOCK_FILE` to constants.py
  - Removed `GLOBAL_CONF` and `DOT_MAN_INI` constants
- **Config file priority**: TOML (.toml) > YAML (.yaml/.yml)
- **`switch` command** - Marked as DEPRECATED, shows warning and points to `navigate`
- **`checkout` command** - Marked as DEPRECATED, shows warning and points to `navigate`

### Deprecated
- `switch` → Use `navigate` instead
- `checkout` → Use `navigate` instead
- `tag switch` → Use `navigate` instead

## [1.2.0] - 2026-06-09

### Added
- **Generalized placeholder system in hooks** — `{qs_config}` replaced with `{config_name}`, `{config_root}`, `{section_name}`, `{paths}`, `{branch}`
- **Shell completions** — `encrypt <section>`, `export --branch`, `rollback <target>`
- **Custom Secret Patterns** — Support defining custom regex patterns for secret detection in config
- **Secret Scanner Customization** — `use_default_patterns = false` to disable built-in patterns
- **Symlink Deploy Mode** — per-section `deploy_method = "symlink"` for edit-in-place workflows
- **Quickshell Hook Aliases** — `quickshell_reload`, `quickshell_restart`, `quickshell_validate` with `{qs_config}` → `{config_name}` placeholder
- **`complete_sections()`** — shell completion callback for section names

### Changed
- **`switch_cmd` consolidated → thin wrapper** — `switch` is now a 17-line wrapper calling `_navigate_impl()` (~80% code reduction)
- **`BranchParamType` deduplicated** — moved from `switch_cmd.py`/`navigate_cmd.py` to `common.py`
- **Schema keys deduplicated** — `VALID_SECTION_KEYS` defined once in `dotman_config.py`
- **`HOOK_ALIASES` unified** — `constants.py` is canonical; `merge.py` imports from it
- **Silent `except: pass` cleanup** — `logging.debug()`/`logging.warning()` added to 11+ bare exceptions across `common.py`, `navigate_cmd.py`, `rollback_cmd.py`, `core.py`, `files.py`, `init_cmd.py`
- **Production `assert` statements removed** — all replaced with `if/error()` pattern in `navigate_cmd.py`, `encrypt_cmd.py`, `import_cmd.py`, `rollback_cmd.py`
- **Coverage improved from 60% → 66%** — 1146 tests (up from 1021), 1 skipped

### Fixed
- **Weak `>=` assertions** in `test_section.py`, `test_save_deploy_ops.py`, `test_status_ops.py`, `test_core_extended.py`, and 4 new test files
- **Missing f-string prefix** in `dotman_config.py:96`
- **Stale `dot-man.ini` reference** in `status_ops.py:158`

### New Tests
| File | Tests | Coverage Impact |
|------|-------|-----------------|
| `test_files_comprehensive.py` | 55 | `files.py` 73% → 94% |
| `test_branch_ops.py` | 39 | `branch_ops.py` 40% → 97% |
| `test_encryption.py` | 32 | `encryption.py` 33% → 100% |
| `test_completions_cmd.py` | 10 | `completions_cmd.py` 12% → 94% |
| `test_shell_completions.py` | 7 | Shell completions verified |
| `test_section.py` | 39 (+36) | `section.py` 70% → 95% |
| `test_save_deploy_ops.py` | 26 | `save_deploy_ops.py` 52% → 75% |
| `test_status_ops.py` | 17 | `status_ops.py` 59% → 89% |
| `test_core_extended.py` | 46 | `core.py` 58% → 66% |

## [1.1.1] - 2026-05-20

### Added
- **PyPI Publication** - Official release published to PyPI as `dotman-git`.
- **Command Aliases** - Short 3-letter command aliases added for all major operations:
  - `nav` (navigate), `doc` (doctor), `dep` (deploy), `enc` (encrypt)
  - `exp` (export), `imp` (import), `dis` (discover), `aud` (audit)
  - `cln` (clean), `ver` (verify), `rev` (revert), `rol` (rollback)
  - `wat` (watch), `cpl` (completions), `rst` (restore), `edt` (edit)
  - `sta` (status), `ini` (init), `syn` (sync), `log` (log), `dif` (diff)
  - `hks` (hooks)
- **`dot-man watch`** — Auto-save tracked dotfiles on change (supporting both watchdog and polling backends, debounced commits, and `--no-commit`/`--dry-run` flags).
- **`dot-man rollback`** — Transaction-style rollback to any previous commit, tag, or `HEAD~N`, with colored diffs and automatic pre-rollback backups.
- **YAML Comment Preservation** - Added round-trip YAML configuration comment and layout preservation using `ruamel.yaml`.

### Changed
- **README Overhaul** - Redesigned README with project badges, architecture diagrams, config examples (TOML/YAML), and command reference tables.
- **License & Copyright** - Updated license with additional copyright holder (ZVAXEROWS) and copyright years to 2025, 2026.

### Fixed
- **Profile Switch & Serialization** - Resolved a traceback in `profile switch` by properly parsing branch parameters for `ctx.invoke`.
- **Global Config Save** - Defaulted `GlobalConfig.save()` to write to disk (`force=True`) to prevent silent save failures across CLI commands.
- **TOML Serialization of None** - Prevented `tomlkit` ConvertError by omitting the `inherits` key if its value is `None` during profile creation.
- **YAML Configuration Overwrites** - Resolved a bug where editing configuration fields would silently convert YAML files back to TOML on save.
- **TOML/YAML Comment Preservation & Key Deletions** - Fixed a bug in document updates where deleted configuration keys were not removed from the saved file, and added value equality checks to prevent losing comments on sequence fields.
- **Integration Tests** - Added robust test cases covering the complete `profile switch` flow, validating branch switching, warnings, inheritance, and error handling.
