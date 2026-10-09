# AGENTS.md - Guidelines for AI Models

Instructions for AI models working on dot-man. Keep this file in sync with
`TODO.md` and `docs/roadmap.md` — numbers and priorities live there; this file
holds the rules. You may self-update it when versions bump, patterns change,
or priorities shift (see "AI Autonomy" at the bottom).

---

## Project Snapshot

**dot-man** — git-powered dotfile manager; each branch is a configuration
(work, personal, minimal, server).

- **Language**: Python 3.10+ · **CLI**: Click · **Tests**: pytest · **Packages**: `uv`
- **Version**: 1.4.0 · **Tests**: 2350 passing · **Coverage**: 96% · **Docs**: mkdocs Material on GitHub Pages
- **CI**: GitHub Actions with `uv` (`uv.lock` committed); pre-commit runs Black, ruff, mypy; `uv build` in the publish workflow

Canonical command vocabulary: **`navigate`** (alias `nav`) switches
configurations. `switch`/`checkout` are deprecated shims, kept until v2.0.

---

## Development Rules

### Setup

```bash
git clone https://github.com/BeshoyEhab/dot-man.git
cd dot-man
uv sync --extra dev
pre-commit install
```

Every command below runs under `uv run` (uv-managed venv). Never bare
`pytest`/`black` — `uv run` is the repo standard.

### Code style

- **Format**: Black (line length 88) · **Lint**: ruff (`E, F, W, I`) · **Types**: mypy (`--ignore-missing-imports`, 0 errors)

```bash
uv run black dot_man/ tests/
uv run ruff check dot_man/ tests/       # append --fix to autofix
uv run mypy dot_man/ --ignore-missing-imports
```

### Testing

```bash
uv run pytest tests/ -v                        # all tests
uv run pytest tests/test_core.py -v            # one file
uv run pytest --cov=dot_man --cov-report=term  # coverage (must not decrease)
```

Strong-test requirements (see examples below):

1. Real `git.Repo` instances, real files via `tmp_path`, real CLI via `CliRunner`
2. Assert values and behavior — never existence (`hasattr`, `callable`, `is not None`, bare imports are NOT tests)
3. Group related tests in classes; put files in `tests/test_<module>.py`
4. `tests/__init__.py` must exist or pytest fails with `ModuleNotFoundError`

### Commits

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`.
Example: `feat(diff): add dot-man diff command`. Never commit secrets; if a
commit fails hooks, fix forward — don't amend the failed commit.

---

## Design Principles

1. **Schema first, then build.** When a feature connects components (hooks,
   config, CLI), write the unifying schema before code: what are the units,
   how do they connect, what is duplicated? Example: one global hook schema
   covering section hooks, `file:` scripts, global `pre_<cmd>`/`post_<cmd>`
   scripts, aliases, and placeholders — deduplicate the systems against it,
   then document from it.
2. **Happy path first.** A normal user is productive in 5 minutes via
   `init` → `add` → `status` → `navigate`. New features must be discoverable
   from there, never required up front. Prefer sensible defaults over new
   options.
3. **One vocabulary.** `navigate` for switching configurations; `{{ }}`
   template syntax for substitution (hook `{x}` is the shell-friendly
   spelling of the same names); `ExitCode` for exits. Never introduce a
   second name or syntax for an existing concept.
4. **Centralized errors.** Failures exit via `raise SystemExit(ExitCode.X)`,
   `error(..., exit_code=...)`, or `handle_exception()` — never `sys.exit()`.
   `DotManGroup.invoke()` already routes uncaught command errors centrally;
   per-command handlers delegate: `handle_exception(e, "<Context>")`.

---

## Pre-Push Quality Checklist

Before EVERY commit/push, in order — all must pass with zero errors:

```bash
uv run black dot_man/ tests/
uv run ruff check dot_man/ tests/
uv run mypy dot_man/ --ignore-missing-imports
uv run pytest tests/ -v
uv run pytest --cov=dot_man --cov-report=term
```

Fix before committing. Do NOT push with known errors.

---

## Scenario Responses

### Adding a CLI command

1. Create `dot_man/cli/<command>_cmd.py`; register it via import in `dot_man/cli/__init__.py`
2. Add completions with the `@completes` decorator (next section)
3. Route failures through `handle_exception(e, "<Command>")` with `ExitCode` values
4. Strong tests in `tests/test_<command>_cmd.py`
5. Update `README.md` tables, `CHANGELOG.md`, `TODO.md` if applicable
6. Run the full Pre-Push Quality Checklist

### Adding a module

1. Create `dot_man/<module>.py` with `__all__` exports and type hints throughout
2. Strong tests in `tests/test_<module>.py`
3. Update `CHANGELOG.md`; run the full checklist

### Fixing a bug

Reproduce with a failing test first → fix → verify green → update
`CHANGELOG.md` if significant → full checklist.

### Adding a feature

Schema first (Principle 1) → tests → implement → `CHANGELOG.md` + `TODO.md`
→ full checklist.

---

## Shell Completions

The engine (`dot_man/cli/completion_engine.py`) reads commands, options,
choices, and defaults from the Click tree. Extend it with `@completes` —
never hand-written callbacks:

```python
from .completion_engine import CompletionContext, ProviderResult, completes

@completes("bootstrap", param="pm")
def _complete_bootstrap_pm(ctx: CompletionContext) -> ProviderResult:
    """Complete package manager names for the bootstrap command."""
    return [("brew", "macOS package manager"), ("apt", "Debian/Ubuntu")]
```

Providers return plain values or `(value, description)` pairs. Dynamic,
git-backed providers live in `dot_man/cli/completions.py` and must never
raise — return `[]` on failure:

```python
def complete_branches(ctx, param, incomplete):
    """Shell completion callback for branches."""
    try:
        # Implementation...
    except Exception:
        return []
```

---

## Strong vs Weak Tests

Strong test — real repo, real files, real assertion:

```python
def test_git_manager_create_branch(self, tmp_path):
    """Test creating a branch - REAL test."""
    from dot_man.core import GitManager
    from git import Repo

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test")
        config.set_value("user", "email", "test@test.com")

    (repo_dir / "test.txt").write_text("test")
    repo.index.add(["test.txt"])
    repo.index.commit("Initial")

    gm = GitManager(repo_dir)
    gm.create_branch("new-branch")

    assert "new-branch" in gm.list_branches()  # REAL assertion
```

Weak tests — NEVER write these (existence checks test Python, not our code):

```python
def test_weak():  # DON'T DO THIS
    from dot_man.core import GitManager
    assert hasattr(GitManager, "create_branch")  # useless

def test_also_weak():  # DON'T DO THIS
    from dot_man.config import Section
    section = Section(name="test", paths=[], repo_base="test")
    _ = section.name  # no assertion at all
```

---

## Section Config Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `paths` | `list[str]` | required | File/directory paths to track |
| `repo_base` | `str` | auto | Base directory name in repo |
| `repo_path` | `str` | None | Explicit repo path for single files |
| `secrets_filter` | `bool` | `true` | Enable secret detection |
| `update_strategy` | `str` | `"replace"` | `"replace"`, `"rename_old"`, `"ignore"` |
| `deploy_method` | `str` | `"copy"` | `"copy"` or `"symlink"` |
| `include` / `exclude` | `list[str]` | `[]` | Glob patterns to include/exclude |
| `pre_deploy` / `post_deploy` | `str` | None | Shell command around deploy; may embed `file:<script> [args]` (resolved from `<repo>/hooks/`, fallback `~/.config/dot-man/hooks/`) |
| `on_activate` / `on_deactivate` | `str` | None | Shell command on branch switch to/from |
| `inherits` | `list[str]` | `[]` | Template names to inherit |
| `follow_symlinks` | `bool` | `false` | Follow symlinks during traversal |
| `shared` | `bool` | `false` | Propagate edits to non-overriding branches |
| `ignored_directories` | `list[str]` | defaults | Directories skipped during traversal |
| `encrypted` / `encryption_method` / `encryption_recipient` | `bool` / `str` / `str` | `false` / `"gpg"` / None | Per-section encryption |

### Quickshell Config Example

```toml
[quickshell-ii]
paths = ["~/.config/quickshell/ii"]
deploy_method = "copy"
post_deploy = "quickshell_reload"
on_deactivate = "killall qs 2>/dev/null || true"
on_activate = "qs -c ii &"
```

`quickshell_reload`, `quickshell_restart`, `quickshell_validate` are
`HOOK_ALIASES` resolved by `Section._resolve_hook()`, which also resolves
`{section_name}`, `{config_root}`, `{config_name}`, `{paths}`, `{branch}`
(`{qs_config}` is the backward-compat alias for `{config_name}`).

---

## Key Commands

| Command | Description |
| ------- | ----------- |
| `dot-man init` | Initialize repository |
| `dot-man add <path>` | Track files |
| `dot-man status` | Show status |
| `dot-man navigate <branch>` | Switch configurations (canonical; `nav` alias; `switch`/`checkout` deprecated until v2.0) |
| `dot-man audit` | Scan for secrets |
| `dot-man diff` | Show changes |
| `dot-man log` | Show commit history |
| `dot-man template` | Template variables |
| `dot-man profile` | Machine profiles |

---

## File Update Checklist

| File | When to Update |
| ---- | -------------- |
| `CHANGELOG.md` | New features, bug fixes, changes under Unreleased |
| `TODO.md` | Check off items, add new ones (source of truth for priorities/numbers) |
| `README.md` | Command tables, examples, version, coverage |
| `docs/roadmap.md` | Version status, completed items |
| `pyproject.toml` + `dot_man/__init__.py` | Version bumps (keep the two in sync) |
| `AGENTS.md` | New principles/patterns as the project evolves |

---

## Version Bump Checklist

1. Bump `pyproject.toml` **and** `dot_man/__init__.py` (e.g., 1.4.0 → 1.5.0)
2. Move `CHANGELOG.md` "Unreleased" to the version date
3. Check off `TODO.md`; update `README.md` (Features, metrics, coverage); update `docs/roadmap.md`; refresh this file's snapshot (version, tests, coverage)
4. Run the full quality gate (`black --check`, `ruff`, `mypy`, `pytest -v`, coverage)
5. Smoke-test the artifact: `uv build`, install the wheel in a clean venv, run `dot-man --help` and `dot-man doctor`
6. Commit and tag
6. **Policy**: majors remove/change APIs (e.g., dropping `switch`/`checkout` lands in v2.0); minors only add deprecation notices

---

## Active Priorities (detail in TODO.md)

1. **Simplification & real-world usability** — happy path, two-level help (`help`/`help-all` + man page), defaults over options, one onboarding, `next_steps` everywhere, docs real-world-first
2. **Coverage floor** — raise the lowest modules (current table in TODO.md; regenerate before trusting)
3. **Global hook schema + template vars in config values** — schema first, then deduplicate and document from it
4. **v2.0 removals** — `switch`/`checkout` shims (kept with warnings until then)
5. **Parked** — Plugin API (too big; revisit after simplification)

---

## Project Structure

```
dot-man/
├── dot_man/              # Main package
│   ├── cli/              # CLI commands (registered via imports in __init__.py)
│   │   ├── main.py       # Entry point (calls cli() from interface.py)
│   │   ├── interface.py  # Shared Click group (DotManGroup)
│   │   ├── common.py     # ExitCode, error(), handle_exception(), guards
│   │   ├── completions.py      # Dynamic completion providers
│   │   ├── completion_engine.py # @completes registry + --complete protocol
│   │   └── *_cmd.py      # One file per command
│   ├── core.py           # GitManager
│   ├── operations.py     # DotManOperations (mixin composition root)
│   ├── *_ops.py          # Operation mixins (branch, status, save/deploy, ...)
│   ├── section.py        # Section config + hook/placeholder resolution
│   ├── hooks.py          # Global hooks + file: script resolution
│   ├── exceptions.py     # DotManError hierarchy (carries exit_code) + diagnostics
│   ├── ui.py             # Rich console helpers (never sys.exit)
│   ├── config.py / secrets.py / vault.py / ...
├── tests/                # tests/test_*.py (+ required __init__.py)
├── scripts/              # Shell helpers (path-setup.sh, utils.sh)
└── docs/                 # mkdocs Material site + roadmap
```

---

## AI Autonomy

You may self-update this file when versions bump, milestones complete, new
patterns emerge, or priorities shift. Keep the checklist, key commands, and
priorities in sync with `TODO.md` and `docs/roadmap.md`.

## Questions?

Check existing code and tests for patterns first — similar commands in
`dot_man/cli/` are the reference implementation.
