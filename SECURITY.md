# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.2.x   | :white_check_mark: |
| < 1.2   | :x:                |

## Reporting a Vulnerability

dot-man handles sensitive data (API keys, tokens, passwords). If you discover a security vulnerability, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

### How to Report

1. Email: **bishoymorad47@gmail.com** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

2. You should receive an initial response within **48 hours**.

3. We will work with you to understand and address the issue before any public disclosure.

### What to Include

- **Type of vulnerability** (e.g., secret leakage, command injection, path traversal)
- **Affected component** (e.g., `dot-man audit`, `dot-man save`, secret detection)
- **Attack vector** (local, remote, requires user interaction)
- **Proof of concept** (if possible)

## Scope

The following are in scope:

- Secret detection bypass
- Encrypted vault compromise
- Command injection via hook scripts or template variables
- Path traversal in file operations
- Privilege escalation through dotfile operations
- Exfiltration of tracked dotfiles

The following are out of scope:

- Vulnerabilities in third-party dependencies (report to upstream)
- Issues requiring physical access to the machine
- Social engineering attacks

## Disclosure Policy

- We follow **coordinated disclosure**.
- We will credit reporters in release notes (unless anonymity is requested).
- We aim to release a fix within **7 days** of confirmation for critical issues.

## Security Best Practices for Users

- Always use `dot-man audit` to scan for secrets before pushing
- Use `dot-man audit --strict` in CI/CD pipelines
- Enable `secrets_filter = true` on sensitive sections
- Review encrypted vault contents periodically
- Use strong passphrases for GPG/AGE encryption
