# backup

Create and restore manual backups.

## Example

```bash
dot-man backup create    # snapshot before risky changes
dot-man backup list      # find the snapshot id
```

## Usage

```bash
dot-man backup create
dot-man backup list
dot-man rollback --backup <id>   # restores a snapshot (replaces backup restore)
```

## Subcommands

### backup create

Create a manual backup:

```bash
dot-man backup create
dot-man backup create --message "Before major changes"
```

### backup list

List available backups:

```bash
dot-man backup list
```

### backup restore (deprecated)

!!! warning "Deprecated"
    `dot-man backup restore <id>` is renamed to
    `dot-man rollback --backup <id>` and will be removed in v2.0. The old
    command still works, prints a warning, and forwards to the new one.

```bash
dot-man rollback --backup <backup-id>
```

## Configuration

Backup settings in `~/.config/dot-man/global.toml`:

```toml
[backup]
max_backups = 5
```

## Examples

```bash
# Create a backup
dot-man backup create

# List backups
dot-man backup list

# Restore a specific backup
dot-man rollback --backup 2024-01-15_12-00-00
```
