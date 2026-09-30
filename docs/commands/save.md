# save

Save current dotfile changes to the active branch.

## Example

```bash
dot-man save --commit -m "updated vim config"   # snapshot with a message
dot-man save --dry-run                          # preview, change nothing
```

## Usage

```bash
dot-man save --commit -m "message"
dot-man save --dry-run
dot-man save --section <name>
dot-man save --force
```

## Behavior

1. Scans all configured paths for changes
2. Detects and strips secrets (replaced with vault tokens)
3. Commits when `--commit` is passed
4. Reports files saved, secrets detected, hooks run

## Options

| Flag | Description |
|------|-------------|
| `--commit`, `-c` | Commit after saving |
| `--message`, `-m` | Commit message (requires `--commit`) |
| `--dry-run` | Preview what would be saved |
| `--section <name>` | Only save specific section |
| `--force` | Skip confirmation prompt |

## Examples

```bash
# Save with a message
dot-man save --commit -m "updated neovim config"

# Preview changes
dot-man save --dry-run

# Only save one section
dot-man save --section nvim --commit -m "nvim updates"
```
