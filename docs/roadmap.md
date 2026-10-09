# Development Roadmap

## v1.5.0 - Current Stable ✅

- ✅ Full coverage floor — every module ≥ 90% (2350 tests, 96% coverage)
- ✅ Consistent exit codes — `ExitCode` enum, `sys.exit()` eliminated
- ✅ Centralized error handling — `DotManGroup.invoke()` routes through `handle_exception()`
- ✅ Two-level help — `help`/`--help` happy path, `help-all` everything, man page
- ✅ Hook scripts directory — `file:<script> [args]` in section hooks
- ✅ Decorator-driven completion engine
- ✅ Shell completions for all commands (bash, zsh, fish)
- ✅ Custom secret patterns
- ✅ Symlink deploy mode
- ✅ Quickshell hook aliases
- ✅ Template substitution & conditionals
- ✅ Vault key rotation
- ✅ Full documentation site (mkdocs Material)

---

## v1.6.0 - Next Release (Planned)

### Extensibility

- [ ] Plugin API — extension mechanism for third-party tools (parked)

---

## Coverage Focus

Lowest-covered modules (source of truth: `TODO.md`, regenerated 2026-10-09): **none
below 90%** — the floor sweep cleared every module (suite 2350 passing, 96% coverage).

---

## v2.0+ - Future Ideas

### Storage & Sync

- [ ] Cloud sync backends — S3, Dropbox, Google Drive
- [ ] Per-branch config inheritance — `inherits_branch = "main"` in config

### User Experience

- [ ] Web dashboard — Browser-based configuration management
- [ ] JSON output — `--json` option for scripting

### Ecosystem

- [ ] Dotfile sharing/marketplace — Share configs with community
- [ ] CI/CD integration — Test dotfiles before deployment

---

## Completed Milestones

### v1.5.0 — Coverage Floor & UX Hardening (2026-10-09)
- ✅ Full coverage floor — every module ≥ 90% (suite 2350 passing, 96% coverage)
- ✅ Consistent exit codes — `ExitCode` enum, `sys.exit()` eliminated
- ✅ Centralized error handling — `DotManGroup.invoke()` routes through `handle_exception()`
- ✅ Two-level help — `help`/`--help` happy path, `help-all` everything, man page
- ✅ Hook scripts directory — `file:<script> [args]` in section hooks, repo `hooks/` + global fallback
- ✅ Path completions for `add`, package-manager completions for `bootstrap`
- ✅ Bug fixes — `revert -c` section paths, `shared_sync` branch exclusion, `verify` broken symlinks

### v1.4.0 — Decorator-Driven Shell Completion Engine (2026-08-25)
- ✅ `@completes(path, param=...)` decorator registry
- ✅ `dot-man --complete <shell>` protocol
- ✅ Fish completions fully dynamic
- ✅ Defaults and choices shown inline
- ✅ Aliases labeled `(alias)` in listings

### v1.3.0 — Template Substitution & Conditionals (2026-06-27)
- ✅ `{{VAR}}` placeholders in config files
- ✅ Conditional syntax `{{ if OS == "darwin" }}...{{ endif }}`
- ✅ Vault key rotation
- ✅ 62 new tests

### v1.2.x — Symlink Mode & Quickshell (2026-05-17 to 2026-06-11)
- ✅ `deploy_method = "symlink"` per section
- ✅ Quickshell hook aliases with `{qs_config}` placeholder
- ✅ Interactive symlink handling
- ✅ Deduplicated deploy logic

### v1.0.0 — Production Release (2026-05-17)
- ✅ YAML configuration support
- ✅ Import from chezmoi, yadm, stow
- ✅ Export to tar, zip, JSON
- ✅ Auto-discover dotfile locations
- ✅ GPG/AGE file encryption
- ✅ Rich diff output
- ✅ PyPI publication

### v0.8.0 — History & Tags (2026-05-10)
- ✅ `dot-man log`, `dot-man tag`, `dot-man diff`
- ✅ Template variables, machine profiles
- ✅ Batch file operations, parallel secret scanning

### v0.1.0–v0.7.0 — Foundation
- ✅ Core commands, hooks, remote sync, TUI
- ✅ TOML config, template inheritance
- ✅ Backup system, file locking
- ✅ Doctor, verify, clean commands

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Test Coverage | 96% (2350 tests) | 90%+ |
| Core Commands | 30+ commands | All stable |
| Lint Errors | 0 (ruff + mypy) | 0 |
| Documentation | Full docs site | Keep updated |
| Distribution | PyPI (`dotman-git`) | Stable releases |
