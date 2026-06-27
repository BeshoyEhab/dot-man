# Architecture

dot-man is a Python CLI tool built with Click.

## Module Structure

```
dot_man/
├── cli/                    # CLI commands
│   ├── interface.py       # CLI group definition
│   ├── main.py            # Entry point
│   ├── common.py          # Shared utilities, completions
│   ├── completions.py     # Shell completion logic
│   ├── navigate_cmd.py    # navigate command
│   ├── navigate_preview.py # Diff/preview display
│   ├── config_cmd.py      # config command
│   ├── config_tutorial.py # Interactive tutorial
│   ├── status_cmd.py      # status command
│   ├── save_cmd.py        # save command
│   ├── bootstrap_cmd.py   # bootstrap command
│   ├── hooks_cmd.py       # hooks command
│   └── vault_cmd.py       # vault command
├── core.py                # GitManager (branch, commit, diff)
├── global_config.py       # Config parsing, template substitution
├── operations.py          # Business logic (save, deploy, status)
├── section.py             # Section class (config sections)
├── files.py               # File operations (copy, symlink, deploy)
├── secrets.py             # Secret detection patterns
├── vault.py               # Fernet encryption vault
├── branch_ops.py          # Branch operations (diff, merge)
├── tag_ops.py             # Tag management
├── save_deploy_ops.py     # Save/deploy operations
└── remote_ops.py          # Remote sync operations
```

## Data Flow

```
User runs: dot-man navigate work
         │
         ▼
┌─────────────────┐
│  navigate_cmd   │ ← CLI parsing, flags
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   operations    │ ← Business logic
└────────┬────────┘
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ files  │ │  core  │
└────────┘ └────────┘
  copy/     git ops
  symlink   commit
            branch
```

## Key Design Decisions

1. **Copy over symlink** — Default deploy method uses physical copies. Prevents broken symlinks when branch structure changes.

2. **Secrets never enter git** — Fernet encryption with local vault. API keys replaced with vault tokens before commit.

3. **POSIX atomic writes** — `os.replace()` prevents dotfile corruption during system crashes.

4. **Resilient hooks** — Hook failures are collected and reported, never abort the main operation.

5. **No external dependencies** — Only stdlib + click + cryptography. No Jinja2 for templates (custom regex parser).
