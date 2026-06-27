# Secret Detection

dot-man automatically detects and removes secrets before any commit.

## How It Works

1. **Detection**: Scans files for patterns (API keys, tokens, passwords)
2. **Extraction**: Removes the secret value from the file
3. **Tokenization**: Replaces with `VAULT_TOKEN_<hash>`
4. **Encryption**: Encrypts the real value in the vault using Fernet

```
# Before commit:
GITHUB_TOKEN=ghp_abc123xyz

# After save:
GITHUB_TOKEN=VAULT_TOKEN_7f3a8b2c
```

## Supported Patterns

- AWS Access Key / Secret Key
- GitHub tokens (`ghp_`, `gho_`, `github_pat_`)
- Google API keys
- Private keys (RSA, SSH, PGP)
- Generic API keys, tokens, passwords
- Connection strings
- JWT tokens

## Custom Patterns

Add custom patterns in `dot-man.toml`:

```toml
[settings]
custom_secret_patterns = [
    "MY_SECRET_[A-Z0-9]+",
    "internal_key_[a-f0-9]{32}",
]
```

## Vault

Secrets are stored in `~/.config/dot-man/vault.json`:
- Encrypted with Fernet (AES-128-CBC + HMAC)
- Key at `~/.config/dot-man/.key`
- Never committed to git

## Commands

```bash
dot-man audit          # Scan for secrets
dot-man audit --fix    # Auto-replace with tokens
dot-man vault status   # Check vault
dot-man vault rotate-key  # Rotate encryption key
```
