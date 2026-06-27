# Quick Start

## 1. Initialize

```bash
dot-man init
```

This creates:
- `~/.config/dot-man/` — dot-man home directory
- `~/.config/dot-man/dot-man.toml` — config file
- `~/.config/dot-man/repo/` — bare git repository

## 2. Discover Dotfiles

dot-man auto-discovers common dotfile locations:

```bash
dot-man discover
```

This shows detected files and adds them to your config.

## 3. Save

Save your current dotfiles to a branch:

```bash
dot-man save "initial config"
```

This:
1. Scans configured paths for changes
2. Strips secrets and encrypts them in the vault
3. Commits everything to the current branch

## 4. Switch

Switch to a different configuration profile:

```bash
dot-man navigate work
```

This saves current changes, switches branch, and deploys files.

## 5. Deploy

Deploy a branch to a new machine:

```bash
dot-man deploy main
```

## Common Workflow

```bash
# Daily: save changes
dot-man save "updated vim config"

# Switch between profiles
dot-man navigate work
dot-man navigate personal

# Check what's different
dot-man status
dot-man diff
```
