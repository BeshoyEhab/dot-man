# Contributing to dot-man

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or: source .venv/bin/activate.fish

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
dot-man --version
pytest tests/ -v
```

## Project Structure

```
dot-man/
├── dot_man/              # Main package (20 modules)
│   ├── __init__.py       # Package version
│   ├── cli/              # CLI commands (Click-based, 28 files)
│   │   ├── main.py       # Entry point: calls cli()
│   │   ├── interface.py  # Click group definition (DotManGroup)
│   │   ├── common.py     # Shared utilities: require_init, completions,
│   │   │                 # get_secret_handler, parse_branch_arg
│   │   ├── __init__.py   # Imports all *_cmd modules (registration trigger)
│   │   └── *_cmd.py      # 21 individual command modules
│   ├── operations.py     # DotManOperations singleton + iter_section_paths
│   ├── save_deploy_ops.py # SaveDeployMixin: save_all, deploy_all (two-phase)
│   ├── branch_ops.py     # BranchMixin: switch_branch, revert_file
│   ├── status_ops.py     # StatusMixin: get_status, audit, orphans
│   ├── core.py           # GitManager (wraps GitPython)
│   ├── config.py         # Re-export shim only (backward compat)
│   ├── global_config.py  # GlobalConfig: reads/writes global.toml
│   ├── dotman_config.py  # DotManConfig: reads/writes dot-man.toml
│   ├── section.py        # Section dataclass + hook alias resolution
│   ├── files.py          # File I/O: atomic copy, compare, cache
│   ├── secrets.py        # Secret detection patterns + filter_secrets()
│   ├── vault.py          # SecretVault: Fernet encrypt/decrypt
│   ├── lock.py           # FileLock: fcntl advisory locking (Linux/macOS)
│   ├── backups.py        # BackupManager: timestamped archives
│   ├── interactive.py    # Interactive wizards (init, global config)
│   ├── ui.py             # Rich console wrappers
│   ├── utils.py          # Misc helpers
│   ├── constants.py      # All paths, defaults, HOOK_ALIASES
│   └── exceptions.py     # Custom exception hierarchy + ErrorDiagnostic
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   └── test_*.py         # Test modules
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # System architecture
│   ├── DEVELOPMENT_GUIDE_MANUAL.md  # In-depth system explanation
│   ├── roadmap.md        # Development roadmap
│   └── specs/            # Detailed specifications
│       ├── commands.md   # Command specifications
│       └── security.md   # Security specifications
├── install.sh            # Installation script
├── uninstall.sh          # Uninstallation script
├── pyproject.toml        # Project configuration
└── README.md             # User documentation
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=dot_man --cov-report=term-missing

# Run specific test
pytest tests/test_core.py -v
```

## Code Style

This project uses:

- **Black** for formatting (line length: 88)
- **Ruff** for linting
- **mypy** for type checking

```bash
# Format code
black dot_man/ tests/

# Lint code
ruff check dot_man/ tests/

# Check types
mypy dot_man/ --ignore-missing-imports
```

## Adding a New Command

1. Create `dot_man/cli/mycommand_cmd.py`
2. Define your Click command decorating with `@cli.command()`
3. Import it in `dot_man/cli/__init__.py` (this triggers registration)
4. Add shell completion in `dot_man/cli/common.py` if needed
5. Add business logic to the appropriate operations mixin (`save_deploy_ops.py`, `branch_ops.py`, or `status_ops.py`)
6. Add tests to `tests/test_mycommand_cmd.py`
7. Update `README.md` command table and `CHANGELOG.md`

Example command file (`dot_man/cli/mycommand_cmd.py`):

```python
import click
from .common import require_init, success, error
from .interface import cli

@cli.command()
@click.option("--verbose", "-v", is_flag=True)
@require_init
def mycommand(verbose: bool):
    """Short description for help text.

    Longer description with examples.
    """
    # Business logic goes in operations mixins
    from ..operations import get_operations
    ops = get_operations()
    # ... implementation
    success("Done!")
```

> **Important:** Commands are registered via import side effects. The `@cli.command()` decorator must run at import time. Adding the import to `cli/__init__.py` is what makes the command available. Without that import, the command will not appear in `dot-man --help`.

## Architecture Overview

```
CLI (cli/) or TUI (interactive.py)
        │
        └──→ DotManOperations (operations.py, singleton via get_operations())
                  │
                  ├──→ SaveDeployMixin (save_deploy_ops.py)
                  │       ├──→ files.py (copy, compare, atomic_write)
                  │       └──→ vault.py (stash/restore secrets)
                  ├──→ BranchMixin (branch_ops.py)
                  │       └──→ core.py (GitManager)
                  └──→ StatusMixin (status_ops.py)
                          └──→ files.py (get_file_status)
```

**Key rule:** `config.py` is a re-export shim only. Import config classes directly from their actual modules:
```python
from dot_man.global_config import GlobalConfig
from dot_man.dotman_config import DotManConfig
from dot_man.section import Section
```

## Adding Secret Patterns

Edit `dot_man/secrets.py`:

```python
DEFAULT_PATTERNS: list[SecretPattern] = [
    # Add new pattern
    SecretPattern(
        name="My Pattern",
        pattern=re.compile(r"pattern_here"),
        severity=Severity.HIGH,
        description="Description of what this detects",
    ),
    # ... existing patterns
]
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes following the pre-push checklist in `AGENTS.md`
4. Add tests for new functionality (see test guidelines in `AGENTS.md`)
5. Ensure all checks pass: `black`, `ruff`, `mypy`, `pytest`
6. Submit a pull request

## Questions?

Open an issue for:

- Bug reports
- Feature requests
- Questions about the codebase
