# init

Initialize a dot-man repository with interactive setup wizard.

## Example

```bash
dot-man init   # detects your dotfiles, tracks what you confirm
```

## Usage

```bash
dot-man init
dot-man init --import        # Import from existing git repo
dot-man init --no-wizard    # Manual setup without the wizard
```

## What It Does

1. Creates `~/.config/dot-man/repo/` with a git repository
2. Runs an interactive wizard to detect and add common dotfiles
3. Generates a `dot-man.toml` configuration file
4. Creates initial commit

## Interactive Wizard

The wizard auto-detects common dotfile locations:

| Category | Locations Checked |
|----------|-------------------|
| Shell | `.bashrc`, `.zshrc`, `.config/fish/config.fish` |
| Editor | `.config/nvim/`, `.vimrc`, `.emacs.d/` |
| Terminal | `.config/kitty/`, `.config/alacritty/` |
| Git | `.gitconfig` |
| SSH | `.ssh/config` |
| Window Manager | `.config/hypr/`, `.config/sway/` |

## Options

| Flag | Description |
|------|-------------|
| `--force` | Reinitialize even if already exists |
| `--no-wizard` | Skip interactive setup wizard |
| `--sandbox` | Test init in a temporary sandbox directory |
| `--import` | Import from an existing git repository |

## Examples

```bash
# Basic initialization
dot-man init

# Import existing dotfiles repo
cd ~/my-dotfiles
dot-man init --import

# Manual setup without the wizard
dot-man init --no-wizard
```

## Post-Init

After initialization, add more files:

```bash
dot-man add ~/.config/nvim
dot-man add ~/.ssh/config --section ssh
```
