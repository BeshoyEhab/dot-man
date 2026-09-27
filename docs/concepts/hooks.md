# Hooks

dot-man has two hook kinds, resolved and executed by one engine
(`dot_man/hook_engine.py`):

1. **Section hooks** — strings in `dot-man.toml` that run at specific
   points during save and deploy:
2. **Global scripts** — executable files named `pre_<cmd>` / `post_<cmd>`
   in a hooks directory, run around a command.

| Hook | When It Runs |
|------|--------------|
| `pre_deploy` | Before files are copied/symlinked |
| `post_deploy` | After files are copied/symlinked |
| `on_activate` | When branch is switched to |
| `on_deactivate` | When branch is switched from |

```toml
[main]
on_activate = "source ~/.bashrc"
on_deactivate = "echo 'Leaving main config'"

[work]
pre_deploy = "systemctl --user stop neovim"
post_deploy = "systemctl --user start neovim"
on_activate = "source ~/.config/work/env.sh"
```

Global `pre_<cmd>` / `post_<cmd>` scripts currently fire for
`switch`/`checkout` only — firing them in more commands
(`deploy`, `save`, `add`, …) is a tracked follow-up.

## Resolution pipeline

Every section hook string resolves in one fixed order —
**alias → `{x}` placeholders → `file:` tokens**:

1. **Alias lookup** — if the whole value matches a built-in alias
   (e.g. `quickshell_reload`, see table below), it expands first.
2. **`{x}` placeholders** — names from the vocabulary table are
   substituted from the hook's context.
3. **`file:` tokens** — `file:<script> [args]` tokens resolve to
   executable script paths (see below).

Resolve-time problems (missing script, path escaping the hooks folder)
raise `ConfigurationError`. Placeholders with no value in the current
context (e.g. an auto-detected hook with no matched section) pass
through literally — never an error.

## Placeholder vocabulary

| Placeholder | Value |
|-------------|-------|
| `{section_name}` | Section name from `dot-man.toml` |
| `{config_name}` | Config name (e.g. `ii` for quickshell) |
| `{config_root}` | Config root directory |
| `{paths}` | Space-joined tracked paths |
| `{branch}` | Active branch name |

`{qs_config}` remains as the deprecated spelling of `{config_name}`.

```toml
[quickshell-ii]
paths = ["~/.config/quickshell/ii"]
post_deploy = "quickshell_reload"
on_activate = "qs -c {config_name} &"
```

Within hooks, the `$DOT_MAN_BRANCH` shell variable also contains the
active branch name:

```bash
on_activate = "echo \"Switched to $DOT_MAN_BRANCH config\""
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
args pass through untouched; `{x}` in the whole string (including args)
resolves in the earlier placeholder step.
A missing script fails the hook with a `ConfigurationError` naming the
script and both searched folders. Scripts gain the exec bit
automatically, and `../` escapes outside the hooks folder are rejected.

To render the literal text `file:<name>` without resolving it, escape
it with a backslash — `\file:<name>` renders as `file:<name>`
(backslash consumed; in TOML basic strings write `"\\file:x"`):

```toml
[work]
post_deploy = "echo 'see \\file:notes.txt for details'"
```

## Failure semantics

Hook shell never fails fast. A hook command that exits nonzero (or
fails to launch) prints a warning — including the exit code and the
first lines of stderr — and execution continues with the next hook.
The runner reports whether any hook failed so callers can note it;
deploy hooks that fail now print the same warning navigate prints,
instead of failing silently.
