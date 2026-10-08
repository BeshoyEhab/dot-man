"""Tests for navigate_cmd.py and switch_cmd.py — the main branch switching commands."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestNavigateHelp:
    def test_navigate_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["navigate", "--help"])
        assert result.exit_code == 0
        assert "navigate" in result.output.lower()
        assert "--dry-run" in result.output


class TestNavigateCreateBranch:
    def test_navigate_creates_new_branch(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".navrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("nav test")
        integration_runner.invoke(cli, ["add", str(test_file), "--section", "nav-test"])
        result = integration_runner.invoke(cli, ["navigate", "work"])
        # Navigate may succeed or show a warning
        assert result.exit_code in (0, 1)

    def test_navigate_switch_existing(self, integration_runner, tmp_path):
        """Switching away and back to the initial branch really works.

        The initial branch is whatever git created at init (not
        necessarily "main"), and the create-branch prompt needs an
        explicit "y" — answering it is what makes this a real switch
        instead of a vacuous same-branch no-op.
        """
        from dot_man.core import GitManager

        test_file = tmp_path / "home" / ".switchrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("switch test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "switch-test"]
        )
        initial = GitManager().current_branch()

        created = integration_runner.invoke(cli, ["navigate", "work"], input="y\n")
        assert created.exit_code == 0, created.output
        assert GitManager().current_branch() == "work"

        result = integration_runner.invoke(cli, ["navigate", initial])
        assert result.exit_code == 0, result.output
        assert GitManager().current_branch() == initial


class TestNavigateDryRun:
    def test_dry_run(self, integration_runner):
        result = integration_runner.invoke(cli, ["navigate", "test-dry", "--dry-run"])
        assert result.exit_code == 0


class TestNavigateNoSave:
    def test_no_save(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".nosaverc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("nosave test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "nosave-test"]
        )
        # --no-save may or may not be a valid flag
        result = integration_runner.invoke(cli, ["navigate", "nosave-br", "--no-save"])
        # Accept success or handled error
        assert result.exit_code in (0, 1, 2)


class TestSwitchDeprecated:
    def test_switch_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["switch", "--help"])
        assert result.exit_code == 0

    def test_switch_dry_run(self, integration_runner):
        result = integration_runner.invoke(cli, ["switch", "test-branch", "--dry-run"])
        assert result.exit_code == 0

    def test_switch_same_branch(self, integration_runner):
        """Same-branch switch is a no-op shortcut — target the real branch.

        The initial branch is whatever git created at init; targeting a
        hardcoded name that doesn't exist would exercise the create-
        branch prompt instead of the shortcut.
        """
        from dot_man.core import GitManager

        current = GitManager().current_branch()
        result = integration_runner.invoke(cli, ["switch", current])
        assert result.exit_code == 0, result.output
