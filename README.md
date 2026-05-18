<div align="center">

# dot-man

**Dotfile manager with git-powered branching**

[![CI](https://github.com/BeshoyEhab/dot-man/actions/workflows/ci.yml/badge.svg)](https://github.com/BeshoyEhab/dot-man/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dotman-git?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/dotman-git/)
[![PyPI downloads](https://img.shields.io/pypi/dm/dotman-git?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/dotman-git/)
[![Python](https://img.shields.io/pypi/pyversions/dotman-git?logo=python&logoColor=white)](https://pypi.org/project/dotman-git/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Coverage](https://img.shields.io/badge/coverage-61%25-yellow)](https://github.com/BeshoyEhab/dot-man)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/BeshoyEhab/dot-man/pulls)

---

*Switch your entire development environment in one command.*

[**Install**](#installation) · [**Quick Start**](#quick-start) · [**Commands**](#commands) · [**Config**](#configuration) · [**Docs**](docs/)

</div>

---

## What is dot-man?

dot-man stores your dotfiles in a **git repository** and uses **branches as configuration profiles**. Each branch is a complete, deployable snapshot of your environment.

```
Your Machine                  dot-man Repo               Any Machine
──────────────                ────────────               ───────────
~/.bashrc      ──── save ──►  branch: main  ── deploy ──►  ~/.bashrc
~/.config/nvim ──── save ──►  branch: work  ── deploy ──►  ~/.config/nvim
~/.gitconfig   ──── save ──►  branch: server             ~/.gitconfig
```

**Secrets are never committed.** API keys, tokens and passwords are automatically detected, encrypted locally in a vault, and replaced with hashes in the repository before any commit.

---

## Features

<table>
<tr>
<td>

**Core**
- 🌿 Git-powered branch profiles
- 🔐 Automatic secret detection & vault
- 🔄 Save → switch → deploy in one command
- ⚡ Pre/post deploy hooks with aliases
- 🏷️ Tag snapshots for fast rollback

</td>
<td>

**Advanced**
- 🔒 GPG / AGE file encryption
- 🌍 Import from chezmoi, yadm, stow
- 📤 Export to tar, zip, JSON
- 🔍 Auto-discover 30+ dotfile locations
- 🌐 YAML + TOML config support

</td>
<td>

**Developer**
- 🐚 Shell completions (bash/zsh/fish)
- 🎨 Syntax-highlighted rich diffs
- 🩺 `doctor` and `verify` diagnostics
- 📦 PyPI — `pip install dotman-git`
- 🔁 Remote sync via `dot-man sync`

</td>
</tr>
</table>

---

## Installation

### From PyPI (recommended)

```bash
pip install dotman-git
```

Shell completions are installed automatically on first run.

### With pipx (isolated)

```bash
pipx install dotman-git
```

### From source

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
pip install .
```

### Verify

```bash
dot-man --version
```

---

## Quick Start

```bash
# 1. Initialize — runs an interactive wizard that auto-detects your dotfiles
dot-man init

# 2. Add files manually if needed
dot-man add ~/.bashrc
dot-man add ~/.config/nvim

# 3. Create a "work" profile (branch)
dot-man navigate work

# 4. Edit your work-specific configs, then switch back — changes are saved automatically
dot-man navigate main

# 5. See what's changed
dot-man status
dot-man diff
```

---

## How Branching Works

Each branch is an independent configuration. Switching branches runs three phases automatically:

```
dot-man navigate work
        │
        ├─► Phase 1: Save   — copies your files into the repo and commits
        ├─► Phase 2: Switch — git checkout work
        └─► Phase 3: Deploy — copies repo files back to your home directory
```

| Branch   | Purpose                              |
|----------|--------------------------------------|
| `main`   | Personal daily driver                |
| `work`   | Office: proxy, work aliases          |
| `server` | Minimal: headless, no GUI tools      |
| `laptop` | Mobile: battery saving, HiDPI        |

---

## Commands

### Navigation

| Command | Description |
|---------|-------------|
| `dot-man navigate <target>` | Switch to branch, tag, or commit |
| `dot-man navigate work --preview` | Preview what will change |
| `dot-man navigate work --preview --diff` | Full diff before switching |
| `dot-man navigate work --no-save` | Discard local changes and switch |
| `dot-man navigate v1.0` | Jump to a tag |
| `dot-man navigate abc1234` | Checkout a specific commit |

### Files & Tracking

| Command | Description |
|---------|-------------|
| `dot-man init` | Initialize repository with setup wizard |
| `dot-man add <path>` | Track a file or directory |
| `dot-man status` | Show tracked files and their state |
| `dot-man status --secrets` | Highlight files containing secrets |
| `dot-man diff` | Show uncommitted changes |
| `dot-man diff --branch main` | Compare current branch to main |
| `dot-man diff --rich` | Syntax-highlighted diff |
| `dot-man revert <file>` | Restore file from repo |
| `dot-man revert <file> -c abc123` | Restore from specific commit |
| `dot-man watch` | Auto-save tracked files on change |
| `dot-man watch --no-commit` | Watch and save without committing |

### History & Tags

| Command | Description |
|---------|-------------|
| `dot-man log` | Show commit history |
| `dot-man log --diff` | History with diffs |
| `dot-man log --interactive` | TUI log browser |
| `dot-man show <commit>` | Full diff for a commit |
| `dot-man tag create v1.0` | Create a tag |
| `dot-man tag list` | List all tags |
| `dot-man tag switch v1.0` | Checkout a tag |
| `dot-man rollback` | Roll back to previous commit |
| `dot-man rollback -n 3` | Roll back 3 commits |
| `dot-man rollback --list` | Show available rollback points |

### Security

| Command | Description |
|---------|-------------|
| `dot-man audit` | Scan repo for secrets |
| `dot-man audit --strict` | Exit non-zero if any secrets found |
| `dot-man audit --fix` | Auto-redact detected secrets |
| `dot-man encrypt encrypt <section>` | Encrypt a section with GPG/AGE |
| `dot-man encrypt status` | Show encryption status |

### Import / Export / Discovery

| Command | Description |
|---------|-------------|
| `dot-man discover` | Auto-detect existing dotfiles |
| `dot-man discover --add` | Add detected configs automatically |
| `dot-man import chezmoi` | Import from chezmoi |
| `dot-man import yadm` | Import from yadm |
| `dot-man import stow` | Import from GNU Stow |
| `dot-man export tar backup.tar.gz` | Export to tar archive |
| `dot-man export zip dots.zip` | Export to zip |
| `dot-man export json manifest.json` | Export to JSON manifest |

### Sync & Remote

| Command | Description |
|---------|-------------|
| `dot-man sync` | Push + pull with remote |
| `dot-man sync --push-only` | Only push |
| `dot-man sync --pull-only` | Only pull |
| `dot-man remote set <url>` | Set remote URL |
| `dot-man setup` | Guided GitHub remote setup |

### Diagnostics

| Command | Description |
|---------|-------------|
| `dot-man doctor` | Run health checks |
| `dot-man verify` | Validate repo integrity |
| `dot-man backup create` | Create a manual backup |
| `dot-man backup restore <id>` | Restore from backup |

---

## Configuration

Configuration lives in `~/.config/dot-man/repo/dot-man.toml` and is tracked **per branch** — different branches can track different files.

### TOML (default)

```toml
# Simple file tracking
[bashrc]
paths = ["~/.bashrc"]
post_deploy = "shell_reload"

# Directory with exclusions
[nvim]
paths = ["~/.config/nvim"]
exclude = ["*.log", "plugin/packer_compiled.lua"]
post_deploy = "nvim_sync"

# SSH config with secret filtering
[ssh-config]
paths = ["~/.ssh/config"]
secrets_filter = true
update_strategy = "rename_old"

# Hyprland with notification on deploy
[hyprland]
paths = ["~/.config/hypr"]
post_deploy = "hyprland_reload"
```

### YAML (also supported)

```yaml
bashrc:
  paths:
    - ~/.bashrc
  post_deploy: shell_reload

nvim:
  paths:
    - ~/.config/nvim
  exclude:
    - "*.log"
  post_deploy: nvim_sync
```

### Hook Aliases

Instead of writing full shell commands, use built-in aliases:

| Alias | Runs |
|-------|------|
| `shell_reload` | `source ~/.bashrc \|\| source ~/.zshrc` |
| `nvim_sync` | `nvim --headless +PackerSync +qa` |
| `hyprland_reload` | `hyprctl reload` |
| `fish_reload` | `source ~/.config/fish/config.fish` |
| `tmux_reload` | `tmux source-file ~/.tmux.conf` |
| `kitty_reload` | `killall -SIGUSR1 kitty` |

### Update Strategies

| Strategy | Behaviour |
|----------|-----------|
| `replace` | Overwrite existing files *(default)* |
| `rename_old` | Back up existing file before overwriting |
| `ignore` | Skip if file already exists |

### Templates & Inheritance

```toml
# Define reusable templates
[templates.linux-desktop]
post_deploy = "notify-send 'Config updated'"
update_strategy = "rename_old"

# Inherit in sections
[hyprland]
paths = ["~/.config/hypr"]
inherits = ["linux-desktop"]

[waybar]
paths = ["~/.config/waybar"]
inherits = ["linux-desktop"]
```

### Environment Variable Expansion

```toml
[work-files]
paths = ["$WORK_DIR/config", "~/$USER/.config/app"]
```

---

## Secret Detection

Before any file enters the repository, dot-man scans it for secrets. Detected values are **encrypted locally** and replaced with a hash placeholder in the repo.

| Pattern | Severity | Example |
|---------|----------|---------|
| Private keys | 🔴 CRITICAL | `-----BEGIN RSA PRIVATE KEY-----` |
| AWS credentials | 🔴 CRITICAL | `AKIA...` |
| GitHub tokens | 🟠 HIGH | `ghp_xxxx` |
| API keys | 🟠 HIGH | `api_key = "sk-..."` |
| Passwords | 🟠 HIGH | `password = "hunter2"` |
| JWT tokens | 🟡 MEDIUM | `eyJ...` |

```
repo file:   api_key = "***REDACTED:e3b0c44298...***"
vault:       { encrypted: "gAAAAABk..." }   ← Fernet AES-128
system file: api_key = "sk-abc123..."       ← restored on deploy
```

Run `dot-man audit` to scan at any time. Use `dot-man audit --strict` in CI/CD pipelines.

---

## Multi-Machine Profiles

Profiles let you auto-select the right branch based on hostname:

```bash
dot-man profile create work-laptop -h work-laptop -h thinkpad
dot-man profile set-branch work-laptop work
dot-man profile detect   # auto-switches to the right profile
```

---

## Template Variables

Use `{{VARIABLE}}` placeholders in your dotfiles that get substituted on deploy:

```bash
dot-man template set EMAIL john@work.com
dot-man template set HOSTNAME work-laptop
```

Then in your `~/.gitconfig`:
```
[user]
    email = {{EMAIL}}
    name  = John Doe
```

System variables (`{{HOSTNAME}}`, `{{USER}}`, `{{SHELL}}`, etc.) are auto-populated.

---

## Project Status

| Metric | Value |
|--------|-------|
| Version | `1.1.0` |
| Python | `3.9+` |
| Platforms | Linux, macOS |
| Test Coverage | 61% |
| Commands | 30+ |
| PyPI | [`dotman-git`](https://pypi.org/project/dotman-git/) |

---

## Development

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run full quality gate
black dot_man/ tests/
ruff check dot_man/ tests/
mypy dot_man/ --ignore-missing-imports
pytest tests/ --cov=dot_man --cov-report=term-missing
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [DEVELOPMENT.md](DEVELOPMENT.md) for full guides.

---

## Roadmap

- [ ] 80%+ test coverage
- [ ] Full documentation site (mkdocs)
- [ ] Symlink mode
- [x] `dot-man watch` — auto-sync on file change
- [x] Deploy rollback (transaction-style)
- [ ] Plugin system

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap.

---

## Contributing

Pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

All contributions must pass the pre-push quality checklist: `black`, `ruff`, `mypy`, and all tests.

---

## License

[MIT](LICENSE) © [Bishoy Ehab](https://github.com/BeshoyEhab)
