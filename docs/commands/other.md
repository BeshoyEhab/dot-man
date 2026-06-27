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
dot-man log
dot-man log --limit 10
dot-man log --oneline
```

## tag

Create and manage tag snapshots for rollback.

```bash
dot-man tag create v1.0         # Tag current state
dot-man tag list                # List all tags
dot-man tag delete v1.0         # Delete a tag
dot-man navigate main --tag v1.0  # Deploy a tag snapshot
```

## remote

Configure remote sync.

```bash
dot-man remote add origin https://github.com/user/dotfiles.git
dot-man remote list
```

## sync

Push/pull to remote.

```bash
dot-man sync push
dot-man sync pull
```

## discover

Auto-discover common dotfile locations.

```bash
dot-man discover
dot-man discover --preview     # Show without adding
```

## hooks

Manage deploy hooks.

```bash
dot-man hooks list
dot-man hooks run pre-deploy
```

## template

Show template variable values.

```bash
dot-man template              # All variables
dot-man template MACHINE     # Specific variable
```

## completions

Install shell completions.

```bash
dot-man completions install
dot-man completions status
```

## watch

Watch for file changes and auto-save.

```bash
dot-man watch
dot-man watch --interval 30
```

## interface

Manage CLI interface mode (standard vs enhanced).

```bash
dot-man interface
dot-man interface standard
```

## migrate

Migrate from other dotfile managers.

```bash
dot-man migrate chezmoi
dot-man migrate yadm
dot-man migrate stow
```
