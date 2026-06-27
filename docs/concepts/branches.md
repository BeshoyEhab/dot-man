# Branch Profiles

Branches in dot-man are configuration profiles. Each branch contains a complete snapshot of your dotfiles for a specific context (work, personal, server, etc.).

## How It Works

```
~/.config/dot-man/repo/
├── main          ← personal config
├── work          ← work config
├── server        ← server config
└── minimal       ← minimal setup
```

When you `dot-man navigate work`, dot-man:

1. Saves current changes on the active branch
2. Switches to the `work` branch
3. Deploys all files from `work` to your home directory
4. Runs activation hooks

## Creating Profiles

```bash
# Start from current state
dot-man init
dot-man save "personal config"
dot-man branch work
dot-man navigate work
# ... customize for work ...
dot-man save "work config"
```

## Branch vs Tag

| | Branch | Tag |
|---|--------|-----|
| **Mutable** | Yes — changes over time | No — point-in-time snapshot |
| **Use for** | Active profiles | Rollback points |
| **Example** | `work`, `personal` | `v1.0`, `backup-2024-01-01` |
