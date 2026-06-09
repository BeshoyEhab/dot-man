"""Tests for cli/init_cmd.py — init command, show_quick_start, run_setup_wizard."""

import os
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Isolated home with patched dot-man constants — no repo yet."""
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    patches = [
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.constants.REPO_DIR", repo_dir),
        patch("dot_man.constants.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.core.REPO_DIR", repo_dir),
        patch("dot_man.config.REPO_DIR", repo_dir),
        patch("dot_man.config.GLOBAL_TOML", global_toml),
        patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        patch("dot_man.dotman_config.REPO_DIR", repo_dir),
        patch("dot_man.operations.REPO_DIR", repo_dir),
        patch("dot_man.save_deploy_ops.REPO_DIR", repo_dir),
        patch("dot_man.branch_ops.REPO_DIR", repo_dir),
        patch("dot_man.status_ops.REPO_DIR", repo_dir),
        patch("dot_man.cli.interface.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.init_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.init_cmd.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.init_cmd.BACKUPS_DIR", backups_dir),
        patch("dot_man.cli.add_cmd.REPO_DIR", repo_dir),
        patch("dot_man.backups.BACKUPS_DIR", backups_dir),
        patch("dot_man.constants.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.navigate_cmd.REPO_DIR", repo_dir),
        patch("dot_man.cli.common.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.common.REPO_DIR", repo_dir),
        patch.dict(os.environ, {"HOME": str(home)}),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()

        yield CliRunner(), dot_man_dir, repo_dir, backups_dir, global_toml


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


class TestInitHelp:
    def test_init_help_shows_force(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_init_help_shows_no_wizard(self, runner):
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--no-wizard" in result.output


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
        """init should print a success banner."""
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "initialized" in result.output.lower()

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

    def test_init_git_not_installed_exits_with_code(self, clean_env):
        """init should exit with code 2 when git is unavailable."""
        runner, *_ = clean_env

        with patch("dot_man.cli.init_cmd.is_git_installed", return_value=False):
            result = runner.invoke(cli, ["init", "--force", "--no-wizard"])

        assert result.exit_code == 2

    def test_init_dotman_toml_content(self, clean_env):
        """dot-man.toml created by init should contain valid TOML."""
        import sys

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        runner, _, repo_dir, _, _ = clean_env
        runner.invoke(cli, ["init", "--force", "--no-wizard"])

        toml_path = repo_dir / "dot-man.toml"
        content = toml_path.read_bytes()
        parsed = tomllib.loads(content.decode())
        assert isinstance(parsed, dict)


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
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "status" in result.output

    def test_quick_start_shows_switch_command(self, clean_env):
        runner, *_ = clean_env

        result = runner.invoke(cli, ["init", "--force", "--no-wizard"])
        assert result.exit_code == 0, result.output
        assert "switch" in result.output

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
        """Wizard should announce 'Setup Complete' at the end."""
        runner, *_ = clean_env

        with (
            patch("dot_man.ui.confirm", return_value=False),
            patch("dot_man.ui.ask", return_value=""),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert (
            "setup complete" in result.output.lower()
            or "complete" in result.output.lower()
        )

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
    def test_init_help_shows_import_option(self, runner):
        """init --help should show the --import option."""
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "--import" in result.output

    def test_import_nonexistent_path_fails(self, clean_env, tmp_path):
        """Import from non-existent path should fail."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        nonexistent = tmp_path / "nonexistent"
        result = runner.invoke(cli, ["init", "--import", str(nonexistent)])

        assert result.exit_code == 2

    def test_import_non_git_repo_fails(self, clean_env, tmp_path):
        """Import from non-git directory should fail."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "somefile.txt").write_text("test")

        result = runner.invoke(cli, ["init", "--import", str(source_dir), "--force"])

        assert result.exit_code == 1
        assert "not a git repository" in result.output.lower()

    def test_import_existing_git_repo(self, clean_env, tmp_path):
        """Import from existing git repo should copy files."""
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir = tmp_path / "source_repo"
        source_dir.mkdir()
        from git import Repo

        source_repo = Repo.init(source_dir)
        config_writer = source_repo.config_writer()
        config_writer.set_value("user", "name", "Test User")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (source_dir / ".bashrc").write_text("export PATH=$PATH:/usr/local/bin")
        (source_dir / ".vimrc").write_text("set nu")
        source_repo.index.add([".bashrc", ".vimrc"])
        source_repo.index.commit("Initial commit")

        source_repo.create_head("work")

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0, result.output
        assert "Imported dotfiles" in result.output
        assert (repo_dir / ".bashrc").exists()
        assert (repo_dir / ".vimrc").exists()
        assert (repo_dir / ".git").exists()

    def test_import_preserves_git_history(self, clean_env, tmp_path):
        """Import from existing git repo should preserve commit history."""
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir = tmp_path / "source_repo"
        source_dir.mkdir()
        from git import Repo

        source_repo = Repo.init(source_dir)
        config_writer = source_repo.config_writer()
        config_writer.set_value("user", "name", "Test User")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (source_dir / "test.txt").write_text("content1")
        source_repo.index.add(["test.txt"])
        source_repo.index.commit("First commit")

        (source_dir / "test.txt").write_text("content2")
        source_repo.index.add(["test.txt"])
        source_repo.index.commit("Second commit")

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0

        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        commits = list(git.repo.iter_commits(max_count=5))
        commit_messages = [c.message.strip() for c in commits]

        assert any("First commit" in msg for msg in commit_messages)
        assert any("Second commit" in msg for msg in commit_messages)

    def test_import_with_branches(self, clean_env, tmp_path):
        """Import from existing git repo should preserve branches."""
        runner, dot_man_dir, repo_dir, backups_dir, global_toml = clean_env

        source_dir = tmp_path / "source_repo"
        source_dir.mkdir()
        from git import Repo

        source_repo = Repo.init(source_dir)
        config_writer = source_repo.config_writer()
        config_writer.set_value("user", "name", "Test User")
        config_writer.set_value("user", "email", "test@test.com")
        config_writer.release()

        (source_dir / "test.txt").write_text("main")
        source_repo.index.add(["test.txt"])
        source_repo.index.commit("Initial")

        work_branch = source_repo.create_head("work")
        work_branch.checkout()
        (source_dir / "test.txt").write_text("work")
        source_repo.index.add(["test.txt"])
        source_repo.index.commit("Work commit")

        source_repo.heads["master"].checkout()

        result = runner.invoke(
            cli, ["init", "--import", str(source_dir), "--force", "--no-wizard"]
        )

        assert result.exit_code == 0

        from dot_man.core import GitManager

        git = GitManager(repo_dir)
        branches = git.list_branches()

        assert "master" in branches
        assert "work" in branches


class TestGitHubImport:
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
