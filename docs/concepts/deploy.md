# Deploy Methods

dot-man supports two methods for deploying files from the repository to your system.

## Copy (Default)

Files are physically copied from the repo to your home directory.

```toml
[main]
deploy_method = "copy"
```

**Pros:**
- Files are independent — editing deployed files doesn't affect the repo
- Works with any application (no broken symlink issues)
- Atomic writes (POSIX `os.replace`) prevent corruption

**Cons:**
- Changes to deployed files are not reflected in the repo
- Must `save` to capture changes

## Symlink

Files are symlinked from the repo to your home directory.

```toml
[main]
deploy_method = "symlink"
```

**Pros:**
- Changes to files are immediately reflected in the repo
- No need to `save` after editing

**Cons:**
- Breaking the symlink breaks the file
- Some apps don't work well with symlinks
- Must keep the repo path stable

## Per-Section

Each section can use a different method:

```toml
[main]
deploy_method = "copy"

[symlinked]
deploy_method = "symlink"
paths = ["~/.config/nvim/", "~/.config/tmux/"]
```

## Comparison

| | Copy | Symlink |
|---|------|---------|
| **Default** | Yes | No |
| **File independence** | Yes | No |
| **Auto-sync** | No | Yes |
| **Breakability** | Low | Higher |
| **Recommended for** | Most configs | Quick iteration |
