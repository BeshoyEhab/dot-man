# deploy

Deploy files from a branch to your system.

## Usage

```bash
dot-man deploy
dot-man deploy --branch work
dot-man deploy --dry-run
dot-man deploy --force
```

## What It Does

1. Reads the target branch's `dot-man.toml` configuration
2. Copies files from the repository to their local paths
3. Runs pre/post deploy hooks if configured
4. Handles secret decryption (restores encrypted values)

## Options

| Flag | Description |
|------|-------------|
| `--branch`, `-b` | Branch to deploy from (default: current) |
| `--dry-run`, `-n` | Show what would be deployed without making changes |
| `--force`, `-f` | Overwrite existing files without prompting |
| `--section`, `-s` | Deploy only a specific section |

## Examples

```bash
# Deploy current branch
dot-man deploy

# Preview deployment
dot-man deploy --dry-run

# Deploy from another branch
dot-man deploy --branch work

# Deploy specific section
dot-man deploy --section nvim
```

## Deploy Behaviour

| Strategy | Behaviour |
|----------|-----------|
| `replace` | Overwrite existing files *(default)* |
| `rename_old` | Back up existing file as `file.bak` before overwriting |
| `ignore` | Skip if file already exists |

## Symlink Mode

If `deploy_method = "symlink"` is set in a section, files are symlinked instead of copied:

```toml
[hyprland]
paths = ["~/.config/hypr"]
deploy_method = "symlink"
```

## Hooks

Pre/post deploy hooks run automatically:

```toml
[nvim]
paths = ["~/.config/nvim"]
pre_deploy = "nvim --headless +qa"
post_deploy = "nvim --headless +PackerSync +qa"
```
