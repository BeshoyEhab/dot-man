# tag

Create and manage tag snapshots for fast rollback.

## Usage

```bash
dot-man tag create <name>
dot-man tag list
dot-man tag delete <name>
dot-man tag show <name>
```

## Subcommands

### tag create

Create a tag at the current commit:

```bash
dot-man tag create v1.0
dot-man tag create work-2024-01
```

### tag list

List all tags with their commit info:

```bash
dot-man tag list
dot-man tag list --verbose
```

### tag delete

Delete a tag:

```bash
dot-man tag delete v1.0
```

### tag show

Show details for a tag:

```bash
dot-man tag show v1.0
```

## Navigation to Tags

Navigate to a tagged snapshot:

```bash
dot-man navigate v1.0
dot-man navigate main@v1.0
```

## Examples

```bash
# Create a snapshot before major changes
dot-man tag create before-refactor

# Make changes...
dot-man add ~/.config/nvim
dot-man save "updated nvim config"

# Roll back if needed
dot-man navigate before-refactor
```
