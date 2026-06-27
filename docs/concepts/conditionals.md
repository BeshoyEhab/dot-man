# Conditional Config

dot-man supports conditional blocks in tracked files for cross-platform configs.

## Syntax

```
{{ if VAR == "value" }}
  content when condition is true
{{ endif }}
```

## Supported Operators

- `==` — equals
- `!=` — not equals

## Examples

### OS-specific

```bash
# ~/.bashrc
{{ if OS == "darwin" }}
export PATH="/opt/homebrew/bin:$PATH"
alias ls="ls -G"
{{ endif }}

{{ if OS == "linux" }}
export PATH="/usr/local/bin:$PATH"
alias ls="ls --color=auto"
{{ endif }}
```

### Machine-specific

```bash
# ~/.gitconfig
{{ if MACHINE == "work-laptop" }}
[url "git@github.com:company/"]
    insteadOf = https://github.com/company/
{{ endif }}
```

### Negation

```bash
{{ if USER != "root" }}
# Only for non-root users
export EDITOR=nvim
{{ endif }}
```

## How It Works

1. Templates are processed during `deploy` and `save`
2. Conditionals are evaluated first
3. Simple `{{VAR}}` substitution happens after
4. If a variable is undefined, the conditional block is skipped
