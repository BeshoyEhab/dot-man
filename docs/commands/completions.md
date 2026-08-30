# completions

Install and manage shell completions.

## Usage

```bash
dot-man completions install
dot-man completions install --shell fish
dot-man completions status
```

## Options

| Flag | Description |
|------|-------------|
| `--shell`, `-s` | Shell to install for (bash, zsh, fish, all) |
| `--status` | Show installation status |

## Supported Shells

| Shell | Config Location |
|-------|-----------------|
| bash | `~/.bashrc` or `~/.bash_completion` |
| zsh | `~/.zshrc` or `~/.zfunc/_dot-man` |
| fish | `~/.config/fish/completions/dot-man.fish` |

## How It Works

Completions use a decorator-driven engine that stays in sync with the CLI. The fish completion script delegates every TAB press to `dot-man --complete fish`, so completions never go stale.

## Examples

```bash
# Install for current shell
dot-man completions install

# Install for fish specifically
dot-man completions install --shell fish

# Check status
dot-man completions status
```
