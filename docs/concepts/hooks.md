# Hooks

Hooks are shell commands that run at specific points during save and deploy.

## Hook Types

| Hook | When It Runs |
|------|--------------|
| `pre_deploy` | Before files are copied/symlinked |
| `post_deploy` | After files are copied/symlinked |
| `on_activate` | When branch is switched to |
| `on_deactivate` | When branch is switched from |

## Config

```toml
[main]
on_activate = "source ~/.bashrc"
on_deactivate = "echo 'Leaving main config'"

[work]
pre_deploy = "systemctl --user stop neovim"
post_deploy = "systemctl --user start neovim"
on_activate = "source ~/.config/work/env.sh"
```

## Built-in Aliases

| Alias | Description |
|-------|-------------|
| `quickshell_reload` | Reload quickshell config |
| `quickshell_restart` | Restart quickshell |
| `quickshell_validate` | Validate quickshell config |

## Example: Quickshell Integration

```toml
[quickshell]
paths = ["~/.config/quickshell/"]
post_deploy = "quickshell_reload"
on_deactivate = "killall qs 2>/dev/null || true"
on_activate = "qs -c ii &"
```

## Shell Variable

Within hooks, the `$DOT_MAN_BRANCH` variable contains the active branch name.

```bash
on_activate = "echo \"Switched to $DOT_MAN_BRANCH config\""
```

## Script Files (`file:` references)

Inline strings get unwieldy for multi-line logic. Any hook value can
embed `file:<script> [args]` tokens that resolve to executable scripts
from a hooks folder — composable with inline shell in a single line:

```toml
[work]
post_deploy = "echo 'start'; file:log.sh 'this is test'"
on_activate = "file:setup-env.sh {config_name}"
```

Lookup order:

1. `<repo>/hooks/` — versioned per branch, synced like your dotfiles
2. `~/.config/dot-man/hooks/` — machine-local fallback

The token is replaced with the quoted absolute script path; trailing
args are passed through untouched, and `{placeholders}` still resolve.
A missing script fails the hook with a `ConfigurationError` naming the
script and both searched folders. Scripts gain the exec bit
automatically, and `../` escapes outside the hooks folder are rejected.
