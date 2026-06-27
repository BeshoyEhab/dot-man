# Configuration

dot-man uses a TOML config file at `~/.config/dot-man/dot-man.toml`.

## Basic Structure

```toml
# Global settings
[settings]
default_branch = "main"
deploy_method = "copy"

# Branch sections
[main]
paths = [
    "~/.bashrc",
    "~/.gitconfig",
    "~/.config/nvim/",
]
exclude = ["*.swp"]

[work]
paths = [
    "~/.bashrc",
    "~/.gitconfig",
    "~/.config/nvim/",
    "~/.config/slack/",
]
```

## Section Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `paths` | list | required | Files/directories to track |
| `exclude` | list | `[]` | Glob patterns to exclude |
| `deploy_method` | string | `"copy"` | `"copy"` or `"symlink"` |
| `repo_path` | string | auto | Explicit repo path for single files |
| `secrets_filter` | bool | `true` | Enable secret detection |
| `render_templates` | bool | `true` | Enable template variable substitution |
| `pre_deploy` | string | none | Shell command before deploy |
| `post_deploy` | string | none | Shell command after deploy |
| `on_activate` | string | none | Shell command when branch activated |
| `on_deactivate` | string | none | Shell command when branch deactivated |

## YAML Config

dot-man also supports YAML config files at `~/.config/dot-man/dot-man.yaml`:

```yaml
settings:
  default_branch: main

main:
  paths:
    - ~/.bashrc
    - ~/.gitconfig
```

## Bootstrap Packages

```toml
[bootstrap]
packages = ["git", "vim", "neovim", "ripgrep", "fzf"]

# Per-package manager overrides
packages_brew = ["htop", "node"]
packages_apt = ["htop", "nodejs"]
```
