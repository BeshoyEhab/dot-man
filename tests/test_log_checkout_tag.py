"""Tests for log, checkout, and tag commands."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestLogCommand:
    """Tests for dot-man log command."""

    def test_log_help(self, runner):
        result = runner.invoke(cli, ["log", "--help"])
        assert result.exit_code == 0
        assert "Show commit history" in result.output

    def test_log_without_init(self, runner):
        """Log should handle uninitialized state."""
        result = runner.invoke(cli, ["log"])
        assert result.exit_code in [0, 1]


class TestCheckoutCommand:
    """Tests for dot-man checkout command."""

    def test_checkout_help(self, runner):
        """Checkout help should show deprecation notice."""
        result = runner.invoke(cli, ["checkout", "--help"])
        assert result.exit_code == 0
        assert "DEPRECATED" in result.output
        assert "navigate" in result.output.lower()

    def test_checkout_without_init(self, runner):
        """Checkout should handle uninitialized state."""
        result = runner.invoke(cli, ["checkout", "abc1234"])
        assert result.exit_code in [0, 1]


class TestTagCommand:
    """Tests for dot-man tag command."""

    def test_tag_help(self, runner):
        result = runner.invoke(cli, ["tag", "--help"])
        assert result.exit_code == 0
        assert "Manage tags" in result.output

    def test_tag_list_help(self, runner):
        result = runner.invoke(cli, ["tag", "list", "--help"])
        assert result.exit_code == 0

    def test_tag_create_help(self, runner):
        result = runner.invoke(cli, ["tag", "create", "--help"])
        assert result.exit_code == 0

    def test_tag_delete_help(self, runner):
        result = runner.invoke(cli, ["tag", "delete", "--help"])
        assert result.exit_code == 0

    def test_tag_switch_help(self, runner):
        result = runner.invoke(cli, ["tag", "switch", "--help"])
        assert result.exit_code == 0

    def test_tag_without_init(self, runner):
        """Tag should handle uninitialized state."""
        result = runner.invoke(cli, ["tag", "list"])
        assert result.exit_code in [0, 1]


class TestCheckoutReturnWording:
    """Detached-HEAD helpers point at navigate, never switch."""

    def _printed(self, mock_ui):
        parts = []
        for call in mock_ui.console.print.call_args_list:
            for arg in call.args:
                parts.append(str(getattr(arg, "renderable", arg)))
        return " ".join(parts)

    def test_checkout_tag_return_wording(self):
        from unittest.mock import MagicMock, patch

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

    def test_checkout_commit_return_wording(self):
        from unittest.mock import MagicMock, patch

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
