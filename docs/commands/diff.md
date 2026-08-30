# diff

Show changes in tracked files.

## Usage

```bash
dot-man diff
dot-man diff --branch work
dot-man diff --rich
dot-man diff --section nvim
```

## Options

| Flag | Description |
|------|-------------|
| `--branch`, `-b` | Compare with another branch |
| `--rich` | Syntax-highlighted diff (default) |
| `--no-rich` | Plain git diff |
| `--section`, `-s` | Show diff for a specific section |
| `--cached` | Show staged changes |

## Examples

```bash
# Show uncommitted changes
dot-man diff

# Compare current branch with main
dot-man diff --branch main

# Plain diff without syntax highlighting
dot-man diff --no-rich

# Show only nvim changes
dot-man diff --section nvim
```
