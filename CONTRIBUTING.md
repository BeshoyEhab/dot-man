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
├── dot_man/              # Main package
│   ├── __init__.py       # Package version
│   ├── cli/              # CLI commands (modular Click package)
│   │   ├── main.py       # Entry point
│   │   ├── interface.py  # Click group definition
│   │   ├── common.py     # Shared CLI utilities (decorators, helpers)
│   │   ├── *_cmd.py      # Individual command modules
│   │   └── __init__.py   # CLI exports
│   ├── operations.py     # Business logic (single source of truth)
│   ├── core.py           # Git operations wrapper
│   ├── config.py         # TOML configuration parsing
│   ├── secrets.py        # Secret detection patterns
│   ├── vault.py          # Encrypted secret vault
│   ├── backups.py        # Backup manager
│   ├── lock.py           # File locking
│   ├── files.py          # File operations (atomic writes)
│   ├── interactive.py    # Interactive prompts
│   ├── tui.py            # Interactive TUI (textual)
│   ├── tui_editor.py     # TUI config editor
│   ├── ui.py             # Rich output helpers
│   ├── utils.py          # Helper functions
│   ├── constants.py      # Paths, defaults, patterns
│   └── exceptions.py     # Custom exception classes
├── tests/                # Test suite (98 tests)
│   ├── conftest.py       # Pytest fixtures
│   └── test_*.py         # Test modules
├── docs/                 # Documentation
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
mypy dot_man/
```

## Adding a New Command

1. Create a new file `dot_man/cli/mycommand_cmd.py`
2. Define your Click command
3. Register it in `dot_man/cli/interface.py`
4. Import it in `dot_man/cli/__init__.py`
5. Add business logic to `dot_man/operations.py`
6. Add tests to `tests/test_mycommand.py`

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
    # Business logic should go in operations.py
    from ..operations import DotManOperations
    ops = DotManOperations()
    # ... implementation
    success("Done!")
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
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Format code with Black
7. Submit a pull request

## Questions?

Open an issue for:

- Bug reports
- Feature requests
- Questions about the codebase
