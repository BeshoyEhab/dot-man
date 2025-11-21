# Security Specification

## Overview

Security is a core pillar of `dot-man`. Since dotfiles often inadvertently contain sensitive information (API keys, tokens, private keys), `dot-man` includes built-in mechanisms to prevent these secrets from being committed to the git repository.

## 1. Secret Detection Architecture

### 1.1 Detection Engine

The detection engine scans file content line-by-line against a set of regular expressions. It operates in two modes:
1.  **Pre-commit Filtering:** Runs automatically during `switch` (save phase) and `sync` to prevent secrets from entering the repo.
2.  **On-demand Auditing:** Runs via `dot-man audit` to scan the existing repository.

### 1.2 Default Patterns

`dot-man` comes with a comprehensive set of default patterns to detect common secrets:

| Category | Pattern Description | Regex (Simplified) | Severity |
| :--- | :--- | :--- | :--- |
| **Private Keys** | SSH/GPG private key headers | `-----BEGIN.*PRIVATE KEY-----` | **CRITICAL** |
| **AWS Credentials** | AWS Access Key ID | `AKIA[0-9A-Z]{16}` | **CRITICAL** |
| **AWS Secrets** | AWS Secret Access Key | `aws_secret_access_key` | **CRITICAL** |
| **GitHub Tokens** | Personal Access Tokens | `ghp_[a-zA-Z0-9]{36}` | **HIGH** |
| **Generic API Keys** | Common assignment patterns | `api_key=`, `API_KEY=`, `apiKey:` | **HIGH** |
| **Passwords** | Password assignments | `password=`, `passwd=` | **HIGH** |
| **Generic Tokens** | Token assignments | `token=`, `bearer`, `auth_token` | **HIGH** |
| **JWT** | JSON Web Tokens | `eyJ[A-Za-z0-9_-]+\.eyJ...` | **MEDIUM** |

### 1.3 Custom Patterns

Users can define custom patterns in `~/.config/dot-man/secrets.py` (advanced) or pass a pattern file to `audit`.

*Future Feature:* Support for `secrets.yaml` configuration for easier user customization.

## 2. Filtering & Redaction Logic

### 2.1 The `secrets_filter` Setting

Secret filtering is controlled by the `secrets_filter` boolean in `dot-man.ini`.

*   **Global Default:** Enabled by default in `[DEFAULT]` section.
*   **Per-Section Override:** Can be disabled for specific files (e.g., if false positives occur).

```ini
[DEFAULT]
secrets_filter = true

[~/.bashrc]
local_path = ~/.bashrc
# Inherits secrets_filter = true

[~/.safe_config]
local_path = ~/.safe_config
secrets_filter = false  # Disable scanning for this file
```

### 2.2 Redaction Process (Auto-Save)

When `dot-man` copies a file from `local_path` to `repo_path` (during `switch` or `sync`):

1.  **Check Config:** If `secrets_filter = false`, copy file as-is.
2.  **Scan Content:** If `true`, read file line-by-line.
3.  **Match:** Apply all enabled patterns.
4.  **Action:**
    *   If a match is found, the secret value is **NOT** copied to the repo.
    *   **Behavior:** The line is either omitted or redacted (replaced with `***REDACTED***`) depending on the implementation phase.
    *   **Warning:** A warning is displayed to the user: `⚠ Secret detected in ~/.bashrc (line 45). Not committed.`

### 2.3 Redaction Process (Audit --fix)

The `dot-man audit --fix` command performs in-place redaction on the repository files:
*   Replaces the matched secret string with `***REDACTED_BY_DOTMAN***`.
*   Commits the change to git.

## 3. Security Levels & Strict Mode

### 3.1 Severity Levels

*   **CRITICAL:** Compromises system identity or cloud infrastructure (e.g., Private Keys, AWS root keys). Immediate action required.
*   **HIGH:** Compromises specific services (e.g., GitHub tokens, database passwords).
*   **MEDIUM:** Potential exposure or ambiguous tokens.
*   **LOW:** Suspicious patterns that require manual review.

### 3.2 Strict Mode (`--strict`)

Used primarily in CI/CD pipelines or for paranoid users.
*   **Flag:** `dot-man audit --strict`
*   **Behavior:** Exits with a non-zero error code (50) if **ANY** secret (even LOW severity) is detected.
*   **Normal Behavior:** Without `--strict`, `audit` returns 0 even if secrets are found (unless a critical error occurs), just listing them.

## 4. Best Practices for Users

1.  **Use Environment Variables:**
    *   Don't hardcode secrets in dotfiles.
    *   Use `export GITHUB_TOKEN=$SAVED_TOKEN` in `.bashrc`.
2.  **Use Password Managers:**
    *   Fetch secrets dynamically (e.g., `op run -- ...`).
3.  **Enable Filtering:**
    *   Keep `secrets_filter = true` enabled globally.
    *   Only disable it for specific, trusted files.
4.  **Regular Audits:**
    *   Run `dot-man audit` periodically.
    *   Run `dot-man audit --strict` before pushing to a public remote.
5.  **Private Repositories:**
    *   Even with filtering, it is recommended to use a **private** git repository for dotfiles as a second layer of defense.

## 5. False Positives

Common sources of false positives:
*   Example configuration files (e.g., `api_key = "your_key_here"`).
*   Test fixtures.
*   Hashes or checksums that look like tokens.

**Mitigation:**
*   `dot-man` ignores lines containing "example", "dummy", "sample", "your_key_here".
*   Users can disable `secrets_filter` for specific files.
*   Users can add exclusion patterns (file globs) in `.dotmanignore`.
