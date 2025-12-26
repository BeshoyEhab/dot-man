# Contributing to dot-man

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: source venv/bin/activate.fish

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
│   ├── cli.py            # Click commands (~1200 lines)
│   ├── tui.py            # Interactive TUI (textual)
│   ├── core.py           # Git operations wrapper
│   ├── config.py         # INI file parsing
│   ├── secrets.py        # Secret detection patterns
│   ├── files.py          # File operations
│   ├── utils.py          # Helper functions
│   ├── constants.py      # Paths, defaults, patterns
│   └── exceptions.py     # Custom exception classes
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   └── test_core.py      # Core module tests
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
pytest tests/test_core.py::TestSecretScanner -v
```

## Code Style

This project uses:

- **Black** for formatting (line length: 88)
- **isort** for import sorting
- **mypy** for type checking

```bash
# Format code
black dot_man/ tests/

# Check types
mypy dot_man/
```

## Adding a New Command

1. Add the command function to `dot_man/cli.py`
2. Use the `@main.command()` decorator
3. Add `@require_init` if the command needs initialization
4. Document with a docstring (shown in `--help`)
5. Add tests to `tests/test_core.py`

Example:

```python
@main.command()
@click.option("--verbose", "-v", is_flag=True)
@require_init
def mycommand(verbose: bool):
    """Short description for help text.

    Longer description with examples.
    """
    # Implementation here
    pass
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
