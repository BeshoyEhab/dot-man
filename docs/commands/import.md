# import

Import dotfiles from other dotfile managers.

## Usage

```bash
dot-man import <source>
dot-man import all
dot-man import chezmoi --dry-run
```

## Supported Sources

| Source | Command |
|--------|---------|
| chezmoi | `dot-man import chezmoi` |
| yadm | `dot-man import yadm` |
| GNU Stow | `dot-man import stow` |
| Auto-detect | `dot-man import all` |

## Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview what would be imported |
| `--force` | Overwrite existing sections |

## Examples

```bash
# Import from chezmoi
dot-man import chezmoi

# Preview import
dot-man import yadm --dry-run

# Auto-detect and import
dot-man import all
```
