# TODO — Enhancements (audit findings, phased)

Source: codebase audit of v1.5.0 (`8a9ff20`). Findings are split into five
independently executable phases, ordered by risk. Each phase is self-contained:
it lists a goal, exit criteria, and one checkbox per item with impact / effort /
complexity / location / fix / verification.

**Impact:** High · Med · Low  **Effort:** S (<½ day) · M (½–2 days) · L (>2 days)
**Complexity:** Low · Med · High

Run the full quality gate before closing any phase (per `AGENTS.md`):

```bash
uv run black dot_man/ tests/
uv run ruff check dot_man/ tests/
uv run mypy dot_man/ --ignore-missing-imports
uv run pytest tests/ -v
uv run pytest --cov=dot_man --cov-report=term
```

---

## Phase 1 — Stop the bleeding (correctness & data loss)

**Goal:** Fix user-visible crashes, silent data loss, and config bugs that
break documented features. Mostly small, isolated fixes.
**Exit criteria:** every item checked, tests added, full quality gate green.
**Depends on:** nothing.

| Done | Item | Impact | Effort | Complexity | Location |
|------|------|--------|--------|-----------|----------|
| [x] | C1 `checkout_commit` doesn't update the worktree | High | M | Med | `core.py:130-141` |
| [x] | C2 Commit/tag navigation never deploys or records branch | High | M | Med | `navigate_cmd.py:296-424` |
| [x] | C3 Live navigate path has no pre-switch backup | High | M | Med | `navigate_cmd.py:449-479,624-650` |
| [x] | C4 `ensure_directory` chmods existing dirs to 0755 | High | S | Low | `files.py:204-207,168,494` |
| [x] | C5 Top-level `[secrets]` parsed as phantom section | High | S | Low | `dotman_config.py:143-149` |
| [x] | C6 Section encryption fields never forwarded to `Section` | High | S | Low | `dotman_config.py:268-286` |
| [x] | C7 `import all`/`import chezmoi` operator-precedence crash | High | S | Low | `import_cmd.py:123` |
| [x] | C8 `status --json` emits invalid JSON (Rich pollutes stdout) | High | S | Low | `status_cmd.py:37-53,76` |
| [x] | C9 First-run onboarding hijacks `--help`/`--version` | High | S | Low | `main.py:25-27` |
| [x] | C10 `dot_man/completions` missing `__init__.py` → install crash | High | S | Low | `cli/completions_cmd.py:43,115` |
| [x] | C11 `export` ignores `--branch`/`--include-secrets`; bad JSON | Med | M | Low | `export_cmd.py:69-150` |
| [x] | C12 `create_symlink` unlinks dest even when backup failed | Med | S | Low | `files.py:490-492` |
| [x] | C13 Binary-copy failures reported as success | Med | S | Low | `files.py:198,312-323` |
| [x] | C14 `switch_branch` dead **and** deadlocks (nested `FileLock`) | Med | S | Low | `branch_ops.py:139-144` |
| [x] | C15 Non-atomic config writes can truncate `*.toml` | Med | S | Low | `global_config.py:206-218` |

### Details

**C1** — `head.reference = commit` moves the ref only; index/worktree stay on
the old content, so `rollback`, `navigate <tag>`, and `navigate <sha>` deploy
stale files. Fix: `repo.git.checkout(sha)` (or `head.reset(commit=sha,
index=True, working_tree=True)`). Test must assert file **content**, not just
detached HEAD (the current `test_core_extended.py:157-159` misses it).

**C2** — Only `_handle_branch_navigate` calls `deploy_all` and persists
`current_branch`. Funnel branch/commit/tag through one save→switch→deploy
pipeline.

**C3** — Backup creation exists only in the dead `switch_branch`
(`branch_ops.py:169-181`). Restore it in the live path (or make the library
method the single implementation).

**C4** — `ensure_directory` runs `path.chmod(mode)` unconditionally, so
deploying `~/.ssh/config` rewrites `~/.ssh` to 0755 and ssh refuses the key.
Only chmod newly-created dirs; never relax an existing dir.

**C5** — `_validate_schema` and `shared_sync._RESERVED_KEYS` treat `secrets` as
reserved, but `get_section_names` excludes only `templates`. Any config with a
`[secrets]` table crashes 19 call sites. Fix: shared `_RESERVED_TABLES =
{"templates", "secrets"}`.

**C6** — `get_section` builds `Section(...)` without `encrypted`,
`encryption_method`, `encryption_recipient`, so `encrypted = true` resolves to
`False`. Forward the three keys.

**C7** — `if d.exists() and (d / ".git").exists() or any(d.iterdir()):` —
`and` binds tighter, so `iterdir()` runs on missing dirs → `FileNotFoundError`.
Parenthesize and guard with `d.exists()`.

**C8** — The Repository Status panel prints before the `json_output` branch.
Gate all human output behind `if not json_output`; JSON to stdout, diagnostics
to stderr.

**C9** — `main()` runs `run_onboarding()` and returns before `cli()` whenever
`.onboarded` is missing, so `--version`/`--help` are ignored on a fresh machine
and no flags apply. Only onboard with no subcommand; add
`--no-onboarding`/non-tty detection; always write the sentinel.

**C10** — `dot_man/completions/` has no `__init__.py`, so `pkg.__file__` is
`None` and `Path(None).parent` raises `TypeError`. Tests patch `__file__` and
hide it. Add `__init__.py` (or `importlib.resources.files`) and a test that does
**not** patch.

**C11** — `_export_tar`/`_export_zip` ignore `branch`/`include_secrets`;
`_export_json` writes `"exported_at": str(Path().home())` and a local path for
`repo_path`. Honor or reject the flags; write a real ISO timestamp.

**C12/C13** — `backup_file` returns `None` on failure but its result is ignored
before `unlink()`; binary-copy `OSError` returns `(False, [])` and increments
no failure counter. Surface failures.

**C14** — No production caller; `switch_branch` locks `LOCK_FILE`, then calls
`save_all`, which re-locks the same file → `LockError`. Delete it (superseded by
C1/C2's unified path) or make locking re-entrant.

**C15** — `write_config_file` uses `open(path, "w")`. Route through
`atomic_write_text` and hold the process lock.

---

## Phase 2 — Security hardening

**Goal:** Close RCE, secret-leakage, and permission vectors; make encryption
actually protect data.
**Exit criteria:** every item checked; targeted security tests added; quality
gate green.
**Depends on:** Phase 1 (C4/C15 overlap permissions/atomic writes).

| Done | Item | Impact | Effort | Complexity | Location |
|------|------|--------|--------|-----------|----------|
| [x] | S1 `bootstrap` uses `shell=True` with repo-supplied names | Critical | S | Low | `cli/bootstrap_cmd.py:108-115` |
| [x] | S2 Repo hooks + `{placeholder}` unquoted into `sh -c` | Critical | M | Med | `hook_engine.py:67-113`, `section.py:166-176` |
| [x] | S3 Encryption not wired into save/deploy (false security) | High | L | High | `save_deploy_ops.py:142-197`, `encrypt_cmd.py:160` |
| [x] | S4 Real secret lines printed cleartext; world-readable export | High | S | Low | `audit_cmd.py:87`, `common.py:336`, `export_cmd.py:139` |
| [x] | S5 `atomic_write_text` resets mode to 0644 | High | S | Low | `files.py:54-74` |
| [x] | S6 `repo_path` from config escapes `REPO_DIR` | Med | S | Low | `section.py:218-230` |
| [x] | S7 Vault key write-then-chmod race + rotation defects | Med | M | Med | `vault.py:79-88,319-358` |
| [x] | S8 `audit` never scans git history/index | Med | M | Med | `audit_cmd.py:38`, `secrets.py:362` |
| [x] | S9 Secret filter false-positives; no entropy; narrow patterns | Med | M | Med | `secrets.py:204-304` |
| [x] | S10 GPG/AGE arg injection; decrypted output 0644 | Med | S | Low | `encryption.py:64,86-91,129` |
| [x] | S11 Non-blocking lock; navigate phases not atomic | Med | M | Med | `lock.py:41`, `navigate_cmd.py:460,593` |
| [x] | S12 Symlink TOCTOU (no `O_NOFOLLOW`/`lstat`) | Med | M | Med | `files.py:490`, `branch_ops.py:276` |
| [x] | S13 `watch` silently redacts secrets with no audit trail | Med | S | Low | `watch_cmd.py:255` |

### Details

**S1** — Parse the command template into an argv list and pass it without
`shell=True`; validate package names/package-manager choice.

**S2** — Hooks and `file:` scripts come from repo config; placeholder values
are raw string-replaced, so `{paths}`/`{branch}` containing `;` or `$()`
execute. Treat repo hooks as untrusted: quote all placeholders with
`shlex.quote`, require first-run confirmation per repo.

**S3** — `section.encrypted` is only read by `encrypt --status`; save/deploy
copy plaintext into the repo and never decrypt `.gpg`. Encrypt on save (replace
plaintext), decrypt on deploy, fail closed if `encrypted=true` and the file
isn't encrypted.

**S4** — `audit` prints `match.line_content[:60]` (the secret); `save` prints
`[:80]`; `--include-secrets` export is written with default umask. Print
redacted context; create secret-bearing files via `os.open(..., 0o600)`.

**S5** — The temp file is created umask-based then `os.replace`d, losing the
destination mode. Copy `path.stat().st_mode` before replace (or open the temp
with an explicit mode).

**S6** — `repo_dir / self.repo_path` has no containment check (inconsistent with
`hook_engine.find_hook_script`, which does). Resolve and assert
`is_relative_to(REPO_DIR)`.

**S7** — Key is `write_bytes` then `chmod(0o600)` (race window); rotation keeps
`.key.bak` forever and can leave key/vault out of sync on failure. Use
`os.open(O_CREAT|O_EXCL, 0o600)`; atomically swap key+vault; make `.key.bak`
retention opt-in.

**S8** — Working-tree-only scan misses committed-then-removed secrets. Add a
`git log -p --all` / object-walk scan and an index scan (or clearly rescope the
command).

**S9** — `is_false_positive` skips any line containing `example`/`xxx`/`${`
anywhere; no entropy scoring; patterns miss `github_pat_`, `ASIA`, GitLab,
Slack, PEM. Match indicators against the value only; add entropy scoring;
broaden patterns.

**S10** — Recipients pass straight into argv after `-r` without `--` or charset
validation (option smuggling); decrypted files inherit 0644. Validate, pass
`--`, supply `--batch` for symmetric mode, chmod 0600.

**S11** — `LOCK_EX|LOCK_NB` raises immediately with no retry; navigate locks
save/checkout/deploy separately. Use a blocking-with-timeout lock and hold one
lock across the whole transaction.

**S12** — Restore/write paths don't `lstat`/`O_NOFOLLOW`, so a swapped symlink
redirects writes. Refuse to write through symlinks unless allowed.

**S13** — `watch` calls `save_all()` with no secret handler → silent `REDACT`.
Pass `get_secret_handler()` or refuse silent redaction in watch mode.

---

## Phase 3 — Architecture & dead-code removal

**Goal:** Remove duplication and dead code; make the design testable without a
global patch wall.
**Exit criteria:** every item checked; coverage not decreased; quality gate
green.
**Depends on:** Phase 1 C1/C2/C14 (unify the switch path).

| Done | Item | Impact | Effort | Complexity | Location |
|------|------|--------|--------|-----------|----------|
| [ ] | A1 Branch-switch workflow duplicated (library vs CLI) | High | L | High | `branch_ops.py:98-222` vs `navigate_cmd.py:578-750` |
| [x] | A2 ~370 lines of dead `merge.py` machinery; buggy merge | Med | M | Med | `merge.py:44-427` |
| [x] | A3 Five overlapping hook vocabularies | Med | M | Med | `constants.py:80`, `merge.py`, `config_detector.py` |
| [ ] | A4 Global singleton + import-time path binding (patch wall) | Med | M | High | `operations.py:198-212`, `tests/conftest.py:56-98` |
| [x] | A5 Section schema duplicated across 4+ places | Med | M | Med | `dotman_config.py:24-44`, `section.py:29-51,232-278` |
| [ ] | A6 153 `except Exception` clauses hide real bugs | Med | M | Med | `core.py:278,335,374`, `secrets.py:566`, … |
| [x] | A7 `iter_section_paths`/pattern logic duplicated 4+× | Low-Med | M | Med | `operations.py:111-193`, `save_deploy_ops.py:389`, `navigate_cmd.py:427,490` |
| [x] | A8 Dead/stale TUI + non-existent coverage omits + `textual` weight | Low-Med | S | Low | `cli/tui_cmd.py`, `pyproject.toml:110-123` |
| [x] | A9 Unreachable dead block in `_switch_to_branch` | Low | S | Low | `navigate_cmd.py:651-698` |
| [x] | A10 `get_section` uncached; re-reads `global.toml` per hook | Low-Med | S | Med | `section.py:190-207` |
| [ ] | A11 Mixins rely on implicit host state (13-method `FakeOps`) | Low-Med | M | Med | `operations.py:42`, `tests/test_branch_ops.py:11-65` |
| [x] | A12 Long functions mixing orchestration/rendering/hooks | Low | M | Med | `cli/doctor_cmd.py`, `cli/status_cmd.py`, `cli/rollback_cmd.py` |
| [x] | A13 `reload_config` clears only `_dotman_config` (stale watch) | Low | S | Low | `operations.py:94-96` |

### Details

**A1** — One save→switch→deploy implementation. Have the library method
produce a plan and let the CLI render it, or delete the library method after
C1/C2 move everything to the unified path.

**A2** — Only `get_hook_for_config` is used in production. Delete the unused
`UniversalMergeManager`/`HOOK_CATEGORIES`/`UNIVERSAL_HOOKS` API and tests; fix
or drop `merge_files("merge")` (it appends content without markers).

**A3** — Collapse `HOOK_ALIASES`, `FILE_TO_HOOK_MAP`, `get_hook_for_config`,
`HOOK_CATEGORIES`, `POPULAR_CONFIGS[*].default_hook` into one
`config-name → alias` table consumed by `hook_engine`.

**A4** — Read paths at call time (e.g. `constants.get_repo_dir()`) or inject a
config object, eliminating conftest's ~25 patch targets. Guard the singleton.

**A5** — Declare section fields once; derive `VALID_SECTION_KEYS`,
`Section.__init__`, and `to_dict` from it (this is how C6 happened).

**A6** — Narrow broad `except Exception`/silent `pass` to specific exceptions;
log or re-raise. This is what hid C1.

**A7** — One `iter_tracked_files(section)` + one pattern helper used by
`operations`, `save_deploy_ops`, and `navigate_cmd`.

**A8** — Either finish the TUI with tests, or delete `cli/tui_cmd.py`,
`tui_log.py`, the stale `omit` entries (`tui.py`, `tui_editor.py`,
`cli/interactive.py` don't exist), and drop `textual` where unused.

**A9** — Delete lines 651-698 (dead duplicate after the unconditional
`return True`).

**A10** — Memoize resolved sections by name + config mtime; pass the branch via
hook context instead of re-reading disk.

**A11** — Prefer composition or a host `Protocol` over the mixin trio; removes
`FakeOps`.

**A12** — Extract orchestration from Click command bodies (doctor 216, status
212, rollback 164 lines).

**A13** — Reset `_global_config` too (or all state) so long-lived `watch`
picks up branch changes.

### Status (partial)

Done in the Phase 3 pass: A2, A3, A5, A7, A8, A9, A10, A12, A13. Some were
scoped, not exhaustive:

- **A5** — single-sourced via `VALID_SECTION_KEYS = inspect.signature(
  Section.__init__)`; `to_dict`/`__init__` remain hand-written but are guarded
  by a test asserting every emitted key is valid.
- **A6** — the four silent `except Exception: pass` sites (branch_ops,
  secrets, template_cmd, export_cmd) now narrow + log; `core.py`,
  `secrets.scan_git_history`, `rollback_cmd._resolve_target`, and the
  branch_ops best-effort fallbacks were narrowed to specific errors. The
  remaining ~140 broad handlers are tracked as **A6b** (incremental).
- **A12** — `status`, `doctor`, and `rollback` command bodies now delegate to
  module-level render/backup helpers.

Still open — deliberately deferred, each a high-complexity change that
deserves its own focused pass rather than a rushed edit:

- **A1** — unify the library `branch_ops` switch path with the CLI pipeline.
- **A4** — replace import-time `REPO_DIR`/path binding with call-time accessors
  or injected config (retires conftest's ~25 patch targets).
- **A6b** — sweep the remaining broad `except Exception` handlers.
- **A11** — replace the mixin trio with composition / a host `Protocol`.

---

## Phase 4 — CLI / UX & automation

**Goal:** Make the CLI scriptable and consistent; trim the surface.
**Exit criteria:** every item checked; CLI tests updated; quality gate green.
**Depends on:** Phase 1 C8/C9 (JSON + onboarding first).

| Done | Item | Impact | Effort | Complexity | Location |
|------|------|--------|--------|-----------|----------|
| [ ] | U1 Add global `--json`/`--quiet`/`--yes`/`--no-input`/`--no-color` | High | M | Med | `interface.py`, all `*_cmd.py` |
| [ ] | U2 Uniform `--dry-run`/`--force`; `init --force` must warn | Med-High | M | Med | `init_cmd.py:22,58-65` |
| [ ] | U3 Merge/remove overlapping commands + hide deprecated shims | Med | M | Med | `restore_cmd.py`, `revert_cmd.py`, `switch_cmd.py`, `log_cmd.py` |
| [ ] | U4 Consistent diagnostics/streams/`ExitCode` everywhere | Med | M | Med | `common.py:96-100,30-43`, `audit_cmd.py:134` |
| [x] | U5 Normalize subcommand styles (groups vs positional `Choice`) | Low-Med | M | Med | `encrypt_cmd.py:26`, `vault_cmd.py:11`, `hooks_cmd.py:11` |
| [x] | U6 `import` commits all changes without confirm/dry-run | Med | S | Low | `import_cmd.py:217-219,269,339` |
| [x] | U7 `profile switch` prints wrong deprecation warning | Low | S | Low | `profile_cmd.py:206-212` |
| [x] | U8 `sync --push-only --pull-only` silently no-ops | Low | S | Low | `remote_cmd.py:172-194` |
| [x] | U9 `config create --examples` always-on no-op flag | Low | S | Low | `config_cmd.py:199` |
| [x] | U10 Trim alias noise + remove self-aliases | Low | S | Low | `add_cmd.py:25`, `log_cmd.py:21` |
| [ ] | U11 Terminal-width aware output; text fallback for emoji | Low-Med | M | Med | `ui.py:120`, `status_cmd.py:167-188`, `rollback_cmd.py:226` |

### Details

**U1** — Only `status` has `--json`. Add global options (and `--no-color`
respecting `NO_COLOR`) so scripts/CI can rely on them.

**U2** — `--dry-run` is missing on `sync`, `bootstrap`, `audit --fix`, `vault
rotate-key`, `profile switch`, and import's commit step; `init --force` bypasses
the destructive-data confirmation. Standardize and never suppress the data-loss
warning.

**U3** — `restore` vs `revert -c`, `show` vs `log`, `backup restore` vs
`rollback` overlap; mark `switch`/`checkout`/`tag switch` `hidden=True` until
removal in v2.0.

**U4** — ~91 `error()` calls omit `exit_code`; diagnostics print to stdout
while `ui.error` uses stderr; magic codes `2`/`50`. Use `ExitCode.*` and route
diagnostics to stderr (reserving stdout for `--json`).

**U5** — Convert `encrypt`/`vault`/`hooks` positional actions to Click groups
so `help-all` and completion list subcommands.

**U6** — Stage only touched files; require confirmation or `--yes`; add
`--no-commit`.

**U7** — Call `navigate`'s impl directly instead of the deprecated `switch`.

**U8** — Make `--push-only`/`--pull-only` mutually exclusive.

**U9** — Remove `--examples` or make it `--examples/--no-examples`.

**U10** — Drop self-aliases and the 22 obscure three-letter aliases; keep
high-value ones (`nav`).

**U11** — Replace hardcoded widths (`display_path[-32:]`, `"─" * 50`) with
Rich auto-fitting tables; pair icons with text; add `--plain`.

### Status

- **Done:** U5–U10 (the Low-effort UX fixes, `import` commit confirmation,
  and the CLI group normalisation).
- **Partial:** U3 (deprecated shims `switch`/`checkout`/`tag switch` are now
  `hidden=True`; the overlapping-command merge — `restore`/`revert -c`,
  `show`/`log`, `backup restore`/`rollback` — is a design call, not done) and
  U4 (magic exit codes replaced with named `ExitCode` members: `AUDIT = 50`,
  `USAGE`; `error()` now defaults to `ExitCode.ERROR`; routing exception
  diagnostics to stderr is not done). U2 so far: `init --force` warns, and
  `--dry-run` added to `sync` + `profile switch`; `--dry-run` on `bootstrap`,
  `audit --fix`, and `vault rotate-key` is not.
- **U6:** `import` now requires confirmation before committing, adds `--yes`
  (skip prompt) and `--no-commit`; helpers return the written paths and no
  longer commit internally. Note: imported files land in `$HOME` (outside the
  repo work tree), so the commit still stages the repo via `add_all()` — the
  "stage only touched files" refinement does not apply here.
- **U9:** `--examples/--no-examples` is now a real toggle; `--minimal`/
  `--no-examples` write a truly comment-free file (drops the preserved TOML
  document, which previously re-appended example comments).
- **U10:** all 22 three-letter aliases and the two self-aliases were removed;
  only the high-value `nav` alias remains (tests updated to assert the removed
  aliases no longer resolve).
- **Test hygiene (overlaps Phase 5 T2):** added an isolated
  `uninitialized_runner` conftest fixture and switched the
  `status`/`branch list`/`switch` "without init" tests off the developer's
  real `~/.config/dot-man` (they were order-dependent and returned `7`);
  added `secrets.py` load/save/`_canonicalize_path` edge tests to re-clear the
  90% module floor.
- **U5:** `encrypt`, `vault`, and `hooks` are now Click groups with
  subcommands (`help-all`/completion discover them); invocation strings are
  unchanged. This exposed a real bug — `vault_cmd` was imported nowhere, so
  `dot-man vault` never registered; it is now wired up and covered by a
  registration test. `--method`/`--recipient` moved from the parent to the
  `encrypt`/`decrypt` subcommands.
- **Deferred (Large/Med):** U1, U11 remain open.

---

## Phase 5 — Tests, CI, packaging, docs

**Goal:** Restore trustworthy tests, enforce quality in CI, fix packaging/docs
drift.
**Exit criteria:** every item checked; CI green on the new matrix; docs build
strict; quality gate green.
**Depends on:** Phase 1 (C10, C11 change test expectations).

| Done | Item | Impact | Effort | Complexity | Location |
|------|------|--------|--------|-----------|----------|
| [ ] | T1 Export tests hit the real repo; assertions vacuous | Med-High | S | Low | `tests/test_export_cmd.py:31-62` |
| [ ] | T2 43 vacuous `exit_code in [0,1]` assertions | Med | M | Low | `tests/test_cli_commands.py`, `test_backup_cmd.py`, … |
| [ ] | T3 No coverage gate despite 96% claim | Med | S | Low | `.github/workflows/ci.yml:31` |
| [ ] | T4 CI gaps: no macOS, no security scan, no docs build, publish unguarded | Med | M | Low | `.github/workflows/*` |
| [ ] | T5 `uninstall.sh` uninstalls wrong dist name (`dot-man` vs `dotman-git`) | Med | S | Low | `uninstall.sh:35,42` |
| [ ] | T6 Version not single-sourced; stale coverage omits; setuptools floor | Low | S | Low | `pyproject.toml:3,73,110-123`, `dot_man/__init__.py` |
| [ ] | T7 `watchdog` not installed in CI → default watch path untested | Low | S | Low | `tests/test_watch_cmd.py:371,561`, `pyproject.toml:46` |
| [ ] | T8 Docs drift (badge, roadmap, SECURITY, DEVELOPMENT, CONTRIBUTING) | Med | M | Low | `README.md:15,199,429,458`, `SECURITY.md`, `DEVELOPMENT.md` |
| [ ] | T9 No property-based tests; no e2e `clone`/`push`/`pull` coverage | Low | L | Med | `tests/`, `core.py` push/pull |
| [ ] | T10 Committed personal artifacts (`pro-mgr.toml`, `integration/`, `docs/superpowers/*`) | Low | S | Low | repo root |

### Details

**T1/T2** — Patch `dot_man.cli.export_cmd.REPO_DIR`; assert exact exit codes
and archive contents; replace `in (0, 1)` with the expected `ExitCode`.

**T3** — Add `fail_under = 95` (or `--cov-fail-under=95`) so the 96% can't
silently regress.

**T4** — Add `macos-latest` to the test matrix; Dependabot (pip +
github-actions); `pip-audit`/`bandit`/CodeQL; a docs `mkdocs build --strict`
job; and make `publish.yml` depend on tests with a `tag == v{version}` check.
Pin actions to SHAs; add top-level `permissions: contents: read` and a
`concurrency` group.

**T5** — Use `dotman-git` (with `dot-man` fallback); derive the version instead
of the stale `v0.1.0` banner.

**T6** — `dynamic = ["version"]` + `[tool.setuptools.dynamic]`; delete the
non-existent `omit` paths; bump `setuptools>=77` (needed for SPDX
`license = "MIT"`).

**T7** — Add `watchdog` to `dev` (or `--extra watch`) so its code runs in CI.

**T8** — Fix README badge `90%`→`96%`, stale roadmap checkboxes, SECURITY
supported versions + contact email, and DEVELOPMENT/CONTRIBUTING fixture names,
counts, and `uv run` usage.

**T9** — Add `hypothesis` for secret-pattern/template/path-filter logic; add
an integration test exercising real `clone`/`push`/`pull`.

**T10** — Remove or refresh `pro-mgr.toml` (says v0.3.0), drop/wire
`integration/`, exclude `docs/superpowers/*` from the published site, and add
`.superpowers/` to the root `.gitignore`.
