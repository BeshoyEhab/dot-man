# Contributing

## Development Setup

```bash
# Clone
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man

# Install with dev dependencies
uv sync --extra dev

# Run checks
uv run black dot_man/ tests/
uv run ruff check dot_man/ tests/
uv run mypy dot_man/ --ignore-missing-imports
uv run pytest tests/ -v
```

## Pre-commit Hooks

```bash
pre-commit install
```

Runs Black, ruff, and mypy automatically on every commit.

## Code Style

- **Formatter**: Black (line length 88)
- **Linter**: ruff (rules: E, F, W, I)
- **Type checker**: mypy (`--ignore-missing-imports`)

## Adding Commands

1. Create `dot_man/cli/<command>_cmd.py`
2. Import in `dot_man/cli/__init__.py`
3. Add completions in `dot_man/cli/common.py`
4. Add tests in `tests/test_<command>_cmd.py`
5. Update docs and CHANGELOG

## Testing

```bash
# All tests
uv run pytest tests/ -v

# Specific file
uv run pytest tests/test_core.py -v

# With coverage
uv run pytest --cov=dot_man --cov-report=term
```

## Commit Messages

```
<type>(<scope>): <subject>

feat(diff): add dot-man diff command
fix(vault): handle missing key file
docs(readme): update installation instructions
test(status): add JSON output tests
```
