---
hide:
  - navigation
---

# dot-man

**Dotfile manager with git-powered branching**

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Install**

    ---

    `pip install dotman-git`

    [:octicons-arrow-right-24: Getting started](getting-started/installation.md)

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Get running in 60 seconds

    [:octicons-arrow-right-24: Quick start](getting-started/quickstart.md)

-   :material-console:{ .lg .middle } **Commands**

    ---

    Full CLI reference

    [:octicons-arrow-right-24: Commands](commands/index.md)

-   :material-book-open-variant:{ .lg .middle } **Concepts**

    ---

    How dot-man works

    [:octicons-arrow-right-24: Concepts](concepts/branches.md)

</div>

---

## What is dot-man?

dot-man stores your dotfiles in a **git repository** and uses **branches as configuration profiles**. Each branch is a complete, deployable snapshot of your environment.

```
Your Machine                  dot-man Repo               Any Machine
──────────────                ────────────               ───────────
~/.bashrc      ──── save ──►  branch: main  ── deploy ──►  ~/.bashrc
~/.config/nvim ──── save ──►  branch: work  ── deploy ──►  ~/.config/nvim
~/.gitconfig   ──── save ──►  branch: server               ~/.gitconfig
```

**Secrets are never committed.** API keys, tokens and passwords are automatically detected, encrypted locally in a vault, and replaced with hashes in the repository before any commit.

---

## Quick Install

```bash
pip install dotman-git
dot-man init
dot-man save "my first config"
```

---

## Core Features

| Feature | Description |
|---------|-------------|
| **Branch Profiles** | Switch between work, personal, server configs with one command |
| **Secret Vault** | API keys encrypted locally, never committed to git |
| **Automatic Discovery** | Detects 30+ common dotfile locations |
| **Shell Hooks** | Pre/post deploy scripts, quickshell integration |
| **Tag Snapshots** | Tag and rollback to any point in time |
| **Template Variables** | Machine-specific configs with `{{ MACHINE }}`, `{{ OS }}` |
| **Conditional Config** | `{{ if OS == "darwin" }}` blocks for cross-platform configs |
| **Package Bootstrap** | Install packages via brew/apt/dnf/pacman on new machines |
| **JSON Output** | `--json` flag on status for CI/scripting integration |
