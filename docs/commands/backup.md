# backup

Create and restore manual backups.

## Usage

```bash
dot-man backup create
dot-man backup list
dot-man backup restore <id>
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

### backup restore

Restore from a backup:

```bash
dot-man backup restore <backup-id>
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
dot-man backup restore 2024-01-15_12-00-00
```
