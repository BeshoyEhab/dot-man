# Changelog

All notable changes to dot-man will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-05-17

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

## [Unreleased]

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

### Changed
- **README Overhaul** - Redesigned README with project badges, architecture diagrams, config examples (TOML/YAML), and command reference tables.
- **License & Copyright** - Updated license with additional copyright holder (ZVAXEROWS) and copyright years to 2025, 2026.

### Fixed
- **Profile Switch & Serialization** - Resolved a traceback in `profile switch` by properly parsing branch parameters for `ctx.invoke`.
- **Global Config Save** - Defaulted `GlobalConfig.save()` to write to disk (`force=True`) to prevent silent save failures across CLI commands.
- **TOML Serialization of None** - Prevented `tomlkit` ConvertError by omitting the `inherits` key if its value is `None` during profile creation.
- **Integration Tests** - Added robust test cases covering the complete `profile switch` flow, validating branch switching, warnings, inheritance, and error handling.
