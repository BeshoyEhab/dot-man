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
- 🐚 **Shell completions** - Bash, Zsh, and Fish support (optimized with caching)
- 🏷️ **Tags** - Tag commits for fast navigation
- 📜 **History & Diff** - View commit history, compare branches, restore files
- 📊 **Diff & Restore** - Compare changes between branches, restore from history
- 🔄 **Global hooks** - System-wide hooks for any dot-man command
- 🔀 **Auto-detect hooks** - Automatically reload configs when switching branches
- 🌍 **Import existing** - Import dotfiles from existing git repositories
- 📦 **Universal merge** - Manage shared content across branches with markers

---

## Current Status

| Metric | Value |
|--------|-------|
| Version | 1.0.0 (Production) |
| Test Coverage | 61% |
| Commands | 30+ |
| Python | 3.9+ |

### What's New in 1.0.0

- **`dot-man init --import`** - Import from existing git repositories:
  - Local paths, GitHub shorthand, HTTPS, or SSH URLs
  - Preserves all commits, branches, and tags
- **`dot-man navigate`** - Unified command replacing `switch` and `checkout`:
  - `--preview, -p` - Preview changes before switching
  - `--diff, -d` - Show full diff when previewing
  - `--files-only` - Show only commits that changed tracked files
- **`dot-man hooks`** - Manage global hooks:
  - `dot-man hooks list` - List available hooks
  - `dot-man hooks create pre|post <name>` - Create hook script
  - `dot-man hooks delete pre|post <name>` - Delete hook script
- **Auto-detect hooks** - When switching branches, dot-man automatically detects which configs changed and runs appropriate reload hooks (hyprland, nvim, quickshell, etc.)
- **Universal file merge** - Manage content across branches using markers:
  - `# >>> dot-man:start <<<` and `# >>> dot-man:end <<<`
  - `UniversalMergeManager` for extract/inject/remove operations
- **Config auto-detection** - Detects Quickshell subdirs and other popular configs automatically during init

### Deprecated (use `navigate` instead)
- `switch` → `dot-man navigate <branch>`
- `checkout` → `dot-man navigate <commit>`

### Roadmap to V1.0

- [x] Increase test coverage (56% achieved)
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

### 2. Add your dotfiles

```bash
dot-man add ~/.bashrc
dot-man add ~/.zshrc
dot-man add ~/.config/nvim
```

### 3. Save your configuration

```bash
dot-man navigate main
```

This copies your dotfiles to the repository and commits them.

### 4. Create different configurations

Create a work configuration:
```bash
dot-man navigate work  # Creates 'work' branch with current files
```

Modify files, then switch back:
```bash
dot-man navigate main  # Saves work, deploys main
```

---

## How Navigation Works

### The `navigate` Command

`dot-man navigate` is your main command for switching between configurations.

```bash
# Switch branches
dot-man navigate work           # Switch to 'work' branch
dot-man navigate personal       # Switch to 'personal' branch

# Preview before switching (recommended!)
dot-man navigate work --preview        # See what changes
dot-man navigate work --preview --diff # See full diff

# Switch to specific point in history
dot-man navigate v1.0          # Go to tag
dot-man navigate abc1234        # Go to commit (detached HEAD)

# Branch at tag
dot-man navigate work@v1.0      # Switch to work branch at tag v1.0
```

### Branch vs Commit: What's the Difference?

| Type | Purpose | Changes Saved? |
|------|---------|----------------|
| **Branch** (e.g., `main`, `work`) | Your full configuration | Yes - auto-saved when you switch |
| **Tag** (e.g., `v1.0`) | Snapshot in time | No - just marks a point |
| **Commit** (e.g., `abc1234`) | Specific state | No - viewing only (detached HEAD) |

### ⚠️ Deprecated Commands

| Old Command | Use Instead | Why |
|------------|-------------|-----|
| `switch` | `navigate` | Unified command with preview |
| `checkout` | `navigate` | Same functionality |

Run these commands and they'll show deprecation warnings. Use `navigate` instead.

---

## Commands

### Core Commands

| Command                        | Description                                   |
| ------------------------------ | --------------------------------------------- |
| `dot-man init`                 | Initialize repository at `~/.config/dot-man/` |
| `dot-man status`              | Show tracked files and their status           |
| `dot-man navigate <target>`   | Navigate to branch, tag, or commit (unified)  |
| `dot-man switch <target>`      | Switch to branch, tag, or commit (legacy)     |
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
| `dot-man hooks list|create|delete` | Manage pre/post command hooks              |
| `dot-man discover`            | Auto-detect existing dotfiles                 |
| `dot-man import <source>`      | Import from chezmoi, yadm, or stow            |
| `dot-man export <format>`     | Export to tar, zip, or json                   |
| `dot-man encrypt`             | Encrypt/decrypt sensitive files               |

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

### Navigate Command (Unified)

The `navigate` command is the unified way to switch between branches, tags, and commits with preview capabilities:

```bash
# Basic navigation
dot-man navigate work              # Switch to branch
dot-man navigate work@tag         # Switch to branch at tag position
dot-man navigate abc1234          # Switch to specific commit
dot-man navigate my-tag           # Switch to tag

# Preview changes before switching
dot-man navigate work --preview              # Preview diff
dot-man navigate work --preview --diff       # Show full diff
dot-man navigate work --preview --files-only  # Only commits with file changes

# Override default save behavior
dot-man navigate work --save                  # Force save current changes
dot-man navigate work --no-save               # Force discard current changes
```

### Hooks

Hooks allow you to run custom scripts before or after commands:

```bash
# List available hooks
dot-man hooks list

# Create a hook (creates ~/.config/dot-man/hooks/pre_switch)
dot-man hooks create pre switch

# Create a post-deploy hook
dot-man hooks create post deploy

# Delete a hook
dot-man hooks delete pre checkout
```

Hook scripts have environment variables available:
- `DOTMAN_HOOK_COMMAND` - The command being run (switch, checkout, deploy, etc.)
- `DOTMAN_HOOK_PHASE` - "pre" or "post"
- `DOTMAN_SOURCE` - Source branch/commit (for switch)
- `DOTMAN_TARGET` - Target branch/commit

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
dot-man diff --rich/--no-rich    # Enable/disable rich diff colors (default: on)
dot-man discover --add          # Auto-add detected configs to dot-man.toml
dot-man import chezmoi --dry-run # Preview what would be imported
dot-man export tar backup.tar.gz # Export to tar archive
dot-man encrypt status           # Show encryption status
```

---

## Configuration

### Supported Formats

dot-man supports both **TOML** and **YAML** configuration formats:

- TOML: `dot-man.toml` (default)
- YAML: `dot-man.yaml` or `dot-man.yml`

### Example: TOML format

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

### Example: YAML format

Located at `~/.config/dot-man/repo/dot-man.yaml`:

```yaml
defaults:
  secrets_filter: true
  update_strategy: replace

bashrc:
  paths:
    - ~/.bashrc

nvim:
  paths:
    - ~/.config/nvim
  update_strategy: rename_old

ssh-config:
  paths:
    - ~/.ssh/config
  secrets_filter: true
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
| `paths`           | list of paths             | Paths to track (supports $HOME, $USER, etc.)  |
| `local_path`      | path                      | Path on your filesystem                       |
| `repo_path`       | path                      | Path in the repository                        |
| `secrets_filter`  | true/false                | Redact secrets when saving                    |
| `update_strategy` | replace/rename_old/ignore | How to deploy files                           |
| `pre_deploy`      | command string            | Shell command to run _before_ file is changed |
| `post_deploy`     | command string            | Shell command to run _after_ file is changed |

### Environment Variables in Paths

Paths support environment variable expansion:

```toml
[work-files]
paths = ["$WORK_DIR/config", "~/$USER/.config/app"]
```

```yaml
work-files:
  paths:
    - $WORK_DIR/config
    - ~/$USER/.config/app
```

---

## Troubleshooting

### Common Issues

**Q: I'm on a detached HEAD state. How do I get back?**
```bash
# List your branches
dot-man branch list

# Return to a branch
dot-man navigate main
```

**Q: How do I undo the last switch?**
```bash
# Your previous work is saved as a commit
dot-man log

# Switch back to it
dot-man navigate <previous-branch>
```

**Q: My changes aren't being saved when I switch**
```bash
# Make sure you're using the save mode (default)
dot-man navigate work --save

# Or check if secrets are being redacted
dot-man status
```

**Q: How do I see what changed in a branch?**
```bash
# Preview changes before switching
dot-man navigate work --preview

# See full diff
dot-man navigate work --preview --diff
```

**Q: What are the differences between branches?**
```bash
# Compare two branches
dot-man diff --branch main

# Show only commits that changed tracked files
dot-man navigate main --preview --files-only
```

### Getting Help

```bash
# See all commands
dot-man --help

# See specific command help
dot-man navigate --help
dot-man add --help

# Diagnose issues
dot-man doctor

# Check repository integrity
dot-man verify
```

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

- [Development Guide Manual](docs/DEVELOPMENT_GUIDE_MANUAL.md) - In-depth architecture and development guide
- [Command Specifications](docs/specs/commands.md) - Detailed command behavior
- [Security Specification](docs/specs/security.md) - Secret detection patterns
- [Development Roadmap](docs/roadmap.md) - Version milestones
- [Architecture Overview](docs/ARCHITECTURE.md) - High-level system structure

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
