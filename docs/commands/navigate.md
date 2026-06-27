# navigate

Switch between branch profiles. This is the primary command for managing different configurations.

## Usage

```bash
dot-man navigate <branch>
dot-man nav <branch>          # alias
```

## Behavior

When you navigate to a branch, dot-man:

1. **Auto-saves** current changes (unless `--no-save`)
2. **Switches** the git branch
3. **Deploys** files from the new branch to your system
4. **Runs hooks** (`on_activate`, `on_deactivate`)
5. **Updates** the config to track the new active branch

## Options

| Flag | Description |
|------|-------------|
| `--no-save` | Skip auto-save before switching |
| `--no-deploy` | Switch branch without deploying files |
| `--no-hooks` | Skip running hook scripts |
| `--dry-run` | Preview changes without applying |

## Examples

```bash
# Switch to work profile
dot-man navigate work

# Preview what would change
dot-man navigate personal --dry-run

# Switch without saving current changes
dot-man navigate server --no-save
```

## Branch Diff Preview

With `--dry-run`, navigate shows a preview of:

- Files that would be saved from current branch
- Files that would be deployed from target branch
- Hooks that would run
- Summary of changes by section
