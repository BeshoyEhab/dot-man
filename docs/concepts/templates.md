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

## Variables in Config Values

Section config values support the same `{{ }}` syntax, rendered at
load with section context on top of the machine variables above:

```toml
[nvim]
paths = ["~/.config/{{HOSTNAME}}/nvim"]
post_deploy = "notify '{{section_name}} deployed on {{HOSTNAME}}'"
```

Available section names: `{{section_name}}`, `{{config_name}}`
(derived from the rendered first path), `{{config_root}}`,
`{{paths}}`, `{{branch}}`. Conditionals work too, so one repo can
serve macOS and Linux:

```toml
[tool]
paths = ["{{ if OS == \"darwin\" }}~/.config/tool-mac{{ endif }}"]
```

Unknown variables pass through literally. Hook `{x}` placeholders
(`{config_name}`, `{branch}`, …) resolve afterward at `Section`
construction, so both spellings compose in one hook string.
