# revert

Restore files from the repository to your local system.

## Example

```bash
dot-man revert ~/.bashrc   # discard local edits, restore repo copy
```

## Usage

```bash
dot-man revert <file>
dot-man revert <file> --commit abc1234
dot-man revert <file> --force
```

## Options

| Flag | Description |
|------|-------------|
| `--commit`, `-c` | Restore from a specific commit |
| `--dry-run`, `-n` | Show what would be reverted |
| `--all` | Revert all tracked files |

## Examples

```bash
# Restore a file from the repo
dot-man revert ~/.bashrc

# Restore from a specific commit
dot-man revert ~/.bashrc --commit abc1234

# Preview what would be reverted
dot-man revert ~/.config/nvim --dry-run

# Restore all files
dot-man revert --all
```
