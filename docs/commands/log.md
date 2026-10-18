# log

Show commit history for the current branch.

## Example

```bash
dot-man log -n 10   # last ten commits
```

## Usage

```bash
dot-man log
dot-man log -n 10
dot-man log --diff
dot-man log --stat
dot-man log --commit abc1234
```

## Options

| Flag | Description |
|------|-------------|
| `--count`, `-n` | Number of commits to show |
| `--diff`, `-d` | Show diffs for each commit |
| `--commit`, `-C` | Full diff for a single commit (replaces `show`) |
| `--stat` | Show file change statistics |
| `--interactive` | Open TUI log browser |

## Examples

```bash
# Recent history
dot-man log

# Last 5 commits with diffs
dot-man log -n 5 --diff

# Full diff for one commit (canonical replacement for `show`)
dot-man log --commit abc1234

# See what files changed
dot-man log --stat
```
