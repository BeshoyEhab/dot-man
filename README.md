# dot-man: Development Specification

## Project Overview

**Goal:** Python CLI tool for dotfiles management with git versioning, secret filtering, and multi-machine sync.

**Team:** 3 developers  
**Timeline:** 8-10 weeks  
**Tech Stack:** Python 3.8+, Click, GitPython, Rich, configparser

---

## Command Structure

```
dot-man
├── init
├── switch <branch>
├── status
├── sync
├── edit
├── deploy <branch>
├── audit
├── doctor
├── template [--set/--unset/--list/--apply]
├── branch [list/delete <branch>]
├── remote [get/set <url>]
├── backup [create/list/restore <name>]
└── conflicts [list/resolve <file>]
```

---

## Core Commands

### 1. init

**Purpose:** Initialize dot-man repository structure

**Implementation Requirements:**
- Create `~/.config/dot-man/{repo,backups}/`
- Initialize git repo in `repo/`
- Generate default `global.conf` and `dot-man.ini`
- Make initial commit
- Set permissions (0700 for security)

**Exit Codes:** 0=success, 1=exists, 2=no git, 3=permission denied

---

### 2. switch <branch>

**Purpose:** Save current state → switch branch → deploy new state

**Three Phases:**

**Phase 1 - Save Current:**
- Parse `dot-man.ini` sections
- For each section:
  - Extract `local_path` (required)
  - Extract or auto-generate `repo_path` (optional, defaults to filename)
  - Copy `local_path` → `repo/<repo_path>`
  - Apply secret filtering if `secrets_filter=true`
- Detect changes (NEW/MODIFIED/DELETED/IDENTICAL)
- Git commit with message: `Auto-save from '<branch>' before switch`
- Create backup (unless `--no-backup`)

**Phase 2 - Switch:**
- `git checkout <branch>` (create if doesn't exist)
- Reload `dot-man.ini` from new branch

**Phase 3 - Deploy:**
- For each section in new config:
  - Apply `update_strategy`:
    - `replace` - overwrite (default)
    - `rename_old` - backup as `.old`, then copy
    - `ignore` - skip
  - Replace template variables: `{{VAR}}` → actual value
- Update `global.conf` current_branch

**repo_path Auto-generation:**
```python
# If repo_path not specified in config:
~/.bashrc        → bashrc
~/.config/nvim/  → nvim
~/.ssh/config    → config
```

**Secret Filtering Patterns:**
- `API_KEY=`, `password=`, `token=`
- `-----BEGIN PRIVATE KEY-----`
- `AKIA[0-9A-Z]{16}` (AWS)
- `ghp_[a-zA-Z0-9]{36}` (GitHub)

**Options:** `--dry-run`, `--force`, `--no-backup`

**Exit Codes:** 0=success, 5=git error, 6=file error, 10=secrets detected (strict mode)

---

### 3. status

**Purpose:** Show current state and pending changes

**Display:**
1. Repository info (branch, last switch, remote status)
2. File status table:
   - NEW: local exists, repo doesn't
   - MODIFIED: content differs
   - DELETED: repo exists, local doesn't
   - IDENTICAL: no changes
3. Secret warnings (if `--secrets`)
4. Actionable next steps

**Implementation:**
- Compare each `local_path` vs `repo_path` byte-by-byte
- Calculate line diffs for MODIFIED files
- Run secret detection patterns on NEW/MODIFIED
- Query git remote status (if `--remote`)

**Options:** `-v` (verbose with diffs), `--secrets`, `--remote`

**Exit Codes:** 0=success, 1=not initialized, 7=config error

---

### 4. sync

**Purpose:** Bidirectional sync with remote git repository

**Standard Flow:**
1. Save local changes (Phase 1 of switch)
2. `git fetch origin`
3. Merge logic:
   - Fast-forward if possible
   - Three-way merge if diverged
   - Detect conflicts if any
4. `git push origin <branch>`
5. Deploy merged files (Phase 3 of switch)

**Force Operations:**

**--force-pull:**
- Warning prompt (destructive)
- Create backup
- `git reset --hard origin/<branch>`
- Deploy remote files

**--force-push:**
- Warning prompt (destructive)
- `git push --force origin <branch>`

**Conflict Handling:**
- Parse `git status --porcelain` for 'U' (unmerged)
- Display table of conflicts
- Exit with code 20
- User resolves via `conflicts` commands
- Resume with `--continue`

**Options:** `--dry-run`, `--force-pull`, `--force-push`, `--continue`

**Exit Codes:** 0=success, 15=network, 16=no remote, 20=conflicts, 21=push rejected

---

### 5. edit

**Purpose:** Edit config with validation and automatic repo reorganization

**Flow:**
1. Select editor (flag → VISUAL → EDITOR → nano)
2. Backup current config (`.pre-edit`)
3. Store snapshot of current `repo_path` values
4. Open editor, wait for close
5. Validate INI syntax
6. **Detect repo_path changes:**
   - Compare old vs new `repo_path` for each section
   - If changed: `git mv old_path new_path`
   - Auto-commit: "Reorganized repository structure via edit"
7. Delete backup if valid

**repo_path Change Detection:**
```python
for section in config:
    old_repo = old_config[section].get('repo_path', auto_generate())
    new_repo = new_config[section].get('repo_path', auto_generate())
    
    if old_repo != new_repo:
        if repo_file_exists(old_repo):
            git_mv(old_repo, new_repo)
        else:
            warn(f"{old_repo} doesn't exist (created on next switch)")
```

**Validation:**
- INI syntax correct
- Each section has `local_path`
- `repo_path` valid (no `..`, no absolute paths)
- `update_strategy` in [replace, rename_old, ignore]
- No duplicate `repo_path` values

**Edge Cases:**
- Source doesn't exist: warn, skip move
- Destination exists: prompt to overwrite
- Multiple sections → same repo_path: error
- Move fails: rollback with `git reset --hard`

**Options:** `--editor`, `--global`, `--validate`

**Exit Codes:** 0=success, 30=validation failed, 31=no editor, 32=move failed

---

### 6. deploy <branch>

**Purpose:** One-way deployment (no save first) - for bootstrapping

**Flow:**
1. Warning prompt (destructive operation)
2. `git checkout <branch>`
3. Load `dot-man.ini`
4. Check disk space
5. Deploy all files (ignore `update_strategy`, always replace unless `--strategy` flag)
6. Apply templates
7. Update `global.conf`

**Use Case:** New machine setup, recovery from corruption

**Options:** `--dry-run`, `--force`, `--strategy`

**Exit Codes:** 0=success, 40=failed, 41=no space, 43=cancelled

---

### 7. audit

**Purpose:** Scan repository for secrets

**Detection Patterns:**
| Type | Pattern | Severity |
|------|---------|----------|
| API Keys | `api_key=`, `API_KEY=` | HIGH |
| Passwords | `password=`, `passwd=` | HIGH |
| Private Keys | `-----BEGIN.*PRIVATE KEY-----` | CRITICAL |
| AWS | `AKIA[0-9A-Z]{16}` | CRITICAL |
| GitHub | `ghp_[a-zA-Z0-9]{36}` | HIGH |
| JWT | `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+` | MEDIUM |

**Implementation:**
- Walk `repo/` directory (skip `.git/`)
- Apply regex patterns to each line
- Skip binary files
- Categorize by severity
- Record: (file, line, pattern, context)

**Modes:**
- Normal: Display findings, exit 0
- `--strict`: Exit 50 if ANY secrets found (CI/CD)
- `--fix`: Auto-redact secrets, commit changes

**Redaction:** Replace matched text with `***REDACTED***`

**Options:** `--strict`, `--fix`, `--patterns <file>`, `--exclude <pattern>`

**Exit Codes:** 0=clean, 50=secrets (strict), 52=fix failed

---

### 8. doctor

**Purpose:** Health diagnostics with auto-fix

**10 Checks:**
1. Repository initialized (`~/.config/dot-man/` exists)
2. Git valid (`.git/` intact, HEAD valid)
3. Config valid (INI parseable, required fields)
4. Branch state (matches global.conf, no detached HEAD)
5. Remote connectivity (`git ls-remote`)
6. File permissions (readable/writable)
7. Secret detection (quick scan)
8. Disk space (>500MB available)
9. Dependencies (Python 3.8+, git installed)
10. Backup status (last backup age)

**Display:**
- ✓ Pass (green)
- ⚠ Warning (yellow)
- ✗ Error (red)

**Auto-Fix (--fix):**
- Fix permissions (chmod)
- Clean old backups
- Reset branch pointer
- Create missing directories

**Options:** `--fix`, `-v`, `--check <category>`

**Exit Codes:** 0=passed, 60-64=specific errors

---

### 9. template

**Purpose:** Manage machine-specific variables

**Storage:** `~/.config/dot-man/template_vars.json`

**Usage in config:**
```ini
[~/.gitconfig]
local_path = ~/.gitconfig
template_vars = EMAIL, USERNAME
```

**Substitution During Deployment:**
```
# In repo file:
email = {{EMAIL}}

# After deployment:
email = john@work.com
```

**Operations:**
- `--list` (default): Display all variables
- `--set KEY=VALUE`: Store variable
- `--unset KEY`: Remove variable
- `--apply`: Re-process deployed files with current variables

**Variable Validation:**
- Must be UPPERCASE
- Alphanumeric + underscore only
- Start with letter
- Max 50 characters

**Exit Codes:** 0=success, 70=invalid name, 71=file corrupted

---

### 10. branch list

**Purpose:** Display all branches

**Output:**
```
Branch          Active    Last Modified
main            *         2025-11-15 14:30
work                      2025-11-10 09:15
```

**Options:** `-v` (show file count, commits), `--remote` (include origin branches)

**Exit Codes:** 0=success

---

### 11. branch delete <branch>

**Purpose:** Delete branch

**Safety Checks:**
- Cannot delete active branch
- Check for unmerged commits
- Confirmation prompt (unless `--force`)

**Process:**
1. Verify branch exists and not current
2. `git branch -D <branch>`
3. If `--remote`: `git push origin --delete <branch>`

**Options:** `-f/--force`, `--remote`

**Exit Codes:** 0=success, 1=active branch, 2=not found, 80=unmerged

---

### 12. remote get

**Purpose:** Show configured remote

**Display:**
- URL, type (SSH/HTTPS), reachability status

**Exit Codes:** 0=success

---

### 13. remote set <url>

**Purpose:** Configure remote

**Validation:**
- Check URL format (SSH/HTTPS/local)
- Test connectivity (optional with `--test`)

**Process:**
1. Validate URL
2. If exists: prompt to replace (unless `--force`)
3. `git remote add/set-url origin <url>`
4. Update `global.conf`

**Options:** `--test`, `--force`

**Exit Codes:** 0=success, 91=invalid URL, 92=operation failed

---

### 14. backup create

**Purpose:** Manual backup

**Process:**
1. Create timestamped dir: `backup_YYYYMMDD_HHMMSS`
2. Copy `repo/` including `.git/`
3. Create `metadata.json` with timestamp, branch, size
4. Enforce limit (max 5 backups, delete oldest)

**Options:** `-m <message>`, `--full`

**Exit Codes:** 0=success, 100=no space, 101=failed

---

### 15. backup list

**Purpose:** List all backups

**Display Table:**
- Name, date, branch, size
- Sort by timestamp (newest first)

**Exit Codes:** 0=success

---

### 16. backup restore <name>

**Purpose:** Restore from backup

**Process:**
1. Load backup metadata
2. Warning prompt (destructive)
3. Create backup of current state
4. Remove `repo/`, copy backup → `repo/`
5. Update `global.conf`
6. Optional: deploy files

**Options:** `--force`, `--preview`

**Exit Codes:** 0=success, 102=not found, 103=corrupted, 104=failed

---

### 17. conflicts list

**Purpose:** Show merge conflicts

**Implementation:**
- Parse `git status --porcelain` for 'U' status
- Categorize: both modified, deleted by us/them, both added
- Show conflict markers excerpt

**Exit Codes:** 0=success, 1=no conflicts

---

### 18. conflicts resolve <file>

**Purpose:** Resolve specific conflict

**Modes:**
- `--ours`: `git checkout --ours <file>`, then `git add`
- `--theirs`: `git checkout --theirs <file>`, then `git add`
- `--edit`: Open in editor for manual resolution
- `--diff`: Show side-by-side comparison
- Interactive menu (default)

**Validation After Edit:**
- Check for remaining conflict markers
- Verify file syntax if possible

**Options:** `--ours`, `--theirs`, `--edit`, `--diff`

**Exit Codes:** 0=success, 111=editor failed, 112=invalid resolution

---

## Configuration Files

### global.conf
```ini
[dot-man]
current_branch = main
initialized_date = 2025-11-19
version = 1.0.0

[remote]
url = git@github.com:user/dotfiles.git
auto_sync = false

[security]
secrets_filter = true
strict_mode = false
```

### dot-man.ini
```ini
[DEFAULT]
secrets_filter = true
update_strategy = replace

[~/.bashrc]
local_path = ~/.bashrc
# repo_path auto-generated as "bashrc"
secrets_filter = false

[~/.config/nvim/]
local_path = ~/.config/nvim/
repo_path = editors/nvim  # custom organization
update_strategy = replace

[~/.gitconfig]
local_path = ~/.gitconfig
repo_path = git/config
template_vars = EMAIL, USERNAME
```

### template_vars.json
```json
{
  "EMAIL": "john@work.com",
  "USERNAME": "johndoe",
  "HOSTNAME": "work-laptop"
}
```

---

## Implementation Details

### repo_path Logic

```python
def get_repo_path(local_path: str, config_repo_path: Optional[str]) -> str:
    """
    Determine repository path.
    If config_repo_path specified: use it
    Else: extract filename from local_path
    """
    if config_repo_path:
        return config_repo_path
    
    from pathlib import Path
    return Path(local_path).expanduser().name
```

### Secret Filtering

```python
PATTERNS = [
    (r'(api_key|API_KEY)\s*=\s*["\']?([^"\'\s]+)', 'API_KEY'),
    (r'(password|passwd)\s*=\s*["\']([^"\']+)["\']', 'PASSWORD'),
    (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', 'PRIVATE_KEY'),
    (r'AKIA[0-9A-Z]{16}', 'AWS_KEY'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GITHUB_TOKEN'),
]

def filter_secrets(content: str, strict: bool = False) -> str:
    for pattern, name in PATTERNS:
        if re.search(pattern, content):
            if strict:
                raise SecretDetectedError(name)
            content = re.sub(pattern, '***REDACTED***', content)
    return content
```

### Template Substitution

```python
def apply_templates(content: str, variables: dict) -> str:
    """Replace {{VAR}} with actual values"""
    for key, value in variables.items():
        content = content.replace(f'{{{{{key}}}}}', value)
    return content
```

### Conflict Detection

```python
def detect_conflicts() -> List[str]:
    """Return list of conflicted files"""
    result = subprocess.run(
        ['git', 'status', '--porcelain'],
        capture_output=True, text=True
    )
    
    conflicts = []
    for line in result.stdout.splitlines():
        if line.startswith('UU') or line.startswith('AA'):
            conflicts.append(line[3:])
    
    return conflicts
```

---

## Development Timeline

### Phase 1: Foundation (Weeks 1-3)
**Dev 1:** Project structure, constants, exceptions  
**Dev 2:** Config parsing, validation, tests  
**Dev 3:** Documentation, examples, schemas  

**Deliverables:**
- Complete project structure
- Config parsing with tests
- File operations module
- Git wrapper with error handling
- 50%+ test coverage

### Phase 2: Core Commands (Weeks 4-5)
**Dev 1:** `init`, `switch` (all 3 phases)  
**Dev 2:** `status`, `branch` commands  
**Dev 3:** `edit` (with repo reorganization), `deploy`  

**Deliverables:**
- 6 working commands with rich output
- repo_path auto-generation
- Automatic file moving on edit
- 70%+ test coverage

### Phase 3: Security (Week 6)
**Dev 1:** Secret pattern library  
**Dev 2:** `audit` command with all modes  
**Dev 3:** Integration into switch/sync  

**Deliverables:**
- `audit` command functional
- 6+ default patterns
- Auto-redaction capability
- Security documentation

### Phase 4: Sync (Week 7)
**Dev 1:** Basic sync, push/pull  
**Dev 2:** Conflict detection  
**Dev 3:** `conflicts` commands, resolution  

**Deliverables:**
- Full sync capability
- Conflict detection and resolution
- `remote` commands
- Network error handling

### Phase 5: Advanced (Week 8)
**Dev 1:** `backup` commands (create/list/restore)  
**Dev 2:** `template` command with substitution  
**Dev 3:** `doctor` command with 10 checks  

**Deliverables:**
- Backup/restore system
- Template variables
- Health diagnostics
- Auto-fix capabilities

### Phase 6: Polish (Weeks 9-10)
**All:** Testing, documentation, CI/CD, release  

**Deliverables:**
- 80%+ test coverage
- Complete documentation
- Shell completions
- v1.0.0 release on PyPI

---

## Success Criteria

**Functional:**
- ✅ Initialize and switch branches without data loss
- ✅ Auto-generate repo_path correctly
- ✅ Detect/redact all critical secrets
- ✅ Sync reliably with remote
- ✅ Auto-backup before risky operations
- ✅ Handle conflicts gracefully

**Quality:**
- 80%+ test coverage
- <5 critical bugs at release
- Clear, actionable error messages
- 100% commands documented

**Performance:**
- Handle 100+ files in <5 seconds
- New user setup in <5 minutes

---

## Technical Requirements

### Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.8"
click = "^8.1"
GitPython = "^3.1"
rich = "^13.0"
```

### Directory Structure
```
dot_man/
├── __init__.py
├── cli.py           # Click commands
├── core.py          # Git operations
├── config.py        # Config parsing
├── files.py         # File operations
├── secrets.py       # Secret detection
├── templates.py     # Template substitution
├── conflicts.py     # Conflict resolution
├── utils.py         # Helpers
├── constants.py     # Paths, patterns
└── exceptions.py    # Custom exceptions

tests/
├── test_core.py
├── test_config.py
├── test_files.py
└── ...
```

### Exit Code Conventions
```
0     - Success
1-9   - General errors (not initialized, etc.)
5-9   - Git errors
10-19 - Security errors (secrets detected)
20-29 - Sync/merge errors
30-39 - Config/validation errors
40-49 - Deployment errors
50-59 - Audit errors
60-69 - Doctor errors
70-79 - Template errors
80-89 - Branch errors
90-99 - Remote errors
100+  - Backup errors
```

---

## Key Design Decisions

1. **repo_path is optional** - Auto-generate from filename for simplicity
2. **Auto-reorganize on edit** - Move files when repo_path changes
3. **Three-phase switch** - Save → Switch → Deploy for safety
4. **Strict vs permissive modes** - Allow flexibility while protecting against secrets
5. **Automatic backups** - Before all destructive operations
6. **Rich CLI output** - Tables, colors, progress indicators
7. **Rollback on failure** - Use git reset to recover from errors

---

## Testing Strategy

### Unit Tests
- Config parsing edge cases
- Secret detection patterns (false positives/negatives)
- repo_path auto-generation
- Template substitution
- File operations with mocked filesystem

### Integration Tests
- Complete switch workflow
- Sync with mocked remote
- Conflict resolution flows
- Backup/restore cycles
- Edit with repo reorganization

### E2E Tests
- New machine setup scenario
- Multi-machine sync scenario
- Secret detection in real configs
- Recovery from failures

---

This specification provides complete requirements for implementing dot-man. Each developer knows their responsibilities and deliverables for each phase. The focus is on **what to build** with enough detail on **how** where necessary for critical features.
