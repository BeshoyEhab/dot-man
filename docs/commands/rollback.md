# rollback

Roll back to a previous commit, tag, or N commits back.

## Usage

```bash
dot-man rollback
dot-man rollback -n 3
dot-man rollback --to v1.0
dot-man rollback --list
```

## Options

| Flag | Description |
|------|-------------|
| `--to`, `-t` | Rollback to a specific tag or commit |
| `-n` | Number of commits to roll back (default: 1) |
| `--list` | Show available rollback points |
| `--dry-run`, `-n` | Preview rollback without changes |

## What Happens

1. Creates a backup of current state
2. Reverts files to the target state
3. Deploys reverted files to your system
4. Commits the rollback

## Examples

```bash
# Roll back one commit
dot-man rollback

# Roll back 3 commits
dot-man rollback -n 3

# Roll back to a tag
dot-man rollback --to v1.0

# See what you can roll back to
dot-man rollback --list

# Preview rollback
dot-man rollback --dry-run
```

## Safety

- Automatic backup before rollback
- Backup stored in `~/.config/dot-man/backups/`
- Max 5 backups retained (configurable)
