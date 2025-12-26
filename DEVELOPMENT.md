# Developer Guide

Welcome to the `dot-man` development guide! This document provides instructions for setting up your development environment, running tests, and understanding the project structure.

## 📚 Documentation Index

Detailed specifications have been moved to the `docs/` directory:

- **[Command Specifications](docs/specs/commands.md)**: Detailed behavior, options, and error codes for all CLI commands.
- **[Security Specification](docs/specs/security.md)**: Secret detection, filtering logic, and auditing.
- **[Roadmap & Timeline](docs/roadmap.md)**: Development phases, milestones, and success metrics.

## 🛠️ Development Setup

### Prerequisites

- Python 3.8+
- Git
- `pip` or `poetry` (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .[dev]
```

This installs the package in editable mode along with development dependencies (pytest, black, mypy, etc.).

## 🧪 Running Tests

We use `pytest` for testing.

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=dot_man
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
│   ├── cli.py            # Click commands (~1200 lines)
│   ├── tui.py            # Interactive TUI (textual)
│   ├── core.py           # Git operations and core logic
│   ├── config.py         # Configuration parsing (INI)
│   ├── constants.py      # Paths, defaults, patterns
│   ├── files.py          # File operations (copy, move)
│   ├── secrets.py        # Secret detection logic
│   ├── utils.py          # Helper functions
│   └── exceptions.py     # Custom exception classes
│
├── tests/                # Test suite
│   ├── conftest.py       # Pytest fixtures
│   └── test_core.py      # Core module tests
│
├── docs/                 # Documentation
│   ├── roadmap.md        # Project roadmap
│   └── specs/            # Detailed specifications
│       ├── commands.md   # Command specifications
│       └── security.md   # Security specifications
│
├── README.md             # User-facing overview
├── CONTRIBUTING.md       # Contributor guidelines
├── DEVELOPMENT.md        # This file
├── CHANGELOG.md          # Version history
└── pyproject.toml        # Project metadata and dependencies
```

## 🎨 Code Style

We follow **PEP 8** and use **Black** for formatting.

```bash
# Format code
black .

# Check types
mypy dot_man
```

## 🚀 Release Process

1.  Update version in `pyproject.toml` and `dot_man/__init__.py`.
2.  Update `CHANGELOG.md`.
3.  Tag the release: `git tag v1.0.0`.
4.  Push tags: `git push --tags`.
5.  Build and publish (CI/CD handles this usually).
