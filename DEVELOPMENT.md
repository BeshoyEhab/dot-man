# Developer Guide
> **Phase 4 of the dot-man Development Guide Manual**

Welcome to the `dot-man` development guide! This document provides instructions for setting up your development environment, navigating the architecture, running the rigorous test suite, and contributing core features.

## 📚 Documentation Index

- **[Architecture](docs/ARCHITECTURE.md)**: Full system architecture, layer diagrams, schema, and design tradeoffs.
- **[Development Guide Manual](docs/DEVELOPMENT_GUIDE_MANUAL.md)**: Deep in-depth system explanation.
- **[Command Specifications](docs/specs/commands.md)**: Detailed behavior for all CLI commands.
- **[Security Specification](docs/specs/security.md)**: Secret detection, filtering logic, and auditing.
- **[Roadmap & Timeline](docs/roadmap.md)**: Development phases and milestones.

---

## 🛠️ Development Setup

### 1. Prerequisites
- Python 3.10+
- Git
- `pip` or `uv` (recommended for faster dependency resolution)

### 2. Clone & Virtual Environment
```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies & Hooks
```bash
# Install package in editable mode with development tools
pip install -e ".[dev]"

# (Optional but recommended) Install pre-commit hooks
pip install pre-commit
pre-commit install
```
*The pre-commit hook automatically runs `black`, `ruff`, and `mypy` before you commit.*

---

## 🏗️ Adding a Core Feature (Tutorial)

Adding a CLI command is simple (see `CONTRIBUTING.md`), but adding a fundamental capability to dot-man requires touching multiple layers. Here is the strict workflow for adding a core feature (e.g., adding a new update strategy).

### Step 1: Update Configuration Models
If your feature requires a configuration toggle, start in `dot_man/section.py` and `dot_man/dotman_config.py`.
- Add the typed attribute to the `Section` dataclass.
- Update `DotManConfig._validate_schema()` to accept the new TOML key.
- Update `DotManConfig.get_section()` to read the key and supply a default.

### Step 2: Implement Business Logic in Operations Mixins
Find the appropriate mixin. 
- Does it involve saving or deploying? Edit `dot_man/save_deploy_ops.py`.
- Does it involve reading repository state without mutating it? Edit `dot_man/status_ops.py`.
- Ensure your method accesses dependencies lazily via `self.global_config` or `self.git`.

### Step 3: Implement Foundation Code
If your operation needs a new file primitive, write it in `dot_man/files.py`.
- **Crucial**: Always use `atomic_write_text()` for file mutation. Never use standard `open(..., 'w')` directly unless writing to `tmp` or caches.

### Step 4: Write Real Tests
dot-man enforces strict testing standards (see `AGENTS.md`). **Tests that only check if a method exists or a class can be instantiated are banned.**

```python
# GOOD: Testing actual behavior with a real repo
def test_my_new_feature(tmp_path):
    from git import Repo
    from dot_man.operations import DotManOperations
    
    # 1. Setup real Git repository
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)
    
    # 2. Setup mock dot-man environment
    # Use conftest fixtures if available, or point ops to tmp_path
    
    ops = DotManOperations()
    # 3. Assert real filesystem side effects
```

---

## 🧪 Running & Debugging Tests

### Test Execution
```bash
# Run all tests (Fast)
pytest tests/ -v

# Run with coverage (Gatekeeper)
pytest --cov=dot_man --cov-report=term-missing
```

### Test Fixtures (`conftest.py`)
Familiarize yourself with the fixtures in `tests/conftest.py`. The suite provides pre-configured mock environments (`mock_env`, `mock_git_repo`) that isolate tests to `/tmp` directories, preventing your local `~/.config/dot-man/` from being destroyed during a test run.

### Debugging the CLI
If a command is failing locally, use the built-in debug logger:
```bash
dot-man --debug <command>
```
This forces all underlying `logging.debug()` calls in `files.py`, `core.py`, and `vault.py` to write to `~/.config/dot-man/dot-man.log`. 

If you want to stream that directly to the terminal without opening the log file:
```bash
dot-man -v <command>
```

---

## 🎨 Code Style

We follow **PEP 8** strictly.

```bash
# 1. Format code (Max line length 88)
black dot_man/ tests/

# 2. Lint code (Catches unused imports, f-string errors)
ruff check dot_man/ tests/ --fix

# 3. Check types (Required: 0 errors)
mypy dot_man/ --ignore-missing-imports
```

If `mypy` complains about a library lacking stubs (like `tomlkit` or `GitPython`), suppress it inline using `# type: ignore` but leave a comment explaining why.

---

## 🚀 Release Process

When a milestone is complete:
1. Bump version strings in `pyproject.toml` and `dot_man/__init__.py`.
2. Move items from `Unreleased` to a new version header in `CHANGELOG.md`.
3. Check off completed checkboxes in `TODO.md`.
4. Update `docs/roadmap.md` to mark the phase as complete.
5. Run the **Full Pre-Push Quality Checklist** (`AGENTS.md`): `black`, `ruff`, `mypy`, `pytest`, `pytest --cov`.
6. Commit, tag (`git tag v0.X.0`), and push tags.
