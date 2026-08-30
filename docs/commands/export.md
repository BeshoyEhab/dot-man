# export

Export dotfiles to portable formats for backup or transfer.

## Usage

```bash
dot-man export <format> <filename>
dot-man export tar backup.tar.gz
dot-man export zip dots.zip
dot-man export json manifest.json
```

## Formats

| Format | Description |
|--------|-------------|
| `tar` | Tar archive (compressed) |
| `zip` | Zip archive |
| `json` | JSON manifest with file metadata |

## Options

| Flag | Description |
|------|-------------|
| `--branch`, `-b` | Export specific branch (default: current) |
| `--sections`, `-s` | Export specific sections only |

## Examples

```bash
# Export current branch as tar
dot-man export tar ~/backup/dotfiles.tar.gz

# Export as zip
dot-man export zip ~/backup/dotfiles.zip

# Export work branch as JSON manifest
dot-man export json manifest.json --branch work

# Export specific sections
dot-man export tar backup.tar.gz --sections nvim,fish
```
