"""Tests for log, checkout, and tag commands."""

from contextlib import ExitStack

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from tests.conftest import _dot_man_patches


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def hermetic_home(tmp_path):
    """Uninitialized dot-man environment isolated from the real $HOME.

    REPO_DIR and friends are bound at import time, so overriding HOME only
    inside CliRunner.invoke cannot hide an initialized real home. Reuse
    conftest's canonical patch list so every import-bound constant (and
    ``os.environ["HOME"]``) points at a fresh temp dir; without it the
    "without init" exit codes depend on whether the developer's machine
    happens to run dot-man.
    """
    from dot_man.operations import reset_operations

    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    stack = ExitStack()
    for patcher in _dot_man_patches(
        dot_man_dir, repo_dir, backups_dir, global_toml, home
    ):
        stack.enter_context(patcher)
    reset_operations()
    yield home
    stack.close()
    reset_operations()


class TestLogCommand:
    """Tests for dot-man log command."""

    def test_log_help(self, runner, hermetic_home):
        """Help documents all three output modes: history, diff, interactive."""
        result = runner.invoke(cli, ["log", "--help"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 0
        assert "Show commit history" in result.output
        assert "diff" in result.output
        assert "interactive" in result.output

    def test_log_without_init(self, runner, hermetic_home):
        """Log fails deterministically with an actionable init hint.

        The old test accepted exit 0 or 1 because it ran against whatever
        repository the real $HOME pointed at.
        """
        result = runner.invoke(cli, ["log"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()
        assert "dot-man init" in result.output

    def test_log_help_after_invalid_file(self, runner, hermetic_home):
        """--help wins over an unknown FILE argument (Click convention)."""
        result = runner.invoke(
            cli, ["log", "bogus", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "Show commit history" in result.output


class TestCheckoutCommand:
    """Tests for dot-man checkout command."""

    def test_checkout_help(self, runner, hermetic_home):
        """Checkout help shows deprecation notice, replacement, and argument."""
        result = runner.invoke(
            cli, ["checkout", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "DEPRECATED" in result.output
        assert "navigate" in result.output.lower()
        assert "TARGET" in result.output

    def test_checkout_without_init(self, runner, hermetic_home):
        """Deprecated checkout still warns, then fails with the init hint."""
        result = runner.invoke(
            cli, ["checkout", "abc1234"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 1
        assert "The command 'checkout' is deprecated" in result.output
        assert "not initialized" in result.output.lower()
        assert "dot-man switch" not in result.output

    def test_checkout_missing_target_usage(self, runner, hermetic_home):
        """Missing required argument is a usage error (exit 2), per Click."""
        result = runner.invoke(cli, ["checkout"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 2
        assert "Usage:" in result.output
        assert "Missing argument 'TARGET'" in result.output

    def test_checkout_unknown_tag(self, integration_runner, tmp_path):
        """A tag that does not exist fails with the exact lookup error.

        Real git state is required: the uninit path short-circuits before
        the tag lookup, so only an initialized repo exercises this branch.
        """
        result = integration_runner.invoke(
            cli,
            ["checkout", "nonexistent-tag"],
            env={"HOME": str(tmp_path / "home")},
        )
        assert result.exit_code == 1
        assert "Unknown commit or tag: nonexistent-tag" in result.output
        assert "dot-man navigate" in result.output
        assert "dot-man switch" not in result.output


class TestTagCommand:
    """Tests for dot-man tag command."""

    def test_tag_help(self, runner, hermetic_home):
        """Tag help explains the concept and lists the subcommands."""
        result = runner.invoke(cli, ["tag", "--help"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 0
        assert "Manage tags" in result.output
        assert "bookmarks" in result.output
        assert "switch" in result.output

    def test_tag_list_help(self, runner, hermetic_home):
        """List help names the behavior it performs, no init required."""
        result = runner.invoke(
            cli, ["tag", "list", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "List all tags" in result.output

    def test_tag_create_help(self, runner, hermetic_home):
        """Create help documents the optional commit and message flag."""
        result = runner.invoke(
            cli, ["tag", "create", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "Create a tag" in result.output
        assert "--message" in result.output

    def test_tag_delete_help(self, runner, hermetic_home):
        """Delete help documents the confirmation bypass flag."""
        result = runner.invoke(
            cli, ["tag", "delete", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "Delete a tag" in result.output
        assert "--force" in result.output

    def test_tag_switch_help(self, runner, hermetic_home):
        """Deprecated tag switch help points at navigate instead."""
        result = runner.invoke(
            cli, ["tag", "switch", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "Switch to a tag" in result.output
        assert "DEPRECATED" in result.output
        assert "navigate" in result.output.lower()

    def test_tag_sub_help_works_before_init(self, runner, hermetic_home):
        """Tag sub-help answers before the init gate, like every --help.

        The guard used to sit on the *group* callback, which Click runs
        after resolving the subcommand but before parsing its --help —
        so `tag list --help` printed the welcome banner (exit 1) while
        `tag --help` and `log --help` worked fine uninitialized.
        """
        result = runner.invoke(
            cli, ["tag", "list", "--help"], env={"HOME": str(hermetic_home)}
        )
        assert result.exit_code == 0
        assert "List all tags" in result.output
        assert "not initialized" not in result.output.lower()

    def test_tag_subcommand_still_requires_init(self, runner, hermetic_home):
        """Moving the gate behind help must not drop the gate itself."""
        result = runner.invoke(cli, ["tag", "list"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()

    def test_tag_without_init(self, runner, hermetic_home):
        """Tag listing fails deterministically with the init hint."""
        result = runner.invoke(cli, ["tag", "list"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 1
        assert "not initialized" in result.output.lower()
        assert "dot-man init" in result.output

    def test_tag_unknown_subcommand_usage(self, runner, hermetic_home):
        """Unknown subcommand is a usage error (exit 2), per Click."""
        result = runner.invoke(cli, ["tag", "bogus"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 2
        assert "Usage:" in result.output
        assert "No such command 'bogus'" in result.output

    def test_tag_without_subcommand_usage(self, runner, hermetic_home):
        """Bare group invocation prints full help and exits 2."""
        result = runner.invoke(cli, ["tag"], env={"HOME": str(hermetic_home)})
        assert result.exit_code == 2
        assert "Usage:" in result.output
        assert "Manage tags" in result.output


class TestCheckoutReturnWording:
    """Detached-HEAD helpers point at navigate, never switch."""

    def _printed(self, mock_ui):
        parts = []
        for call in mock_ui.console.print.call_args_list:
            for arg in call.args:
                parts.append(str(getattr(arg, "renderable", arg)))
        return " ".join(parts)

    def test_checkout_tag_return_wording(self):
        from unittest.mock import MagicMock, call, patch

        from dot_man.cli import log_cmd

        ops = MagicMock()
        ops.git.get_tag_commit.return_value = "abc1234"
        with (
            patch.object(log_cmd, "ui") as mock_ui,
            patch.object(log_cmd, "success"),
        ):
            log_cmd._checkout_tag(ops, "main", "v1")

        printed = self._printed(mock_ui)
        assert "dot-man navigate" in printed
        assert "dot-man switch" not in printed
        # Same dirty check as _checkout_commit: warn (naming the branch)
        # before moving HEAD, so uncommitted changes aren't abandoned
        # silently. get_tag_commit first — no warning for a missing tag.
        assert "You have uncommitted changes on branch [bold]main[/bold]" in printed
        assert ops.method_calls == [
            call.git.get_tag_commit("v1"),
            call.git.is_dirty(),
            call.git.checkout_commit("abc1234"),
        ]

    def test_checkout_commit_return_wording(self):
        from unittest.mock import MagicMock, call, patch

        from dot_man.cli import log_cmd

        ops = MagicMock()
        with (
            patch.object(log_cmd, "ui") as mock_ui,
            patch.object(log_cmd, "success"),
        ):
            log_cmd._checkout_commit(ops, "main", "abc1234")

        printed = self._printed(mock_ui)
        assert "dot-man navigate" in printed
        assert "dot-man switch" not in printed
        assert ops.method_calls == [
            call.git.repo.commit("abc1234"),
            call.git.is_dirty(),
            call.git.checkout_commit("abc1234"),
        ]
