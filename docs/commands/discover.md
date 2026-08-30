# discover

Auto-detect existing dotfiles on your system.

## Usage

```bash
dot-man discover
dot-man discover --add
dot-man discover --no-extended
```

## What It Scans

The discover command scans 30+ common dotfile locations:

| Category | Locations |
|----------|-----------|
| Shell | `.bashrc`, `.zshrc`, `.bash_profile`, `.config/fish/` |
| Editor | `.config/nvim/`, `.vimrc`, `.emacs.d/`, `.config/emacs/` |
| Terminal | `.config/kitty/`, `.config/alacritty/`, `.config/wezterm/` |
| Git | `.gitconfig`, `.gitignore_global` |
| SSH | `.ssh/config` |
| Window Manager | `.config/hypr/`, `.config/sway/`, `.config/i3/` |
| Status Bar | `.config/waybar/`, `.config/polybar/` |

## Options

| Flag | Description |
|------|-------------|
| `--add` | Automatically add detected files to config |
| `--extended` | Include VS Code, Sublime, etc. (default) |
| `--no-extended` | Skip extended locations |

## Examples

```bash
# Scan and show results
dot-man discover

# Scan and add automatically
dot-man discover --add

# Skip VS Code, Sublime, etc.
dot-man discover --no-extended --add
```
