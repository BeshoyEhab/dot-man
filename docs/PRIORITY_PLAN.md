# Priority Improvement Plan

> Generated from project analysis — 2026-06-27

---

## P0 — Critical (Do First)

These are bugs or broken things that affect correctness.

### 1. Fix `doctor_cmd.py:117` — `.exists()` on string
- **What:** mypy reports `"str" has no attribute "exists"`. Calling `.exists()` on a string path instead of `Path` object.
- **Impact:** Will crash at runtime when `dot-man doctor` runs.
- **Fix:** Wrap the path in `Path()` before calling `.exists()`.
- **Effort:** 5 min

### 2. Fix `remote_cmd.py:225` — `Path` vs `str` type mismatch
- **What:** `Path` passed where API expects `str`.
- **Impact:** May cause runtime errors on remote operations.
- **Fix:** Add `.as_posix()` or `str()` conversion.
- **Effort:** 5 min

### 3. Remove committed build artifacts from git
- **What:** `backup.tar.gz` (3.7MB), `backup.zip` (4.1MB), `build/`, `dist/`, `.egg-info/`, `.coverage`, `coverage.json` — **~8.7MB of junk**.
- **Fix:**
  1. Add patterns to `.gitignore`
  2. `git rm --cached` the tracked artifacts
  3. Consider `git filter-branch` or BFG to purge from history (optional)
- **Effort:** 15 min

### 4. Fix stale README coverage claim
- **What:** README says "83% (1519 tests)" but actual is **81% (1527 tests)**.
- **Fix:** Update the coverage and test count in README.md.
- **Effort:** 2 min

---

## P1 — High Priority (Next Sprint)

Significant quality or feature gaps that limit competitiveness.

### 5. Increase test coverage on core commands

| Module | Current | Target | Risk |
|--------|---------|--------|------|
| `save_cmd.py` | **15%** | 80%+ | Core command, barely tested |
| `status_cmd.py` | **39%** | 80%+ | Core UX, mostly untested |
| `navigate_cmd.py` | **58%** | 80%+ | Most complex command |
| `audit_cmd.py` | **68%** | 80%+ | Security command |
| `revert_cmd.py` | **68%** | 80%+ | Data safety command |
| `core.py` | **66%** | 80%+ | Git wrapper, remote paths untested |

**Approach:** Focus on error paths and edge cases — happy paths are mostly covered.

### 6. Break up `navigate_cmd.py` (934 lines)
- **What:** God file with 211-line function `_handle_branch_navigate` and duplicated hook execution logic (lines 795-818 ≈ 832-855).
- **Fix:**
  1. Extract hook execution into `hooks.py` helper (`run_hooks(phase, hooks, context)`)
  2. Split `_handle_branch_navigate` into `_save_phase()`, `_switch_phase()`, `_deploy_phase()`
- **Effort:** 2-3 hours

### 7. Break up `config_cmd.py` (967 lines)
- **What:** Second largest file, already had a 302-line function broken up but still massive.
- **Fix:** Extract subcommand groups into `config_subcommands/` or at minimum split into logical sections.
- **Effort:** 2-3 hours

### 8. Break up `common.py` (671 lines, 64% coverage)
- **What:** Grab-bag module: completions, error handling, decorators, secret handler creation.
- **Fix:** Split into `completions.py`, `decorators.py`, `error_handling.py`.
- **Effort:** 1-2 hours

### 9. Remove `Section._get_current_branch()` circular import hack
- **What:** Creates a new `GlobalConfig()` instance on every call just to get the branch name. Done to avoid circular imports.
- **Fix:** Pass branch name as a parameter instead of reaching through global state.
- **Effort:** 1 hour

---

## P2 — Medium Priority (Next Month)

Features that close competitive gaps with chezmoi/yadm.

### 10. Add templating with conditional logic
- **What:** Current templates only support `{{VAR}}` substitution. chezmoi's killer feature is Go templates with `{{ if eq .os "darwin" }}...{{ end }}`.
- **Proposed syntax:**
  ```toml
  # In section config
  [myapp]
  paths = ["~/.config/myapp/config.toml"]
  template_vars = { os = "darwin", hostname = "work-laptop" }
  ```
  ```toml
  # In template file: config.toml.tmpl
  {{ if eq .os "darwin" }}
  editor = "code"
  {{ else }}
  editor = "nvim"
  {{ end }}
  ```
- **Approach:** Use Python's `string.Template` with custom extensions, or integrate `jinja2` (already common in Python ecosystem).
- **Effort:** 1-2 days
- **Priority rationale:** This is the #1 reason people choose chezmoi over alternatives.

### 11. Add vault key rotation
- **What:** Fernet vault has no key rotation mechanism. If the key is compromised, there's no safe way to rotate.
- **Fix:** Add `dot-man vault rotate` command that re-encrypts all secrets with a new key.
- **Effort:** 4-6 hours

### 12. Add `--diff` to more commands
- **What:** `dot-man diff` exists but `navigate`, `deploy`, `save` don't show previews by default.
- **Fix:** Add `--dry-run` flag to `navigate` and `deploy` that shows what would change before applying.
- **Effort:** 3-4 hours

### 13. Add package manager integration
- **What:** chezmoi can install brew/apt packages as part of machine setup. dot-man has no equivalent.
- **Fix:** Add `pre_deploy` hook alias for common package managers, or a `dot-man bootstrap` command.
- **Effort:** 1 day

### 14. Reduce bare `except Exception` handlers
- **What:** 138 bare `except Exception` handlers. Some silently swallow real errors (especially in `navigate_cmd.py` hook execution).
- **Fix:** Audit and replace with specific exception types where possible. Add logging to swallowed exceptions.
- **Effort:** 4-6 hours

---

## P3 — Lower Priority (Next Quarter)

Nice-to-haves and long-term improvements.

### 15. Windows support
- **What:** Currently Linux/macOS only. No path normalization for Windows.
- **Fix:** Add `pathlib.Path` normalization throughout, handle drive letters, test on Windows CI.
- **Effort:** 2-3 days
- **Note:** Low demand for Python dotfile managers on Windows — most users use WSL.

### 16. Add `age` encryption support alongside Fernet
- **What:** chezmoi and yadm support `age` (modern, simpler than GPG). dot-man only has Fernet.
- **Fix:** Add optional `age` backend via `pyage` or subprocess call to `age` binary.
- **Effort:** 1 day

### 17. Add YAML conditionals in config
- **What:** YAML config support exists but no conditional logic based on OS/hostname.
- **Fix:** Add `when` field to section config:
  ```toml
  [myapp]
  paths = ["~/.config/myapp"]
  when = { os = "linux" }
  ```
- **Effort:** 4-6 hours

### 18. Create full documentation site
- **What:** README + markdown docs exist but no hosted documentation site.
- **Fix:** Set up mkdocs or sphinx, deploy to GitHub Pages.
- **Effort:** 1-2 days

### 19. Add `--json` output option
- **What:** No machine-readable output for scripting/CI integration.
- **Fix:** Add `--json` flag to `status`, `log`, `diff`, `branch list`.
- **Effort:** 4-6 hours

### 20. Cloud sync backends
- **What:** Currently git-only for remote sync. ConfigSync offers S3/Dropbox/Google Drive.
- **Fix:** Add optional sync backends via plugin system.
- **Effort:** 2-3 days
- **Note:** YAGNI — git remote covers 95% of use cases.

---

## Competitive Landscape Summary

| Feature | chezmoi | yadm | Stow | dot-man | Priority |
|---------|---------|------|------|---------|----------|
| Git branch profiles | No | Yes | No | Yes | ✅ Already have |
| Conditional templating | Go templates | Alt files | No | **Missing** | P2 |
| Secret management | 15+ pw managers | GPG | None | Fernet vault | ✅ Have (add rotation) |
| Cross-platform | Win/Mac/Linux | Mac/Linux | Unix | Linux/Mac | P3 |
| Package management | brew/apt | No | No | **Missing** | P2 |
| Watch mode | No | No | No | **Have** | ✅ Advantage |
| TUI | Yes | No | No | **Have** | ✅ Advantage |
| TOML config | No | No | No | **Have** | ✅ Unique |

---

## Effort vs Impact Matrix

```
                    HIGH IMPACT
                        │
    P0: Bugs ──────────┤
    (quick fixes)       │
                        │
    P2: Templating ─────┤
    P2: Key rotation    │
                        │
    P1: Test coverage ──┤
    P1: Refactor ───────┤
                        │
                        ├──────────────── LOW IMPACT
    P3: Windows ────────┤
    P3: JSON output ────┤
    P3: Cloud sync ─────┤
                        │
                    LOW EFFORT ──────────── HIGH EFFORT
```

---

## Recommended Order

1. **Week 1:** P0 bugs (items 1-4) — quick wins, high impact
2. **Week 2-3:** P1 test coverage (item 5) — biggest quality gap
3. **Week 3-4:** P1 refactoring (items 6-9) — reduce complexity
4. **Month 2:** P2 templating (item 10) — biggest feature gap vs chezmoi
5. **Month 2:** P2 vault rotation (item 11) — security hardening
6. **Month 3:** P2 remaining, then P3 as time permits
