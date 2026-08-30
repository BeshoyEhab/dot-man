# verify

Validate repository integrity and configuration.

## Usage

```bash
dot-man verify
dot-man verify --fix
```

## What It Checks

| Check | Description |
|-------|-------------|
| Git integrity | Repository is valid git repo |
| Config validity | `dot-man.toml` is valid TOML/YAML |
| Section paths | All configured paths exist |
| Repo sync | Repo files match configuration |
| Secret vault | Vault file is intact |

## Options

| Flag | Description |
|------|-------------|
| `--fix` | Attempt to fix detected issues |

## Examples

```bash
# Run all checks
dot-man verify

# Fix issues automatically
dot-man verify --fix
```
