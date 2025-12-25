# {{name}}

A dotfiles project managed with [dot-man](https://github.com/BeshoyEhab/dot-man).

## Quick Start

```bash
# Initialize dot-man (if not already done)
dot-man init

# Check status
pro-mgr run {{name}} status

# Audit for secrets
pro-mgr run {{name}} audit

# Switch configurations
dot-man switch work
dot-man switch personal
```

## Adding Dotfiles

Edit `dot-man.ini` to add files:

```ini
[~/.bashrc]
local_path = ~/.bashrc
repo_path = bashrc

[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = gitconfig
secrets_filter = true
```

## Commands

| Task       | Description          |
| ---------- | -------------------- |
| `status`   | Show dotfile status  |
| `audit`    | Scan for secrets     |
| `switch`   | Switch branch        |
| `deploy`   | Deploy configuration |
| `edit`     | Edit config file     |
| `branches` | List all branches    |
