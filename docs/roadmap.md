# Development Roadmap

## v1.4.0 - Current Stable ✅

- ✅ Decorator-driven completion engine
- ✅ Shell completions for all commands (bash, zsh, fish)
- ✅ Custom secret patterns
- ✅ Symlink deploy mode
- ✅ Quickshell hook aliases
- ✅ Template substitution & conditionals
- ✅ Vault key rotation
- ✅ 1700+ tests, 84% coverage
- ✅ Full documentation site (mkdocs Material)

---

## v1.5.0 - Next Release (Planned)

### Shell Completions

- [ ] Complete local file paths for `add` command ✅
- [ ] Complete package manager names for `bootstrap` command ✅

### User Experience

- [ ] Consistent exit codes — replace `sys.exit(1)` / `raise SystemExit(1)` mix
- [ ] Centered error handling — route all commands through `handle_exception()`

### Extensibility

- [ ] Hook scripts directory — support executing custom hook scripts from a folder
- [ ] Plugin API — extension mechanism for third-party tools

---

## Coverage Focus

Lowest-covered modules:

| Module | Coverage |
|--------|----------|
| `cli/bootstrap_cmd.py` | 15% |
| `cli/export_cmd.py` | 25% |
| `cli/completions.py` | 62% |
| `cli/watch_cmd.py` | 65% |
| `core.py` | 66% |
| `cli/audit_cmd.py` | 68% |
| `cli/navigate_cmd.py` | 68% |
| `cli/revert_cmd.py` | 68% |

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
| Test Coverage | 84% (1700+ tests) | 90%+ |
| Core Commands | 30+ commands | All stable |
| Lint Errors | 0 (ruff + mypy) | 0 |
| Documentation | Full docs site | Keep updated |
| Distribution | PyPI (`dotman-git`) | Stable releases |
