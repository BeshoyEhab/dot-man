# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-25

### Added

- Initial release
- Core CLI with Click framework
- Git operations using GitPython
- Commands: `init`, `status`, `switch`, `edit`, `deploy`, `audit`
- Branch management: `branch list`, `branch delete`
- **Hooks**: `pre_deploy` and `post_deploy` commands for automated tasks (e.g. reload config)
- Secret detection with 10 default patterns:
  - Private keys (SSH, GPG)
  - AWS credentials
  - GitHub tokens
  - Generic API keys
  - Password assignments
  - Bearer tokens
  - JWT tokens
- Automatic secret redaction during save
- `--dry-run` mode for switch and deploy
- `--strict` mode for audit (CI/CD integration)
- `--fix` mode for auto-redacting secrets
- Install script with shell completions (bash, zsh, fish)
- Unit tests with pytest
- MIT License

### Security

- Built-in secret detection prevents accidental credential commits
- Secrets are redacted before saving to repository
- `secrets_filter` can be enabled/disabled per file
