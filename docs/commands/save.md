# save

Save current dotfile changes to the active branch.

## Usage

```bash
dot-man save [MESSAGE]
```

## Behavior

1. Scans all configured paths for changes
2. Detects and strips secrets (replaced with vault tokens)
3. Commits changes with the provided message
4. Reports files saved, secrets detected, hooks run

## Options

| Flag | Description |
|------|-------------|
| `--force` | Save even if no tracked files changed |
| `--dry-run` | Preview what would be saved |
| `--section <name>` | Only save specific section |

## Examples

```bash
# Save with a message
dot-man save "updated neovim config"

# Preview changes
dot-man save --dry-run

# Only save one section
dot-man save --section main "bashrc updates"

# Force save even with no tracked changes
dot-man save --force "vault rotation"
```
