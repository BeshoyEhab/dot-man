# dot-man

<p align="center">
  <strong>Dotfile manager with git-powered branching</strong>
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
- 📝 **Edit in place** - Opens your `$EDITOR` for quick changes
- 🛡️ **Dry-run mode** - Preview changes before making them
- 🐚 **Shell completions** - Bash, Zsh, and Fish support

---

## Installation

### With pipx (Recommended)

```bash
# Basic install
pipx install git+https://github.com/BeshoyEhab/dot-man.git

# With interactive TUI (recommended)
pipx install "dot-man[tui]" --pip-args="git+https://github.com/BeshoyEhab/dot-man.git"
# Or after basic install:
pipx inject dot-man textual
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

# With TUI:
pip install "git+https://github.com/BeshoyEhab/dot-man.git#egg=dot-man[tui]"
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

### 2. Add files to track

```bash
dot-man edit
```

Add sections to `dot-man.ini`:

```ini
[~/.bashrc]
local_path = ~/.bashrc
repo_path = bashrc

[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = gitconfig
secrets_filter = true
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

| Command                        | Description                                   |
| ------------------------------ | --------------------------------------------- |
| `dot-man init`                 | Initialize repository at `~/.config/dot-man/` |
| `dot-man status`               | Show tracked files and their status           |
| `dot-man switch <branch>`      | Save current config, switch to branch, deploy |
| `dot-man edit`                 | Open `dot-man.ini` in your editor             |
| `dot-man deploy <branch>`      | One-way deploy (for new machines)             |
| `dot-man audit`                | Scan repository for secrets                   |
| `dot-man branch list`          | List all configuration branches               |
| `dot-man branch delete <name>` | Delete a branch                               |

### Options

```bash
dot-man switch work --dry-run   # Preview without changes
dot-man switch work --force     # Skip confirmation
dot-man audit --strict          # Exit with error if secrets found
dot-man audit --fix             # Auto-redact detected secrets
dot-man status --secrets        # Highlight files with secrets
```

---

## Configuration

### dot-man.ini

Located at `~/.config/dot-man/repo/dot-man.ini`:

```ini
[DEFAULT]
secrets_filter = true
update_strategy = replace

[~/.bashrc]
local_path = ~/.bashrc
repo_path = bashrc

[~/.config/nvim]
local_path = ~/.config/nvim
repo_path = nvim
update_strategy = rename_old

[~/.ssh/config]
local_path = ~/.ssh/config
repo_path = ssh_config
secrets_filter = true
```

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
