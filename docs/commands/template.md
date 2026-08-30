# template

Manage template variables for cross-machine configs.

## Usage

```bash
dot-man template set <key> <value>
dot-man template get <key>
dot-man template list
dot-man template system
```

## Subcommands

### template set

Set a template variable:

```bash
dot-man template set EMAIL user@example.com
dot-man template set HOSTNAME work-laptop
```

### template get

Get a template variable value:

```bash
dot-man template get EMAIL
```

### template list

List all custom template variables:

```bash
dot-man template list
```

### template system

Show auto-detected system variables:

```bash
dot-man template system
```

## System Variables

These are auto-populated:

| Variable | Description |
|----------|-------------|
| `{{HOSTNAME}}` | System hostname |
| `{{USER}}` | Current username |
| `{{SHELL}}` | Default shell |
| `{{OS}}` | Operating system |
| `{{ARCH}}` | CPU architecture |

## Usage in Config Files

Use `{{VARIABLE}}` placeholders in your dotfiles:

```gitconfig
[user]
    email = {{EMAIL}}
    name  = {{USER}}
```

Variables are substituted during deploy.

## Examples

```bash
# Set custom variables
dot-man template set EMAIL john@work.com
dot-man template set EDITOR nvim

# See what's available
dot-man template list
dot-man template system
```
