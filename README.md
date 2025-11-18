# **dot-man: Simplified Command Specifications**

## **1. Project Overview**

A Python CLI tool for managing dotfiles with git versioning, secret filtering, and multi-machine sync.

**Team:** 3 developers | **Timeline:** 8-10 weeks | **Complexity:** Medium

---

## **2. Command Structure**

```
dot-man
├── init                    # Initialize repository
├── switch <branch>        # Switch configurations
├── status                 # Show current state
├── sync                   # Push/pull with remote
├── edit                   # Edit configuration
├── deploy <branch>        # One-way deployment
├── audit                  # Scan for secrets
├── doctor                 # Health diagnostics
├── template               # Manage variables
├── branch
│   ├── list              # List branches
│   └── delete <branch>   # Delete branch
├── remote
│   ├── get               # Show remote URL
│   └── set <url>         # Configure remote
├── backup
│   ├── create            # Create backup
│   ├── list              # List backups
│   └── restore <name>    # Restore backup
└── conflicts
    ├── list              # List conflicts
    └── resolve <file>    # Resolve conflict
```

---

## **3. Core Commands**

### **3.1 `init`** - Initialize Repository

**Purpose:** First-time setup of dot-man

**Process:**
1. Create `~/.config/dot-man/` structure
2. Initialize git repository
3. Create default `global.conf` and `dot-man.ini`
4. Make initial commit

**Default dot-man.ini:**
```ini
[DEFAULT]
secrets_filter = true
update_strategy = replace

# Example configuration - uncomment and modify
# [~/.bashrc]
# local_path = ~/.bashrc
# # repo_path is optional - defaults to "bashrc"
# secrets_filter = false
#
# [~/.config/nvim/]
# local_path = ~/.config/nvim/
# # repo_path defaults to "nvim"
# # Or specify custom: repo_path = editors/nvim
```

**Exit codes:** 0=success, 1=already exists, 2=git missing, 3=permission error

---

### **3.2 `switch <branch>`** - Switch Configurations

**Purpose:** Save current state and deploy target branch

**Options:** `--dry-run`, `--force`, `--no-backup`

**Process:**

**Phase 1: Save Current Branch**
1. Load current branch config from `dot-man.ini`
2. For each section:
   - Extract `local_path` (e.g., `~/.bashrc`)
   - Extract or generate `repo_path`:
     - If specified: use as-is (e.g., `git/config-work`)
     - If omitted: extract final path component (e.g., `~/.bashrc` → `bashrc`)
   - Resolve full paths using `pathlib`
3. Copy local files → repo (with secret filtering if enabled)
4. Detect changes (NEW/MODIFIED/DELETED)
5. Commit changes with auto-save message
6. Create safety backup

**repo_path Auto-generation:**
```python
# Examples:
~/.bashrc           → bashrc
~/.config/nvim/     → nvim
~/.ssh/config       → config
/etc/hosts          → hosts
~/.gitconfig        → gitconfig
```

**Phase 2: Switch Branch**
7. Checkout target branch (create if doesn't exist)
8. Reload new branch's `dot-man.ini`

**Phase 3: Deploy New Files**
9. Apply update strategy per file:
   - **replace:** Delete old, copy new
   - **rename_old:** Keep old as `.old`, deploy new
   - **ignore:** Skip deployment
10. Apply template substitutions ({{VAR}} → value)
11. Update `global.conf` with new branch

**Secret Filtering:**
- Redact patterns: `API_KEY=...`, `password=...`, private keys
- If `strict_mode=true`: Abort if secrets detected

**Exit codes:** 0=success, 5=git error, 6=file error, 10=secrets detected

---

### **3.3 `status`** - Show Current State

**Purpose:** Display repository status and pending changes

**Options:** `-v` (verbose), `--secrets`, `--remote`

**Shows:**
- Current branch and last switch time
- Remote sync status
- File changes (NEW/MODIFIED/DELETED/IDENTICAL)
- Secret detection warnings
- What would happen on next `switch`

**Output example:**
```
Repository Status
─────────────────────────────────────
Current Branch:    main
Last Switch:       2025-11-15 09:30
Remote:            synced
Local Changes:     3 modified, 1 new

Tracked Files Status
─────────────────────────────────────
~/.bashrc          MODIFIED      +5 -2 lines
~/.vimrc           IDENTICAL     
~/.gitconfig       MODIFIED 🔒   Secret detected
~/.zshrc           DELETED       
```

**Exit codes:** 0=success, 1=not initialized, 7=config error

---

### **3.4 `sync`** - Remote Synchronization

**Purpose:** Push/pull changes with remote repository

**Options:** `--force-pull`, `--force-push`, `--continue`, `--dry-run`

**Standard Process:**
1. Save local changes first
2. Fetch from remote
3. Merge (fast-forward if possible)
4. Handle conflicts if any
5. Push local commits
6. Deploy merged files

**Force Pull:** Discard local changes, pull from remote
**Force Push:** Overwrite remote with local changes

**Conflict Handling:**
- Detect conflicted files
- Show resolution options
- Use `dot-man conflicts` commands to resolve
- Continue with `--continue` after fixing

**Exit codes:** 0=success, 15=network error, 20=conflicts, 21=push rejected

---

### **3.5 `edit`** - Edit Configuration

**Purpose:** Open `dot-man.ini` in text editor

**Options:** `--editor <name>`, `--global`, `--validate`

**Process:**
1. Select editor (flag > VISUAL > EDITOR > nano)
2. Create backup of config
3. Open in editor
4. Validate syntax after editing
5. Show errors or confirm success

**Validates:**
- INI syntax correctness
- Required field `local_path` present
- Optional field `repo_path` (defaults to filename if omitted)
- Valid update strategies
- Resolvable paths

**Exit codes:** 0=success, 30=validation failed, 31=editor not found

---

### **3.6 `deploy <branch>`** - One-Way Deployment

**Purpose:** Bootstrap new machine or recover from corruption

**Options:** `--force`, `--dry-run`, `--strategy <name>`

**Warning:** Destructive operation - overwrites local files without saving

**Process:**
1. Show warning, require confirmation
2. Checkout target branch
3. Load config and generate repo_paths where needed
4. Verify all repo files exist
5. Deploy files (ignoring update_strategy by default)
6. Apply template substitutions
7. Update global config

**Use cases:** New machine setup, recovery from corruption

**Exit codes:** 0=success, 40=failed, 41=no disk space, 43=cancelled

---

### **3.7 `audit`** - Security Scan

**Purpose:** Find accidentally committed secrets

**Options:** `--strict`, `--fix`, `--patterns <file>`, `--exclude <pattern>`

**Detects:**
- API keys, tokens, passwords
- Private keys (SSH, TLS)
- AWS credentials
- GitHub tokens
- JWT tokens

**Severity Levels:**
- CRITICAL: Private keys, AWS credentials
- HIGH: API tokens, plaintext passwords
- MEDIUM: Potential tokens (ambiguous)
- LOW: Suspicious patterns

**Output example:**
```
🔒 Security Audit Results
─────────────────────────────────────
CRITICAL (2 findings):
File: .ssh/config
Line 15: -----BEGIN RSA PRIVATE KEY-----

File: .env
Line 3: AWS_SECRET_ACCESS_KEY=wJalr...

Recommendations:
1. Enable secrets_filter for affected files
2. Move credentials to environment variables
3. Rotate compromised credentials immediately
```

**Modes:**
- `--strict`: Exit with error if ANY secrets found (CI/CD)
- `--fix`: Auto-redact found secrets and commit

**Exit codes:** 0=no secrets, 50=secrets found (strict), 52=fix failed

---

### **3.8 `doctor`** - Health Diagnostics

**Purpose:** Detect and fix common issues

**Options:** `--fix`, `-v` (verbose), `--check <category>`

**Checks:**
1. Repository initialized and valid
2. Git repository integrity
3. Configuration file validity
4. Current branch state
5. Remote connectivity
6. File system permissions
7. Secret detection
8. Disk space
9. Dependencies (Python, git)
10. Backup status

**Output:**
```
dot-man Health Check Report
───────────────────────────────────
✓ Repository initialized
✓ Git repository valid
✓ Configuration valid (8 sections)
⚠ Uncommitted changes (3 files)
✓ Remote configured and reachable
⚠ 2 files missing locally
✓ Sufficient disk space (12 GB)
✓ All dependencies satisfied

Summary: 7 passed, 2 warnings, 0 errors

Recommended Actions:
1. Commit or revert uncommitted changes
2. Review missing files: dot-man status
```

**Exit codes:** 0=passed, 60-64=specific errors

---

### **3.9 `template`** - Variable Management

**Purpose:** Manage machine-specific template variables

**Options:** `--set KEY=VALUE`, `--unset KEY`, `--list`, `--apply`

**Concept:** Replace `{{VARIABLE}}` in configs with actual values

**Example workflow:**
```bash
# On work laptop
dot-man template --set EMAIL=john@work.com --set HOST=work-laptop
dot-man switch work
# Files now have actual values, not {{EMAIL}}

# On personal laptop
dot-man template --set EMAIL=john@personal.com --set HOST=home-pc
dot-man switch personal
# Same templates, different values
```

**Usage in configs:**
```ini
[~/.gitconfig]
local_path = ~/.gitconfig
# repo_path defaults to "gitconfig"
template_vars = EMAIL, USERNAME
```

**Storage:** `~/.config/dot-man/template_vars.json`

**Exit codes:** 0=success, 70=invalid name, 71=file corrupted

---

## **4. Supporting Commands**

### **`branch list`** - List All Branches
Shows all branches with active indicator and metadata

### **`branch delete <branch>`** - Delete Branch
Removes branch after safety checks and confirmation

### **`remote get/set`** - Remote Configuration
View or configure git remote URL

### **`backup create/list/restore`** - Backup Management
- Create manual backups
- List existing backups with metadata
- Restore from backup (with warning)
- Auto-backup before risky operations (max 5 kept)

### **`conflicts list/resolve`** - Conflict Resolution
- List files with merge conflicts
- Resolve with `--ours`, `--theirs`, or manual edit
- Continue sync after resolution

---

## **5. Configuration Files**

### **`global.conf`** - System Configuration
```ini
[dot-man]
current_branch = main
initialized_date = 2025-11-16
version = 1.0.0

[remote]
url = git@github.com:user/dotfiles.git
auto_sync = false

[security]
secrets_filter = true
strict_mode = false
```

### **`dot-man.ini`** - Dotfiles Configuration
```ini
[DEFAULT]
secrets_filter = true
update_strategy = replace

# Simple example - repo_path auto-generated
[~/.bashrc]
local_path = ~/.bashrc
# repo_path = bashrc (auto-generated)
secrets_filter = false

# Custom repo organization
[~/.ssh/config]
local_path = ~/.ssh/config
repo_path = ssh/config           # Explicit custom path
secrets_filter = true
update_strategy = rename_old

# Directory example
[~/.config/nvim/]
local_path = ~/.config/nvim/
# repo_path = nvim (auto-generated)
# Or custom: repo_path = editors/nvim
update_strategy = replace

# Branch-specific config
[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = git/config-work      # Different per branch
template_vars = EMAIL, USERNAME
```

### **repo_path Auto-generation Logic**

**Rule:** Extract the final component of `local_path`

```python
from pathlib import Path

def get_repo_path(local_path, config_repo_path=None):
    """
    Get repository path - use explicit value or auto-generate.
    
    Args:
        local_path: The local file/directory path
        config_repo_path: Explicit repo_path from config (optional)
    
    Returns:
        The path to use in repository
    """
    if config_repo_path:
        return config_repo_path
    
    # Auto-generate from local_path
    path = Path(local_path).expanduser()
    return path.name  # Just the final component

# Examples:
# ~/.bashrc           → bashrc
# ~/.config/nvim/     → nvim
# ~/.ssh/config       → config
# /etc/hosts          → hosts
# ~/.local/bin/script → script
```

**Benefits:**
- ✅ Less typing for 90% of configs
- ✅ Clear, predictable behavior
- ✅ Still allows custom organization when needed
- ✅ Repository stays clean (no `.bashrc`, just `bashrc`)

**When to specify explicit `repo_path`:**
- Custom organization: `repo_path = editors/nvim`
- Branch-specific: `repo_path = git/config-work` vs `git/config-personal`
- Avoiding name conflicts: Multiple configs with same filename
- Grouping by category: `terminals/alacritty.yml`, `terminals/kitty.conf`

---

## **6. Implementation Timeline**

### **Phase 1: Foundation (Weeks 1-3)**
- Project setup, config parsing, file operations, git integration
- Implement repo_path auto-generation logic

### **Phase 2: Core Commands (Weeks 4-5)**
- `init`, `switch`, `status`, `branch`, `edit`, `deploy`
- Test with both explicit and auto-generated repo_paths

### **Phase 3: Security (Week 6)**
- Secret detection, `audit` command, filtering integration

### **Phase 4: Sync (Week 7)**
- `sync`, `conflicts`, `remote` commands

### **Phase 5: Advanced (Week 8)**
- `backup`, `template`, `doctor` commands

### **Phase 6: Polish (Weeks 9-10)**
- Testing (80%+ coverage), documentation, release

---

## **7. Success Criteria**

**Functional:**
- ✅ Initialize and switch branches without data loss
- ✅ Auto-generate repo_path correctly
- ✅ Detect and redact all critical secret types
- ✅ Sync reliably with remote
- ✅ Automatic backups before risky operations

**Quality:**
- 80%+ test coverage
- Clear error messages
- <5 critical bugs at release
- Complete documentation

**Performance:**
- Handle 100+ files in <5 seconds
- New user setup in <5 minutes

---

## **8. Key Features Summary**

| Feature | Description |
|---------|-------------|
| **Branch-based** | Different configs for work/personal/minimal |
| **Auto repo_path** | Smart defaults - just specify `local_path` |
| **Secret filtering** | Auto-redact sensitive data before commit |
| **Remote sync** | Push/pull with conflict resolution |
| **Templates** | Machine-specific variable substitution |
| **Backups** | Auto-backup before destructive operations |
| **Diagnostics** | Health checks with auto-fix |
| **Safe operations** | Warnings and dry-run for all changes |

---

## **9. Example Configurations**

### **Minimal Config (Most Common)**
```ini
[~/.bashrc]
local_path = ~/.bashrc

[~/.vimrc]
local_path = ~/.vimrc

[~/.config/nvim/]
local_path = ~/.config/nvim/
```
All repo_paths auto-generated: `bashrc`, `vimrc`, `nvim`

### **Organized Config (Power Users)**
```ini
[~/.bashrc]
local_path = ~/.bashrc
repo_path = shell/bashrc

[~/.zshrc]
local_path = ~/.zshrc
repo_path = shell/zshrc

[~/.config/nvim/]
local_path = ~/.config/nvim/
repo_path = editors/nvim

[~/.config/alacritty/alacritty.yml]
local_path = ~/.config/alacritty/alacritty.yml
repo_path = terminals/alacritty.yml
```

### **Branch-Specific Configs**
```ini
# In "work" branch
[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = git/config-work
template_vars = EMAIL

# In "personal" branch
[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = git/config-personal
template_vars = EMAIL
```

### **Reorganizing Your Repository**

When you change `repo_path` values via `dot-man edit`, files are automatically moved:

```bash
# Step 1: Edit config
dot-man edit

# Step 2: Change repo_paths
# Before:
[~/.bashrc]
local_path = ~/.bashrc
# repo_path = bashrc (auto)

# After:
[~/.bashrc]
local_path = ~/.bashrc
repo_path = shell/bashrc

# Step 3: dot-man auto-detects and moves files
✓ Moved: bashrc → shell/bashrc
✓ Committed changes automatically

# Your repository structure is now updated!
```

**Benefits of repo reorganization:**
- Group related configs: `shell/`, `editors/`, `terminals/`
- Flatten nested structures: `~/.config/nvim/` → `nvim`
- Branch-specific files: `git/config-work`, `git/config-personal`
- No manual file moving needed - dot-man handles it!

---

**Ready to build! 🚀**
