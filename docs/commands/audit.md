# audit

Scan tracked files for secrets, API keys, tokens, and passwords.

## Usage

```bash
dot-man audit
```

## Behavior

Scans all files currently tracked by dot-man for:
- API keys (AWS, GitHub, Google, etc.)
- Private keys (RSA, SSH, PGP)
- Passwords in config files
- Connection strings
- JWT tokens

## Options

| Flag | Description |
|------|-------------|
| `--fix` | Automatically replace detected secrets with vault tokens |
| `--json` | Output results as JSON |
| `--section <name>` | Audit only a specific section |

## Examples

```bash
# Scan all tracked files
dot-man audit

# Auto-fix detected secrets
dot-man audit --fix

# Audit one section
dot-man audit --section main
```
