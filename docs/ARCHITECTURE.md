# dot-man Architecture & Design Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Directory Structure](#directory-structure)
3. [Core Modules](#core-modules)
4. [CLI Architecture](#cli-architecture)
5. [Data Flow](#data-flow)
6. [Design Decisions](#design-decisions)
7. [Alternatives Considered](#alternatives-considered)

---

## Project Overview

**dot-man** is a dotfile manager that uses Git branches to manage different configurations (work, personal, server, etc.). Instead of managing dotfiles directly on your system, you store them in a Git repository and deploy them using branch switching.

### Core Concept
```
┌─────────────────────────────────────────────────────────┐
│                    Your System                          │
│  ~/.bashrc, ~/.gitconfig, ~/.config/nvim/             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  dot-man                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │  main   │    │  work   │    │ server  │  ...       │
│  │ branch  │    │ branch  │    │ branch  │            │
│  └─────────┘    └─────────┘    └─────────┘            │
│                         │                                │
│              saves changes from your system             │
│              deploys files from branch to your system  │
└─────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
dot-man/
├── dot_man/                  # Main package
│   ├── __init__.py          # Version, exports
│   ├── cli/                 # CLI commands
│   │   ├── main.py          # Entry point
│   │   ├── interface.py     # Click group definition
│   │   ├── switch_cmd.py    # Switch command
│   │   ├── log_cmd.py      # Log command
│   │   ├── tag_cmd.py      # Tag command
│   │   └── ...             # Other commands
│   ├── core.py              # Git operations (GitManager)
│   ├── operations.py        # Main business logic
│   ├── config.py            # Config file parsing
│   ├── global_config.py     # Global settings
│   ├── files.py             # File operations
│   ├── secrets.py           # Secret detection
│   ├── vault.py             # Secret storage
│   ├── backups.py           # Backup management
│   └── constants.py          # Constants, paths
├── tests/                   # Test suite
├── docs/                    # Documentation
└── pyproject.toml           # Package config
```

---

## Core Modules

### 1. `constants.py` - Configuration Constants

Defines paths and default values used throughout the project:

```python
# Key paths
DOT_MAN_DIR = Path.home() / ".config" / "dot-man"  # ~/.config/dot-man/
REPO_DIR = DOT_MAN_DIR / "repo"                     # ~/.config/dot-man/repo/
BACKUPS_DIR = DOT_MAN_DIR / "backups"               # ~/.config/dot-man/backups/
GLOBAL_TOML = DOT_MAN_DIR / "global.toml"           # ~/.config/dot-man/global.toml

# Defaults
DEFAULT_BRANCH = "main"
```

**Why separate constants?** Easy to mock in tests, single source of truth for paths.

### 2. `core.py` - Git Operations (GitManager)

Wraps GitPython to provide a clean interface for Git operations:

```python
class GitManager:
    def list_branches(self) -> list[str]: ...
    def list_tags(self) -> list[str]: ...
    def checkout(self, branch: str, create: bool = False): ...
    def commit(self, message: str) -> str | None: ...
    def get_commits(self, count: int = 10) -> Iterator[dict]: ...
```

**Why wrap GitPython?** 
- Provides type hints
- Consistent error handling
- Adds convenience methods (e.g., `branch_exists()`, `get_tag_commit()`)

### 3. `config.py` & `global_config.py` - Configuration

Two levels of configuration:

| Config | Location | Purpose |
|--------|----------|---------|
| `config.py` | `~/.config/dot-man/repo/dot-man.toml` | Section definitions, paths to track |
| `global_config.py` | `~/.config/dot-man/global.toml` | App settings, current branch, preferences |

```python
# dot-man.toml example:
[bashrc]
paths = ["~/.bashrc"]
secrets_filter = true
post_deploy = "source ~/.bashrc"

[nvim]
paths = ["~/.config/nvim"]
```

### 4. `operations.py` - Main Business Logic

Central hub that coordinates all operations:

```python
class DotManOperations(BranchMixin, SaveMixin, DeployMixin, StatusMixin):
    def save_all(self) -> dict: ...       # Save current files to repo
    def deploy_all(self) -> dict: ...     # Deploy files from repo
    def switch_branch(self, target: str): ...  # Save + deploy + checkout
    def get_status(self) -> dict: ...     # Get current status
```

**Why a central class?** Single instance management, shared state between operations.

### 5. `files.py` - File Operations

Low-level file operations:

```python
def compare_files(path1: Path, path2: Path) -> bool: ...
def copy_file(src: Path, dst: Path) -> tuple[bool, str]: ...
def atomic_write_text(path: Path, content: str): ...
```

### 6. `secrets.py` - Secret Detection

Detects and redacts secrets in files:

```python
class SecretGuard:
    def should_redact(self, file: Path, content: str) -> bool: ...
```

Uses regex patterns to detect:
- Private keys (`-----BEGIN RSA PRIVATE KEY-----`)
- AWS keys (`AKIAIOSFODNN7EXAMPLE`)
- API tokens, passwords, etc.

### 7. `vault.py` - Secret Storage

Stores detected secrets securely for restoration after deployment.

---

## CLI Architecture

### Entry Point

```python
# dot_man/cli/main.py
from .interface import cli

def main():
    cli()
```

### Click Group Structure

```python
# dot_man/cli/interface.py
@click.group(cls=DotManGroup)
def cli():
    """dot-man: The Dotfile Manager for Professionals."""
    ...
```

### Command Registration

Each command is a separate module that registers with the CLI:

```python
# dot_man/cli/switch_cmd.py
from .interface import cli as main

@main.command()
@click.argument("branch")
def switch(branch: str):
    ...
```

### Why Separate Files?
- Single responsibility
- Easy to test independently
- Clear separation of concerns

---

## Data Flow

### Switch Command Flow

```
dot-man switch work
        │
        ▼
┌───────────────────┐
│ 1. Save Phase     │
│ - scan sections   │
│ - copy files to   │  ~/.config/dot-man/repo/
│   repo            │
│ - detect secrets  │
│ - commit changes  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 2. Checkout Phase │
│ - git checkout    │
│   work branch     │
│ - reload config   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 3. Deploy Phase   │
│ - scan sections   │
│ - compare files  │
│ - copy from repo │
│   to ~/.config   │
│ - run hooks      │
└───────────────────┘
```

### Configuration Loading

```
dot-man start
     │
     ▼
┌─────────────────┐
│ Load global.toml│  ~/.config/dot-man/global.toml
│ - current_branch│
│ - remote_url   │
│ - preferences  │
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Load dot-man.toml│  ~/.config/dot-man/repo/dot-man.toml
│ - sections      │
│ - paths         │
│ - hooks         │
└─────────────────┘
```

---

## Design Decisions

### 1. Git-Based Storage

**Decision:** Store dotfiles in Git repository, not a special file format.

**Why?**
- Already familiar to developers
- Version control is free
- Branch-based workflow is intuitive
- Easy to share/backup

**Alternative Considered:**
- JSON/YAML config (chezmoi) - Good, but less flexible
- SQLite database - Overkill for this use case

### 2. Section-Based Configuration

**Decision:** Use sections in dot-man.toml to group related files.

```toml
[bashrc]
paths = ["~/.bashrc"]

[nvim]
paths = ["~/.config/nvim"]
```

**Why?**
- Groups related files together
- Each section can have own hooks
- Easy to understand

**Alternative Considered:**
- Flat list - Hard to manage hooks for groups
- Directory-based - Less explicit

### 3. Secret Redaction

**Decision:** Detect and redact secrets automatically when saving to repo.

**Why?**
- Security by default
- Prevents accidentally committing secrets

**Alternative Considered:**
- Ask user every time - Too many prompts
- Ignore secrets - Too risky

### 4. Tag System

**Decision:** Lightweight Git tags for marking commits.

**Why?**
- Native Git feature
- No extra storage needed
- Easy to switch to

**Alternative Considered:**
- Custom refs in .dot-man/ - More complex
- Database - Overkill

### 5. Optional TUI

**Decision:** Provide both CLI and TUI (Textual-based).

**Why?**
- CLI for power users
- TUI for visual users
- Both use same backend

**Alternative Considered:**
- TUI only - Too complex
- CLI only - Less accessible

---

## Alternatives Considered

### 1. Why Not Use Existing Tools?

| Tool | Why Not? |
|------|----------|
| chezmoi | Uses different paradigm (stateless), no branching |
| yadm | Good, but less active development |
| GNU Stow | No branching, no secrets detection |
| rcm | Less features |

**Decision:** Build our own with:
- Git branching as core concept
- Secret detection
- TUI for accessibility

### 2. Why Click for CLI?

**Alternatives Considered:**
- argparse - Too verbose
- typer - Good, but Click has better shell completion
- docopt - No type hints

**Decision:** Click provides:
- Shell completion out of the box
- Type hints support
- Subcommands made easy

### 3. Why GitPython?

**Alternatives:**
- dulwich - Pure Python but slower
- subprocess calls to git - Works but harder to maintain

**Decision:** GitPython is:
- Well-maintained
- Pythonic interface
- Good performance

### 4. Why TOML for Config?

**Alternatives:**
- JSON - No comments
- YAML - Slower, more complex
- INI - Limited structure

**Decision:** TOML:
- Comments supported
- Type-safe
- Good for nested configs

---

## Test Coverage Notes

### Current Coverage: 45%

The coverage is lower than 80% because:
1. **TUI tests** (0% coverage) - Optional component, 1226 lines
2. **CLI command internals** - Many error paths hard to test
3. **Integration-heavy** - Requires mocking many Git operations

### What's Well Tested:
- GitManager operations
- File comparison
- Config parsing
- Core business logic

### What's Hard to Test:
- Interactive UI (TUI)
- Error recovery paths
- Full end-to-end flows

---

## Future Improvements

### For Test Coverage
- Add more integration tests with fixtures
- Test error conditions
- Add property-based tests

### For Features
- Performance optimization (batch operations)
- Plugin system
- Cloud sync backends

### For Documentation
- API documentation
- Architecture diagrams
- Video tutorials