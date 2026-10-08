"""Tests for CLI ``--help``: per-command help text plus the repo-wide
before-init invariant (every invocable name answers help on a virgin env).
"""

from contextlib import ExitStack

import click
import pytest
from click.testing import CliRunner

from dot_man.cli.interface import cli
from tests.conftest import _dot_man_patches


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path):
    """Hermetic, UN-initialized dot-man environment → CliRunner.

    Layers on conftest's ``_dot_man_patches`` registry so every
    import-bound path constant (notably ``cli.common.DOT_MAN_DIR``,
    which ``require_init`` reads) points at a fresh temp dir that was
    never initialized. Without the patching, ``require_init`` would
    inspect the developer's real home and the invariant below could not
    fail here.
    """
    home = tmp_path / "home"
    home.mkdir()
    dot_man_dir = home / ".config" / "dot-man"
    repo_dir = dot_man_dir / "repo"
    backups_dir = dot_man_dir / "backups"
    global_toml = dot_man_dir / "global.toml"

    with ExitStack() as stack:
        for p in _dot_man_patches(
            dot_man_dir, repo_dir, backups_dir, global_toml, home
        ):
            stack.enter_context(p)

        from dot_man.operations import reset_operations

        reset_operations()
        yield CliRunner()


class TestConfigCommand:
    """Tests for dot-man config command."""

    def test_config_help(self, runner):
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage global configuration" in result.output

    def test_config_list_help(self, runner):
        result = runner.invoke(cli, ["config", "list", "--help"])
        assert result.exit_code == 0

    def test_config_get_help(self, runner):
        result = runner.invoke(cli, ["config", "get", "--help"])
        assert result.exit_code == 0

    def test_config_set_help(self, runner):
        result = runner.invoke(cli, ["config", "set", "--help"])
        assert result.exit_code == 0


class TestBranchCommand:
    """Tests for branch command."""

    def test_branch_help(self, runner):
        result = runner.invoke(cli, ["branch", "--help"])
        assert result.exit_code == 0

    def test_branch_list_help(self, runner):
        result = runner.invoke(cli, ["branch", "list", "--help"])
        assert result.exit_code == 0

    def test_branch_delete_help(self, runner):
        result = runner.invoke(cli, ["branch", "delete", "--help"])
        assert result.exit_code == 0


class TestRemoteCommand:
    """Tests for remote command."""

    def test_remote_help(self, runner):
        result = runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0


class TestBackupCommand:
    """Tests for backup command."""

    def test_backup_help(self, runner):
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0


class TestVerifyCommand:
    """Tests for verify command."""

    def test_verify_help(self, runner):
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0


class TestCleanCommand:
    """Tests for clean command."""

    def test_clean_help(self, runner):
        result = runner.invoke(cli, ["clean", "--help"])
        assert result.exit_code == 0


class TestDoctorCommand:
    """Tests for doctor command."""

    def test_doctor_help(self, runner):
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0


class TestOtherCommands:
    """Tests for other commands."""

    def test_edit_help(self, runner):
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0

    def test_revert_help(self, runner):
        result = runner.invoke(cli, ["revert", "--help"])
        assert result.exit_code == 0

    def test_status_help(self, runner):
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_audit_help(self, runner):
        result = runner.invoke(cli, ["audit", "--help"])
        assert result.exit_code == 0


# =============================================================================
# The --help invariant: answers help before init, for EVERY invocable name
# =============================================================================


def _iter_invocable_paths(group, prefix=()):
    """Yield the argv prefix of every name a user can type.

    ``DotManGroup.add_command`` registers aliases as extra keys in
    ``group.commands``, so this walk covers canonical names, aliases
    (``n``) and deprecated shims (``switch``/``checkout``) alike.
    """
    for name, cmd in list(group.commands.items()):
        path = prefix + (name,)
        yield path
        if isinstance(cmd, click.Group):
            yield from _iter_invocable_paths(cmd, path)


_HELP_PATHS = [()] + list(_iter_invocable_paths(cli))


class TestHelpBeforeInit:
    """``--help`` must succeed on a virgin environment for every command.

    Guards like ``require_init`` belong on subcommand callbacks: Click
    runs a GROUP's callback before parsing the subcommand's eager
    ``--help``, so a group-level guard turns a help request into an
    onboarding failure. This sweep pins the invariant across the whole
    Click tree instead of trusting per-command spot checks (the ``tag``
    group regressed exactly this way).
    """

    @pytest.mark.parametrize("path", _HELP_PATHS, ids=lambda p: " ".join(p) or "root")
    def test_help_on_virgin_env(self, clean_env, path):
        result = clean_env.invoke(cli, [*path, "--help"])

        assert result.exit_code == 0, (
            f"`dot-man {' '.join(path)} --help` failed on a virgin env: "
            f"exit={result.exit_code} exc={result.exception!r}\n{result.output}"
        )
        assert "Usage:" in result.output
        # require_init's onboarding banner = a guard ran during --help
        assert "Welcome to dot-man!" not in result.output
