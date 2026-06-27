# Template Variables

Template variables let you customize dotfiles per machine, OS, or user.

## Built-in Variables

| Variable | Example Value |
|----------|---------------|
| `{{ MACHINE }}` | `work-laptop` |
| `{{ USER }}` | `john` |
| `{{ OS }}` | `linux`, `darwin`, `windows` |
| `{{ ARCH }}` | `x86_64`, `aarch64` |
| `{{ HOSTNAME }}` | `john-laptop` |

## Usage

In any tracked file:

```bash
# ~/.bashrc
if [ "{{ OS }}" = "darwin" ]; then
    alias ls="ls -G"
else
    alias ls="ls --color=auto"
fi

# ~/.gitconfig
[user]
    name = {{ USER }}
```

## Conditional Blocks

```bash
# macOS-specific
{{ if OS == "darwin" }}
export PATH="/opt/homebrew/bin:$PATH"
{{ endif }}

# Linux-specific
{{ if OS == "linux" }}
export PATH="/usr/local/bin:$PATH"
{{ endif }}
```

## Custom Variables

Define custom variables in config:

```toml
[settings]
template_vars = { EDITOR = "nvim", SHELL = "zsh" }
```

## Disable Templates

Per section:

```toml
[main]
render_templates = false
```
