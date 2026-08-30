# log

Show commit history for the current branch.

## Usage

```bash
dot-man log
dot-man log --limit 10
dot-man log --diff
dot-man log --oneline
```

## Options

| Flag | Description |
|------|-------------|
| `--limit`, `-n` | Number of commits to show (default: 20) |
| `--diff` | Show diffs for each commit |
| `--oneline` | Compact one-line format |
| `--stat` | Show file change statistics |
| `--interactive` | Open TUI log browser |

## Examples

```bash
# Recent history
dot-man log

# Last 5 commits with diffs
dot-man log -n 5 --diff

# Compact view
dot-man log --oneline

# See what files changed
dot-man log --stat
```
