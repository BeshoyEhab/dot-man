"""Tests for cli/init_cmd.py — init command, show_quick_start, run_setup_wizard.

Conventions this file demonstrates (copy them when rewriting other CLI tests):

* Hermetic env: ``clean_env`` layers init-specific extras on top of
  conftest's ``_dot_man_patches`` registry, so ``HOME`` and every
  import-bound path constant point at a fresh temp dir. Never depend on
  the real ``$HOME``.
* Exact exit codes: every invoke asserts a literal (0, 1 or 2), never a
  range or an ``in (0, 1)`` fallback.
* Exact output: assertions pin phrases observed from real runs
  ("Git not found", "Setup Complete", "dot-man status") — no ``or``-
  weakened fallbacks, no bare existence / isinstance-only checks.
* One behavior per test; sweep a family of options with parametrized ids
  instead of near-duplicate tests (see ``TestInitHelp``).
* Shared arrangement (building a source repo for ``--import``) lives in a
  module-level helper instead of copy-pasted Repo.init/config/commit
  blocks.
"""

import os
import subprocess
import sys
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from tests.conftest import _dot_man_patches


def _load_toml(text):
    """Parse TOML with stdlib tomllib (3.11+) or the tomli backport."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    return tomllib.loads(text)


def _actual_branch(repo_dir):
    """The branch git reports for ``repo_dir`` (via the git binary)."""
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Hermetic, UN-initialized dot-man environment (runner + temp paths).

    CLI tests needing an un-initialized env: reuse ``_dot_man_patches`` +
    extras (this fixture); for an initialized env use ``integration_runner``.

    The shared registry supplies every import-bound path constant plus the
    patched ``HOME``; extras below cover bindings the registry lacks:
      * ``dot_man.cli.init_cmd.BACKUPS_DIR`` — init-only consumer that
        appeared solely in the old local patch list, so it is kept here
        (and noted in the comment) instead of being silently dropped.
    """
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    # Init-specific extras not present in the shared registry.
    extras = [patch("dot_man.cli.init_cmd.BACKUPS_DIR", backups_dir)]

    with ExitStack() as stack:
        for p in (
            _dot_man_patches(dot_man_dir, repo_dir, backups_dir, global_toml, home)
            + extras
        ):
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, backups_dir, global_toml


def _make_source_repo(tmp_path, commits=(), branches=(), dirname="source_repo"):
    """Build a real git source repo for the ``--import`` tests.

    Replaces the Repo.init/config/commit boilerplate that was triplicated
    across the import tests.

    ``commits``: sequence of ``(message, {filename: content})`` applied in
    order on the default branch (an empty ``{}`` commits an empty tree).
    ``branches``: sequence of ``(branch_name, commits)`` — each branch is
    created off the default head, checked out, its commits applied, then
    the default branch is checked back out.

    Returns ``(source_dir, repo)``. The default branch name comes from the
    host's git configuration (``master`` vs ``main``): callers must read
    ``repo.active_branch.name`` instead of assuming ``"master"``.
    """
    from git import Repo

    source_dir = tmp_path / dirname
    source_dir.mkdir()
    repo = Repo.init(source_dir)
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@test.com")

    def apply_commit(message, files):
        for name, content in files.items():
            (source_dir / name).write_text(content)
        if files:
            repo.index.add(sorted(files))
        repo.index.commit(message)

    for message, files in commits:
        apply_commit(message, files)

    if branches:
        default_branch = repo.active_branch.name
        for branch_name, branch_commits in branches:
            repo.create_head(branch_name).checkout()
            for message, files in branch_commits:
                apply_commit(message, files)
        repo.heads[default_branch].checkout()

    return source_dir, repo


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestInitHelp:
    @pytest.mark.parametrize(
        "option",
        ["--force", "--no-wizard", "--import"],
        ids=["force", "no-wizard", "import"],
    )
    def test_init_help_documents_option(self, runner, option):
        """Help lists each setup-control option and states the purpose.

        Consolidates the three copy-pasted help tests; the parametrized ids
        keep a failure readable per option, and the purpose keyword guards
        against a help page that lists flags but forgets what init does.
        """
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert option in result.output
        assert "Initialize" in result.output


# ---------------------------------------------------------------------------
# Core init behaviour  (always use --force so the existing real repo is ignored)
# ---------------------------------------------------------------------------


class TestInitCommand:
    def test_init_creates_directory_structure(self, clean_env):
        """init --force should create dot-man-dir, repo, and backups directories."""
        runner, dot_man_dir, repo_dir, backups_dir, _ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert dot_man_dir.exists()
        assert repo_dir.exists()
        assert backups_dir.exists()

    def test_init_creates_global_toml(self, clean_env):
        """init should produce a global.toml config file."""
        runner, dot_man_dir, _, _, global_toml = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert global_toml.exists()

    def test_init_creates_dotman_toml(self, clean_env):
        """init should produce a dot-man.toml inside the repo."""
        runner, _, repo_dir, _, _ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert (repo_dir / "dot-man.toml").exists()

    def test_init_creates_git_repo(self, clean_env):
        """init should create a git repository inside repo_dir."""
        runner, _, repo_dir, _, _ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert (repo_dir / ".git").exists()

    def test_init_success_message(self, clean_env):
        """Success banner pins two stable phrases: the result and the follow-up.

        A single substring ("initialized") is too easy to satisfy by
        accident; pairing it with the quick-start heading proves the full
        no-wizard flow rendered.
        """
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        out = result.output.lower()
        assert "initialized successfully" in out
        assert "quick start guide" in out

    def test_init_force_reinitializes(self, clean_env):
        """--force skips the confirmation prompt and re-initializes successfully."""
        runner, _, repo_dir, _, _ = clean_env

        # First init
        result1 = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result1.exit_code == 0, result1.output
        assert repo_dir.exists()

        # Second init with --force should succeed without prompting
        result2 = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result2.exit_code == 0, result2.output
        # Repo dir still exists and git is valid
        assert (repo_dir / ".git").exists()

    def test_init_twice_without_force_decline_aborts(self, clean_env):
        """Re-running without --force and declining must abort untouched.

        The no-force path asks for confirmation before wiping; declining has
        to exit 1 with the abort message instead of proceeding. The old suite
        only exercised the --force route around this branch.
        """
        runner, _, repo_dir, *_ = clean_env

        first = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert first.exit_code == 0, first.output

        with patch("dot_man.ui.confirm", return_value=False):
            second = runner.invoke(cli, ["init", "--no-wizard"])

        assert second.exit_code == 1
        assert "Aborted" in second.output
        assert (repo_dir / ".git").exists()

    def test_init_twice_without_force_accept_reinitializes(self, clean_env):
        """Confirming the no-force re-init wipes and rebuilds successfully.

        The flip side of the decline test: a 'yes' must reach exit 0 with the
        success banner and a valid repo, proving the prompt gates (rather than
        blocks) re-initialization.
        """
        runner, _, repo_dir, *_ = clean_env

        first = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert first.exit_code == 0, first.output

        with patch("dot_man.ui.confirm", return_value=True):
            second = runner.invoke(cli, ["init", "--no-wizard"])

        assert second.exit_code == 0, second.output
        assert "initialized successfully" in second.output.lower()
        assert (repo_dir / ".git").exists()

    def test_init_without_force_on_fresh_env_succeeds_silently(self, clean_env):
        """A first ``init`` without --force must NOT warn about reinitializing.

        The CLI group creates DOT_MAN_DIR on every invocation (for logs), so
        checking the directory's existence is not evidence of an initialized
        repo — the scary DELETE-all-data prompt must be reserved for repos
        that actually contain a .git.
        """
        runner, _, repo_dir, *_ = clean_env

        result = runner.invoke(cli, ["init", "--no-wizard"])

        assert result.exit_code == 0, result.output
        assert "already initialized" not in result.output.lower()
        assert "DELETE" not in result.output
        assert (repo_dir / ".git").exists()

    def test_init_git_not_installed_exits_with_code(self, clean_env):
        """Missing git exits 2 (dependency error) and names the missing tool.

        The bare exit code would also match an unrelated failure; the pinned
        message proves init failed for the right reason.
        """
        runner, *_ = clean_env

        with patch("dot_man.cli.init_cmd.is_git_installed", return_value=False):
            result = runner.invoke(cli, ["init", "--force", "--no-wizard"])

        assert result.exit_code == 2
        assert "Git not found" in result.output

    def test_init_dotman_toml_content(self, clean_env):
        """Default dot-man.toml is a fully commented template, exactly.

        Pinning the exact structure (zero live sections; the two documented
        examples present once each) catches accidental "helpful" sections
        leaking into the scaffolded config. The old test only asserted the
        file parsed to some dict.
        """
        runner, _, repo_dir, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output

        content = (repo_dir / "dot-man.toml").read_text()
        assert _load_toml(content) == {}
        assert content.count("# [") == 2
        assert '# [bashrc]\n# paths = ["~/.bashrc"]' in content
        assert '# [nvim]\n# paths = ["~/.config/nvim"]' in content
        assert (
            "# dot-man — track files with `dot-man add <path>`, "
            "switch with `dot-man navigate <branch>`."
        ) in content

    def test_init_global_toml_matches_default_branch(self, clean_env):
        """global.toml must record the branch git actually created.

        status, navigate and ``{branch}`` read ``[dot-man].current_branch``
        as the active configuration, so it must equal the branch in the
        repo — recording anything else (e.g. the DEFAULT_BRANCH constant
        while ``init.defaultBranch`` made git create a different name)
        reports a branch that was never created. The exact key sets pin
        the whole schema.
        """
        runner, _, repo_dir, _, global_toml = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output

        parsed = _load_toml(global_toml.read_text())
        assert sorted(parsed) == [
            "defaults",
            "dot-man",
            "remote",
            "security",
            "switch",
            "templates",
        ]
        assert sorted(parsed["dot-man"]) == [
            "current_branch",
            "initialized_date",
            "version",
        ]
        assert parsed["dot-man"]["current_branch"] == _actual_branch(repo_dir)


# ---------------------------------------------------------------------------
# [dot-man].current_branch must match reality after init
# ---------------------------------------------------------------------------


class TestInitRecordsActualBranch:
    """global.toml records the branch git created, not a constant.

    Git picks the initial branch from ``init.defaultBranch`` (host
    config; built-in default ``master``); an ``--import`` keeps the
    source repo's branch. Writing DEFAULT_BRANCH unconditionally leaves
    global.toml claiming ``main`` while the repo sits elsewhere, so
    status, ``{branch}`` and hooks disagree with git.
    """

    def test_fresh_init_records_git_created_branch(self, tmp_path, clean_env):
        """A virgin init records git's init.defaultBranch, not DEFAULT_BRANCH.

        Forcing ``init.defaultBranch = master`` pins the divergence
        deterministically regardless of the test host's git config.
        """
        runner, _, repo_dir, _, global_toml = clean_env
        gitconfig = tmp_path / "gitconfig"
        gitconfig.write_text("[init]\n\tdefaultBranch = master\n")

        with patch.dict(
            os.environ,
            {"GIT_CONFIG_GLOBAL": str(gitconfig), "GIT_CONFIG_NOSYSTEM": "1"},
        ):
            result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output

        assert _actual_branch(repo_dir) == "master"
        parsed = _load_toml(global_toml.read_text())
        assert parsed["dot-man"]["current_branch"] == "master"

    def test_import_init_records_source_branch(self, tmp_path, clean_env):
        """``--import`` records the source repo's branch, not DEFAULT_BRANCH."""
        runner, _, repo_dir, _, global_toml = clean_env
        source_dir, source_repo = _make_source_repo(
            tmp_path, commits=[("Initial", {"a.txt": "1"})]
        )
        source_branch = source_repo.active_branch.name

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )
        assert result.exit_code == 0, result.output

        assert _actual_branch(repo_dir) == source_branch
        parsed = _load_toml(global_toml.read_text())
        assert parsed["dot-man"]["current_branch"] == source_branch


# ---------------------------------------------------------------------------
# --no-wizard quick-start output
# ---------------------------------------------------------------------------


class TestShowQuickStart:
    def test_quick_start_shows_add_command(self, clean_env):
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "dot-man add" in result.output

    def test_quick_start_shows_status_command(self, clean_env):
        """The status hint must render as a command, not the bare word.

        A bare "status" would also match prose elsewhere in the output; the
        two-word command phrase is what the guide actually prints.
        """
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "dot-man status" in result.output

    def test_quick_start_shows_navigate_command(self, clean_env):
        """The navigate hint must render as a command, not the bare word."""
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "dot-man navigate" in result.output

    def test_quick_start_shows_config_hint(self, clean_env):
        """Quick-start should show where the config file lives."""
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "dot-man.toml" in result.output


# ---------------------------------------------------------------------------
# Wizard path (smoke tests — wizard requires interactive input, so we mock UI)
# ---------------------------------------------------------------------------


class TestSetupWizard:
    def test_wizard_completes_without_dotfiles(self, clean_env):
        """Wizard with no found dotfiles + user declining custom additions should complete."""
        runner, *_ = clean_env

        # No dotfiles exist in the temp home → confirm always False, ask returns ""
        with (
            patch("dot_man.ui.confirm", return_value=False),
            patch("dot_man.ui.ask", return_value=""),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output

    def test_wizard_output_contains_setup_complete(self, clean_env):
        """Wizard must end with the exact 'Setup Complete' banner.

        The old test's ``or "complete"`` fallback accepted nearly any output;
        this phrase is what the finale actually renders.
        """
        runner, *_ = clean_env

        with (
            patch("dot_man.ui.confirm", return_value=False),
            patch("dot_man.ui.ask", return_value=""),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert "Setup Complete" in result.output

    def test_wizard_adds_found_file(self, clean_env, tmp_path):
        """When a dotfile exists and user confirms, it should be added."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        # Create a fake ~/.bashrc
        fake_home = tmp_path / "home"
        bashrc = fake_home / ".bashrc"
        bashrc.write_text("# bash config\n")

        confirm_answers = iter(
            [True, False, False]
        )  # track this? yes; custom? no; remote? no

        def fake_confirm(msg, **_kw):
            return next(confirm_answers, False)

        with (
            patch("dot_man.ui.confirm", side_effect=fake_confirm),
            patch("dot_man.ui.ask", return_value=""),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        # Check if dotman config was updated
        assert (repo_dir / "dot-man.toml").exists()
        content = (repo_dir / "dot-man.toml").read_text()
        assert "[bashrc]" in content
        assert "~/.bashrc" in content

    def test_wizard_custom_files_loop(self, clean_env, tmp_path):
        """Test the custom file loop in the wizard."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        fake_home = tmp_path / "home"
        custom_file = fake_home / ".mycustom"
        custom_file.write_text("custom\n")

        # custom file that doesn't exist

        confirm_answers = iter([True, False])  # add custom? yes; remote? no

        def fake_confirm(msg, **_kw):
            return next(confirm_answers, False)

        ask_answers = iter(["~/.missing", "~/.mycustom", "mysection", ""])

        def fake_ask(msg, **_kw):
            return next(ask_answers, "")

        with (
            patch("dot_man.ui.confirm", side_effect=fake_confirm),
            patch("dot_man.ui.ask", side_effect=fake_ask),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert "Path doesn't exist" in result.output

        content = (repo_dir / "dot-man.toml").read_text()
        assert "[mysection]" in content
        assert "~/.mycustom" in content

    def test_wizard_quickshell_multiple_subdirs(self, clean_env, tmp_path):
        """Test auto-detection of Quickshell configs and auto-hooks."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        fake_home = tmp_path / "home"
        qs_dir = fake_home / ".config" / "quickshell"
        qs_dir.mkdir(parents=True)
        (qs_dir / "dir1").mkdir()
        (qs_dir / "dir2").mkdir()

        # confirm for both qs configs, then False for custom, False for remote
        confirm_answers = iter([True, True, False, False])

        def fake_confirm(msg, **_kw):
            return next(confirm_answers, False)

        with (patch("dot_man.ui.confirm", side_effect=fake_confirm),):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert "Quickshell - dir1" in result.output
        assert "Quickshell - dir2" in result.output
        assert "Auto-detected post_deploy hook" in result.output

        content = (repo_dir / "dot-man.toml").read_text()
        assert "[qs-dir1]" in content or "[qs-dir2]" in content
        assert (
            "~/.config/quickshell/dir1" in content
            or "~/.config/quickshell/dir2" in content
        )

    def test_wizard_remote_setup_prompt(self, clean_env):
        """Test the remote setup prompt."""
        runner, *_ = clean_env

        # confirm: custom? no; remote? yes
        confirm_answers = iter([False, True])

        def fake_confirm(msg, **_kw):
            return next(confirm_answers, False)

        # remote url
        ask_answers = iter(["https://github.com/test/repo.git", ""])

        def fake_ask(msg, **_kw):
            return next(ask_answers, "")

        with (
            patch("dot_man.ui.confirm", side_effect=fake_confirm),
            patch("dot_man.ui.ask", side_effect=fake_ask),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert "Remote set to" in result.output


# ---------------------------------------------------------------------------
# Import from existing repo
# ---------------------------------------------------------------------------


class TestInitImport:
    def test_import_nonexistent_path_fails(self, clean_env, tmp_path):
        """A non-existent local path fails with the CLI's own error, exit 1.

        The exists-check used to live in ``click.Path(exists=True)``,
        which also rejected GitHub URLs at parse time (usage error 2)
        before ``_parse_github_url`` could ever run — validation is in
        the import code itself now, so local and URL sources fail the
        same way.
        """
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        nonexistent = tmp_path / "nonexistent"
        result = runner.invoke(cli, ["init", "--import", str(nonexistent)])

        assert result.exit_code == 1
        # Rich wraps long paths; compare whitespace-normalized output
        normalized = " ".join(result.output.split())
        assert f"Path '{nonexistent}' does not exist." in normalized

    def test_import_non_git_repo_fails(self, clean_env, tmp_path):
        """Import from non-git directory should fail."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "somefile.txt").write_text("test")

        result = runner.invoke(cli, ["init", "--import", str(source_dir), "--force"])

        assert result.exit_code == 1
        assert "git repository" in result.output.lower()

    def test_import_existing_git_repo(self, clean_env, tmp_path):
        """Import from existing git repo should copy files and branches."""
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir, _source_repo = _make_source_repo(
            tmp_path,
            commits=[
                (
                    "Initial commit",
                    {
                        ".bashrc": "export PATH=$PATH:/usr/local/bin",
                        ".vimrc": "set nu",
                    },
                )
            ],
            branches=[("work", [])],
        )

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output
        assert (repo_dir / ".bashrc").exists()
        assert (repo_dir / ".vimrc").exists()
        assert (repo_dir / ".git").exists()

        from dot_man.core import GitManager

        branches = GitManager(repo_dir).list_branches()
        assert "work" in branches

    def test_import_preserves_git_history(self, clean_env, tmp_path):
        """Import from existing git repo should preserve commit history."""
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir, _source_repo = _make_source_repo(
            tmp_path,
            commits=[
                ("First commit", {"test.txt": "content1"}),
                ("Second commit", {"test.txt": "content2"}),
            ],
        )

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output

        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        commits = list(git.repo.iter_commits(max_count=5))
        commit_messages = [c.message.strip() for c in commits]

        assert any("First commit" in msg for msg in commit_messages)
        assert any("Second commit" in msg for msg in commit_messages)

    def test_import_with_branches(self, clean_env, tmp_path):
        """Import preserves every branch, including the host's default name.

        git names the initial branch after host config (master vs main), so
        capture ``active_branch.name`` instead of hardcoding "master" — the
        old test silently depended on the machine's init.defaultBranch.
        """
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir, source_repo = _make_source_repo(
            tmp_path,
            commits=[("Initial", {"test.txt": "main"})],
            branches=[("work", [("Work commit", {"test.txt": "work"})])],
        )
        default_branch = source_repo.active_branch.name

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output

        from dot_man.core import GitManager

        branches = GitManager(repo_dir).list_branches()

        assert default_branch in branches
        assert "work" in branches

    def test_import_unicode_filename_lands_in_repo(self, clean_env, tmp_path):
        """Non-ASCII filenames must survive the import copy byte-for-byte.

        Filesystem round-trips are where encodings break; a lost unicode name
        would silently drop the user's file from tracking.
        """
        runner, _, repo_dir, *_ = clean_env

        source_dir, _source_repo = _make_source_repo(
            tmp_path,
            commits=[("Unicode commit", {"héllo wörld.txt": "unicode content"})],
        )

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output

        imported = repo_dir / "héllo wörld.txt"
        assert imported.exists()
        assert imported.read_text() == "unicode content"

    def test_import_repo_without_commits_succeeds(self, clean_env, tmp_path):
        """A freshly git-inited repo (zero commits) imports without crashing.

        There is no history to copy, so the target must fall back to
        dot-man's own scaffold — an empty repo is a legal import source.
        """
        runner, _, repo_dir, _, global_toml = clean_env

        source_dir, _source_repo = _make_source_repo(tmp_path)

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output
        assert (repo_dir / ".git").exists()
        assert (repo_dir / "dot-man.toml").exists()
        assert global_toml.exists()

    def test_import_empty_tree_repo_preserves_commit(self, clean_env, tmp_path):
        """A source repo whose only commit has no files still imports cleanly.

        Guards the copy path against an empty-tree crash and proves history
        survives even when the commit carries zero entries.
        """
        runner, _, repo_dir, *_ = clean_env

        source_dir, _source_repo = _make_source_repo(
            tmp_path, commits=[("Empty commit", {})]
        )

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output

        from dot_man.core import GitManager

        messages = [c.message.strip() for c in GitManager(repo_dir).repo.iter_commits()]
        assert "Empty commit" in messages


class TestGitHubImport:
    def test_clone_failure_exits_once_with_message(self, clean_env):
        """``init --import <github url>`` reaches the clone and fails cleanly.

        ``click.Path(exists=True)`` on ``--import`` used to reject URLs
        at parse time (exit 2) so this branch was unreachable; the URL
        must now flow to ``_clone_github_repo``, which failing exits 1
        and is ATTEMPTED EXACTLY ONCE (the duplicate retry that used to
        sit after ``error()`` was unreachable — error() raises).
        """
        runner, *_ = clean_env

        with patch(
            "dot_man.cli.init_cmd._clone_github_repo", return_value=None
        ) as mock_clone:
            result = runner.invoke(
                cli,
                [
                    "init",
                    "--import",
                    "https://github.com/user/dotfiles.git",
                    "--force",
                    "--no-wizard",
                ],
            )

        assert result.exit_code == 1, result.output
        assert "Failed to clone GitHub repository." in result.output
        assert mock_clone.call_count == 1

    def test_parse_github_https_url(self):
        """Parse HTTPS GitHub URL."""
        from dot_man.cli.init_cmd import _parse_github_url

        result = _parse_github_url("https://github.com/user/dotfiles")
        assert result == "https://github.com/user/dotfiles.git"

        result = _parse_github_url("https://github.com/user/dotfiles.git")
        assert result == "https://github.com/user/dotfiles.git"

    def test_parse_github_ssh_url(self):
        """Parse SSH GitHub URL."""
        from dot_man.cli.init_cmd import _parse_github_url

        result = _parse_github_url("git@github.com:user/dotfiles")
        assert result == "git@github.com:user/dotfiles.git"

    def test_parse_github_shorthand(self):
        """Parse GitHub shorthand URL."""
        from dot_man.cli.init_cmd import _parse_github_url

        result = _parse_github_url("github.com/user/dotfiles")
        assert result == "https://github.com/user/dotfiles.git"

    def test_parse_non_github_url(self):
        """Non-GitHub URLs should return None."""
        from dot_man.cli.init_cmd import _parse_github_url

        result = _parse_github_url("/home/user/dotfiles")
        assert result is None

        result = _parse_github_url("https://gitlab.com/user/dotfiles")
        assert result is None

        result = _parse_github_url("https://github.com")
        assert result is None

    def test_parse_github_url_trailing_slash_normalized(self):
        """A trailing slash (browser copy/paste) still parses to a clone URL.

        Returning None sent the URL down the *local path* branch, where
        ``dot-man import https://github.com/user/dots/`` failed with
        "Path does not exist". The slash must be stripped before appending
        .git so the result is ``dots.git``, never the mangled ``dots/.git``.
        """
        from dot_man.cli.init_cmd import _parse_github_url

        assert (
            _parse_github_url("https://github.com/user/dots/")
            == "https://github.com/user/dots.git"
        )
        assert (
            _parse_github_url("github.com/user/dots/")
            == "https://github.com/user/dots.git"
        )
        assert (
            _parse_github_url("https://github.com/user/dots/ ")
            == "https://github.com/user/dots.git"
        )

    def test_parse_github_url_tolerates_surrounding_whitespace(self):
        """Leading/trailing whitespace from copy/paste is stripped, not fatal."""
        from dot_man.cli.init_cmd import _parse_github_url

        assert (
            _parse_github_url(" https://github.com/user/dots")
            == "https://github.com/user/dots.git"
        )
        assert (
            _parse_github_url("https://github.com/user/dots.git ")
            == "https://github.com/user/dots.git"
        )
        assert (
            _parse_github_url("git@github.com:user/dots ")
            == "git@github.com:user/dots.git"
        )


def test_hook_suggestion_shown(tmp_path):
    """Detected tool hooks are announced inline while prompting."""
    from dot_man.cli import init_cmd

    target = tmp_path / ".bashrc"
    target.write_text("export X=1")
    with (
        patch("dot_man.cli.init_cmd.ui") as mock_ui,
        patch(
            "dot_man.cli.init_cmd.get_auto_hooks_for_config",
            return_value={"post_deploy": "echo reloaded"},
        ),
    ):
        mock_ui.confirm.return_value = True
        init_cmd._wizard_prompt_for_files([(str(target), "Bash shell", "bashrc")], [])
    printed = " ".join(str(c) for c in mock_ui.console.print.call_args_list)
    assert "post_deploy" in printed
    assert "echo reloaded" in printed


def test_hook_suggestion_shown_qs_branch(tmp_path):
    """Hook suggestion also prints on the qs- early-continue path."""
    from dot_man.cli import init_cmd

    target = tmp_path / "my-config"
    target.mkdir()
    (target / "shell.qml").write_text("// qml")
    with (
        patch("dot_man.cli.init_cmd.ui") as mock_ui,
        patch(
            "dot_man.cli.init_cmd.get_auto_hooks_for_config",
            return_value={"post_deploy": "echo reloaded"},
        ),
    ):
        mock_ui.confirm.return_value = True
        init_cmd._wizard_prompt_for_files(
            [(str(target), "Quickshell foo", "qs-foo")], []
        )
    printed = " ".join(str(c) for c in mock_ui.console.print.call_args_list)
    assert "post_deploy" in printed
    assert "echo reloaded" in printed


def test_format_hook_example():
    from dot_man.cli.init_cmd import _format_hook_example

    assert _format_hook_example("bash", None) is None
    line = _format_hook_example("bash", "echo reloaded")
    assert "bash" in line
    assert "echo reloaded" in line


def test_format_hook_example_empty_string_returns_none():
    """An empty hook must behave like None — no blank 'Example:' line.

    Empty strings are what an unset config value collapses to after
    stripping, so treating them differently would render a dangling line.
    """
    from dot_man.cli.init_cmd import _format_hook_example

    assert _format_hook_example("bash", "") is None


def test_show_next_steps_mentions_navigate():
    from dot_man.cli import init_cmd

    with patch("dot_man.cli.init_cmd.ui") as mock_ui:
        with patch("dot_man.cli.init_cmd.status_cmd") as mock_status:
            init_cmd._wizard_show_next_steps([("~/.bashrc", "bashrc")])
    steps = mock_ui.next_steps.call_args[0][0]
    assert any("navigate" in step for step in steps)
    mock_status.status.callback.assert_called_once_with(False, False, False)


def test_show_next_steps_uses_next_steps_block():
    """Wizard finale renders through the shared next-steps block."""
    from dot_man.cli import init_cmd

    with patch("dot_man.cli.init_cmd.ui") as mock_ui:
        with patch("dot_man.cli.init_cmd.status_cmd"):
            init_cmd._wizard_show_next_steps([("~/.bashrc", "bashrc")])
    steps = mock_ui.next_steps.call_args[0][0]
    assert any("dot-man status" in step for step in steps)

    with patch("dot_man.cli.init_cmd.ui") as mock_ui:
        with patch("dot_man.cli.init_cmd.status_cmd"):
            init_cmd._wizard_show_next_steps([])
    steps = mock_ui.next_steps.call_args[0][0]
    assert any("dot-man add" in step for step in steps)
