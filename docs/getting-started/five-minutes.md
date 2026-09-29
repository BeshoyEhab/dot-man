# dot-man in 5 Minutes

Track your first dotfile and switch configurations. Each step shows
the command, what you'll see, and why.

## 0:00 — Install

```bash
pip install dotman-git
```

## 0:30 — Initialize

```bash
dot-man init
```

Answer a few prompts. dot-man detects your shell configs and tracks
the ones you confirm. You end with a git-backed repository under
`~/.config/dot-man/` — that repository *is* your backup.

## 2:00 — Add a file

```bash
dot-man add ~/.bashrc
```

```text
✓ Added file: /home/you/.bashrc
  Section: [bashrc]

📋 Next Steps:
  1. Run dot-man status to verify your tracked files
  2. Run dot-man navigate work to start a work configuration
```

Every command points at the next one — follow the suggestions.

## 3:00 — Check status

```bash
dot-man status
```

```text
Summary: 0 modified, 1 new, 0 deleted, 0 identical
```

New files need a snapshot before they travel with you:

```bash
dot-man save "track bashrc"
```

## 4:00 — Navigate

```bash
dot-man navigate work
```

dot-man saves the current state, switches branch, and deploys the
work configuration's files. Switch back anytime with
`dot-man navigate main`.

## 5:00 — Done

Your dotfiles are tracked, snapshotted, and switchable. Where next:

- `dot-man help-all` — every command
- [Hooks](../concepts/hooks.md) — run scripts around deploy and switches
- [Template Variables](../concepts/templates.md) — one repo for macOS and Linux
- [Configuration](configuration.md) — the full `dot-man.toml` reference
