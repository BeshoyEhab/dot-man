# Changelog

All notable changes to dot-man will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Navigate to a commit/tag now deploys and records the branch** — previously
  only branch navigation ran `deploy_all` and persisted `current_branch`;
  commit/tag navigation dropped you into a detached HEAD with the old files.
  All three paths now share one save→switch→deploy pipeline.
- **Pre-switch backup on the live navigate path** — navigating creates a
  recovery backup of tracked files before deploying the target configuration.
- **`checkout_commit` updates the working tree** — it moved the branch ref
  only, so `rollback` and `navigate <tag>`/`<sha>` deployed stale file content;
  it now checks out the commit properly.
- **`ensure_directory` no longer relaxes existing directory modes** — deploying
  `~/.ssh/config` used to chmod `~/.ssh` to `0755`, breaking ssh.
- **`create_symlink` keeps the destination when its backup fails** — a failed
  backup previously still deleted the file, silently destroying user data.
- **Binary-copy failures are surfaced** — a failed copy was reported as
  "no change" (and directory deploys counted the file as success); it now
  raises so callers record the error.
- **`export` honors `--branch` and `--include-secrets`** — tar/zip now export
  the requested branch's committed tree via `git archive` (previously the
  flags were silently ignored); JSON gets a real ISO-8601 `exported_at` and a
  repo-relative `repo_path`.
- **`status --json` emits valid JSON** — the repository info panel used to
  print to stdout before the JSON, breaking `json.loads`; human output is now
  gated on non-JSON mode.
- **Non-atomic config writes could truncate `*.toml`** — `write_config_file`
  now routes through `atomic_write_text` (temp file + `os.replace`).
- **First-run onboarding no longer hijacks `--help`/`--version` or scripts** —
  it runs only for an interactive bare `dot-man` or `dot-man init`; added
  `--no-onboarding`.
- **`dot_man/completions` is now a real package** — the missing `__init__.py`
  made `__file__` `None`, so `dot-man completions` crashed locating its scripts.
- **Section encryption fields are forwarded to `Section`** — `encrypted`,
  `encryption_method`, and `encryption_recipient` were parsed but discarded.
- **`[templates]`/`[secrets]` are reserved tables** — they can no longer be
  mistaken for a user section.
- **`import chezmoi`/`import all` no longer crash on empty directories** —
  fixed operator precedence in chezmoi detection.

### Removed

- **Dead `BranchMixin.switch_branch`** — no production caller; superseded by
  the unified navigate pipeline.

## [1.5.0] - 2026-10-09

### Added

- **Full coverage floor (every module ≥ 90%)** — cleared the sub-90 tail with strong tests
  across 17 modules: `navigate_preview` 69%→100%, `init_cmd` 70%→98%, `edit_cmd` 73%→99%,
  `log_cmd` 79%→97%, `revert_cmd` 80%→100%, `clean_cmd` 81%→96%, `restore_cmd` 82%→98%,
  `hooks_cmd` 83%→94%, `shared_sync` 84%→99%, `hooks` 85%→98%, `status_ops` 85%→100%,
  `common` 86%→99%, `show_cmd` 86%→100%, `save_deploy_ops` 86%→99%, `add_cmd` 88%→100%,
  `verify_cmd` 88%→100%; test isolation gaps closed in the conftest registry
  (`clean_cmd.REPO_DIR`, `hooks.HOOKS_DIR`/`DOT_MAN_DIR` — hook tests previously touched
  the real `~/.config/dot-man/hooks`); total suite 2350 passing, coverage 92%→96%
  (302 missed, down from 646)
- **Backup coverage floor** — `backups.py` 71%→100%, `cli/backup_cmd.py` 72%→95% (+16 strong tests: missing-path skips, OSError cleanup, manifest roundtrips, CLI create/list/restore flows); total suite 1985 passing, coverage 90%→91%
- **Lock coverage + cleanup fix** — `lock.py` 79%→100% (+5 strong tests: missing parents, real fcntl contention, open/flock OSError, unlock tolerance); failed lock acquisition now resets `_fd` to `None` instead of holding a closed fd
- **Merge coverage** — `merge.py` 80%→100% (+13 strong tests: marker parsing, missing-file paths, idempotent inject, replace position, content extraction, direct-file listing, merge/dedup strategies); total suite 2003 passing
- **Utils coverage** — `utils.py` 80%→100% (+6 strong tests: editor fallback chain, `open_in_editor` paths, stat-error tolerance); total suite 2009 passing, coverage 91%→92%
- **UI coverage** — `ui.py` 81%→100% (7 weak existence checks replaced with 17 real output/behavior assertions); total suite 2019 passing
- **Config coverage** — `dotman_config.py` 82%→100% (+17 strong tests: TOML priority, template inheritance, section validation, `validate()`); total suite 2036 passing
- **Operations coverage** — `operations.py` 83%→100% (+6 strong tests: traversal filters, DELETED reporting, outside-tree tolerance); total suite 2042 passing
- **Black-box test rewrite** — core/config/section/init suites rewritten against the CLI and public API only (real `git.Repo`s, hermetic `HOME`, registry-based patch fixtures in `tests/conftest.py`, dead `tests/utils.py` removed); the sweep exposed 14 suspected bugs, 13 fixed below and 1 rejected as intended behavior (duplicate section paths stay verbatim so saves never silently rewrite config); total suite 2117 passing, coverage 92%
- **Help-before-init invariant sweep** — every invocable name in the Click tree (canonical commands, aliases, deprecated shims, nested subcommands) now gets `--help` on a virgin hermetic env in one parametrized test, locking the whole bug-7 class repo-wide (mutation-verified: re-adding a group-level `@require_init` turns exactly the `tag <sub>` cases red); `config get branch` and the navigate/switch tests no longer hardcode `main` — they compare against the branch git is actually on (they previously passed vacuously on the stale recorded value); total suite 2212 passing, coverage 92% (646 missed, down from 653)

- **Unified hook engine** — new `dot_man/hook_engine.py`: one resolve path (alias → placeholders → `file:`) and one shell runner for all hook shell; auto-detected hooks now resolve `{config_name}`; deploy hook failures warn instead of vanishing
- **Canonical `ExitCode` enum** (`dot_man/cli/common.py`) — `OK=0`, `ERROR=1`, `USAGE=2`, `CONFIG=7`, `INTERRUPTED=130`; single vocabulary for every exit path
- **Centralized error handling** — `DotManGroup.invoke()` routes unexpected failures from *every* command through `handle_exception()`; `ClickException`/`Abort`/`Exit`/`SystemExit` pass through untouched so `--help`, usage errors (exit 2), and deliberate exits keep working
- **Hook scripts directory** — section hooks accept `file:<script> [args]` tokens (e.g. `post_deploy = "echo 'start'; file:log.sh 'hi'"`), resolved from `<repo>/hooks/` (versioned per branch) with `~/.config/dot-man/hooks/` fallback; missing scripts raise `ConfigurationError`, `../` escapes rejected, exec bit auto-added; `on_activate`/`on_deactivate` now also get alias/placeholder resolution
- **Two-level help** — `dot-man help` and bare `--help` show the 6 happy-path commands (`init`, `add`, `status`, `navigate`, `deploy`, `doctor`) with a pointer to `dot-man help-all` (full listing incl. aliases and deprecated shims); static man page at `docs/man/dot-man.1`, installed via `dot-man help --install-man`
- **Template variables in config values** — `{{section_name}}`, `{{config_name}}`, `{{branch}}`, `{{paths}}` (plus machine vars and conditionals) render in section settings at load via the existing template engine; unknowns pass through literally; validation runs after rendering
- **Happy path guidance** — `add`, `deploy`, and `status` (only with pending changes) end with shared `next_steps` pointing forward along `init` → `add` → `status` → `navigate`; wizard finale renders through the same block; stale `switch` teaching removed from `add`
- **Sensible defaults surface** — default `dot-man.toml` slimmed to a short header + 2 examples (teaches `navigate`, links docs site); `config list` hides machine internals and points at `config defaults`
- **5-minute guide** — new `getting-started/five-minutes.md` first in the docs nav (install → init → add → status → navigate with expected outputs)
- **Command pages open with examples** — every `commands/` page leads with a verified real-world example; fixed stale flags along the way (`deploy --branch`, `diff --rich`, `log --oneline`, `revert --all`, `tag show`, `completions install`, `watch --no-commit`, `save [MESSAGE]`), corrected `other.md` (phantom `interface`/`migrate` sections removed), fixed `save` docs to `--commit -m` (positional messages never worked)
- **Global hooks fire in save/deploy/add** — `pre_<cmd>`/`post_<cmd>` scripts run around real work (skipped on dry-run/abort/no-op) with per-command env; failures warn and continue, never block
- **Auto-install on detection** — `add` applies detected section hooks like the wizard does; detection expanded (foot, bspwm, qtile, eww, mako with real reloads; helix, zed, yazi, ghostty, river, niri for tracking)
- **Import fixes** — chezmoi `dot_` prefixes map to dotfiles (no more `..double-dot` destinations); dry-run summaries count the files they list (with singular grammar); migration walkthroughs for chezmoi/yadm/stow in `commands/import.md`
- **15 new tests** in `tests/test_exit_codes.py` — exit-code preservation, `handle_exception` routing (`navigate`, `bootstrap`, `config get`, `doctor`), central group handling, `DotManError` code propagation

- **Shell completions for `add` command** — file/directory path completion using `@completes("add", param="path")` decorator
- **Shell completions for `bootstrap` command** — package manager name completion (`brew`, `apt`, `dnf`, `pacman`, etc.) via `@completes("bootstrap", param="pm")` decorator
- **19 new documentation pages** — dedicated pages for `init`, `add`, `deploy`, `tag`, `log`, `diff`, `revert`, `import`, `export`, `discover`, `encrypt`, `hooks`, `template`, `profile`, `watch`, `rollback`, `backup`, `verify`, `completions` commands
- **Docs navigation restructured** — commands grouped by category (Core, Configuration, Inspection, Tags, Encryption, Import/Export, Hooks, Shell)
- **Roadmap updated** — consistent with v1.4.0 state, removed stale duplicate sections
- **Unified onboarding** — the init wizard is the single interactive path (first-run tutorial menu and Architecture/Manual sections removed; `config tutorial` stays as opt-in reference); wizard suggests hooks inline, shows a hook example, and ends with a live `status`; finale teaches `navigate`/`help-all`

### Fixed

- **`revert -c` restore built paths outside the repository** — the commit path computed
  `target.relative_to(REPO_DIR.parent)`, which can never point inside the repo, so restoring
  a tracked file from a commit always failed with `fatal: path ... exists on disk, but not
  in <commit>`; it now resolves the section's repo path the same way `diff`/`log` do
- **`shared_sync` never excluded the current branch** — `current = self.git.current_branch`
  compared against the uncalled bound method, so the edited branch was treated as a
  propagation target and showed up in `skipped`/`unchanged` report buckets; it now calls
  `current_branch()`
- **`verify` reported broken symlinks as missing** — `Path.exists()` follows links, so a
  broken symlink fell into the `Missing path` branch and the dedicated `Broken symlink`
  check was unreachable; the symlink check now runs first
- **`init` records the branch git actually created** — `global.toml` unconditionally wrote the `DEFAULT_BRANCH` constant (`main`) while `git init` honours the host's `init.defaultBranch` (and `--import` keeps the source repo's branch), so `status`, `{branch}` and `navigate` could disagree with git from the first second (`global.toml` said `main`, repo sat on `master`); init now records `current_branch` straight from git, and an `--import` records the source branch
- **`init --import <github url>` reaches the clone** — `--import` was typed `click.Path(exists=True)`, so any URL died at parse time with a usage error (exit 2) and the entire GitHub branch (`_parse_github_url`, clone, the trailing-slash fix) was unreachable from the CLI; validation moved into the import code, which also gives local paths the CLI's own error (exit 1) instead of a click usage message — and the unreachable duplicate `_clone_github_repo` retry that sat after `error()` (which raises) is gone
- **`tag switch` warns on dirty worktrees** — the dirty-worktree guard lived only in `log_cmd`; the shared helper moved to `cli/common.py::warn_if_dirty()` so both HEAD-moving paths warn before abandoning uncommitted changes
- **Template conditionals case-insensitive** — `{{if eq branch "main"}}`-style conditionals compared exactly, so `Darwin` vs `darwin` (or any case variant) silently took the false branch; values now compare case-insensitively
- **Same-basename files no longer collide** — `get_repo_path()` dropped intermediate directories, so `~/.config/a/x` and `~/.config/b/x` both landed on `repo_base/x`; paths under a tracked root keep their structure relative to that root
- **`init` no longer overwrites `.gitignore`** — a re-run replaced the user's file with the default patterns; it now merges, appending only what's missing
- **First `init` no longer offers to "DELETE all data"** — the CLI creates `DOT_MAN_DIR` on every run (for logs), so `init` read mere directory existence as "already initialized"; the reinitialize prompt now requires an actual repo (`.git` present)
- **Invalid branch names rejected at creation** — `create_branch("has space")` wrote a ref git ignores (`warning: ignoring ref with broken name`), leaving `list_branches()` and branch stats disagreeing; names now pass `git check-ref-format --branch` before anything is written
- **`get_status()` reports staged changes** — the `new` bucket was unreachable (the index-vs-worktree diff never reports additions) and staged edits/deletions were invisible; a HEAD-vs-index pass fills them, deduplicates files seen by both diffs, and works on an unborn HEAD
- **`tag <sub> --help` works before init** — the init guard sat on the *group* callback, which Click runs after resolving the subcommand but before parsing its `--help`, so `tag list --help` printed the welcome banner (exit 1) while every other help worked; the guard moved to each subcommand, matching `branch`/`remote`
- **`log checkout <tag>` warns on dirty worktrees** — shared `_warn_if_dirty()` with `_checkout_commit`, so uncommitted changes are never abandoned silently (the `current_branch` parameter was accepted but ignored)
- **Bare-string `paths` rejected** — `paths = "~/a"` was silently coerced into one (possibly bogus) path, hiding typos behind confusing not-found errors later; it's now a `ConfigValidationError` like the other schema violations
- **`deploy_method`/`update_strategy` validated at construction** — `Section()` stored garbage verbatim (e.g. `deploy_method = "rsync"` then silently behaved as `copy`); validation moved into `Section.__init__`, and the loader's duplicate checks were removed so there's one place that validates
- **Schema warnings visible** — unknown-key warnings went only to the log file that nothing reads during normal runs; they now print to the console as well
- **GitHub import URLs with a trailing slash** — `dot-man import https://github.com/user/dots/` missed every parse regex, fell through to the local-path branch, and failed with "Path does not exist"; the slash is stripped before `.git` is appended
- **`{branch}` placeholder reads the recorded branch** — it resolved against raw git with `search_parent_directories=True`, leaking whatever repository sat at or above `REPO_DIR` (observed: a personal branch named `custom`) and disagreeing with `operations.current_branch`; it now reads `global.toml`, the same source deploy-time hook contexts use
- **Tag checkout paths** — `tag switch` and log `checkout <tag>` died with `BranchNotFoundError`; both now check out the tag's commit, and `tag switch` carries a v2.0 deprecation notice pointing at `navigate`
- **Dangling hook references** — `awesome`/`rofi` default hooks named nonexistent aliases; now `awesome_reload` / `None`
- **Stale teachings** — `log` helpers and tag docs pointed at `switch`; now `navigate`
- **Navigate to tags** — `navigate <tag>` died with `BranchNotFoundError` (`checkout` only resolves branch heads); now checks out the tag's commit
- **Swallowed error details** — save/deploy error lists printed after `ui.error()` raised, so details never showed; now printed before exiting (abort semantics unchanged)
- **Eliminated all bare `sys.exit()` calls** — `ui.error()`, `init` abort, `onboarding` interrupt, and `--complete` dispatch now use `raise SystemExit(...)` with `ExitCode` values
- **`navigate` error handling deduplicated** — `_navigate_impl` delegates to `handle_exception(e, "Navigate")` instead of an inline duplicate renderer
- **`bootstrap` / `config get` / `doctor` error paths** — route through `common.error()`; `doctor` failure summary is a single `error(..., exit_code=1)` instead of `error(..., exit_code=0)` + separate `raise SystemExit(1)`
- **`save_cmd.py`** — fixed `_sync_shared_sections` → `sync_shared_sections` name mismatch that caused `NameError` on `--commit` flag
- **`shared_sync.py`** — `_sync_branch` now records overridden sections in `report.skipped` even when other shared sections are still wanted (partial overrides)
- **Tests** — all 1966 tests passing (up from 1700), 1 skipped; coverage 84% → 90%
- **Refactoring batch** — long functions split into phase helpers (`navigate` 233→51 lines, `files.py` copy/save splits, deploy closure hoisted to a method); `type: ignore` count 13 → 3 via truthful types (Literal encryption chain, `BaseException` diagnostics, None-guard, `dict[str, Any]` manifest); fixed test isolation leaks (`add` copies and completion cache no longer touch the real repo)
- **`test_shared_sync.py`** — fixed test expectations for `test_edits_reach_non_overriding_branches` (work overrides fish, so only server gets propagated), `test_unparsable_target_config_is_skipped_safely` (fixed `run_git()` call to use `subprocess.run` with `input=`), `test_source_branch_never_modified` (fixed log assertion to use `-1` flag)
- **CI on Python 3.10/3.11** — `patch("dot_man.cli.completions.*")` and `patch("dot_man.cli.help_cmd.*")` resolved to the `completions`/`help` Commands (they shadow the modules) on `unittest.mock`'s getattr-chain resolver (≤3.11; 3.12+ uses `pkgutil.resolve_name` via `sys.modules`); all 31 string patches now use `patch.object()` on the `importlib.import_module()` handle, so they work on every version

### Changed

- **Repository cleanup** — single source of truth for completion scripts (`dot_man/completions/`); removed the duplicated `scripts/completions/` copies and the unused packaged `install.sh`. `install.sh` now installs completions via the built-in `dot-man completions` command. Removed the stale `docs/development/roadmap.md` duplicate and surfaced `docs/roadmap.md` in the docs site nav.

### Removed

- **Tracked artifacts** — dropped `coverage.json` (256 KB CI artifact) and the author's personal `config.toml` from version control; both now gitignored along with benchmark output.
- **Local clutter** — `.gitignore` fixed (broken merged pattern) and extended: coverage reports, benchmarks, stale build/dist/site outputs no longer pollute the working tree.

## [1.4.0] - 2026-08-25

### Added

- **Decorator-driven completion engine** — new `dot_man/cli/completion_engine.py` gathers commands, subcommands, options, accepted values (static or dynamic) and defaults from the Click CLI definition itself. Extended via the `@completes(path, param=...)` decorator registry; a `(path, param)` registration wins over the generic one.
- **`dot-man --complete <shell>` protocol** — handled before onboarding/git/side effects in `main()`. Fish output uses `value<TAB>description` lines so descriptions render natively.
- **Defaults & choices surfaced** — option completions now show `[choices: bash|zsh|fish|all]` and `[default: all]` inline (e.g. `dot-man completions --s<TAB>`).
- **Alias labeling** — shell shortcuts like `nav`, `cpl`, `aud` are listed as `(alias)` entries instead of indistinguishable duplicates.
- **`--option=<TAB>` form** — completing after `=` emits full tokens (`--shell=fish`).
- **Static choice provider** — `config set KEY <TAB>` suggests `true`/`false`.

### Fixed

- **Fish completions showed invalid/stale choices** — the hand-written `dot-man.fish` listed missing commands (`backup`, `tag`, `template`, `profile`, `doctor`, ...), treated navigate options as subcommands, and kept deprecated `switch` prominent. It is now a tiny delegating script calling `dot-man --complete fish` on every TAB (wifi-tracker style), so completions can never go stale.
- **Unformatted fish output** — the old script's naive `string split ","` broke on help text containing commas and dropped descriptions. Tab-separated engine output renders descriptions natively in fish.

### Tests

- 37 new tests in `tests/test_completion_engine.py` (registry priority, root/subcommand listing, static choices, defaults display, alias labeling, eq-form values, dynamic git-backed callbacks, request parsing, formatting, entry safety). Suite: 1682 passed, coverage 84% (up from 81%).

## [1.3.0] - 2026-06-27

### Added

- **Template substitution in deployed files** — `{{VAR}}` placeholders in config files (e.g. `{{HOSTNAME}}`, `{{USER}}`, `{{OS}}`) are now rendered automatically during deploy. Enabled by default via `render_templates` on each section.
- **Conditional template syntax** — `{{ if OS == "darwin" }}...{{ endif }}` and `{{ if VAR != "value" }}...{{ endif }}` blocks in config files. Conditionals are evaluated before variable substitution. Uses stdlib regex, no new dependencies.
- **Vault key rotation** — `dot-man vault rotate-key` re-encrypts all secrets with a new Fernet key. Old key backed up to `.key.bak`. `dot-man vault status` shows vault stats.
- **Expanded `--dry-run` on navigate** — now shows all 4 phases: sections that would save, branch status, files that would deploy + hooks, config update.
- **62 new tests** — `test_save_cmd.py` (23), `test_status_cmd.py` (18), `test_navigate_helpers.py` (21), plus 14 template/conditional tests.
- **Shell completions split** — extracted completion functions into `completions.py` (310 lines), `common.py` reduced from 642 to 260 lines.
- **Priority improvement plan** — documented 20-item prioritized improvement roadmap in `docs/PRIORITY_PLAN.md`.

### Fixed

- **`doctor_cmd.py:117`** — `.exists()` called on string instead of `Path`. Added `from pathlib import Path` and wrapped `DOT_MAN_TOML` in `Path()`.
- **`remote_cmd.py:225`** — `Path` passed where API expects `str`. Added `str()` conversion.
- **Stale coverage claims** — README and TODO updated from 83% to 81% (actual), test count from 1519 to 1526.
- **`test_doctor_cmd.py`** — fixed test to properly mock `DOT_MAN_DIR` instead of relying on bug-induced crash.
- **Import patch targets** — `test_completion.py` and `test_shell_completions.py` updated to patch `dot_man.cli.completions._git_runner`.

### Refactored

- **Deduplicate hook execution in navigate** — extracted `_run_shell_hooks()` helper, replacing 3 identical ~25-line hook blocks.
- **Split `common.py`** — completion functions moved to `completions.py`, backward-compatible re-exports preserved.

## [1.2.3] - 2026-06-11

### Added

- **Interactive symlink handling** — `dot-man add`, `navigate`, and `watch` now detect symlinked config paths and prompt the user with three choices: follow the link (save target content), ignore (skip this path), or ignore all. Deploying also warns when overwriting a symlinked local path.

### Fixed

- **Python 3.10 CI compatibility** — `dot_man/cli/__init__.py` no longer shadows module names with same-named function imports.

## [1.2.1] - 2026-06-10

### Refactored

- **Deduplicate deploy logic** — extracted `_build_final_excludes`, `_deploy_repo_path`, `_restore_file_secrets_inplace` from duplicate code in `deploy_section` and `deploy_item` (save_deploy_ops.py)
- **Unify config loading** — extracted `load_config_file()` function in `global_config.py`, removing 30 lines of duplicate YAML/TOML loading from both `DotManConfig` and `GlobalConfig`
- **Clean up silent `except: pass`** — removed 4 redundant `pass` statements after `logging.debug()` in `common.py`, added `logging.debug()` to a bare `except` in `core.py`
- **Break up `_run_interactive_tutorial`** — 302-line function split into 8 discrete step functions (config_cmd.py)
- **Extract `SECTION_EXAMPLES`** — 260-line data dict moved from function body to module-level constant (config_cmd.py)
- **Break up `run_setup_wizard`** — 250-line wizard split into 5 helpers (init_cmd.py)
- **Break up `setup`** — 253-line remote setup split into 17 helpers; deep nesting reduced from 11 to 4 levels (remote_cmd.py)
- **Reduce deep nesting in `edit`** — from 11 to 4-5 levels (edit_cmd.py)

### Test Improvements

- Strengthened loose assertions (24 tests): added output content checks, mock-call assertions, or file-state assertions
- **`interactive.py`** — 47 tests, 47% → 100% coverage
- **`branch_cmd.py`** — 23 tests, 51% → 100% coverage
- **`deploy_cmd.py`** — 25 tests, 59% → 100% coverage
- Overall coverage: 66% → 83%

## [1.2.0] - 2026-05-17

### Added
- **Symlink deploy mode** — `deploy_method = "symlink"` per section
- **Quickshell hook aliases** — `quickshell_reload`, `quickshell_restart`, `quickshell_validate` with `{qs_config}` → `{config_name}` placeholder

### Fixed
- README outdated commands (switch → navigate)
- Test compatibility for Python 3.10

## [1.0.0] - 2026-05-17

### Added
- **Production Release** - Official v1.0.0 stable release
- **YAML configuration support** - Config files now support `.yaml` and `.yml` formats alongside TOML:
  - Automatic format detection
  - Warning when multiple config files exist (TOML takes priority)
  - Environment variable expansion in paths (`$HOME`, `$USER`, `$WORK_DIR`, etc.)
- **`dot-man import`** - Import dotfiles from other dotfile managers:
  - `dot-man import chezmoi` - Import from chezmoi
  - `dot-man import yadm` - Import from yadm
  - `dot-man import stow` - Import from GNU Stow packages
  - `dot-man import all` - Auto-detect and import from any source
  - `--dry-run` to preview what would be imported
- **`dot-man export`** - Export dotfiles to portable formats:
  - `dot-man export tar backup.tar.gz` - Tar archive
  - `dot-man export zip dots.zip` - Zip archive
  - `dot-man export json manifest.json` - JSON manifest
  - `--branch` to export specific branch
- **`dot-man discover`** - Auto-detect existing dotfiles:
  - Scans 30+ common dotfile locations (shells, WMs, terminals, editors)
  - `--add` to automatically add to dot-man.toml
  - `--include-extended/--no-extended` for VS Code, Sublime, etc.
- **`dot-man encrypt`** - Encrypt/decrypt sensitive files:
  - GPG and AGE encryption support
  - `encrypt status` - Show encryption status
  - `encrypt encrypt <section>` - Encrypt section files
  - `encrypt decrypt <section>` - Decrypt section files
- **`dot-man diff --rich`** - Syntax-highlighted diffs using rich library:
  - Monokai theme with line numbers
  - `--no-rich` to use plain git diff (default: enabled)
- **PyPI packaging** - Ready for `pip install dot-man`

### Changed
- **Version bump to 1.0.0** - Production stable release
- **Removed legacy code**:
  - Removed INI migration (TOML/YAML only)
  - Removed unused `LegacyConfigLoader` class
  - Consolidated `LOCK_FILE` to constants.py
  - Removed `GLOBAL_CONF` and `DOT_MAN_INI` constants
- **Config file priority**: TOML (.toml) > YAML (.yaml/.yml)
- **`switch` command** - Marked as DEPRECATED, shows warning and points to `navigate`
- **`checkout` command** - Marked as DEPRECATED, shows warning and points to `navigate`

### Deprecated
- `switch` → Use `navigate` instead
- `checkout` → Use `navigate` instead

### Fixed
- Type annotations for shell completion
- Import assertions for type safety
- Various lint and type checking issues

## [0.10.0] - 2026-05-17

### Added
- **YAML configuration support** - Config files now support `.yaml` and `.yml` formats alongside TOML:
  - Automatic format detection
  - Warning when multiple config files exist (TOML takes priority)
  - Environment variable expansion in paths (`$HOME`, `$USER`, `$WORK_DIR`, etc.)
- **`dot-man import`** - Import dotfiles from other dotfile managers:
  - `dot-man import chezmoi` - Import from chezmoi
  - `dot-man import yadm` - Import from yadm
  - `dot-man import stow` - Import from GNU Stow packages
  - `dot-man import all` - Auto-detect and import from any source
  - `--dry-run` to preview what would be imported
- **`dot-man export`** - Export dotfiles to portable formats:
  - `dot-man export tar backup.tar.gz` - Tar archive
  - `dot-man export zip dots.zip` - Zip archive
  - `dot-man export json manifest.json` - JSON manifest
  - `--branch` to export specific branch
- **`dot-man discover`** - Auto-detect existing dotfiles:
  - Scans 30+ common dotfile locations (shells, WMs, terminals, editors)
  - `--add` to automatically add to dot-man.toml
  - `--include-extended/--no-extended` for VS Code, Sublime, etc.
- **`dot-man encrypt`** - Encrypt/decrypt sensitive files:
  - GPG and AGE encryption support
  - `encrypt status` - Show encryption status
  - `encrypt encrypt <section>` - Encrypt section files
  - `encrypt decrypt <section>` - Decrypt section files
- **`dot-man diff --rich`** - Syntax-highlighted diffs using rich library:
  - Monokai theme with line numbers
  - `--no-rich` to use plain git diff (default: enabled)

### Changed
- **Removed legacy code**:
  - Removed INI migration (TOML/YAML only)
  - Removed unused `LegacyConfigLoader` class
  - Consolidated `LOCK_FILE` to constants.py
  - Removed `GLOBAL_CONF` and `DOT_MAN_INI` constants
- **Config file priority**: TOML (.toml) > YAML (.yaml/.yml)
- **`switch` command** - Marked as DEPRECATED, shows warning and points to `navigate`
- **`checkout` command** - Marked as DEPRECATED, shows warning and points to `navigate`

### Deprecated
- `switch` → Use `navigate` instead
- `checkout` → Use `navigate` instead
- `tag switch` → Use `navigate` instead

## [1.2.0] - 2026-06-09

### Added
- **Generalized placeholder system in hooks** — `{qs_config}` replaced with `{config_name}`, `{config_root}`, `{section_name}`, `{paths}`, `{branch}`
- **Shell completions** — `encrypt <section>`, `export --branch`, `rollback <target>`
- **Custom Secret Patterns** — Support defining custom regex patterns for secret detection in config
- **Secret Scanner Customization** — `use_default_patterns = false` to disable built-in patterns
- **Symlink Deploy Mode** — per-section `deploy_method = "symlink"` for edit-in-place workflows
- **Quickshell Hook Aliases** — `quickshell_reload`, `quickshell_restart`, `quickshell_validate` with `{qs_config}` → `{config_name}` placeholder
- **`complete_sections()`** — shell completion callback for section names

### Changed
- **`switch_cmd` consolidated → thin wrapper** — `switch` is now a 17-line wrapper calling `_navigate_impl()` (~80% code reduction)
- **`BranchParamType` deduplicated** — moved from `switch_cmd.py`/`navigate_cmd.py` to `common.py`
- **Schema keys deduplicated** — `VALID_SECTION_KEYS` defined once in `dotman_config.py`
- **`HOOK_ALIASES` unified** — `constants.py` is canonical; `merge.py` imports from it
- **Silent `except: pass` cleanup** — `logging.debug()`/`logging.warning()` added to 11+ bare exceptions across `common.py`, `navigate_cmd.py`, `rollback_cmd.py`, `core.py`, `files.py`, `init_cmd.py`
- **Production `assert` statements removed** — all replaced with `if/error()` pattern in `navigate_cmd.py`, `encrypt_cmd.py`, `import_cmd.py`, `rollback_cmd.py`
- **Coverage improved from 60% → 66%** — 1146 tests (up from 1021), 1 skipped

### Fixed
- **Weak `>=` assertions** in `test_section.py`, `test_save_deploy_ops.py`, `test_status_ops.py`, `test_core_extended.py`, and 4 new test files
- **Missing f-string prefix** in `dotman_config.py:96`
- **Stale `dot-man.ini` reference** in `status_ops.py:158`

### New Tests
| File | Tests | Coverage Impact |
|------|-------|-----------------|
| `test_files_comprehensive.py` | 55 | `files.py` 73% → 94% |
| `test_branch_ops.py` | 39 | `branch_ops.py` 40% → 97% |
| `test_encryption.py` | 32 | `encryption.py` 33% → 100% |
| `test_completions_cmd.py` | 10 | `completions_cmd.py` 12% → 94% |
| `test_shell_completions.py` | 7 | Shell completions verified |
| `test_section.py` | 39 (+36) | `section.py` 70% → 95% |
| `test_save_deploy_ops.py` | 26 | `save_deploy_ops.py` 52% → 75% |
| `test_status_ops.py` | 17 | `status_ops.py` 59% → 89% |
| `test_core_extended.py` | 46 | `core.py` 58% → 66% |

## [1.1.1] - 2026-05-20

### Added
- **PyPI Publication** - Official release published to PyPI as `dotman-git`.
- **Command Aliases** - Short 3-letter command aliases added for all major operations:
  - `nav` (navigate), `doc` (doctor), `dep` (deploy), `enc` (encrypt)
  - `exp` (export), `imp` (import), `dis` (discover), `aud` (audit)
  - `cln` (clean), `ver` (verify), `rev` (revert), `rol` (rollback)
  - `wat` (watch), `cpl` (completions), `rst` (restore), `edt` (edit)
  - `sta` (status), `ini` (init), `syn` (sync), `log` (log), `dif` (diff)
  - `hks` (hooks)
- **`dot-man watch`** — Auto-save tracked dotfiles on change (supporting both watchdog and polling backends, debounced commits, and `--no-commit`/`--dry-run` flags).
- **`dot-man rollback`** — Transaction-style rollback to any previous commit, tag, or `HEAD~N`, with colored diffs and automatic pre-rollback backups.
- **YAML Comment Preservation** - Added round-trip YAML configuration comment and layout preservation using `ruamel.yaml`.

### Changed
- **README Overhaul** - Redesigned README with project badges, architecture diagrams, config examples (TOML/YAML), and command reference tables.
- **License & Copyright** - Updated license with additional copyright holder (ZVAXEROWS) and copyright years to 2025, 2026.

### Fixed
- **Profile Switch & Serialization** - Resolved a traceback in `profile switch` by properly parsing branch parameters for `ctx.invoke`.
- **Global Config Save** - Defaulted `GlobalConfig.save()` to write to disk (`force=True`) to prevent silent save failures across CLI commands.
- **TOML Serialization of None** - Prevented `tomlkit` ConvertError by omitting the `inherits` key if its value is `None` during profile creation.
- **YAML Configuration Overwrites** - Resolved a bug where editing configuration fields would silently convert YAML files back to TOML on save.
- **TOML/YAML Comment Preservation & Key Deletions** - Fixed a bug in document updates where deleted configuration keys were not removed from the saved file, and added value equality checks to prevent losing comments on sequence fields.
- **Integration Tests** - Added robust test cases covering the complete `profile switch` flow, validating branch switching, warnings, inheritance, and error handling.
