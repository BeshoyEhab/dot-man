# Codebase Review & Future Improvements
> **Phase 5 of the dot-man Development Guide Manual**  
> Based on the extensive codebase analysis conducted for v0.9.0.

---

## 1. Architectural Observations & Technical Debt

During the documentation rewrite, several structural patterns and potential technical debt items were identified. Addressing these will improve maintainability as the project scales.

### 1.1 Tightly Coupled Mixins
The `DotManOperations` class relies on `SaveDeployMixin`, `BranchMixin`, and `StatusMixin`.
- **The Issue**: While this successfully split a 2000+ line file into smaller files, the mixins are highly interdependent. For example, `BranchMixin` calls `self.save_all()` (defined in `SaveDeployMixin`). This makes unit testing a single mixin in isolation difficult, as it requires mocking the entire `DotManOperations` state.
- **Improvement**: Consider moving from a Mixin pattern to a **Composition pattern**. `DotManOperations` could instantiate `self.save_engine = SaveDeployEngine(self.config, self.vault)`, passing dependencies explicitly rather than relying on `self`.

### 1.2 Vault Scalability (`vault.json`)
- **The Issue**: The `SecretVault` currently reads and parses the entire `vault.json` file into memory, and `batch()` writes the entire JSON tree back to disk. 
- **Improvement**: If users store thousands of secrets across many branches, this monolithic JSON read/write will become a bottleneck. Migrating to SQLite (`sqlite3`) or splitting the vault into per-branch files (`vault_main.json`, `vault_work.json`) would drastically improve I/O performance.

### 1.3 `files.py` Binary Detection
- **The Issue**: Binary files are skipped during secret scanning using a hardcoded list of extensions (`_BINARY_EXTENSIONS = {".jpg", ".png", ".so", ...}`).
- **Improvement**: Relying on extensions is fragile (e.g., an extension-less executable). Implementing a magic-byte check (checking if the file contains null bytes in the first 1024 bytes) would provide robust binary detection without external dependencies.

### 1.4 Cache Concurrency
- **The Issue**: The `_comparison_cache` in `files.py` relies on Python's Global Interpreter Lock (GIL) for thread safety during `ThreadPoolExecutor` concurrent reads/writes.
- **Improvement**: While safe in CPython, this is technically an implementation detail. Wrapping the cache in an explicit `threading.Lock` would make the code strictly thread-safe regardless of the Python runtime (e.g., PyPy).

---

## 2. Missing Documentation

While the core architecture, CLI, and security systems are now heavily documented, a few areas lack comprehensive coverage:

1. **The TUI System (`tui.py`, `tui_editor.py`)**: The Textual-based UI is currently experimental. There is no architectural documentation on how the TUI state reacts to the underlying `DotManOperations` state. A new specification (`docs/specs/tui.md`) should be created once the TUI stabilizes in v0.10.0.
2. **Hook Execution Environment**: `Section.pre_deploy` and `post_deploy` commands are executed via `subprocess.run(shell=True)`. Documentation should explicitly warn users about the environment variables available to these hooks (or the lack thereof) and exactly what directory they execute in.
3. **Backup Restoration Scenarios**: The `BackupManager` is well-written, but the user-facing documentation doesn't explain what happens to their local, uncommitted system files if they run `dot-man backup restore`. 

---

## 3. Proposed Future Features (Roadmap Additions)

Based on the architecture, the following features would naturally extend the system's capabilities:

### Interactive Conflict Resolution
Currently, `deploy_all` uses strategies like `replace` or `rename_old`. If a user modifies their local `~/.bashrc` but also pulls changes from the remote repository, a deploy will blindly overwrite the local changes (or rename them).
- **Proposal**: Implement a 3-way merge or an interactive prompt (similar to `git merge`) during deployment if the local file's `mtime` indicates it was modified after the last deployment.

### Rich Diffing
The `dot-man diff` command currently prints raw `git diff` output.
- **Proposal**: Route the diff output through the `rich` library's `Syntax` module to provide syntax-highlighted, colored diffs in the terminal, vastly improving UX.

### Secret Rotation
- **Proposal**: A CLI command `dot-man vault rotate` that generates a new Fernet key in `~/.config/dot-man/.key`, decrypts all secrets in `vault.json`, re-encrypts them with the new key, and securely deletes the old key.

### Dry-Run Enhancements
Currently, `--dry-run` prints what would happen during a deploy.
- **Proposal**: Enhance `--dry-run` to output a structured JSON plan (similar to Terraform's plan output), allowing users or CI/CD pipelines to programmatically verify what configuration changes are about to occur.
