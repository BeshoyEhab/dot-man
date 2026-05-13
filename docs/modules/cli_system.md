# CLI System — Deep Explanation
> **Phase 2 of the dot-man Development Guide Manual**  
> Source of truth: `dot_man/cli/` — all information derived from actual code.

---

## Table of Contents

1. [The CLI Stack](#the-cli-stack)
2. [Entry Point to Execution](#entry-point-to-execution)
3. [Command Registration Mechanism](#command-registration-mechanism)
4. [DotManGroup — Typo Suggestions](#dotmangroup--typo-suggestions)
5. [Global Middleware (interface.py)](#global-middleware-interfacepy)
6. [Common Utilities (common.py)](#common-utilities-commonpy)
7. [Command Lifecycle — Step by Step](#command-lifecycle--step-by-step)
8. [Command Modules Deep Dive](#command-modules-deep-dive)
9. [Shell Completion System](#shell-completion-system)
10. [Error Handling Pattern](#error-handling-pattern)

---

## The CLI Stack

```
pyproject.toml entry point
        │
        ▼
dot_man/cli/main.py → main() → cli()
        │
        ▼
dot_man/cli/interface.py → @click.group(cls=DotManGroup)
        │
        │ ← side-effect imports from cli/__init__.py
        │
        ├── init_cmd.py         @cli.command()
        ├── add_cmd.py          @cli.command()
        ├── switch_cmd.py       @cli.command()
        ├── status_cmd.py       @cli.command()
        ├── deploy_cmd.py       @cli.command()
        ├── log_cmd.py          @cli.command() × 3 (log, diff, checkout)
        ├── remote_cmd.py       @cli.group() + @remote.command() × N + @cli.command() (sync, setup)
        └── ... (21 total command modules)
```

---

## Entry Point to Execution

### `pyproject.toml`

```toml
[project.scripts]
dot-man = "dot_man.cli.main:main"
```

This registers `dot-man` as a shell command that calls `main()` in `dot_man/cli/main.py`.

### `main.py` — 6 Lines

```python
from .interface import cli

def main():
    cli()

if __name__ == "__main__":
    main()
```

`main.py` is intentionally minimal. Its **only job** is to import `cli` from `interface.py` and call it. All the actual command registration happens as side effects of what `cli/__init__.py` imports.

**Why this design?** Separating `main.py` from `interface.py` prevents circular imports. If command modules import `cli` from `interface.py`, and `main.py` also imported all commands, a circular chain would form. Instead, `main.py` is the entry point but delegates registration to `cli/__init__.py`.

---

## Command Registration Mechanism

This is the most non-obvious part of the CLI system. Commands are registered via **Python import side effects**.

### How it Works

```python
# cli/__init__.py — the crucial file
from .add_cmd import add          # ← this line causes @cli.command() to execute
from .audit_cmd import audit      # ← same
from .backup_cmd import backup
from .branch_cmd import branch
from .clean_cmd import clean
from .config_cmd import config
from .deploy_cmd import deploy
from .doctor_cmd import doctor
from .edit_cmd import edit
from .init_cmd import init
from .interface import cli
from .log_cmd import checkout, diff, log
from .main import main
from .profile_cmd import profile
from .remote_cmd import remote, sync
from .revert_cmd import revert
from .status_cmd import status
from .switch_cmd import switch
from .tag_cmd import tag
from .template_cmd import template
from .tui_cmd import tui
from .verify_cmd import verify
```

When Python imports `add_cmd`, the module-level code in `add_cmd.py` executes:

```python
# add_cmd.py (simplified)
from .interface import cli as main

@main.command()          # ← This executes immediately at import time
@click.argument(...)
@require_init
def add(...):
    ...
```

The `@main.command()` decorator calls `cli.add_command(add)` under the hood. So every import in `cli/__init__.py` registers that command with the Click group. **This is why `cli/__init__.py` is required** — without it, the commands wouldn't exist in the CLI even if the command files existed.

### Import Chain Visualization

```
[user runs] dot-man switch work
        │
        ▼
Python imports dot_man.cli.main
        │
        ▼
cli/__init__.py is processed
  ├── import switch_cmd → @cli.command() fires → cli has "switch"
  ├── import status_cmd → @cli.command() fires → cli has "status"
  └── ... all 21 commands registered
        │
        ▼
cli() is called with args ["switch", "work"]
        │
        ▼
Click finds "switch" command → calls switch()
```

---

## DotManGroup — Typo Suggestions

```python
# common.py
class DotManGroup(click.Group):
    """Custom Click Group to provide suggestions for typos."""

    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        matches = [cmd for cmd in self.list_commands(ctx)]
        suggestion = ui.suggest_command(cmd_name, matches)

        ui.error(f"Unknown command '{cmd_name}'", exit_code=0)
        if suggestion:
            ui.warn(f"Did you mean '{suggestion}'?")

        ctx.exit(2)
```

When a user types `dot-man stauts`, Click calls `get_command("stauts")`. Since no command named `stauts` exists, `DotManGroup` computes the closest match (via `ui.suggest_command`, which uses fuzzy string matching) and prints `Did you mean 'status'?` before exiting with code 2.

**Why exit code 2?** Convention: code 1 is application error, code 2 is misuse (wrong command). Click uses 2 for usage errors.

---

## Global Middleware (`interface.py`)

```python
@click.group(cls=DotManGroup)
@click.version_option(version=__version__, prog_name="dot-man")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output on console")
@click.option("--debug", is_flag=True, help="Enable debug logging to file")
@click.pass_context
def cli(ctx, verbose: bool, debug: bool):
    """dot-man: The Dotfile Manager for Professionals."""
    ...
```

Every `dot-man` invocation runs this function first, before the subcommand. It:

1. **Creates `~/.config/dot-man/`** if it doesn't exist (best-effort).
2. **Configures logging**: Always logs to `~/.config/dot-man/dot-man.log` at INFO level. With `--debug`, switches to DEBUG. With `--verbose`, additionally adds a console handler.
3. **Stores flags in Click context**: `ctx.obj["DEBUG"]` and `ctx.obj["VERBOSE"]` — available to any subcommand via `@click.pass_context`.

### Why Two Log Options?

- `--debug`: Developer mode. Writes verbose logs to file only. Keeps console output clean.
- `--verbose / -v`: User mode. Also streams logs to console. Useful for troubleshooting without reading a log file.

---

## Common Utilities (`common.py`)

This module is the backbone shared by every command module. Key exports:

### `require_init` Decorator

```python
def require_init(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not DOT_MAN_DIR.exists() or not REPO_DIR.exists():
            error("Not initialized. Run 'dot-man init' first.", exit_code=1)
        return func(*args, **kwargs)
    return wrapper
```

Applied to every command except `init`. Checks `~/.config/dot-man/` and `~/.config/dot-man/repo/` existence. If either is missing, exits immediately with a clear message. **Order matters**: this decorator must be innermost (closest to the function) to run before Click's argument parsing injects values.

### `handle_exception(exc, context)` — Centralized Error Handler

```python
def handle_exception(exc, context="Operation"):
    from ..exceptions import DotManError, ErrorDiagnostic

    if isinstance(exc, DotManError):
        error(str(exc), exc.exit_code)
        return

    if isinstance(exc, KeyboardInterrupt):
        warn("Operation cancelled by user")
        raise SystemExit(130)

    diagnostic = ErrorDiagnostic.from_exception(exc)
    ui.console.print(f"[red bold]{diagnostic.title}[/red bold]")
    ui.console.print(f"[red]{diagnostic.details}[/red]")
    ui.console.print(f"[dim]💡 {diagnostic.suggestion}[/dim]")
    raise SystemExit(1)
```

`ErrorDiagnostic.from_exception()` (in `exceptions.py`) categorizes unhandled exceptions and provides contextual suggestions. For example, a `PermissionError` generates "Try running with sudo?" while a `ConnectionError` generates "Check your internet connection."

### `get_secret_handler()` — Interactive Secret Resolution

Returns a closure that handles each `SecretMatch` interactively:

```
Potential secret detected!
File: ~/.gitconfig
Line 5: api_key = "sk-abc123..."
Pattern: Generic API Key (severity: HIGH)

Choose how to handle this secret:
  1. Ignore (skip it this time)
  2. Protect (replace with ***REDACTED*** this time)
  3. Add to skip list (skip this line every time)
  4. Protect forever (always replace in repo)
```

The handler uses two guards:
- `SecretGuard` — in-memory allow list (skip same line in current run)
- `PermanentRedactGuard` — persisted permanent redact list (always redact across runs)

### `parse_branch_arg(arg)` — Multi-Format Branch Parsing

The `switch` command accepts three formats. This function disambiguates:

| Input | Detection | Result |
|-------|-----------|--------|
| `work` | Not hex, not in tags → branch | `{type: "branch", base: "work", target: "work"}` |
| `work@stable-v1` | Contains `@` → branch@tag | `{type: "tag", base: "work", target: "stable-v1"}` |
| `work@abc1234` | `@` + 7+ hex chars → branch@commit | `{type: "commit", base: "work", target: "abc1234"}` |
| `abc1234` | 7+ hex chars → commit SHA | `{type: "commit", base: "HEAD", target: "abc1234"}` |
| `stable-v1` | No `@`, not hex, in `git.list_tags()` → tag | `{type: "tag", base: "HEAD", target: "stable-v1"}` |

The last case requires a `GitManager` instantiation (hits the filesystem). This runs at argument parsing time inside the `BranchParamType.convert()` method of `switch_cmd.py`.

---

## Command Lifecycle — Step by Step

For any `dot-man <cmd> <args>`:

```
1. Python starts, imports dot_man.cli.main
2. cli/__init__.py runs all imports → all commands registered with Click
3. cli() group function runs:
   a. Create ~/.config/dot-man/ if needed
   b. Configure logging
   c. Store --verbose/--debug flags in ctx.obj
4. Click dispatches to the matching subcommand function
5. Decorator stack runs (outer to inner):
   a. @main.command() — Click setup
   b. @click.option/argument — argument parsing + type coercion
   c. @require_init — check initialization
6. The command function body runs:
   a. ops = get_operations()  ← lazy singleton, configs loaded here
   b. Business logic via ops.*
   c. Output via ui.console.print() / success() / warn() / error()
7. Any exception:
   a. DotManError → error(str(e), e.exit_code)
   b. KeyboardInterrupt → warn("cancelled") + SystemExit(130)
   c. Other → handle_exception(e) → ErrorDiagnostic + SystemExit(1)
```

---

## Command Modules Deep Dive

### `init_cmd.py` — `dot-man init`

**Purpose:** Bootstrap the entire dot-man system from scratch.

**Execution flow:**
1. Check `is_git_installed()` — exit code 2 if git not found.
2. If `~/.config/dot-man/` already exists and no `--force`, prompt before deleting.
3. Create directory structure: `DOT_MAN_DIR`, `REPO_DIR`, `BACKUPS_DIR`.
4. `git.init()` — creates git repo + `.gitignore` + default git config.
5. `GlobalConfig.create_default()` — writes default `global.toml`.
6. `DotManConfig.create_default()` — writes minimal `dot-man.toml` with extensive comments.
7. `git.commit("dot-man: Initial commit")` — initial commit.
8. Unless `--no-wizard`: calls `run_setup_wizard()`.

**Setup wizard** (`run_setup_wizard`): Scans for 14 common dotfile paths (`.bashrc`, `.zshrc`, `.gitconfig`, `.config/nvim`, `.config/hypr`, etc.). For each found path, prompts user to track it. Special handling for Quickshell: if multiple config subdirs exist, presents a selection menu. After selection, calls `dotman_config.add_section()` and commits. Optionally calls `remote_cmd.setup` at the end.

**Why no `@require_init`?** Because `init` creates the structure that `require_init` checks for. Circular dependency.

---

### `switch_cmd.py` — `dot-man switch`

**Purpose:** Save current branch, checkout target, deploy target's files.

**Key design:** Uses `BranchParamType(click.ParamType)` to parse the branch argument at Click's type coercion level — before the function body runs. This means `switch` receives a pre-parsed `dict` (with `type`, `base`, `target` keys) rather than a raw string.

**Three dispatch paths:**
1. `target_type == "commit"` → `_handle_commit_switch()` — optionally save, then `git.checkout_commit()` (detached HEAD)
2. `target_type == "tag"` → `_handle_tag_switch()` — optionally save, then `git.checkout(tag_name)`
3. `target_type == "branch"` → `_handle_branch_switch()` — the full 3-phase flow

**3-phase branch switch (in `_handle_branch_switch`):**

```
Phase 1 — Save or Discard
  if save_mode == "save":
    ops.save_all(secret_handler)   ← parallel, with vault.batch()
    ops.git.commit("Auto-save...")
  else:
    (no-op, local changes discarded after checkout)

Phase 2 — Git Checkout
  ops.git.checkout(target_branch, create=not branch_exists)
  ops.reload_config()   ← _dotman_config = None → reloads dot-man.toml

Phase 3 — Deploy
  collect pre_hooks, post_hooks from sections
  run pre_deploy hooks (subprocess)
  ops.deploy_all()   ← two-phase: scan changes → parallel copy → restore secrets
  run post_deploy hooks (subprocess)

  ops.global_config.current_branch = target_branch
  ops.global_config.save()
```

**`save_mode` resolution:** Default comes from `ops.global_config.switch_default_behavior` (`"save"` or `"no-save"`). Overridden by `--save` or `--no-save` flags. The default default is `"save"`.

**`--dry-run`**: Shows what would happen without making any changes. Uses `ops.iter_section_paths(section)` to list files and their current status.

---

### `deploy_cmd.py` — `dot-man deploy`

**Purpose:** One-way deployment from a branch to the system. Does **not** save current state first.

**Key distinction from `switch`:** `deploy` is for fresh machine setup. You already have the right branch committed; you just want to push those files to the new system.

**Flow:**
1. Check branch exists.
2. Warn about destructive overwrite (unless `--force` or `--dry-run`).
3. `git.checkout(branch)` + `ops.reload_config()`.
4. `ops.scan_deployable_changes(sections)` — Phase 1: find changed files.
5. If `--dry-run`: print plan and exit.
6. Run pre-deploy hooks.
7. `ops.execute_deployment_plan(plan)` — Phase 2: parallel deploy.
8. Run post-deploy hooks.
9. `ops.global_config.current_branch = branch` + save.

---

### `status_cmd.py` — `dot-man status`

**Purpose:** Show current branch, tracked files, and their status (NEW/MODIFIED/IDENTICAL/DELETED).

**Key design:** Calls `ops.get_detailed_status()` (from `StatusMixin`) which returns a single iterable of status items — one pass through all sections and files. Groups results by section using `itertools.groupby`. Limits output to 10 sections × 5 files each to prevent overwhelming output.

**`--secrets` flag:** Instantiates a `SecretScanner` and scans each tracked file for secrets. Shows a 🔒 indicator on files with matches and prints a summary warning.

**Rich table structure:**
```
┌─────────────────────────────────────────────────────┐
│               Repository Status                     │
│  Current Branch: work                               │
│  Remote: git@github.com:user/dotfiles.git           │
│  Repository: ~/.config/dot-man/repo                 │
└─────────────────────────────────────────────────────┘

┌──────────────────── Tracked Sections (3) ───────────┐
│ Section / Path    │ Status    │ Details             │
│ [bashrc]          │           │                     │
│   📄 ~/.bashrc    │ MODIFIED  │ Content differs     │
│ [nvim]            │           │                     │
│   📁 ~/.config/nvim│ IDENTICAL│                     │
└─────────────────────────────────────────────────────┘
```

---

### `log_cmd.py` — Three Commands in One File

This file registers three commands on the CLI group:

#### `dot-man log`
Shows commit history. Iterates `ops.git.get_commits(count=N)`. With `--stat`, fetches commit object and reads `commit.stats.total`. With `--diff`, calls `ops.git.repo.git.diff(parent, commit)` and prints first 2000 chars.

#### `dot-man diff`
Three modes:
- No args: `git.repo.git.diff(patch=True)` — uncommitted changes in working tree
- `--branch <name>`: `git.repo.git.diff("branch...current")` — branch comparison
- `<file>`: finds section tracking that file, reads local and repo copies, calls `git.diff(repo_path, local_path)`

#### `dot-man checkout`
Uses `parse_branch_arg()` to determine if target is a commit SHA or tag. Calls `git.checkout_commit()` (for SHAs) or `git.checkout()` (for tags). Warns about detached HEAD state. Does **not** save first.

---

### `remote_cmd.py` — Remote & Sync

This file registers a **command group** plus two standalone commands:

```python
@main.group()          # → dot-man remote (subcommand group)
def remote(): ...

@remote.command("set") # → dot-man remote set <url>
@remote.command("get") # → dot-man remote get
@remote.command("sync-branch")  # → dot-man remote sync-branch

@main.command()        # → dot-man sync (standalone)
def sync(): ...

@main.command()        # → dot-man setup (standalone)
def setup(): ...
```

#### `dot-man remote set <url>`
Calls `git.set_remote(url)` (GitPython: create or update `origin`) AND updates `global_config.remote_url`. Both are necessary: git knows the remote for push/pull, and dot-man stores it in `global.toml` to display in `status`.

#### `dot-man remote sync-branch`
Detects mismatch between local branch name and remote default branch (e.g., local `main` vs remote `master`). Uses `git remote show origin` output, then offers to rename the local branch via `git.repo.git.branch("-m", old, new)`.

#### `dot-man sync`
```
1. Acquire FileLock(LOCK_FILE)
2. git.fetch()
3. git.pull(rebase=True)  ← auto-stash/pop if dirty
4. ops.pre_push_audit()   ← check for secrets before push
5. git.push()
```

The `pre_push_audit()` call (in `StatusMixin`) is the gate before push — it warns/blocks if secrets are detected in tracked files, preventing accidental credential exposure.

#### `dot-man setup`
Interactive remote setup wizard. Detects `gh` CLI. If available, offers to create a private GitHub repository. If repo exists, offers to connect to it and push/pull. Falls back to manual URL entry.

---

### `add_cmd.py` — `dot-man add`

Adds a path to `dot-man.toml`. Calls `dotman_config.add_section(name, paths=[path])`. If the path is already tracked, warns. Optionally saves (copies the file to repo) immediately.

---

### `branch_cmd.py` — `dot-man branch`

Manages branches (list, create, delete, rename). Wraps `git.list_branches()`, `git.create_branch()`, `git.delete_branch()`. Shows stats via `git.get_all_branch_stats()` (efficient `for-each-ref`).

---

### `tag_cmd.py` — `dot-man tag`

Creates, lists, and deletes git tags. Calls `git.create_tag(name, ref, message)` and `git.delete_tag(name)`.

---

### `template_cmd.py` — `dot-man template`

Manages template variables (`{{HOSTNAME}}`, `{{USER}}`, custom keys). Lists system variables from `global_config.SYSTEM_VARS`. Sets user templates in `global.toml` via `global_config`. Shows all resolved substitutions.

---

### `profile_cmd.py` — `dot-man profile`

Manages machine profiles stored in `global.toml` under `[profiles.*]`. Profiles can set defaults (like `secrets_filter`, `update_strategy`) and activation hooks. `dot-man profile use <name>` applies profile settings.

---

### `config_cmd.py` — `dot-man config`

Large command (~800 lines) with subcommands for reading/writing all configurable settings in both `global.toml` and `dot-man.toml`. Provides a user-friendly interface to fields exposed as typed properties on `GlobalConfig` and `DotManConfig`.

---

### `doctor_cmd.py` — `dot-man doctor`

System health check. Verifies:
- Git installed and accessible
- Repository initialized correctly
- `global.toml` and `dot-man.toml` parseable
- All section paths in `dot-man.toml` are valid
- Vault accessible (can encrypt/decrypt a test value)
- No orphaned files in repo

---

### `verify_cmd.py` — `dot-man verify`

Calls `dotman_config.validate()` and prints warnings. Checks:
- Section paths exist on disk
- `inherits` references resolve
- No unknown config keys
- Valid `update_strategy` values

---

### `edit_cmd.py` — `dot-man edit`

Opens `dot-man.toml` in the user's editor (`$EDITOR` or `$VISUAL`, falling back to `vim`). After editing, calls `dotman_config.load()` to validate the new config.

---

### `revert_cmd.py` — `dot-man revert`

Calls `ops.revert_file(path)` (from `BranchMixin`). Finds the section tracking the given file, copies the repo version back to the system (restoring secrets from vault).

---

### `clean_cmd.py` — `dot-man clean`

Removes orphaned files from the repo (files that exist in `~/.config/dot-man/repo/` but are no longer tracked by any section in `dot-man.toml`).

---

### `backup_cmd.py` — `dot-man backup`

Lists and manages backups created by `BackupManager`. Backs up are timestamped tar.gz archives in `~/.config/dot-man/backups/`.

---

### `audit_cmd.py` — `dot-man audit`

Scans all tracked files for secrets using `SecretScanner`. Reports findings with file, line, pattern name, and severity. Does not modify any files.

---

### `tui_cmd.py` — `dot-man tui`

Launches the Textual-based TUI. Imports `textual` lazily to avoid startup cost when TUI is not used.

---

## Shell Completion System

Completions are defined in `common.py` as callbacks with the signature `(ctx, param, incomplete) → list[str]`:

```python
# Branches
def complete_branches(ctx, param, incomplete):
    git = GitManager()
    return [b for b in git.list_branches() if b.startswith(incomplete)]

# Tags
def complete_tags(ctx, param, incomplete):
    git = GitManager()
    return [t for t in git.list_tags() if t.startswith(incomplete)]

# Commits (recent 50, short SHAs)
def complete_commits(ctx, param, incomplete):
    git = GitManager()
    return [c["sha"][:7] for c in git.get_commits(50) if c["sha"].startswith(incomplete)]

# The switch arg: branches + tags + commits + branch@tag combos
def complete_switch_args(ctx, param, incomplete):
    ...
```

Each completion callback instantiates `GitManager()` directly (not via `get_operations()`) to avoid loading configs just for completion.

All exceptions in completions are silently caught and return `[]` — completions must never crash the shell.

### Registering Completions

```python
@click.argument("branch", shell_complete=complete_branches)
@click.option("--branch", shell_complete=complete_branches)
```

Click passes the registered callback to the shell completion engine. For bash/zsh/fish, users must run the appropriate setup command once:

```bash
eval "$(_DOT_MAN_COMPLETE=bash_source dot-man)"   # bash
eval "$(_DOT_MAN_COMPLETE=zsh_source dot-man)"    # zsh
eval (env _DOT_MAN_COMPLETE=fish_source dot-man)  # fish
```

---

## Error Handling Pattern

Every command follows the same exception handling structure:

```python
@main.command()
@require_init
def mycommand():
    try:
        ops = get_operations()
        # ... actual work
    except DotManError as e:
        error(str(e), e.exit_code)       # clean user-facing error, typed exit code
    except KeyboardInterrupt:
        handle_exception(KeyboardInterrupt())   # Ctrl+C → exit 130
    except Exception as e:
        handle_exception(e, "Context")    # unexpected → ErrorDiagnostic
```

### Exception Hierarchy (`exceptions.py`)

```
DotManError (base, has exit_code: int)
├── NotInitializedError       (exit_code=1)
├── ConfigurationError        (exit_code=1)
│   └── ConfigValidationError (exit_code=1)
├── GitOperationError         (exit_code=1)
│   └── BranchNotFoundError   (exit_code=1)
│   └── BranchNotMergedError  (exit_code=1)
├── FileOperationError        (exit_code=1)
└── VaultError                (exit_code=1)
```

`DotManError` carries `exit_code` — commands can propagate specific exit codes to the shell. `ErrorDiagnostic.from_exception()` maps Python built-in exceptions to user-friendly titles/suggestions.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Application error (DotManError or unhandled exception) |
| 2 | Usage error (wrong command name, missing required argument) |
| 130 | Interrupted by Ctrl+C (Unix convention: 128 + SIGINT) |

---

*Next: [Phase 3 — Core System Deep Explanation](./core_system.md)*
