# Architecture Deep-Dive

How dot-man fits together: entry, CLI, mixin operations, config loading.

## Entry

`main()` (`cli/main.py`) runs three gates in order: `--complete`
dispatch (shell completions, no side effects), first-run onboarding,
background completions install — then `cli()` (the `DotManGroup` in
`cli/interface.py`). All command errors funnel through
`DotManGroup.invoke()` → `handle_exception()`, exiting via `ExitCode`.

## CLI layer

One file per command (`cli/*_cmd.py`), registered by import in
`cli/__init__.py`. Completions come from the Click tree itself via the
`@completes` decorator (`completion_engine.py`); dynamic providers live
in `completions.py` and never raise. User output goes through `ui.py`
(Rich helpers + `next_steps`); commands never call `sys.exit()`.

## Operations: mixin composition

All business logic hangs off `DotManOperations`
(`operations.py`), which inherits three mixins and adds shared accessors
(`git`, `global_config`, `dotman_config`, `backups`, `vault`) plus
`get_operations()` (cached singleton) / `reset_operations()`:

- `SaveDeployMixin` (`save_deploy_ops.py`) — two-phase deploy
  (`scan_deployable_changes` → `execute_deployment_plan`, thread-pooled)
  and `save_all`; per-section work in `deploy_section`.
- `BranchMixin` (`branch_ops.py`) — switching, revert, tag/commit
  resolution, auto-detected hooks (`detect_hooks_for_changed_files`).
- `StatusMixin` (`status_ops.py`) — `get_detailed_status`,
  audits, orphans.

Mixins declare the surface they need as abstract stubs (see the top of
each `*_ops.py`) so each file is understandable alone; `operations.py`
is the only composition root.

## Config loading

`~/.config/dot-man/repo/dot-man.toml` wins over `.yaml`/`.yml`
(`CONFIG_FILE_PRIORITY`); `global.toml` holds machine state. Per
section, `DotManConfig.get_section()` merges in order — global
defaults → inherited `templates` → section values — then renders
`{{ }}` template variables (two passes, so `config_name` follows
rendered paths), constructs the `Section` (alias → `{x}` placeholders
→ `file:` scripts via the hook engine), and validates
(`update_strategy`, non-empty `paths`) against rendered values.

## Storage and hooks

The repo is a normal working-copy git repository (not bare); each
branch holds a complete configuration. Files deploy by atomic copy
(`os.replace`), with per-section `symlink` mode for edit-in-place
workflows. Secrets are redacted to the local vault before commit.
Hook shell runs through one runner (`hook_engine.run`,
warn-and-continue); global `pre_<cmd>`/`post_<cmd>` scripts run via
`run_hook` with hook env vars.

## Design principles

Schema first (one vocabulary: `navigate`, `{{ }}`/`{x}`, `ExitCode`);
happy path before options (`init` → `add` → `status` → `navigate`);
centralized errors; stdlib over dependencies (custom regex template
parser, no Jinja2).
