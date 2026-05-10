# AGENTS.md - Guidelines for AI Models

This file contains instructions for AI models working on the dot-man project.

---

## Project Overview

**dot-man** is a dotfile manager with git-powered branching. Each branch represents a different configuration (work, personal, minimal, server).

- **Language**: Python 3.9+
- **CLI Framework**: Click
- **Testing**: pytest
- **Current Version**: 0.8.0 (Beta)

---

## File Update Checklist

When making changes, always update these files as needed:

| File | When to Update |
|------|----------------|
| `CHANGELOG.md` | Add new features, bug fixes, changes under current version |
| `TODO.md` | Mark completed items with ✅, add new items |
| `README.md` | Update command tables, add examples, update features |
| `docs/roadmap.md` | Update version status, add completed items |
| `pyproject.toml` | Bump version for releases |
| `AGENTS.md` | Add new guidelines as project evolves |

---

## Making Commits

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `perf` - Performance improvement
- `docs` - Documentation
- `test` - Tests
- `refactor` - Code refactoring
- `chore` - Maintenance

**Examples:**
```
feat(diff): add dot-man diff command

- Show uncommitted changes
- Compare branches with --branch flag
- Show staged changes

Closes #123
```

---

## Shell Completions

When adding new CLI commands, **ALWAYS add shell completions**:

1. Import completion functions from `dot_man.cli.common`:
```python
from .common import complete_branches, complete_tags, complete_commits, complete_profiles, complete_template_keys
```

2. Add `shell_complete` to click arguments:
```python
@click.argument("branch", shell_complete=complete_branches)
@click.option("--commit", "-c", shell_complete=complete_commits)
```

3. Add new completion functions if needed in `common.py`:
```python
def complete_new_thing(ctx, param, incomplete):
    """Shell completion callback for new thing."""
    try:
        # Implementation...
    except Exception:
        return []
```

---

## Working with Tests

### ✅ Strong Tests Requirements

When writing tests, follow these guidelines:

1. **Use real git repositories** - Create actual `git.Repo` instances
2. **Test actual file operations** - Use `tmp_path` to create real files
3. **Test real CLI commands** - Use `CliRunner` from Click
4. **Assert real behavior** - Check actual values, not just existence
5. **Clean up after tests** - Use fixtures properly

### Example of Strong Test

```python
def test_git_manager_create_branch(self, tmp_path):
    """Test creating a branch - REAL test."""
    from dot_man.core import GitManager
    from git import Repo
    
    # Create real git repo
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    
    # Configure git
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")
    
    # Create initial commit
    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial")
    
    # Test GitManager
    gm = GitManager(repo_dir)
    gm.create_branch("new-branch")
    
    assert "new-branch" in gm.list_branches()  # REAL assertion
```

### ❌ Weak Tests to Avoid

```python
def test_weak():  # DON'T DO THIS
    """Weak test - just checks if method exists."""
    from dot_man.core import GitManager
    assert hasattr(GitManager, "create_branch")  # This is useless

def test_also_weak():  # DON'T DO THIS
    """Weak test - no real assertions."""
    from dot_man.config import Section
    section = Section(name="test", paths=[], repo_base="test")
    _ = section.name  # Just accessing, no assertion
```

### Test File Location

- Put tests in `tests/test_<module_name>.py`
- Use descriptive class names: `TestGitManagerBasic`, `TestSectionClass`
- Group related tests in classes

---

## Running Tests

### Using pipx (recommended on Linux systems)

```bash
# Install dev dependencies with pipx
pipx install -e ".[dev]"

# Run all tests
pipx run pytest tests/ -v

# Run with coverage
PYTHONPATH=. pipx run pytest tests/ --cov=dot_man --cov-report=term

# Run specific test file
PYTHONPATH=. pipx run pytest tests/test_core.py -v
```

### Using pip with --break-system-packages (alternative)

```bash
pip install -e ".[dev]" --break-system-packages
pytest tests/ -v
```

### Standard pytest commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=dot_man --cov-report=term

# Run specific test file
pytest tests/test_core.py -v

# Run with verbose output
pytest -vv
```

### Important: Tests directory requires __init__.py

The `tests/` directory must contain a `__init__.py` file to be a proper package:
```
tests/
├── __init__.py      # REQUIRED - makes tests a package
├── conftest.py
├── utils.py
└── test_*.py
```

Without `tests/__init__.py`, pytest will fail with `ModuleNotFoundError`.

---

## Code Style

- **Format**: Black (line length 88)
- **Type Checking**: mypy
- **Linting**: ruff

```bash
# Format code
black dot_man/ tests/

# Type check
mypy dot_man/

# Lint
ruff check dot_man/ tests/
```

---

## Scenario Responses

### When adding a new CLI command:

1. Create `dot_man/cli/<command>_cmd.py`
2. Import in `dot_man/cli/__init__.py`
3. Add shell completions in `dot_man/cli/common.py`
4. Add tests in `tests/test_<command>_cmd.py`
5. Update `README.md` command tables
6. Update `CHANGELOG.md`

### When adding a new module:

1. Create `dot_man/<module>.py`
2. Add `__all__` exports
3. Add type hints throughout
4. Add tests in `tests/test_<module>.py`
5. Update `CHANGELOG.md`

### When fixing a bug:

1. Write a test that reproduces the bug first
2. Fix the bug
3. Verify the test passes
4. Update `CHANGELOG.md` if significant

### When adding a feature:

1. Implement the feature
2. Write tests for it
3. Update `CHANGELOG.md`
4. Update `TODO.md` to mark complete if applicable

---

## Version Bump Checklist

When releasing a new version:

1. ✅ Update `pyproject.toml` version (e.g., 0.8.0 → 0.9.0)
2. ✅ Update `CHANGELOG.md` - move "Unreleased" to version date
3. ✅ Update `TODO.md` - mark completed items with ✅
4. ✅ Update `README.md` - update "What's New" section
5. ✅ Update `docs/roadmap.md` - update version status
6. ✅ Run full test suite: `pytest`
7. ✅ Run coverage: `pytest --cov=dot_man`
8. ✅ Run linting: `ruff check dot_man/ tests/`
9. ✅ Run type check: `mypy dot_man/`
10. ✅ Create git commit and tag

---

## Project Structure

```
dot-man/
├── dot_man/              # Main package
│   ├── cli/             # CLI commands
│   │   ├── main.py      # Entry point
│   │   ├── interface.py # CLI interface
│   │   ├── common.py    # Common utilities & completions
│   │   └── *_cmd.py     # Individual commands
│   ├── core.py          # GitManager
│   ├── operations.py   # Business logic
│   ├── config.py       # Config classes
│   ├── secrets.py      # Secret detection
│   ├── vault.py       # Secret storage
│   └── ...
├── tests/               # Test files
├── scripts/            # Scripts & completions
└── docs/              # Documentation
```

---

## Key Commands

| Command | Description |
|---------|-------------|
| `dot-man init` | Initialize repository |
| `dot-man switch` | Switch branches |
| `dot-man status` | Show status |
| `dot-man audit` | Scan for secrets |
| `dot-man diff` | Show changes |
| `dot-man log` | Show commit history |
| `dot-man template` | Template variables |
| `dot-man profile` | Machine profiles |

---

## Updating This File

When updating AGENTS.md, consider:

1. **New patterns** - Add examples of good code patterns
2. **New scenarios** - Document how to handle new situations
3. **Test examples** - Add more test examples if patterns emerge
4. **File updates** - Update the file checklist if project structure changes

Add new guidelines at the appropriate section. Use clear headers and examples.

---

## Questions?

Check the existing code and tests for patterns. When in doubt, look at similar commands in `dot_man/cli/` directory.