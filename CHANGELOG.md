# Changelog

All notable changes to dot-man will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Added
- (No new changes in unreleased)
