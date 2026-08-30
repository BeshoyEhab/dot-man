# encrypt

Encrypt and decrypt sensitive files using GPG or AGE.

## Usage

```bash
dot-man encrypt status
dot-man encrypt encrypt <section>
dot-man encrypt decrypt <section>
```

## Subcommands

### encrypt status

Show encryption status for all sections:

```bash
dot-man encrypt status
```

### encrypt encrypt

Encrypt files in a section:

```bash
dot-man encrypt encrypt ssh-keys
dot-man encrypt encrypt --all
```

### encrypt decrypt

Decrypt files in a section:

```bash
dot-man encrypt decrypt ssh-keys
dot-man encrypt decrypt --all
```

## Encryption Methods

| Method | Description |
|--------|-------------|
| GPG | Uses your GPG keyring |
| AGE | Modern, simpler encryption |

## Examples

```bash
# Check what's encrypted
dot-man encrypt status

# Encrypt SSH keys
dot-man encrypt encrypt ssh-keys

# Decrypt for use
dot-man encrypt decrypt ssh-keys
```
