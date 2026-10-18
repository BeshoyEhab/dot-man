# revert

Restore files from the repository to your local system.

This is the canonical single-file restore. The deprecated `dot-man restore
<file> <sha>` command forwards here (and is removed in v2.0).

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
| `--force` | Skip the confirmation prompt |

## Examples

```bash
# Restore a file from the repo
dot-man revert ~/.bashrc

# Restore from a specific commit (canonical replacement for `restore`)
dot-man revert ~/.bashrc --commit abc1234
```
