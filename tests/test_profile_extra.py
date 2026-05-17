"""Additional tests for profile command."""

import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestProfileExtra:
    """Additional profile command tests."""

    def test_profile_invalid_command(self, runner):
        """Test invalid profile subcommand."""
        result = runner.invoke(cli, ["profile", "invalid"])
        assert result.exit_code == 2


class TestProfileCommands:
    """Test profile CLI commands."""

    def test_profile_help(self, runner):
        """Test profile help displays."""
        result = runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0
