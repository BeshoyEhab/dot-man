# vault

Manage the encrypted secret vault.

## Usage

```bash
dot-man vault status
dot-man vault rotate-key
```

## Subcommands

### `vault status`

Show vault status: number of secrets, key age, vault file location.

```bash
dot-man vault status
```

### `vault rotate-key`

Rotate the Fernet encryption key. Old key is backed up to `.key.bak`.

```bash
dot-man vault rotate-key
```

This re-encrypts all secrets with the new key.

## How It Works

- Secrets are stored in `~/.config/dot-man/vault.json`
- Encrypted with Fernet (AES-128-CBC + HMAC)
- Key stored at `~/.config/dot-man/.key`
- Old key backed up during rotation at `.key.bak`
