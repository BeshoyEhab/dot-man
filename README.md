<p align="center"><h1>dot-man</h1></p>

<p align="center">
  <strong>Dotfile manager with git-powered branching</strong>
</p>

<p align="center">
  <a href="https://github.com/BeshoyEhab/dot-man/actions/workflows/ci.yml">
    <img src="https://github.com/BeshoyEhab/dot-man/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="#configuration">Configuration</a>
</p>

---

## Overview

**dot-man** manages your dotfiles across multiple machines using git branches. Each branch represents a different configuration (work, personal, minimal, server).

```bash
# Switch between configurations instantly
dot-man switch work      # Deploy work setup
dot-man switch personal  # Deploy personal setup

# Audit for secrets before pushing
dot-man audit --strict
```

---

## Features

- 🌿 **Git-powered branching** - Each config is a branch, easy to sync
- 🔐 **Secret detection** - Automatically redacts API keys, passwords, tokens
- 🔄 **Save & deploy** - One command to save current state and switch configs
- ☁️ **Remote sync** - Push/pull dotfiles across machines with `dot-man sync`
- ⚡ **Pre/Post hooks** - Run commands before/after deploying (e.g., reload config)
- 📝 **Edit in place** - Opens your `$EDITOR` for quick changes
- 🛡️ **Dry-run mode** - Preview changes before making them
- 🐚 **Shell completions** - Bash, Zsh, and Fish support
- 🏷️ **Tags** - Tag commits for fast navigation
- 📜 **History & Diff** - View commit history, compare branches, restore files
- 📊 **Diff & Restore** - Compare changes between branches, restore from history

---

## Current Status

| Metric | Value |
|--------|-------|
| Version | 0.8.0 (Beta) |
| Test Coverage | 60% |
| Commands | 25+ |
| Python | 3.9+ |

### What's New in 0.8.0

- `dot-man diff` - Show changes between branches or files
  - `dot-man diff` - Show uncommitted changes
  - `dot-man diff --branch main` - Compare branches
  - `dot-man diff <file>` - Show specific file changes
  - `dot-man diff --staged` - Show staged changes
- `dot-man log` - Show commit history with `--diff` and `--stat`
- `dot-man checkout <sha|tag>` - Checkout specific commit or tag
- `dot-man tag create/list/delete/switch` - Tag management
- `dot-man revert <file> -c <commit>` - Restore file from specific commit
- `dot-man template` - Template variables
  - `dot-man template set KEY VALUE` - Set template variable
  - `dot-man template list` - List templates + system vars
  - `dot-man template system` - Show auto-detected vars
  - System vars: `{{HOSTNAME}}`, `{{USER}}`, `{{SHELL}}`, etc.
- `dot-man profile` - Multi-machine profiles
  - `dot-man profile create <name>` - Create profile
  - `dot-man profile switch <name>` - Switch to profile
  - `dot-man profile detect` - Auto-detect by hostname
  - Profile inheritance support
- `switch branch@tag` - Switch to branch at tag position
- `switch <commit>` - Switch to specific commit
- `switch --save/--no-save` - Control save behavior
- `switch.default_behavior` config option
- Performance optimizations (batch ops, parallel scanning, lazy loading)

### Roadmap to V1.0

- [ ] Increase test coverage to 80%+
- [ ] PyPI publication
- [ ] Full documentation site
- [ ] Stable API guarantee

---

## Installation

### With pipx (Recommended)

```bash
pipx install git+https://github.com/BeshoyEhab/dot-man.git
```

### From Source

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
./install.sh
```

### With pip

```bash
pip install git+https://github.com/BeshoyEhab/dot-man.git
```

### Uninstall

```bash
pipx uninstall dot-man
# or
./uninstall.sh
```

---

## Quick Start

### 1. Initialize

```bash
dot-man init
```

Creates `~/.config/dot-man/` with a git repository.

### 2. Create configuration file

```bash
dot-man config create
```

This creates `dot-man.toml` with commented examples. Uncomment and customize sections for your dotfiles:

```toml
[bashrc]
paths = ["~/.bashrc"]
post_deploy = "shell_reload"

[gitconfig]
paths = ["~/.gitconfig"]
```

Or edit manually:

```bash
dot-man edit
```

### 3. Save your configuration

```bash
dot-man switch main
```

This copies your dotfiles to the repository and commits them.

### 4. Create a work configuration

```bash
dot-man switch work
```

Creates a new branch with your current setup. Modify files, then switch back:

```bash
dot-man switch main  # Saves work, deploys main
```

---

## Commands

### Core Commands

| Command                        | Description                                   |
| ------------------------------ | --------------------------------------------- |
| `dot-man init`                 | Initialize repository at `~/.config/dot-man/` |
| `dot-man status`              | Show tracked files and their status           |
| `dot-man switch <target>`      | Switch to branch, tag, or commit              |
| `dot-man edit`                 | Open `dot-man.toml` in your editor            |
| `dot-man deploy <branch>`      | One-way deploy (for new machines)             |
| `dot-man audit`                | Scan repository for secrets                   |
| `dot-man log`                  | Show commit history with optional diffs      |
| `dot-man checkout <target>`   | Checkout a specific commit or tag (detached)  |
| `dot-man diff`                 | Show changes between branches or files       |
| `dot-man revert <file>`        | Revert file to repository version            |
| `dot-man revert <file> -c <sha>` | Restore file from specific commit            |
| `dot-man template`            | Manage template variables                    |
| `dot-man profile`            | Manage machine-specific profiles            |

### Switch Enhancements

The `switch` command now supports multiple target types:

```bash
dot-man switch work              # Switch to branch
dot-man switch work@tag          # Switch to branch at tag position
dot-man switch abc1234          # Switch to specific commit
dot-man switch my-tag           # Switch to tag

# Override default save behavior
dot-man switch work --save       # Force save current changes
dot-man switch work --no-save    # Force discard current changes
dot-man switch --save work       # Flexible argument order
```

Set a default behavior preference:
```bash
dot-man config set switch.default_behavior no-save
```

### Remote & Sync

| Command                      | Description                                     |
| ---------------------------- | ----------------------------------------------- |
| `dot-man sync`               | Push/pull dotfiles with remote repository       |
| `dot-man remote set <url>`   | Set remote repository URL                       |
| `dot-man remote get`         | Show current remote URL                         |
| `dot-man remote sync-branch` | Sync local/remote branch names (main vs master) |
| `dot-man setup`              | Guided setup for GitHub remote (supports `gh`)  |

### Branch Management

| Command                        | Description                           |
| ------------------------------ | ------------------------------------- |
| `dot-man branch list`          | List all configuration branches       |
| `dot-man branch delete <name>` | Delete a branch (prompts if unmerged) |

### Tags

Tags allow you to mark specific commits for fast navigation:

| Command                        | Description                           |
| ------------------------------ | ------------------------------------- |
| `dot-man tag list`             | List all tags                         |
| `dot-man tag create <name>`    | Create tag at current commit          |
| `dot-man tag create <name> <sha>` | Create tag at specific commit     |
| `dot-man tag delete <name>`    | Delete a tag                          |
| `dot-man tag switch <name>`    | Switch to tag (checkout tag)          |

### Diff & History

Compare changes and restore from history:

```bash
# Show uncommitted changes
dot-man diff

# Compare current branch with main
dot-man diff --branch main

# Show changes for a specific file
dot-man diff ~/.bashrc

# Show staged changes
dot-man diff --staged

# Show last 20 commits with diffs
dot-man log --diff -n 20

# Restore file from specific commit
dot-man revert ~/.bashrc -c abc1234

# View commit history for a file
dot-man log -- path/to/file
```

### Profile Variables

Profiles allow different machine-specific configurations:

```bash
# Create a profile
dot-man profile create work-laptop -h laptop -h work-laptop -i minimal

# Set the branch for a profile
dot-man profile set-branch work-laptop work-main

# Auto-detect profile by hostname
dot-man profile detect

# Switch to a profile
dot-man profile switch work-laptop
```

**Profile inheritance**: Profiles can inherit from another profile.

### Utilities

| Command         | Description                                  |
| --------------- | -------------------------------------------- |
| `dot-man repo`  | Print repository path for direct access      |
| `dot-man shell` | Open a shell in the repository directory     |
| `dot-man verify` | Validate repository integrity                |
| `dot-man doctor` | Run diagnostics and health checks            |

### Options

```bash
dot-man switch work --dry-run   # Preview without changes
dot-man switch work --force     # Skip confirmation
dot-man switch work --save      # Save current changes before switching
dot-man switch work --no-save   # Discard current changes
dot-man sync --push-only        # Only push, don't pull
dot-man sync --pull-only        # Only pull, don't push
dot-man audit --strict          # Exit with error if secrets found
dot-man audit --fix             # Auto-redact detected secrets
dot-man status --secrets        # Highlight files with secrets
```

---

## Configuration

### dot-man.toml

Located at `~/.config/dot-man/repo/dot-man.toml`:

```toml
# Global defaults (applied to all sections)
[defaults]
secrets_filter = true
update_strategy = "replace"

# Individual file sections
[bashrc]
paths = ["~/.bashrc"]

[nvim]
paths = ["~/.config/nvim"]
update_strategy = "rename_old"

[ssh-config]
paths = ["~/.ssh/config"]
secrets_filter = true
```

### Global Configuration

Global settings are stored in `~/.config/dot-man/global.toml`. Use `dot-man config` to manage them:

```bash
# View current settings
dot-man config list

# Set switch default behavior (save or no-save)
dot-man config set switch.default_behavior no-save
```

| Setting                     | Values         | Description                           |
| --------------------------- | -------------- | ------------------------------------- |
| `switch.default_behavior`  | save / no-save | Default for switch command            |

### Options

| Option            | Values                    | Description                                   |
| ----------------- | ------------------------- | --------------------------------------------- |
| `local_path`      | path                      | Path on your filesystem                       |
| `repo_path`       | path                      | Path in the repository                        |
| `secrets_filter`  | true/false                | Redact secrets when saving                    |
| `update_strategy` | replace/rename_old/ignore | How to deploy files                           |
| `pre_deploy`      | command string            | Shell command to run _before_ file is changed |
| `post_deploy`     | command string            | Shell command to run _after_ file is changed  |

---

## Secret Detection

dot-man detects and redacts common secrets:

| Pattern       | Severity | Example                           |
| ------------- | -------- | --------------------------------- |
| Private Keys  | CRITICAL | `-----BEGIN RSA PRIVATE KEY-----` |
| AWS Keys      | CRITICAL | `AKIAIOSFODNN7EXAMPLE`            |
| GitHub Tokens | HIGH     | `ghp_xxxxxxxxxxxx`                |
| API Keys      | HIGH     | `api_key=sk_live_xxxxx`           |
| Passwords     | HIGH     | `password=mysecret`               |

Run `dot-man audit` to scan your repository.

---

## Documentation

- [Command Specifications](docs/specs/commands.md) - Detailed command behavior
- [Security Specification](docs/specs/security.md) - Secret detection patterns
- [Development Roadmap](docs/roadmap.md) - Version milestones

---

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup and contribution guidelines.

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

---

## License

MIT License - see [LICENSE](LICENSE)
