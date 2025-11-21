## **3. Detailed Command Specifications**

### **3.1 `dot-man init`**

**Purpose:** Initialize a new dot-man repository for the first time on a machine.

**Behavior:**
1. **Pre-checks:**
   - Verify `~/.config/dot-man/` doesn't already exist
   - If it exists, prompt user: "Repository already initialized. Reinitialize? (This will DELETE all data)"
   - Only proceed if user confirms or directory doesn't exist

2. **Directory Creation:**
   - Create `~/.config/dot-man/`
   - Create `~/.config/dot-man/repo/`
   - Create `~/.config/dot-man/backups/` (for future backups)
   - Set appropriate permissions (0700 for security)

3. **Git Repository Initialization:**
   - Initialize empty git repository in `repo/`
   - Set user.name and user.email if not already configured globally
   - Configure git to ignore certain files (`.DS_Store`, `*.swp`, etc.)

4. **Create Default Configuration:**
   - Generate `global.conf` with:
     ```ini
     [dot-man]
     current_branch = main
     initialized_date = <current_timestamp>
     version = 1.0.0
     
     [remote]
     url = 
     auto_sync = false
     
     [security]
     secrets_filter = true
     audit_on_commit = true
     strict_mode = false
     ```

5. **Create Default dot-man.ini:**
   - Generate `repo/dot-man.ini` with example configuration:
     ```ini
     [DEFAULT]
     secrets_filter = true
     update_strategy = replace
     
     # Example configuration - uncomment and modify
     # [~/.bashrc]
     # local_path = ~/.bashrc
     # repo_path = .bashrc
     # secrets_filter = false
     ```

6. **Initial Commit:**
   - Stage `dot-man.ini`
   - Create initial commit with message: "dot-man: Initial commit"
   - Ensure commit is on `main` branch

7. **User Feedback:**
   - Display success message with green styling
   - Show next steps:
     ```
     ✓ dot-man initialized successfully!
     
     Next steps:
     1. Edit configuration: dot-man edit
     2. Add your dotfiles to dot-man.ini
     3. Switch to save: dot-man switch main
     4. View status: dot-man status
     ```

**Error Handling:**
- If git is not installed: "Git not found. Please install git first."
- If permissions denied: "Permission denied. Cannot create ~/.config/dot-man/"
- If disk space insufficient: "Insufficient disk space"

**Exit Codes:**
- 0: Success
- 1: Already initialized (and user declined reinit)
- 2: Git not available
- 3: Permission error
- 4: Disk space error

---

### **3.2 `dot-man switch <branch-name>`**

**Purpose:** Switch between different dotfile configurations (e.g., work, personal, minimal) by saving current changes and deploying the target branch's files.

**Arguments:**
- `branch-name` (required): Name of branch to switch to

**Options:**
- `--dry-run`: Show what would happen without making changes
- `--force`: Skip confirmation prompts
- `--no-backup`: Don't create automatic backup before switching

**Behavior:**

**Phase 1: Save Current Branch State**

1. **Load Current Context:**
   - Read `global.conf` to determine current branch (e.g., "main")
   - Load `repo/dot-man.ini` configuration for current branch
   - If current branch == target branch: Display "Already on <branch>" and exit

2. **Discovery and Collection:**
   - For each `[section]` in `dot-man.ini`:
     - Extract `local_path` (e.g., `~/.bashrc`)
     - Extract `repo_path` (e.g., `.bashrc`)
     - Resolve full paths using `pathlib`
     
3. **Change Detection Logic:**
   - **For Files:**
     - If `local_path` doesn't exist but `repo_path` exists:
       - Mark as "DELETED"
       - Remove `repo_path` from repository
     - If `local_path` exists:
       - Read file content
       - Check if `secrets_filter = true` for this section
       - If yes: Apply redaction patterns (see Secrets section below)
       - Compare with existing `repo_path` (if exists)
       - If different: Copy to `repo_path` (mark as "MODIFIED" or "NEW")
       - Preserve file permissions metadata
   
   - **For Directories:**
     - Use `local_path.rglob('*')` to walk entire tree
     - For each file found:
       - Calculate relative path from `local_path`
       - Determine destination: `repo_path / relative_path`
       - Apply same file logic as above
     - Check for deleted files (exist in repo but not locally)
     - Handle `.dotmanignore` patterns (skip matching files)

4. **Secrets Filtering (if enabled):**
   - Read file content as text
   - Apply regex patterns:
     - `API_KEY=...` → `API_KEY=***REDACTED***`
     - `password = "..."` → `password = "***REDACTED***"`
     - `-----BEGIN PRIVATE KEY-----...` → `***REDACTED_PRIVATE_KEY***`
   - Preserve file structure and non-sensitive content
   - If `strict_mode = true` in config:
     - Detect secrets but refuse to proceed
     - Display: "Secret detected in <file>:<line>. Aborting."
     - Exit with code 10

5. **Commit Changes:**
   - Stage all changes: `git add .`
   - Check if repository is "dirty" (has changes)
   - If dirty:
     - Create commit with message: `Auto-save from '<current-branch>' before switch`
     - Include timestamp in commit message
   - If clean: No commit needed

6. **Create Safety Backup (unless --no-backup):**
   - Copy entire `repo/` to `backups/pre-switch-<timestamp>/`
   - Limit backups to last 5 (delete oldest if exceeded)

**Phase 2: Switch Branch**

7. **Branch Existence Check:**
   - Query git for list of branches
   - If `branch-name` exists:
     - Execute `git checkout <branch-name>`
   - If doesn't exist:
     - Create new branch: `git checkout -b <branch-name>`
     - Copy current `dot-man.ini` as starting point
     - Commit with message: `Created branch '<branch-name>'`

8. **Reload Configuration:**
   - Git checkout has now changed `repo/dot-man.ini`
   - Parse the NEW configuration file
   - Load all sections for deployment

**Phase 3: Deploy New Branch Files**

9. **Deployment Strategy:**
   - For each `[section]` in the new `dot-man.ini`:
     - Extract `update_strategy` (default: "replace")
     - Extract `local_path` and `repo_path`
     
10. **Strategy: "ignore"**
    - Skip this section entirely
    - Don't modify user's local files
    - Use case: Files managed by other tools

11. **Strategy: "rename_old"**
    - If `local_path` exists:
      - Rename to `<local_path>.dotman-backup-<timestamp>`
      - Example: `~/.bashrc` → `~/.bashrc.dotman-backup-20251116`
    - Copy `repo_path` → `local_path`
    - Restore file permissions from metadata

12. **Strategy: "replace"**
    - If `local_path` exists:
      - Delete it (files) or remove tree (directories)
    - Copy `repo_path` → `local_path`
    - For directories: Use `dirs_exist_ok=True` to merge
    - Restore file permissions

13. **Template Variable Substitution:**
    - If section has `template_vars = HOSTNAME, USERNAME`
    - Load `template_vars.json` from `~/.config/dot-man/`
    - Replace `{{HOSTNAME}}` with actual value
    - Replace `{{USERNAME}}` with actual value
    - Write templated content to `local_path`

14. **Dry-Run Mode (if --dry-run):**
    - Execute all logic above but DON'T:
      - Write any files
      - Commit to git
      - Modify filesystem
    - Instead, display table:
      ```
      File                    Action           Details
      ────────────────────────────────────────────────
      ~/.bashrc              REPLACE          Modified (3 lines)
      ~/.vimrc               NO CHANGE        Identical
      ~/.config/nvim/        RENAME_OLD       Directory exists
      ~/.gitconfig           SKIP             Strategy: ignore
      ```

15. **Update Global State:**
    - Write to `global.conf`:
      ```ini
      [dot-man]
      current_branch = <new-branch>
      last_switch = <timestamp>
      ```

16. **User Feedback:**
    - Display success with rich formatting:
      ```
      ✓ Switched to 'work'
      
      Changes applied:
      • Deployed 5 files
      • Backed up 2 files
      • Skipped 1 file (ignored)
      
      Run 'dot-man status' to verify.
      ```

**Error Handling:**
- If branch checkout fails: "Git error: <message>. Repository may be corrupted."
- If file copy fails: "Permission denied: <file>. Check file permissions."
- If secrets detected in strict mode: Exit before making any changes
- If disk space insufficient: "Cannot deploy: Insufficient disk space"

**Exit Codes:**
- 0: Success
- 1: Already on target branch
- 5: Git operation failed
- 6: File operation failed
- 10: Secrets detected (strict mode)
- 11: Disk space error

---

### **3.3 `dot-man status`**

**Purpose:** Display current state of dot-man repository and show what changes would be saved if you ran `switch` now.

**Options:**
- `--verbose, -v`: Show detailed file-by-file changes
- `--secrets`: Highlight files containing detected secrets
- `--remote`: Include remote sync status (requires remote configured)

**Behavior:**

1. **Repository Information Section:**
   - Load and display:
     ```
     Repository Status
     ─────────────────────────────────────────
     Current Branch:        main
     Initialized:           2025-11-10 14:23:00
     Last Switch:           2025-11-15 09:30:00
     Remote:                git@github.com:user/dotfiles.git
     Branch Synced:         Yes (up to date)
     Local Changes:         3 modified, 1 new
     ```

2. **Git Status:**
   - Check if repository is "dirty" (uncommitted changes)
   - Display staged vs unstaged changes
   - Show untracked files in repo

3. **Dry-Run Diff Analysis:**
   - This is the core feature
   - Simulate what `switch <current-branch>` would do
   - For each section in `dot-man.ini`:
     - Compare `local_path` vs `repo_path`
     - Categorize as: NEW, MODIFIED, DELETED, IDENTICAL

4. **File Comparison Logic:**
   - **DELETED:**
     - `repo_path` exists
     - `local_path` does NOT exist
     - User deleted the file locally
   
   - **NEW:**
     - `local_path` exists
     - `repo_path` does NOT exist
     - User created new file locally
   
   - **MODIFIED:**
     - Both exist
     - Content differs (byte-by-byte comparison)
     - Show line diff count if possible
   
   - **IDENTICAL:**
     - Both exist
     - Content identical
     - No action needed

5. **Secrets Detection (if --secrets flag):**
   - For MODIFIED and NEW files:
     - Run secret detection patterns
     - Mark files containing secrets with 🔒 icon
     - Display: "⚠️  3 files contain potential secrets"
     - List files with line numbers

6. **Remote Status (if --remote flag):**
   - Check if remote is configured
   - Fetch remote branch (without merging)
   - Compare local vs remote:
     - "Ahead by 3 commits" (local has unpushed changes)
     - "Behind by 2 commits" (remote has changes to pull)
     - "Diverged" (both have unique commits)
     - "Up to date"
   - Show last sync timestamp

7. **Output Formatting:**
   - Use rich Table for clean display
   - Color coding:
     - Green: IDENTICAL, up to date
     - Yellow: MODIFIED
     - Blue: NEW
     - Red: DELETED
     - Purple: Contains secrets
   
   - Example output:
     ```
     Tracked Files Status
     ─────────────────────────────────────────────────────────
     File                    Status        Changes
     ─────────────────────────────────────────────────────────
     ~/.bashrc              MODIFIED      +5 -2 lines
     ~/.vimrc               IDENTICAL     
     ~/.config/nvim/init.lua NEW          268 lines
     ~/.gitconfig           MODIFIED 🔒   +1 line (secret detected)
     ~/.zshrc               DELETED       (removed locally)
     ```

8. **Verbose Mode (if -v flag):**
   - For each MODIFIED file:
     - Show actual diff (unified diff format)
     - Limit to first 20 lines (prevent spam)
   - For secrets:
     - Show line numbers and context (not actual secret values)

9. **Actionable Summary:**
   - At bottom, show what user should do:
     ```
     Summary:
     • 3 files will be saved on next switch
     • 1 file contains secrets (will be redacted)
     • 1 file was deleted locally
     
     Next steps:
     • Review changes above
     • Run 'dot-man switch <branch>' to save
     • Run 'dot-man audit' to review secrets
     ```

**Error Handling:**
- If not initialized: "Not initialized. Run 'dot-man init' first."
- If `dot-man.ini` missing: "Configuration file missing. Repository corrupted?"
- If remote fetch fails: "Cannot reach remote. Check network connection."

**Exit Codes:**
- 0: Success
- 1: Not initialized
- 7: Configuration error

---

### **3.4 `dot-man sync`**

**Purpose:** Synchronize local repository with remote git repository (push/pull changes).

**Options:**
- `--force-pull`: Discard local changes and pull from remote
- `--force-push`: Overwrite remote with local changes
- `--continue`: Continue after resolving merge conflicts
- `--dry-run`: Show what would be synced without doing it

**Behavior:**

**Pre-Sync Phase:**

1. **Check Remote Configuration:**
   - Read `global.conf` for `[remote] url`
   - If empty: Display "No remote configured. Use 'dot-man remote set <url>'"
   - Exit if no remote

2. **Verify Network Connectivity:**
   - Try to reach remote (lightweight fetch)
   - If fails: "Cannot reach remote. Check network and URL."

3. **Check Repository State:**
   - If repository is in middle of merge: "Merge in progress. Use --continue or 'dot-man conflicts resolve'"
   - If detached HEAD: "Repository in detached state. Aborting."

**Force Pull Mode (--force-pull):**

4. **Destructive Warning:**
   - Display prominent warning:
     ```
     ⚠️  WARNING: Force pull will DISCARD all local changes!
     
     This will:
     • Delete all uncommitted changes
     • Reset to remote state
     • Cannot be undone (unless you have backups)
     
     Continue? [y/N]
     ```
   - Only proceed if user types 'y' or 'yes'

5. **Force Pull Execution:**
   - Create safety backup first: `backup create -m "Pre-force-pull"`
   - Fetch from remote: `git fetch origin`
   - Hard reset to remote: `git reset --hard origin/<current-branch>`
   - Clean untracked files: `git clean -fd`
   - Deploy files to home directory (same as `switch` Phase 3)
   - Display: "✓ Force pulled from remote. Local changes discarded."

**Force Push Mode (--force-push):**

6. **Destructive Warning:**
   - Display:
     ```
     ⚠️  WARNING: Force push will OVERWRITE remote repository!
     
     This will:
     • Overwrite remote branch history
     • Lose remote commits not present locally
     • Affect all users of this repository
     
     Continue? [y/N]
     ```

7. **Force Push Execution:**
   - Save local changes first (call Phase 1 of `switch`)
   - Push with force: `git push --force origin <current-branch>`
   - Display: "✓ Force pushed to remote. Remote history overwritten."

**Standard Sync Mode (default):**

8. **Save Local Changes:**
   - Execute Phase 1 of `switch` command
   - Commit any uncommitted changes
   - Message: "Auto-save before sync at <timestamp>"

9. **Fetch Remote Changes:**
   - Execute: `git fetch origin`
   - Get list of remote branches
   - Compare local vs remote commits

10. **Determine Sync Strategy:**
    - **Up to date:** Local == Remote
      - Display: "✓ Already up to date with remote"
      - Exit early
    
    - **Fast-forward possible:** Local behind remote
      - Local has no unique commits
      - Can safely pull
      - Execute: `git merge --ff-only origin/<branch>`
    
    - **Diverged:** Both have unique commits
      - Requires real merge
      - Proceed to merge logic below

11. **Merge Execution:**
    - Attempt: `git merge origin/<current-branch>`
    - Wrap in try/catch for merge conflicts

12. **Merge Conflict Handling:**
    - If conflicts detected:
      - Parse git status for conflicted files
      - Display rich table:
        ```
        ⚠️  Merge Conflicts Detected
        ───────────────────────────────────────
        File                    Conflict Type
        ───────────────────────────────────────
        ~/.bashrc              Content conflict
        ~/.vimrc               Both modified
        ```
      - Display instructions:
        ```
        To resolve:
        1. Edit conflicted files manually, OR
        2. Use 'dot-man conflicts resolve <file> --ours/--theirs'
        3. Run 'dot-man sync --continue' when done
        ```
      - Exit with code 20 (merge conflict)

13. **Continue After Conflict Resolution (--continue):**
    - Verify all conflicts resolved:
      - Check git status for 'U' (unmerged) files
      - If any remain: "Still have unresolved conflicts in: <files>"
    - Commit the merge: `git commit -m "Merged remote changes"`
    - Proceed to push

14. **Push Local Changes:**
    - Execute: `git push origin <current-branch>`
    - Handle push rejection:
      - If rejected: "Push rejected. Remote has changes. Run sync again."
      - Retry with pull-rebase if user confirms

15. **Deploy Merged Changes:**
    - After successful merge, files in `repo/` may have changed
    - Run deployment logic (Phase 3 of `switch`)
    - Update home directory with merged content

16. **Final Status Report:**
    - Display:
      ```
      ✓ Sync completed successfully
      
      Changes:
      • Pulled 3 commits from remote
      • Pushed 2 local commits
      • Deployed 4 updated files
      
      Repository is now in sync with remote.
      ```

**Dry-Run Mode (--dry-run):**

17. **Simulate Sync:**
    - Fetch remote (safe operation)
    - Analyze what would happen:
      ```
      Sync Preview (Dry Run)
      ─────────────────────────────────────
      Local Status:     2 uncommitted changes
      Remote Status:    3 commits ahead
      Action Required:  Pull then push
      
      Would pull:
      • commit abc123: "Update bashrc"
      • commit def456: "Add vim config"
      
      Would push:
      • commit 789ghi: "Local changes"
      
      Conflicts:        None detected
      ```

**Error Handling:**
- If network fails mid-sync: "Network error. Repository state preserved."
- If push fails: "Push failed. Try again or check remote permissions."
- If merge fails unexpectedly: "Merge failed. Run 'dot-man doctor' to diagnose."

**Exit Codes:**
- 0: Success (synced)
- 1: Already up to date
- 15: Network error
- 16: Remote not configured
- 20: Merge conflicts (user must resolve)
- 21: Push rejected

---

### **3.5 `dot-man edit`**

**Purpose:** Open the current branch's configuration file in user's preferred text editor.

**Options:**
- `--editor <name>`: Override default editor (e.g., `vim`, `nano`, `code`)
- `--global`: Edit global configuration (`global.conf`) instead
- `--validate`: Check configuration syntax after editing

**Behavior:**

1. **Determine Target File:**
   - Default: `repo/dot-man.ini` (current branch config)
   - If `--global`: `~/.config/dot-man/global.conf`

2. **Editor Selection:**
   - Priority order:
     1. `--editor` flag if provided
     2. `VISUAL` environment variable
     3. `EDITOR` environment variable
     4. Fallback: `nano` (most beginner-friendly)
   - Verify editor exists on system
   - If not found: "Editor '<name>' not found. Available: nano, vim, vi"

3. **Pre-Edit Backup:**
   - Create temporary backup: `dot-man.ini.pre-edit`
   - Allows revert if user makes mistakes

4. **Launch Editor:**
   - Open file in editor
   - Block (wait) until editor closes
   - Use click's `edit()` helper for cross-platform support

5. **Post-Edit Validation (automatic):**
   - Parse configuration file with configparser
   - Check for syntax errors:
     - Invalid INI format
     - Missing required fields (`local_path`, `repo_path`)
     - Invalid values (`update_strategy` not in [replace, rename_old, ignore])
     - Path syntax errors
   
6. **Error Display (if validation fails):**
   - Show specific errors:
     ```
     ⚠️  Configuration Errors Detected
     ────────────────────────────────────────
     Line 15: Missing 'local_path' in [~/.bashrc]
     Line 23: Invalid strategy 'merge' (use replace/rename_old/ignore)
     Line 30: Path '~invalid' cannot be resolved
     
     Your changes were saved to: dot-man.ini.pre-edit
     Fix errors and run 'dot-man edit' again.
     ```
   - Restore from backup automatically
   - Exit with error code

7. **Success Case:**
   - Delete backup file
   - Display:
     ```
     ✓ Configuration updated
     
     Run 'dot-man status' to see how changes affect your files.
     ```

8. **Additional Validation (--validate flag):**
   - Check for common mistakes:
     - Duplicate sections
     - Paths outside home directory (warn, don't error)
     - Sections with `secrets_filter=true` but no patterns defined
     - Circular dependencies (if implemented)
   - Provide suggestions:
     ```
     💡 Suggestions:
     • [~/.ssh/config] should have secrets_filter=true
     • [~/.bashrc] contains EXPORT statements - consider filtering
     ```

9. **Global Config Editing (--global):**
   - Show warning if editing advanced settings
   - Validate different schema:
     - `current_branch` must exist as git branch
     - `sync_interval` must be positive integer
     - `remote.url` must be valid git URL format
   - Don't allow changing certain fields (e.g., `initialized_date`)

**Error Handling:**
- If file doesn't exist: "Configuration file missing. Repository corrupted?"
- If editor crashes: "Editor exited abnormally. Configuration unchanged."
- If permissions deny write: "Cannot write configuration. Check permissions."

**Exit Codes:**
- 0: Success (valid changes saved)
- 1: No changes made
- 30: Validation failed
- 31: Editor not found
- 32: Write permission denied

---

### **3.6 `dot-man deploy <branch-name>`**

**Purpose:** One-way deployment of a branch to local filesystem. Used for bootstrapping a new machine or recovering from corruption. Unlike `switch`, this doesn't save local changes first.

**Arguments:**
- `branch-name` (required): Branch to deploy

**Options:**
- `--force`: Skip confirmation prompt
- `--dry-run`: Show what would be deployed
- `--strategy <name>`: Override all update strategies (replace/rename_old)

**Behavior:**

1. **Pre-Deployment Warning:**
   - This is a destructive operation
   - Display prominent warning:
     ```
     ⚠️  WARNING: Deploy will OVERWRITE local files!
     
     This will deploy '<branch-name>' configuration:
     • All files in dot-man.ini will be copied
     • Existing files will be overwritten (no backup by default)
     • Local changes will be LOST
     
     Typical use: Setting up a new machine or recovering
     
     Continue? [y/N]
     ```
   - Require explicit confirmation unless `--force`

2. **Branch Checkout:**
   - Verify branch exists in git
   - If not: "Branch '<branch-name>' does not exist. Available: main, work, minimal"
   - Checkout branch: `git checkout <branch-name>`
   - This changes `repo/dot-man.ini` to the target branch version

3. **Load Target Configuration:**
   - Parse `repo/dot-man.ini`
   - Load all `[section]` definitions
   - Validate paths are resolvable

4. **Pre-Flight Checks:**
   - For each section:
     - Verify `repo_path` exists in repository
     - If doesn't exist: Warn "Missing: <repo_path>. Skipping."
     - Check if `local_path` exists
     - Calculate disk space needed
   - Verify sufficient disk space
   - Display summary:
     ```
     Deployment Plan for 'work' branch
     ─────────────────────────────────────────
     Files to deploy:      12
     Directories:          3
     Will overwrite:       8 existing files
     Will create new:      4 files
     Disk space needed:    2.3 MB
     ```

5. **Deployment Strategy:**
   - **By default:** IGNORE all `update_strategy` settings from config
   - Rationale: Deploy is for bootstrapping, so force overwrite
   - **Override with --strategy flag:**
     - `--strategy replace`: Delete then copy (default)
     - `--strategy rename_old`: Preserve existing files as `.old`

6. **File Deployment Loop:**
   - For each `[section]` in config:
     - Get `repo_path` and `local_path`
     - Create parent directories: `local_path.parent.mkdir(parents=True)`
     
     - **For Files:**
       - If `local_path` exists and strategy is `rename_old`:
         - Rename to `<local_path>.old`
       - Copy `repo_path` → `local_path`
       - Restore file permissions from metadata (if stored)
       - Apply template substitution (if configured)
     
     - **For Directories:**
       - If `local_path` exists and strategy is `rename_old`:
         - Rename to `<local_path>.old`
       - Recursively copy `repo_path` → `local_path`
       - Preserve directory structure
       - Apply permissions recursively

7. **Template Processing:**
   - If section has `template_vars = HOSTNAME, USERNAME`
   - Load `template_vars.json`
   - For each file deployed:
     - Read content
     - Replace `{{HOSTNAME}}` with actual hostname
     - Replace `{{USERNAME}}` with actual username
     - Write back to file

8. **Post-Deployment Actions:**
   - Update `global.conf`:
     ```ini
     [dot-man]
     current_branch = <branch-name>
     last_deploy = <timestamp>
     ```
   - Create post-deploy marker: `.dotman-deployed-<branch>-<timestamp>`

9. **Verification Step:**
   - For each deployed file:
     - Verify it exists
     - Verify size matches (basic corruption check)
   - Count successes vs failures

10. **Success Report:**
    - Display:
      ```
      ✓ Deployment of 'work' completed
      
      Deployed:
      • 10 files copied successfully
      • 2 directories created
      • 8 existing files overwritten
      
      Your dotfiles are now configured for 'work' environment.
      ```

11. **Dry-Run Mode (--dry-run):**
    - Execute all checks but don't write files
    - Display detailed plan:
      ```
      Deployment Preview (Dry Run)
      ────────────────────────────────────────────────
      File                  Action         Current Size
      ────────────────────────────────────────────────
      ~/.bashrc            OVERWRITE      2.1 KB
      ~/.vimrc             NEW            15 KB
      ~/.gitconfig         OVERWRITE      1.3 KB
      ~/.config/nvim/      NEW DIR        45 KB (12 files)
      ```

**Use Cases:**
- **New Machine Setup:**
  ```bash
  git clone <dotfiles-repo> ~/.config/dot-man/repo
  cd ~/.config/dot-man/repo
  dot-man init  # Creates structure
  dot-man deploy main  # Deploy main configuration
  ```

- **Recovery from Corruption:**
  ```bash
  dot-man deploy main --force  # Restore from repository
  ```

- **Testing Configuration:**
  ```bash
  dot-man deploy experimental --dry-run  # Preview changes
  ```

**Error Handling:**
- If branch doesn't exist: List available branches
- If repo file missing: "Cannot deploy <file>: Missing from repository"
- If disk space insufficient: "Insufficient space. Need 5MB, have 2MB."
- If permission denied: "Cannot write <file>. Check permissions."

**Exit Codes:**
- 0: Success (all files deployed)
- 1: Branch not found
- 40: Deployment failed (partial success possible)
- 41: Disk space insufficient
- 42: Permission denied
- 43: User cancelled

---

### **3.7 `dot-man audit`**

**Purpose:** Scan repository for accidentally committed secrets or sensitive data.

**Options:**
- `--strict`: Exit with error if ANY secrets found (for CI/CD)
- `--fix`: Automatically redact found secrets and commit
- `--patterns <file>`: Use custom regex patterns from file
- `--exclude <pattern>`: Exclude files matching glob pattern

**Behavior:**

1. **Initialization:**
   - Load secret detection patterns from `secrets.py`
   - Default patterns:
     - API keys: `api_key=`, `API_KEY=`, `apiKey:`
     - Tokens: `token=`, `bearer`, `auth_token`
     - Private keys: `-----BEGIN PRIVATE KEY-----`
     - Passwords: `password=`, `passwd=`
     - AWS: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key`
     - GitHub: `gh[ps]_[a-zA-Z0-9]{36}`
     - JWT: `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+`
   - Load custom patterns if `--patterns <file>` specified
   - Load exclusion patterns from `--exclude` and `.dotmanignore`

2. **Repository Scan:**
   - Walk through entire `repo/` directory
   - Exclude `.git/` directory
   - For each file:
     - Skip binary files (check for null bytes)
     - Skip files matching exclusion patterns
     - Read content as text
     - Apply all regex patterns

3. **Detection Logic:**
   - For each line in each file:
     - Run all patterns against line
     - If match found:
       - Record: (file, line_number, pattern_name, matched_text)
       - Capture surrounding context (±2 lines)
   - Handle false positives:
     - Skip comments containing "example" or "dummy"
     - Skip URLs in documentation
     - Skip test fixtures with obvious fake values

4. **Severity Classification:**
   - **CRITICAL:** Private keys, AWS credentials
   - **HIGH:** API tokens, passwords in plaintext
   - **MEDIUM:** Potential tokens (ambiguous patterns)
   - **LOW:** Suspicious patterns needing review

5. **Results Display:**
   - Group findings by severity
   - Use rich table with color coding:
     ```
     🔒 Security Audit Results
     ═══════════════════════════════════════════════════════════
     
     CRITICAL (2 findings):
     ────────────────────────────────────────────────────────────
     File: .ssh/config
     Line 15: -----BEGIN RSA PRIVATE KEY-----
     Context:
       14: # SSH key for production server
       15: -----BEGIN RSA PRIVATE KEY-----
       16: MIIEpAIBAAKCAQEA...
     
     File: .env
     Line 3: AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG...
     Context:
       2: AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
       3: AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG...
       4: REGION=us-west-2
     
     HIGH (1 finding):
     ────────────────────────────────────────────────────────────
     File: .bashrc
     Line 45: export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
     
     ═══════════════════════════════════════════════════════════
     Total: 3 secrets detected across 3 files
     ```

6. **Recommendations:**
   - Display actionable advice:
     ```
     Recommendations:
     ─────────────────────────────────────────────────────────
     1. Enable secrets_filter for affected sections:
        [~/.ssh/config]
        secrets_filter = true
     
     2. Move credentials to environment variables:
        - Store in password manager
        - Use shell's secure credential storage
     
     3. Rotate compromised credentials immediately:
        - AWS keys in .env (line 3)
        - GitHub token in .bashrc (line 45)
     
     4. Consider using 'dot-man audit --fix' to auto-redact
     ```

7. **Strict Mode (--strict flag):**
   - Used in CI/CD pipelines
   - If ANY secrets found (even LOW severity):
     - Display all findings
     - Print: "STRICT MODE: Secrets detected. Refusing to proceed."
     - Exit with code 50
   - If no secrets:
     - Print: "✓ No secrets detected. Safe to commit."
     - Exit with code 0

8. **Auto-Fix Mode (--fix flag):**
   - For each finding:
     - Read file content
     - Apply redaction: Replace matched text with `***REDACTED_BY_DOTMAN***`
     - Write back to file
   - Create git commit:
     - Message: "Security: Auto-redacted secrets detected by audit"
     - Include list of affected files in commit body
   - Display:
     ```
     ✓ Auto-fixed 3 secrets
     
     Modified files:
     • .ssh/config (1 secret redacted)
     • .env (1 secret redacted)
     • .bashrc (1 secret redacted)
     
     Changes committed. Run 'dot-man sync' to push.
     ```

9. **Git History Scan (Advanced):**
   - Optional deep scan through git history
   - Check all commits for secrets
   - Warn if secrets found in old commits:
     ```
     ⚠️  Secrets found in git history:
     
     commit abc1234 (3 months ago)
     File: .bashrc
     Secret: API_KEY=sk_live_xxxx
     
     These secrets are still accessible in git history.
     Consider using 'git filter-branch' or 'BFG Repo-Cleaner'.
     ```

10. **Custom Patterns (--patterns flag):**
    - Accept file with custom regex patterns
    - Format (YAML or JSON):
      ```yaml
      patterns:
        - name: "Company API Key"
          regex: "COMPANY_API_[A-Z0-9]{32}"
          severity: HIGH
        
        - name: "Internal Token"
          regex: "internal_token_[a-f0-9]{40}"
          severity: MEDIUM
      ```
    - Merge with default patterns
    - Display which patterns matched

**Error Handling:**
- If repository corrupted: "Cannot scan: Repository structure invalid"
- If file unreadable: "Skipping <file>: Cannot read (encoding issue)"
- If patterns file invalid: "Pattern file format error: <details>"

**Exit Codes:**
- 0: Success (no secrets found)
- 50: Secrets found (strict mode)
- 51: Pattern file invalid
- 52: Fix failed (file write error)

---

### **3.8 `dot-man doctor`**

**Purpose:** Comprehensive diagnostic tool to detect and suggest fixes for common issues.

**Options:**
- `--fix`: Automatically fix issues where possible
- `--verbose, -v`: Show detailed diagnostic information
- `--check <category>`: Run specific check only (git, config, files, secrets, remote)

**Behavior:**

1. **Diagnostic Categories:**
   - Repository health
   - Git integrity
   - Configuration validity
   - File permissions
   - Secret detection
   - Remote connectivity
   - Disk space
   - Dependencies

2. **Check 1: Repository Initialization**
   - Verify `~/.config/dot-man/` exists
   - Verify `repo/` subdirectory exists
   - Check permissions (readable/writable)
   - **Pass:** ✓ Repository initialized
   - **Fail:** ✗ Repository not found
   - **Fix:** Offer to run `dot-man init`

3. **Check 2: Git Repository Validity**
   - Verify `.git/` directory exists
   - Check git repository not corrupted
   - Verify HEAD is valid
   - Check for detached HEAD state
   - **Pass:** ✓ Git repository valid
   - **Fail:** ✗ Git repository corrupted
   - **Fix:** Offer to reinitialize or restore from backup

4. **Check 3: Configuration Files**
   - Check `global.conf` exists and is parseable
   - Check `repo/dot-man.ini` exists and is valid INI
   - Validate all sections have required fields
   - Check for duplicate sections
   - Verify paths are resolvable
   - **Pass:** ✓ Configuration valid (X sections)
   - **Warn:** ⚠ Configuration has warnings
   - **Fail:** ✗ Configuration invalid
   - **Fix:** Offer to open in editor or restore default

5. **Check 4: Current Branch State**
   - Verify current branch exists
   - Check if branch matches `global.conf`
   - Detect if in middle of merge/rebase
   - Check for uncommitted changes
   - **Pass:** ✓ On branch 'main' (clean)
   - **Warn:** ⚠ Uncommitted changes (3 files modified)
   - **Fail:** ✗ Branch mismatch or merge in progress

6. **Check 5: Remote Configuration**
   - Check if remote 'origin' is set
   - Test connectivity to remote
   - Verify remote URL is valid git URL
   - Check authentication (if possible)
   - **Pass:** ✓ Remote configured and reachable
   - **Warn:** ⚠ No remote configured
   - **Fail:** ✗ Cannot reach remote
   - **Fix:** Offer to set remote or test connection

7. **Check 6: File System Issues**
   - For each tracked file in `dot-man.ini`:
     - Check if `local_path` exists
     - Check if `repo_path` exists
     - Verify read/write permissions
     - Check for symlink issues
   - **Pass:** ✓ All tracked files accessible
   - **Warn:** ⚠ 2 files missing locally
   - **Fail:** ✗ Permission denied on 1 file

8. **Check 7: Secret Detection**
   - Run quick audit scan
   - Check if `secrets_filter` is enabled where needed
   - Look for obvious secrets in common files
   - **Pass:** ✓ No obvious secrets detected
   - **Warn:** ⚠ 3 potential secrets found
   - **Fail:** ✗ Definite secrets in repository
   - **Fix:** Suggest `dot-man audit --fix`

9. **Check 8: Disk Space**
   - Check available space in home directory
   - Check space in `~/.config/dot-man/`
   - Warn if low (<500MB)
   - Calculate size of tracked files
   - **Pass:** ✓ Sufficient disk space (12 GB free)
   - **Warn:** ⚠ Low disk space (400 MB free)

10. **Check 9: Dependencies**
    - Verify Python version (3.8+)
    - Check git is installed and version
    - Verify required Python packages
    - Check for optional dependencies
    - **Pass:** ✓ All dependencies satisfied
    - **Fail:** ✗ Git not found or Python too old

11. **Check 10: Backup Status**
    - Check if backups exist
    - Verify last backup age
    - Check backup integrity
    - **Pass:** ✓ Recent backup found (2 days ago)
    - **Warn:** ⚠ No backups found or old backup (30 days)

12. **Aggregate Report:**
    ```
    ════════════════════════════════════════════════════════
    dot-man Health Check Report
    ════════════════════════════════════════════════════════
    
    ✓ Repository initialized
    ✓ Git repository valid
    ✓ Configuration valid (8 sections)
    ⚠ Uncommitted changes (3 files)
    ✓ Remote configured: git@github.com:user/dotfiles.git
    ⚠ 2 files missing locally
    ⚠ 3 potential secrets detected
    ✓ Sufficient disk space (12 GB free)
    ✓ All dependencies satisfied
    ✓ Recent backup found
    
    ════════════════════════════════════════════════════════
    Summary: 7 passed, 3 warnings, 0 errors
    ════════════════════════════════════════════════════════
    
    Recommended Actions:
    1. Commit or revert uncommitted changes
    2. Review missing files: run 'dot-man status'
    3. Run 'dot-man audit' to review potential secrets
    ```

13. **Auto-Fix Mode (--fix flag):**
    - For each fixable issue:
      - Display: "Fixing: <issue description>"
      - Apply fix
      - Verify fix succeeded
    - Example fixes:
      - Fix file permissions (chmod)
      - Resolve simple merge conflicts
      - Clean up old backups
      - Reset branch pointer if mismatched
    - Display summary of fixes applied

14. **Verbose Mode (-v flag):**
    - Show detailed output for each check
    - Include git status output
    - Show file listings
    - Display full error messages
    - Include system information

15. **Specific Check (--check flag):**
    ```bash
    dot-man doctor --check git     # Only check git health
    dot-man doctor --check secrets # Only scan for secrets
    dot-man doctor --check remote  # Only check remote
    ```

**Error Handling:**
- If multiple critical errors: Suggest `dot-man init` to reset
- If only warnings: Exit 0 (warnings don't fail)
- If errors: Exit with specific code for each category

**Exit Codes:**
- 0: All checks passed (or only warnings)
- 60: Repository not initialized
- 61: Git repository corrupted
- 62: Configuration invalid
- 63: Critical file system issue
- 64: Dependency missing

---

### **3.9 `dot-man template`**

**Purpose:** Manage template variables for machine-specific configuration values.

**Options:**
- `--set KEY=VALUE`: Set a template variable
- `--unset KEY`: Remove a template variable
- `--list`: Show all defined variables (default if no args)
- `--apply`: Manually trigger template substitution in deployed files

**Behavior:**

1. **Template Variable Concept:**
   - Store machine-specific values separately
   - Replace placeholders in config files during deployment
   - Example: `{{HOSTNAME}}`, `{{EMAIL}}`, `{{WORK_DIR}}`
   - Allows same dotfiles repo across multiple machines

2. **Storage Location:**
   - Variables stored in `~/.config/dot-man/template_vars.json`
   - Format:
     ```json
     {
       "HOSTNAME": "work-laptop",
       "EMAIL": "john@work.com",
       "WORK_DIR": "/opt/projects",
       "EDITOR": "vim"
     }
     ```

3. **List Variables (default behavior):**
   - Display current variables in table:
     ```
     Template Variables
     ═══════════════════════════════════════════════
     Variable          Value
     ───────────────────────────────────────────────
     HOSTNAME         work-laptop
     EMAIL            john@work.com
     WORK_DIR         /opt/projects
     EDITOR           vim
     ═══════════════════════════════════════════════
     4 variables defined
     
     Usage in configs:
       email = {{EMAIL}}
       export WORKSPACE={{WORK_DIR}}
     ```
   - If no variables: Display "No template variables set. Use --set to define."

4. **Set Variable (--set KEY=VALUE):**
   - Parse input: Split on first `=`
   - Validate KEY:
     - Must be uppercase alphanumeric + underscores
     - Must start with letter
     - Max 50 characters
   - Store in JSON file
   - Display confirmation:
     ```
     ✓ Set HOSTNAME = work-laptop
     
     This variable will be substituted in configs marked with:
     template_vars = HOSTNAME
     ```

5. **Set Multiple Variables:**
   ```bash
   dot-man template --set EMAIL=john@work.com --set HOSTNAME=laptop
   ```
   - Process each --set flag in order
   - Display summary:
     ```
     ✓ Set 2 variables:
       • EMAIL = john@work.com
       • HOSTNAME = laptop
     ```

6. **Unset Variable (--unset KEY):**
   - Remove from JSON file
   - Warn if variable was referenced in any config:
     ```
     ⚠ Warning: HOSTNAME is used in 3 config files:
       • ~/.bashrc
       • ~/.gitconfig
       • ~/.ssh/config
     
     Removed HOSTNAME. These files will have blank values on next deploy.
     ```

7. **Template Substitution in Configs:**
   - When deploying files (during `switch` or `deploy`):
     - Check if section has `template_vars` field
     - Example in `dot-man.ini`:
       ```ini
       [~/.gitconfig]
       local_path = ~/.gitconfig
       repo_path = .gitconfig
       template_vars = EMAIL, USERNAME
       ```
     - During deployment:
       - Read file from `repo_path`
       - Find all `{{VAR_NAME}}` patterns
       - Replace with values from `template_vars.json`
       - Write to `local_path`

8. **Example Workflow:**
   ```bash
   # On work laptop
   dot-man template --set EMAIL=john@work.com --set HOST=work-laptop
   dot-man switch work
   # ~/.gitconfig now has actual email, not {{EMAIL}}
   
   # On personal laptop
   dot-man template --set EMAIL=john@personal.com --set HOST=home-pc
   dot-man switch personal
   # Same template, different values
   ```

9. **Apply Templates (--apply flag):**
   - Re-process already deployed files
   - Useful when you change a template variable
   - For each file with `template_vars`:
     - Read current file from repo
     - Apply current template variables
     - Overwrite deployed file
   - Display:
     ```
     ✓ Applied templates to 3 files:
       • ~/.gitconfig
       • ~/.bashrc
       • ~/.ssh/config
     ```

10. **Advanced: Default Values:**
    - Support fallback syntax: `{{VAR_NAME:default}}`
    - Example: `export EDITOR={{EDITOR:vim}}`
    - If `EDITOR` not defined, use `vim`
    - Prevents blank values

11. **Advanced: System Variables:**
    - Automatically populate some variables:
      - `{{SYSTEM_HOSTNAME}}`: From `os.uname()`
      - `{{SYSTEM_USER}}`: From `os.getenv('USER')`
      - `{{HOME}}`: Home directory path
    - Users can override these with --set

12. **Error Handling:**
    - If template_vars.json corrupted: Create new empty file
    - If variable referenced but not defined: Warn during deployment
    - If circular reference: Detect and error
    - If invalid variable name: "Invalid variable name. Use UPPERCASE_LETTERS only."

**Use Cases:**
- **Multi-machine setup:** Work laptop vs personal laptop
- **Environment-specific configs:** Dev vs production paths
- **User-specific values:** Email, name, preferences

**Exit Codes:**
- 0: Success
- 70: Invalid variable name
- 71: Template file corrupted
- 72: Circular reference detected

---

### **3.10 `dot-man branch list`**

**Purpose:** Display all branches in the dot-man repository.

**Options:**
- `-v, --verbose`: Show additional branch metadata
- `--remote`: Include remote branches

**Behavior:**

1. **Fetch Branch List:**
   - Query git for all local branches
   - Get current branch from `global.conf`
   - If `--remote`: Also fetch remote branches

2. **Display Format:**
   ```
   Branches
   ═══════════════════════════════════════════════════
   Branch            Active    Last Modified
   ───────────────────────────────────────────────────
   main              *         2025-11-15 14:30
   work                        2025-11-10 09:15
   minimal                     2025-11-01 16:45
   experimental               2025-11-14 11:20
   ═══════════════════════════════════════════════════
   4 branches (1 active)
   ```

3. **Current Branch Indicator:**
   - Mark with `*` or highlight in green
   - Must match branch in `global.conf`

4. **Verbose Mode:**
   - Show additional info:
     - Number of tracked files per branch
     - Commit count
     - Branch description (if set)
     - Last commit message
   ```
   Branches (Detailed)
   ═══════════════════════════════════════════════════════════════
   Branch       Active  Files  Commits  Last Commit
   ───────────────────────────────────────────────────────────────
   main         *       12     45       "Update bashrc aliases"
   work                 15     32       "Add work-specific paths"
   minimal              5      12       "Minimal config for servers"
   ═══════════════════════════════════════════════════════════════
   ```

5. **Remote Branches:**
   - If `--remote` and remote configured:
     - Show remote tracking branches
     - Indicate sync status with local
   ```
   Local Branches: 4
   ───────────────────────────────────────────────────
   main *
   work
   minimal
   
   Remote Branches: 3
   ───────────────────────────────────────────────────
   origin/main        (synced with local)
   origin/work        (2 commits ahead)
   origin/production  (not checked out locally)
   ```

**Exit Codes:**
- 0: Success
- 1: No branches found (corrupted repo)

---

### **3.11 `dot-man branch delete <branch-name>`**

**Purpose:** Delete a branch from the dot-man repository.

**Arguments:**
- `branch-name` (required): Branch to delete

**Options:**
- `--force, -f`: Skip confirmation and force delete even if unmerged
- `--remote`: Also delete from remote repository

**Behavior:**

1. **Safety Checks:**
   - Get current branch from `global.conf`
   - If `branch-name` == current_branch:
     - Error: "Cannot delete active branch 'main'"
     - Suggest: "Switch to another branch first: dot-man switch <other-branch>"
     - Exit with error

2. **Branch Existence Check:**
   - Query git for branch list
   - If branch doesn't exist:
     - Error: "Branch 'xyz' not found"
     - Show available branches
     - Exit

3. **Unmerged Changes Check:**
   - Check if branch has commits not in other branches
   - If unmerged and not `--force`:
     - Warn: "Branch 'experimental' has unmerged changes"
     - Show commit count: "3 commits unique to this branch"
     - Require `--force` flag to proceed

4. **Confirmation Prompt:**
   - Display warning:
     ```
     ⚠️  Delete branch 'work'?
     
     This will:
     • Remove branch from local repository
     • Delete all configuration unique to this branch
     • Cannot be undone (unless backed up)
     
     Continue? [y/N]
     ```
   - Skip if `--force` flag

5. **Local Deletion:**
   - Execute: `git branch -D <branch-name>`
   - Handle errors (branch locked, etc.)
   - Confirm success:
     ```
     ✓ Deleted branch 'work'
     ```

6. **Remote Deletion (if --remote):**
   - Check if remote is configured
   - Check if branch exists on remote
   - Execute: `git push origin --delete <branch-name>`
   - Handle errors:
     - Remote not reachable
     - Branch doesn't exist remotely
     - Permission denied
   - Confirm:
     ```
     ✓ Deleted branch 'work' from local repository
     ✓ Deleted branch 'work' from remote
     ```

7. **Cleanup:**
   - Remove any local references to deleted branch
   - Clean up git's internal state
   - Suggest running `git gc` if repo is large

**Error Handling:**
- If active branch: Cannot delete (suggest switch first)
- If doesn't exist: Show available branches
- If remote deletion fails: "Local branch deleted, but remote deletion failed"

**Exit Codes:**
- 0: Success
- 1: Cannot delete active branch
- 2: Branch not found
- 80: Unmerged changes (need --force)
- 81: Remote deletion failed

---

### **3.12 `dot-man remote get`**

**Purpose:** Display currently configured remote repository URL.

**Behavior:**

1. **Read Remote Configuration:**
   - Check `global.conf` for `[remote] url`
   - Also query git: `git remote get-url origin`
   - These should match (if not, warn)

2. **Display Output:**
   - If remote configured:
     ```
     Remote Repository
     ═══════════════════════════════════════════════════
     Name:     origin
     URL:      git@github.com:username/dotfiles.git
     Type:     SSH
     Status:   Reachable
     ═══════════════════════════════════════════════════
     ```
   - If no remote:
     ```
     No remote repository configured.
     
     To add a remote:
       dot-man remote set <url>
     
     Example:
       dot-man remote set git@github.com:username/dotfiles.git
     ```

3. **Additional Info (verbose):**
   - Test connectivity
   - Show last sync time
   - Display branch tracking info
   - Show remote branches available

4. **Mismatch Warning:**
   - If `global.conf` and git remote differ:
     ```
     ⚠️ Warning: Remote URL mismatch detected
     
     global.conf:  git@github.com:user/old-repo.git
     git remote:   git@github.com:user/new-repo.git
     
     Run 'dot-man doctor' to diagnose.
     ```

**Exit Codes:**
- 0: Success (remote shown or confirmed absent)
- 90: Mismatch detected

---

### **3.13 `dot-man remote set <url>`**

**Purpose:** Configure or update the remote repository URL.

**Arguments:**
- `url` (required): Git repository URL

**Options:**
- `--test`: Test connection before saving
- `--force`: Overwrite existing remote without confirmation

**Behavior:**

1. **URL Validation:**
   - Check format is valid git URL:
     - SSH: `git@host:user/repo.git`
     - HTTPS: `https://host/user/repo.git`
     - Local: `/path/to/repo.git` or `file:///path/to/repo`
   - If invalid:
     - Error: "Invalid git URL format"
     - Show examples
     - Exit

2. **Connection Test (if --test or auto):**
   - Attempt: `git ls-remote <url>`
   - If fails:
     - Warn: "Cannot reach remote. Possible issues:"
     - List: Authentication, network, URL typo, repo doesn't exist
     - Ask: "Save anyway? [y/N]"

3. **Existing Remote Check:**
   - Check if 'origin' already configured
   - If exists and not `--force`:
     ```
     ⚠️  Remote 'origin' already configured
     
     Current: git@github.com:user/old-repo.git
     New:     git@github.com:user/new-repo.git
     
     Replace? [y/N]
     ```

4. **Set Remote:**
   - If remote exists:
     - Execute: `git remote set-url origin <url>`
   - If doesn't exist:
     - Execute: `git remote add origin <url>`
   
5. **Update Configuration:**
   - Write to `global.conf`:
     ```ini
     [remote]
     url = <url>
     added_date = <timestamp>
     ```

6. **Success Confirmation:**
   ```
   ✓ Remote configured successfully
   
   Remote: git@github.com:username/dotfiles.git
   
   Next steps:
   • Push to remote: dot-man sync
   • Or pull from remote: dot-man sync --force-pull
   ```

7. **First-Time Setup Helper:**
   - If this is first remote being set:
     - Offer to push current branch:
       ```
       Push current configuration to remote? [y/N]
       
       This will create the repository on the remote.
       ```
     - If yes: Execute `dot-man sync`

**Error Handling:**
- If invalid URL: Show format examples
- If connection test fails: Warn but allow saving
- If git remote command fails: Show git error

**Exit Codes:**
- 0: Success
- 91: Invalid URL format
- 92: Remote operation failed

---

### **3.14 `dot-man backup create`**

**Purpose:** Manually create a backup of current repository state.

**Options:**
- `--message, -m <text>`: Description for this backup
- `--full`: Include entire repository (not just current branch)

**Behavior:**

1. **Pre-Backup:**
   - Check available disk space
   - Calculate size of backup
   - Warn if space insufficient

2. **Backup Creation:**
   - Generate timestamp: `YYYYMMDD_HHMMSS`
   - Create directory: `~/.config/dot-man/backups/backup_<timestamp>/`
   - Copy entire `repo/` directory
   - Include `.git/` directory for full restore capability

3. **Metadata Storage:**
   - Create `metadata.json` in backup directory:
     ```json
     {
       "timestamp": "20251116_143022",
       "branch": "main",
       "message": "Before major restructure",
       "dot_man_version": "1.0.0",
       "files_count": 12,
       "size_bytes": 2456789
     }
     ```

4. **Backup Limit Enforcement:**
   - Check existing backup count
   - If exceeds max (default: 5):
     - Identify oldest backup
     - Prompt: "Delete oldest backup (30 days old)? [y/N]"
     - If yes: Remove and proceed
     - If no: Create anyway (exceed limit)

5. **Success Report:**
   ```
   ✓ Backup created successfully
   
   Name:     backup_20251116_143022
   Size:     2.3 MB
   Branch:   main
   Location: ~/.config/dot-man/backups/backup_20251116_143022
   
   To restore: dot-man backup restore backup_20251116_143022
   ```

**Exit Codes:**
- 0: Success
- 100: Disk space insufficient
- 101: Backup creation failed

---

### **3.15 `dot-man backup list`**

**Purpose:** Display all available backups.

**Options:**
- `--verbose, -v`: Show detailed backup information

**Behavior:**

1. **Scan Backups Directory:**
   - List all subdirectories in `~/.config/dot-man/backups/`
   - For each, load `metadata.json`
   - Sort by timestamp (newest first)

2. **Display Table:**
   ```
   Available Backups
   ═══════════════════════════════════════════════════════════════
   Name                      Date                Branch    Size
   ───────────────────────────────────────────────────────────────
   backup_20251116_143022   2025-11-16 14:30   main      2.3 MB
   backup_20251115_091500   2025-11-15 09:15   work      1.8 MB
   backup_20251110_160000   2025-11-10 16:00   main      2.1 MB
   ═══════════════════════────────────────────────────────────────
   3 backups | Total size: 6.2 MB
   ```

3. **Verbose Mode:**
   - Show message/description
   - Show file count
   - Show last modified time
   - Show backup integrity status

4. **Empty State:**
   - If no backups:
     ```
     No backups found.
     
     Create a backup:
       dot-man backup create -m "Description"
     
     Backups are automatically created before:
     • Switching branches
     • Running sync --force-pull
     ```

**Exit Codes:**
- 0: Success

---

### **3.16 `dot-man backup restore <backup-name>`**

**Purpose:** Restore repository state from a backup.

**Arguments:**
- `backup-name` (required): Name of backup to restore (e.g., `backup_20251116_143022`)

**Options:**
- `--force, -f`: Skip confirmation prompt
- `--preview`: Show what would be restored without doing it

**Behavior:**

1. **Backup Validation:**
   - Check backup exists in `~/.config/dot-man/backups/`
   - If not found:
     - Error: "Backup '<name>' not found"
     - Run `dot-man backup list` to show available
     - Exit

2. **Load Backup Metadata:**
   - Read `metadata.json` from backup
   - Display backup information:
     ```
     Backup Details
     ═══════════════════════════════════════════════════
     Name:         backup_20251116_143022
     Created:      2025-11-16 14:30:22
     Branch:       main
     Message:      Before major restructure
     Files:        12 tracked files
     Size:         2.3 MB
     ═══════════════════════════════════════════════════
     ```

3. **Preview Mode (if --preview):**
   - Show what will be replaced:
     ```
     Restore Preview
     ─────────────────────────────────────────────────────
     Current State:
     • Branch: work
     • Last modified: 2025-11-17 10:00
     • 15 tracked files
     
     Will restore to:
     • Branch: main
     • Backup date: 2025-11-16 14:30
     • 12 tracked files
     
     Changes:
     • 3 files will be removed
     • 5 files will be replaced
     • 4 files unchanged
     ```
   - Exit without restoring

4. **Destructive Warning:**
   - Display prominent warning:
     ```
     ⚠️  WARNING: Restore will OVERWRITE current repository!
     
     This will:
     • Replace all files in the repository
     • Reset to branch: main
     • Lose ALL changes since: 2025-11-16 14:30
     • Cannot be undone (unless you create a new backup now)
     
     Current state will be lost unless you backup first.
     
     Continue? [y/N]
     ```
   - Require explicit confirmation unless `--force`

5. **Pre-Restore Safety Backup:**
   - Automatically create backup of current state
   - Message: "Auto-backup before restore"
   - Display: "✓ Current state backed up to: backup_20251117_..."

6. **Restore Process:**
   - Stop any running operations
   - Remove current `repo/` directory
   - Copy backup contents to `repo/`
   - Verify git repository integrity
   - Load branch from backup metadata
   - Update `global.conf` with restored branch

7. **Post-Restore Verification:**
   - Check git status
   - Verify all expected files present
   - Count files and compare to metadata
   - If mismatch: Warn "Restore may be incomplete"

8. **Deploy Restored Files:**
   - Ask user: "Deploy restored configuration to home directory? [y/N]"
   - If yes: Run deployment logic (like `deploy` command)
   - If no: Display "Repository restored. Run 'dot-man switch <branch>' to deploy."

9. **Success Report:**
   ```
   ✓ Restore completed successfully
   
   Restored from:    backup_20251116_143022
   Current branch:   main
   Files restored:   12
   
   Your repository has been restored to: 2025-11-16 14:30
   
   Next steps:
   • Verify with: dot-man status
   • Deploy files: dot-man switch main
   ```

**Error Handling:**
- If backup corrupted: "Backup appears corrupted. Cannot restore."
- If disk space insufficient: "Cannot restore: Insufficient disk space"
- If restore fails mid-operation: "Restore failed. Attempting rollback..."

**Exit Codes:**
- 0: Success
- 102: Backup not found
- 103: Backup corrupted
- 104: Restore failed

---

### **3.17 `dot-man conflicts list`**

**Purpose:** List all files with merge conflicts after a failed sync.

**Behavior:**

1. **Detect Merge State:**
   - Check if repository is in merge/rebase state
   - If not: "No conflicts. Repository is clean."
   - Exit early

2. **Parse Git Status:**
   - Execute: `git status --porcelain`
   - Look for 'U' status codes (unmerged)
   - Extract conflicted file paths

3. **Categorize Conflicts:**
   - **Both modified:** User and remote both changed same file
   - **Deleted by us:** Remote deleted, local modified
   - **Deleted by them:** Local deleted, remote modified
   - **Both added:** Same file added in both places

4. **Display Conflicts Table:**
   ```
   ⚠️  Merge Conflicts
   ═══════════════════════════════════════════════════════════════
   File                    Type              Modified By
   ───────────────────────────────────────────────────────────────
   .bashrc                BOTH MODIFIED     local + remote
   .vimrc                 BOTH MODIFIED     local + remote
   .gitconfig             DELETED BY THEM   local only
   ═══════════════════════════════════════════════════════════════
   3 conflicts detected
   
   Resolution Options:
   1. Edit manually:       vim ~/.config/dot-man/repo/.bashrc
   2. Keep local version:  dot-man conflicts resolve .bashrc --ours
   3. Keep remote version: dot-man conflicts resolve .bashrc --theirs
   4. After resolving all: dot-man sync --continue
   ```

5. **Show Conflict Markers:**
   - For each conflicted file, show excerpt:
     ```
     File: .bashrc (lines 23-30)
     ─────────────────────────────────────────────────────
     <<<<<<< HEAD (local)
     export PATH=/usr/local/bin:$PATH
     =======
     export PATH=/opt/homebrew/bin:$PATH
     >>>>>>> origin/main (remote)
     ─────────────────────────────────────────────────────
     ```

6. **Conflict Statistics:**
   - Count total conflicts
   - Count by type
   - Estimate resolution effort (simple vs complex)

**Exit Codes:**
- 0: Conflicts listed successfully
- 1: No conflicts found
- 110: Not in merge state

---

### **3.18 `dot-man conflicts resolve <file>`**

**Purpose:** Resolve a specific merge conflict interactively or automatically.

**Arguments:**
- `file` (required): Path to conflicted file (relative to repo)

**Options:**
- `--ours`: Keep local version (discard remote changes)
- `--theirs`: Keep remote version (discard local changes)
- `--edit`: Open file in editor for manual resolution
- `--diff`: Show diff between versions before choosing

**Behavior:**

1. **Validate Conflict Exists:**
   - Check file is in conflicted state
   - If not: "File '<file>' is not conflicted"
   - Exit

2. **Show Conflict Context (if --diff):**
   - Display side-by-side diff:
     ```
     Conflict in: .bashrc
     
     LOCAL (yours)              REMOTE (theirs)
     ──────────────────────────────────────────────────────
     export PATH=/local/bin     export PATH=/remote/bin
     alias ll='ls -lah'         alias ll='ls -la'
                                alias gs='git status'
     ```

3. **Automatic Resolution:**

   **Option A: --ours (keep local)**
   - Execute: `git checkout --ours <file>`
   - Stage file: `git add <file>`
   - Display: "✓ Kept local version of <file>"
   - Show what was discarded:
     ```
     Discarded remote changes:
     - Added alias gs='git status'
     - Modified PATH to /remote/bin
     ```

   **Option B: --theirs (keep remote)**
   - Execute: `git checkout --theirs <file>`
   - Stage file: `git add <file>`
   - Display: "✓ Kept remote version of <file>"
   - Show what was discarded:
     ```
     Discarded local changes:
     - alias ll was 'ls -lah', now 'ls -la'
     ```

4. **Manual Resolution (--edit or default):**
   - Get editor from environment (EDITOR/VISUAL)
   - Open file in editor
   - File contains git conflict markers:
     ```
     <<<<<<< HEAD
     export PATH=/local/bin
     =======
     export PATH=/remote/bin
     >>>>>>> origin/main
     ```
   - Wait for editor to close
   - After closing, check if markers still exist:
     - If yes: "Conflict markers still present. Continue editing? [y/N]"
     - If no: Stage file automatically

5. **Verification:**
   - After resolution, verify file is valid
   - For config files: Parse to check syntax
   - For shell scripts: Check for basic syntax errors
   - Warn if suspicious: "File may have resolution errors"

6. **Stage Resolved File:**
   - Execute: `git add <file>`
   - Display: "✓ Resolved and staged <file>"

7. **Progress Tracking:**
   - Count remaining conflicts
   - Display:
     ```
     ✓ Resolved: .bashrc
     
     Remaining conflicts: 2
     - .vimrc
     - .gitconfig
     
     Continue resolving or run: dot-man sync --continue
     ```

8. **Interactive Mode (no flags):**
   - Show options menu:
     ```
     Resolve conflict in: .bashrc
     
     Options:
     1. Keep local version (--ours)
     2. Keep remote version (--theirs)
     3. Edit manually
     4. Show diff
     5. Skip for now
     
     Choose [1-5]:
     ```
   - Process choice
   - Loop until resolved or skipped

**Error Handling:**
- If file doesn't exist: "File not found in repository"
- If not in conflict: "File is not conflicted"
- If editor fails: "Editor exited abnormally. File unchanged."

**Exit Codes:**
- 0: Success (conflict resolved)
- 1: File not conflicted
- 111: Editor failed
- 112: Resolution invalid


