# import

Import dotfiles from other dotfile managers.

## Usage

```bash
dot-man import <source> [--path <dir>] [--dry-run]
dot-man import all
```

Always preview first with `--dry-run` — it lists every file mapping
without copying anything. Then run without it to copy and commit.

## Supported Sources

| Source | Command | What it reads |
|--------|---------|---------------|
| chezmoi | `dot-man import chezmoi` | `~/.local/share/chezmoi` (or `--path`) |
| yadm | `dot-man import yadm` | yadm worktree (or `--path`) |
| GNU Stow | `dot-man import stow` | `~/dotfiles` packages (or `--path`) |
| Auto-detect | `dot-man import all` | Tries each source in turn |

## Options

| Flag | Description |
|------|-------------|
| `--path`, `-p` | Custom source directory (default: auto-detect) |
| `--dry-run` | Preview what would be imported |

## Migrating from chezmoi

Point at your chezmoi source directory (the one with `dot_` files):

```bash
dot-man import chezmoi --path ~/.local/share/chezmoi --dry-run
```

Name mapping (verified): `dot_bashrc` → `~/.bashrc`,
`dot_config/nvim/init.lua` → `~/.config/nvim/init.lua`. A leading
`dot_` becomes a dot; anything else lands under `~/.config/`.
Dotfiles already starting with `.` keep a single dot.

```bash
dot-man import chezmoi --path ~/.local/share/chezmoi
dot-man status        # review what landed
dot-man add ~/.bashrc # track what you want to keep
```

## Migrating from yadm

```bash
dot-man import yadm --dry-run   # auto-detects yadm if present
dot-man import yadm
```

Files map to the same relative path under home (`work/.vimrc` →
`~/.vimrc`). Files that already exist are skipped, never overwritten.
Pass `--path` with any directory to import from a plain folder instead
of the detected worktree.

## Migrating from GNU Stow

```bash
dot-man import stow --path ~/dotfiles --dry-run
dot-man import stow --path ~/dotfiles
```

Each subdirectory is treated as a package: the first path segment
gains its dot (`nvim/.config/nvim/init.lua` →
`~/.config/nvim/init.lua`). Directories starting with `.` map as-is.

## After importing

Imported files land in your home directory but are not tracked yet —
review with `dot-man status`, then `dot-man add` the ones you want.
Finish with `dot-man navigate work` to snapshot the new configuration.
