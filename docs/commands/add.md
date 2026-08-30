# add

Track a file or directory with dot-man.

## Usage

```bash
dot-man add <path>
dot-man add <path> --section <name>
dot-man add <path> --exclude "*.log"
dot-man add <path> --post-deploy "reload"
```

## What It Does

1. Adds the path to `dot-man.toml` configuration
2. Copies the file/directory content to the repository
3. Scans for secrets and redacts them if found

## Options

| Flag | Description |
|------|-------------|
| `--section`, `-s` | Custom section name (default: auto-generated) |
| `--repo-base`, `-r` | Base directory name in repo |
| `--exclude`, `-e` | Glob patterns to exclude (repeatable) |
| `--include`, `-i` | Glob patterns to include (repeatable) |
| `--inherits`, `-t` | Templates to inherit from |
| `--post-deploy` | Command to run after deploying |
| `--pre-deploy` | Command to run before deploying |

## Examples

```bash
# Add a single file
dot-man add ~/.bashrc

# Add a directory with exclusions
dot-man add ~/.config/nvim --exclude "*.log" --exclude "plugin/"

# Add with custom section name
dot-man add ~/.ssh/config --section ssh-config

# Add with deploy hook
dot-man add ~/.config/hypr --post-deploy "hyprctl reload"

# Add with template inheritance
dot-man add ~/.config/waybar --inherits linux-desktop
```

## Section Naming

If `--section` is not specified, the section name is auto-generated:

| Path | Section Name |
|------|--------------|
| `~/.config/nvim` | `nvim` |
| `~/.bashrc` | `bashrc` |
| `~/.gitconfig` | `gitconfig` |

## Secret Detection

Files are scanned for secrets during add. Detected values are encrypted and replaced with hashes. Run `dot-man audit` to review.
