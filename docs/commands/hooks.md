# hooks

Manage pre/post deploy hooks.

## Usage

```bash
dot-man hooks list
dot-man hooks run <hook-name>
dot-man hooks test
```

## Available Hook Aliases

| Alias | Command |
|-------|---------|
| `shell_reload` | `source ~/.bashrc \|\| source ~/.zshrc` |
| `bash_reload` | `source ~/.bashrc` |
| `zsh_reload` | `source ~/.zshrc` |
| `fish_reload` | `source ~/.config/fish/config.fish` |
| `nvim_sync` | `nvim --headless +PackerSync +qa` |
| `hyprland_reload` | `hyprctl reload` |
| `kitty_reload` | `killall -SIGUSR1 kitty` |
| `tmux_reload` | `tmux source-file ~/.tmux.conf` |
| `waybar_reload` | `waybar-control reload` |
| `quickshell_reload` | `killall qs; qs -c {config_name} &` |

## Configuration

Hooks are configured per section in `dot-man.toml`:

```toml
[nvim]
paths = ["~/.config/nvim"]
pre_deploy = "nvim --headless +qa"
post_deploy = "nvim_sync"

[hyprland]
paths = ["~/.config/hypr"]
post_deploy = "hyprland_reload"
on_activate = "qs -c ii &"
on_deactivate = "killall qs 2>/dev/null || true"
```

## Placeholders

Placeholders are resolved automatically in hook commands:

| Placeholder | Value |
|-------------|-------|
| `{section_name}` | Current section name |
| `{config_name}` | Config file name |
| `{config_root}` | Repository root path |
| `{paths}` | Comma-separated list of paths |
| `{branch}` | Current branch name |

## Examples

```bash
# List all available hooks
dot-man hooks list

# Test hooks without deploying
dot-man hooks test
```
