# rollback

Roll back to a previous commit, tag, or N commits back.

## Example

```bash
dot-man rollback --list   # pick a restore point
dot-man rollback -n 3     # go back three commits
```

## Usage

```bash
dot-man rollback
dot-man rollback -n 3
dot-man rollback <target>
dot-man rollback --backup <id>
dot-man rollback --list
dot-man rollback --dry-run
```

## Options

| Flag | Description |
|------|-------------|
| `TARGET` | Commit SHA, tag, or `HEAD~N` to roll back to |
| `--steps`, `-n` | Number of commits to roll back (default: 1) |
| `--backup <id>` | Restore local files from a safety snapshot (replaces `backup restore`) |
| `--list` | Show available rollback points |
| `--dry-run` | Preview rollback without changes |
| `--force`, `-f` | Skip the confirmation prompt |

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
dot-man rollback v1.0

# Restore a safety snapshot (canonical replacement for `backup restore`)
dot-man rollback --backup 2024-01-15_12-00-00

# See what you can roll back to
dot-man rollback --list

# Preview rollback
dot-man rollback --dry-run
```

## Safety

- Automatic backup before rollback
- Backup stored in `~/.config/dot-man/backups/`
- Max 5 backups retained (configurable)
