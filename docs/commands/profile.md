# profile

Manage machine profiles for auto-switching branches.

## Usage

```bash
dot-man profile create <name>
dot-man profile list
dot-man profile switch <name>
dot-man profile detect
```

## Subcommands

### profile create

Create a new profile:

```bash
dot-man profile create work-laptop -h work-laptop -h thinkpad
```

### profile list

List all profiles:

```bash
dot-man profile list
```

### profile switch

Switch to a profile:

```bash
dot-man profile switch work-laptop
```

### profile detect

Auto-detect the current machine's profile:

```bash
dot-man profile detect
```

## Configuration

Profiles are stored in `~/.config/dot-man/global.toml`:

```toml
[profiles.work-laptop]
hostnames = ["work-laptop", "thinkpad"]
branch = "work"

[profiles.personal]
hostnames = ["home-pc", "macbook"]
branch = "main"
```

## Examples

```bash
# Create profiles for different machines
dot-man profile create work -h office-pc -h work-laptop
dot-man profile create personal -h home-pc

# Set branch for each profile
dot-man profile set-branch work work
dot-man profile set-branch personal main

# Auto-detect and switch
dot-man profile detect
```
