# Developer Guide

Welcome to the `dot-man` development guide! This document provides instructions for setting up your development environment, running tests, and understanding the project structure.

## 📚 Documentation Index

Detailed specifications have been moved to the `docs/` directory:

- **[Command Specifications](docs/specs/commands.md)**: Detailed behavior, options, and error codes for all CLI commands.
- **[Security Specification](docs/specs/security.md)**: Secret detection, filtering logic, and auditing.
- **[Roadmap & Timeline](docs/roadmap.md)**: Development phases, milestones, and success metrics.

## 🛠️ Development Setup

### Prerequisites

- Python 3.9+
- Git
- `pip` or `uv` (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with development dependencies (pytest, black, mypy, ruff, etc.).

## 🧪 Running Tests

We use `pytest` for testing.

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=dot_man --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_core.py
```

## 📂 Project Structure

```
dot-man/
├── dot_man/              # Source code
│   ├── __init__.py       # Package version
│   ├── cli/              # CLI commands (modular Click package)
│   │   ├── __init__.py   # CLI exports
│   │   ├── main.py       # Entry point
│   │   ├── interface.py  # Click group definition
│   │   ├── common.py     # Shared CLI utilities
│   │   ├── init_cmd.py   # dot-man init
│   │   ├── add_cmd.py    # dot-man add
│   │   ├── status_cmd.py # dot-man status
│   │   ├── switch_cmd.py # dot-man switch
│   │   ├── deploy_cmd.py # dot-man deploy
│   │   ├── edit_cmd.py   # dot-man edit
│   │   ├── audit_cmd.py  # dot-man audit
│   │   ├── backup_cmd.py # dot-man backup
│   │   ├── branch_cmd.py # dot-man branch
│   │   ├── remote_cmd.py # dot-man remote / sync
│   │   ├── config_cmd.py # dot-man config
│   │   ├── clean_cmd.py  # dot-man clean
│   │   ├── revert_cmd.py # dot-man revert
│   │   └── tui_cmd.py    # dot-man tui
│   ├── operations.py     # Business logic (single source of truth)
│   ├── core.py           # Git operations wrapper
│   ├── config.py         # TOML configuration parsing
│   ├── constants.py      # Paths, defaults, patterns
│   ├── files.py          # File operations (atomic copy, move)
│   ├── secrets.py        # Secret detection logic
│   ├── vault.py          # Encrypted secret vault
│   ├── backups.py        # Backup manager
│   ├── lock.py           # File locking
│   ├── interactive.py    # Interactive prompts (questionary)
│   ├── tui.py            # Interactive TUI (textual)
│   ├── tui_editor.py     # TUI config editor
│   ├── ui.py             # Rich output helpers
│   ├── utils.py          # Helper functions
│   └── exceptions.py     # Custom exception classes
│
├── tests/                # Test suite (98 tests)
│   ├── conftest.py       # Pytest fixtures
│   ├── test_cli_commands.py
│   ├── test_cli_revert.py
│   ├── test_clean.py
│   ├── test_completion.py
│   ├── test_core.py
│   ├── test_files_atomic.py
│   ├── test_hooks.py
│   ├── test_interactive.py
│   ├── test_iter_files_optimization.py
│   ├── test_lock.py
│   ├── test_performance_logic.py
│   ├── test_secrets.py
│   └── test_vault.py
│
├── docs/                 # Documentation
│   ├── roadmap.md        # Project roadmap
│   └── specs/            # Detailed specifications
│       ├── commands.md   # Command specifications
│       └── security.md   # Security specifications
│
├── scripts/              # Helper scripts
├── integration/          # Integration tests
├── README.md             # User-facing overview
├── CONTRIBUTING.md       # Contributor guidelines
├── DEVELOPMENT.md        # This file
├── CHANGELOG.md          # Version history
├── TODO.md               # Development roadmap & tasks
├── install.sh            # Installation script
├── uninstall.sh          # Uninstallation script
└── pyproject.toml        # Project metadata and dependencies
```

## 🏗️ Architecture

```
cli/ ────┐
         ├──> operations.py ─┬─> config.py (TOML)
tui.py ──┘                   ├─> core.py (Git)
                             ├─> files.py
                             ├─> secrets.py
                             ├─> vault.py
                             ├─> backups.py
                             └─> lock.py
```

`operations.py` is the single source of truth for all business logic. Both the CLI and TUI call into it.

## 🎨 Code Style

We follow **PEP 8** and use **Black** for formatting.

```bash
# Format code
black dot_man/ tests/

# Lint code
ruff check dot_man/ tests/

# Check types
mypy dot_man/
```

## 🚀 Release Process

1.  Update version in `pyproject.toml` and `dot_man/__init__.py`.
2.  Update `CHANGELOG.md`.
3.  Tag the release: `git tag v0.7.0`.
4.  Push tags: `git push --tags`.
5.  Build and publish (CI/CD handles this usually).
