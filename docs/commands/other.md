# Other Commands

## diff

Show uncommitted changes in tracked files.

```bash
dot-man diff
dot-man diff --branch work    # Compare with another branch
```

## log

Show commit history for the current branch.

```bash
dot-man log          # recent commits
dot-man log -n 10    # last ten
```

## tag

Create and manage tag snapshots for rollback.

```bash
dot-man tag create v1.0   # snapshot before risky changes
dot-man tag list          # see restore points
dot-man tag delete v1.0   # drop one
```

## remote

Configure remote sync.

```bash
dot-man remote get   # show configured URL
dot-man sync         # push and pull
```

## sync

Push/pull to remote.

```bash
dot-man sync               # both directions
dot-man sync --push-only   # push without pulling
```

## discover

Auto-discover common dotfile locations.

```bash
dot-man discover         # list what it finds
dot-man discover --add   # track everything found
```

## hooks

Manage deploy hooks.

```bash
dot-man hooks list               # see all hook slots
dot-man hooks create post deploy # scaffold a script
```

## template

Show template variable values.

```bash
dot-man template list         # all variables
dot-man template get HOSTNAME # one value
```

## completions

Install shell completions.

```bash
dot-man completions --shell fish
```

## watch

Watch for file changes and auto-save.

```bash
dot-man watch                     # auto-save on change
dot-man watch --interval 30       # poll every 30s
```

## help

Show the happy-path commands for everyday use (`init`, `add`, `status`,
`navigate`, `deploy`, `doctor`). Bare `dot-man --help` shows the same
short listing.

```bash
dot-man help                 # happy-path commands
dot-man help-all             # every command, incl. aliases
dot-man help --install-man   # install dot-man.1 to ~/.local/share/man
```
