# watch

Watch tracked files for changes and auto-save.

## Usage

```bash
dot-man watch
dot-man watch --no-commit
dot-man watch --interval 30
dot-man watch --dry-run
```

## Options

| Flag | Description |
|------|-------------|
| `--no-commit` | Save changes without committing |
| `--interval`, `-i` | Polling interval in seconds (default: 5) |
| `--dry-run`, `-n` | Show what would be watched |
| `--no-commit` | Skip git commit on change |

## How It Works

1. Monitors all tracked file paths for modifications
2. When a change is detected, copies the file to the repo
3. Optionally commits the change with a timestamp message

## Backends

| Backend | Description |
|---------|-------------|
| `watchdog` | Native filesystem events (recommended) |
| `polling` | Fallback, checks file mtimes periodically |

## Examples

```bash
# Watch with auto-commit
dot-man watch

# Watch without committing
dot-man watch --no-commit

# Slower polling (less CPU)
dot-man watch --interval 10

# Preview what would be watched
dot-man watch --dry-run
```
