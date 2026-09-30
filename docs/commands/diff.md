# diff

Show changes in tracked files.

## Example

```bash
dot-man diff --branch work   # what would change if you switched
```

## Usage

```bash
dot-man diff
dot-man diff --branch work
dot-man diff --staged
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
