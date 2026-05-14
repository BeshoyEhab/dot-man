# API Stability Policy

This document defines the stable API surface for dot-man and the guarantees provided to users, scripts, and integrations.

---

## Versioning Scheme

dot-man follows [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH
```

- **MAJOR** (x.0.0): Incompatible API changes
- **MINOR** (1.x.0): New backwards-compatible features
- **PATCH** (1.1.x): Backwards-compatible bug fixes

---

## Stable API Surface

The following are considered stable and will not change without a MAJOR version bump:

### CLI Commands

All commands in `dot-man --help` are stable:
- `init`, `status`, `navigate`, `edit`, `deploy`, `audit`
- `branch`, `tag`, `remote`, `config`, `profile`, `template`
- `hooks`, `log`, `diff`, `show`, `restore`, `revert`
- `clean`, `backup`, `verify`, `doctor`

Command flags that are documented in `--help` are stable.

### Configuration Files

| File | Stability |
|------|-----------|
| `dot-man.toml` | Stable |
| `~/.config/dot-man/global.toml` | Stable |
| Hook scripts in `~/.config/dot-man/hooks/` | Stable |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid usage (bad arguments) |
| 7 | Not initialized (no repo) |

### Environment Variables

Stable environment variables:
- `DOTMAN_HOOK_COMMAND` - Hook being executed
- `DOTMAN_HOOK_PHASE` - pre or post
- `DOTMAN_SOURCE` - Source branch/commit
- `DOTMAN_TARGET` - Target branch/commit
- `HOME` - User home directory

### Hook Script Interface

Hook scripts receive these arguments:
- `$1` - Command name (e.g., "switch", "deploy")
- `$2` - Phase ("pre" or "post")

Hook scripts must exit with:
- 0 to continue
- non-zero to abort (for pre-hooks)

### Output Format

- CLI help text format is stable
- Error messages are stable
- Success/warning/info message patterns are stable

---

## Unstable API (May Change)

The following are NOT stable and may change without notice:

- Internal module imports (`from dot_man import X`)
- Python API (functions/classes in `dot_man/*.py`)
- Config internal keys (underscore-prefixed: `_internal_key`)
- TUI interface
- Debug output (--verbose, --debug flags)

---

## Compatibility Promise

### For MINOR versions (1.x.0):
- ✅ All documented CLI commands work
- ✅ All documented flags work
- ✅ Config files remain compatible
- ✅ Hook scripts continue to work
- ✅ Exit codes remain consistent

### For PATCH versions (1.1.x):
- ✅ Everything in MINOR promise
- ✅ Bug fixes that don't change behavior
- ✅ Performance improvements

### For MAJOR versions (x.0.0):
- Any of the above may change
- Minimum 6-month deprecation notice
- Migration guide provided

---

## Deprecation Policy

When features are deprecated:

1. **Deprecation warning** - Shown for 2 MINOR versions
2. **Removal** - Removed in next MAJOR version

Example:
```
# v1.2.0
$ dot-man switch
Warning: 'switch' is deprecated. Use 'navigate' instead.

# v1.3.0 (2 minor versions later)
$ dot-man switch
Error: 'switch' has been removed. Use 'navigate'.
```

---

## Reporting Breaking Changes

If you encounter a breaking change that violates this policy, please [open an issue](https://github.com/BeshoyEhab/dot-man/issues).

---

## This Policy Applies To

- dot-man v1.0.0 and later
- All CLI commands
- Configuration files
- Hook system
- Exit codes