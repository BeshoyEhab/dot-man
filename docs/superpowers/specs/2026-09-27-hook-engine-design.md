# Unified Hook Engine — Design Spec

Date: 2026-09-27 · Status: approved design, awaiting implementation plan
Approach: central engine module (no prose-only schema, no event bus).

## 1. Problem

dot-man grew three overlapping hook mechanisms with no unifying schema:

| # | Piece | Lives in | Gap |
|---|-------|----------|-----|
| 1 | Section hook fields (`pre_deploy`, `post_deploy`, `on_activate`, `on_deactivate`) | `section.py` (`_resolve_hook`) | OK (alias → `{x}` → `file:`) |
| 2 | `HOOK_ALIASES` (~30 named one-liners) | `constants.py` | resolved in 3 places, one without context |
| 3 | `file:<script> [args]` references | `hooks.py` | no escape for literal text |
| 4 | Global `pre_<cmd>` / `post_<cmd>` scripts | `hooks.py` (`run_hook`) | only switch/checkout fire |
| 5 | `{{VAR}}` + conditionals for file contents | `global_config.py` (`substitute_templates`) | separate vocabulary |
| 6 | Auto-detected hooks (`FILE_TO_HOOK_MAP`, `get_hook_for_config`, `get_auto_hooks_for_config`) | `branch_ops.py`, `config_detector.py` | alias resolved **without** section context — `{config_name}` ships raw |

Executors are tripled too: navigate's `_run_shell_hooks` (capture + warn),
deploy's inline `subprocess.run(cmd, shell=True)` loop, and `run_hook`
(script files + env + timeout).

## 2. Scope

**In:** one resolve path + one shell runner for all hook shell; one
canonical placeholder vocabulary; `\file:` escape; docs rewritten from
the engine.

**Out (explicit):** firing global scripts in the other 8 commands
(separate follow-up); `{{ }}` engine changes; config-values template
variables (separate TODO item — consumes §4's vocabulary when built);
`{x}` placeholders inside deployed file contents (unsafe: collides with
Python/JSON/shell braces — never allowed).

## 3. Module surface

New `dot_man/hook_engine.py`, exactly two public functions:

- `resolve(hook: str | None, context: HookContext) -> str | None`
- `run(commands: list[str], label: str, env: dict | None = None) -> bool`
  (returns True if any hook failed — today's `_run_shell_hooks` contract)

`HookContext`: section name, config name/root, paths, branch. The
existing `run_hook()` (global script *files*) stays as the file
executor — out of scope by design, not oversight.

## 4. Resolution pipeline and vocabulary

Order inside `resolve()`: alias lookup → `{x}` placeholders →
`file:` tokens. Canonical vocabulary:

`section_name`, `config_name`, `config_root`, `paths`, `branch`.

`{qs_config}` remains as the deprecated spelling of `config_name`.
`\file:<name>` renders the literal text `file:<name>` (backslash
consumed; in TOML basic strings write `"\\file:x"`). `../` escapes are
rejected; missing scripts raise `ConfigurationError` naming both
searched dirs (`<repo>/hooks/`, then `~/.config/dot-man/hooks/`);
exec bit auto-added, mirroring `run_hook()`. Placeholder names absent
from the context (e.g. auto-detected hooks with no matched section)
pass through literally — never an error.

## 5. Call-site migration (exhaustive)

- `Section._resolve_hook` → `resolve()` (same order as today).
- `branch_ops.detect_hooks_for_changed_files` → `resolve()` with
  section context. **Intended behavior change:** auto-detected aliases
  no longer ship raw `{config_name}`.
- navigate `_run_shell_hooks`, deploy inline loop, `run_branch_hooks`
  → `run()`.
- `config_detector.get_auto_hooks_for_config` unchanged (returns names;
  resolution happens at Section load).
- Global `run_hook()`, `hooks_cmd`, command firing untouched.

## 6. Failure semantics (one intended change)

Resolve-time problems raise `ConfigurationError`. Run-time failures
warn and continue; `run()` reports. No fail-fast.

Carve-out: deploy's inline loops currently swallow nonzero exits
silently (`check=False`, no output); after migrating to `run()`,
failing deploy hooks print the same warning navigate prints today.
No test pins the silence (verified); the change is an improvement,
not a regression.

## 7. Testing

TDD: new `tests/test_hook_engine.py` — pipeline order, escape,
vocabulary, repo-over-global precedence, traversal rejection, run
success/failure/mixed, env passthrough. All existing hook, section,
navigate, and deploy tests must pass with behavior intact; two
mechanical repoints allowed (no behavior change): `test_hook_scripts.py`
fixture patches move to `dot_man.hook_engine`, and the three
`run_branch_hooks` tests patch `dot_man.hook_engine.subprocess`
instead of `dot_man.cli.navigate_cmd.subprocess`. Full quality gate
(black, ruff, mypy, pytest, coverage must not decrease).

## 8. Docs

`docs/concepts/hooks.md` rewritten from this spec (schema → docs).
`CHANGELOG.md` + `TODO.md` updated. No per-command help rewrites.
