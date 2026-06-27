# bootstrap

Install system packages on a new machine using your system's package manager.

## Usage

```bash
dot-man bootstrap
```

## Behavior

1. Detects your system's package manager (brew, apt, dnf, pacman, zypper, nix, xbps)
2. Reads packages from config `[bootstrap]` section
3. Installs missing packages

## Detection Order

| Manager | Platform |
|---------|----------|
| `brew` | macOS (Homebrew) |
| `apt` | Debian/Ubuntu |
| `dnf` | Fedora |
| `pacman` | Arch/Manjaro |
| `zypper` | openSUSE |
| `nix` | NixOS |
| `xbps` | Void Linux |

## Config

```toml
[bootstrap]
packages = ["git", "vim", "neovim", "ripgrep", "fzf"]

# Per-manager overrides
packages_brew = ["htop", "node"]
packages_apt = ["htop", "nodejs"]
packages_pacman = ["htop", "nodejs"]
```

## Options

| Flag | Description |
|------|-------------|
| `--dry-run` | Show what would be installed |
| `--manager <name>` | Force a specific package manager |
