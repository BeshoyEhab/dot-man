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
        patch("dot_man.backups.DOT_MAN_DIR", dot_man_dir),
        patch("dot_man.cli.switch_cmd.REPO_DIR", repo_dir),
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
        import tomllib

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
        """Test the Quickshell disambiguation prompt."""
        runner, dot_man_dir, repo_dir, _, _ = clean_env

        fake_home = tmp_path / "home"
        qs_dir = fake_home / ".config" / "quickshell"
        qs_dir.mkdir(parents=True)
        (qs_dir / "dir1").mkdir()
        (qs_dir / "dir2").mkdir()

        # confirm for final add, then False for custom, False for remote
        confirm_answers = iter([True, False, False])

        def fake_confirm(msg, **_kw):
            return next(confirm_answers, False)

        # Ask: first 'invalid', then '1' (track dir1)
        ask_answers = iter(["invalid", "1", ""])

        def fake_ask(msg, **_kw):
            return next(ask_answers, "")

        with (
            patch("dot_man.ui.confirm", side_effect=fake_confirm),
            patch("dot_man.ui.ask", side_effect=fake_ask),
        ):
            result = runner.invoke(cli, ["init", "--force"])

        assert result.exit_code == 0, result.output
        assert "Please enter a number" in result.output

        content = (repo_dir / "dot-man.toml").read_text()
        assert "[dir1]" in content
        assert "~/.config/quickshell/dir1" in content

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
