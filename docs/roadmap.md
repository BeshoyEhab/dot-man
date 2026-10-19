# Development Roadmap

## v1.6.0 - Current Stable ✅ (2026-10-19)

### Correctness & Security

- ✅ Audit sweep — 15 correctness fixes (navigate to a commit/tag now deploys
  and records state, atomic config writes, `create_symlink` data-loss guard,
  `export` flags honored, `status --json` emits valid JSON, …)
- ✅ 13 security fixes — no `shell=True` in `bootstrap`, shell-quoted hook
  placeholders, encryption wired into save/deploy, secret masking, `repo_path`
  containment, vault key hardening, and `audit --history`
- ✅ Restore is byte-exact — `restore`/`revert --commit` no longer drop the
  trailing newline

### CLI Experience

- ✅ Global flags — `--quiet`/`--yes`/`--no-input`/`--no-color`/`--json`/`--plain`
- ✅ Uniform `--dry-run` across mutating commands
- ✅ `encrypt`/`vault`/`hooks` normalized to Click groups
- ✅ Terminal-width-aware output and plain mode
- ✅ `import` asks before committing (`--yes`/`--no-commit`)
- ✅ Diagnostics go to stderr; stdout carries data only

### Architecture

- ✅ Paths resolved at call time (`constants.get_*`) — a single patch point
- ✅ Silent exception handlers narrowed and logged
- ✅ Overlapping commands consolidated — `log --commit`, `rollback --backup`,
  `revert --commit`
- ✅ Version single-sourced from `dot_man.__version__`

### Deprecated (removed in v2.0)

- `switch`, `checkout`, `tag switch` → `navigate`
- `restore <file> <sha>` → `revert <file> --commit <sha>`
- `show <sha>` → `log --commit <sha>`
- `backup restore <id>` → `rollback --backup <id>`

---

## v1.7.0 - Next Release (Planned)

### Extensibility

- [ ] Plugin API — extension mechanism for third-party tools (parked) — also the
  target for removing the v1.6.0 deprecated shims in v2.0

---

## Coverage Focus

Lowest-covered modules (source of truth: `TODO.md`, regenerated 2026-10-19): **none
below 90%** — the floor sweep cleared every module (suite 2490 passing, 96% coverage).

---

## v2.0+ - Future Ideas

### Storage & Sync

- [ ] Cloud sync backends — S3, Dropbox, Google Drive
- [ ] Per-branch config inheritance — `inherits_branch = "main"` in config

### User Experience

- [ ] Web dashboard — Browser-based configuration management
- ✅ JSON output — global `--json` flag (shipped in v1.6.0 CLI improvements)

### Ecosystem

- [ ] Dotfile sharing/marketplace — Share configs with community
- [ ] CI/CD integration — Test dotfiles before deployment

---

## Completed Milestones

### v1.5.0 — Coverage Floor & UX Hardening (2026-10-09)
- ✅ Full coverage floor — every module ≥ 90% (suite 2476 passing, 96% coverage)
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
