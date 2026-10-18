"""Tests for the 'dot-man hooks' command argument guards."""

import click
import pytest

from dot_man.cli.interface import cli


def test_hooks_create_missing_args(integration_runner):
    """'hooks create' without phase/name exits with the guard message."""
    result = integration_runner.invoke(cli, ["hooks", "create"])
    assert result.exit_code == 1, result.output
    assert "'create' requires: pre|post NAME" in result.output


def test_hooks_delete_missing_args(integration_runner):
    """'hooks delete' without phase/name exits with the guard message."""
    result = integration_runner.invoke(cli, ["hooks", "delete"])
    assert result.exit_code == 1, result.output
    assert "'delete' requires: pre|post NAME" in result.output


def test_hooks_create_non_string_guard(integration_runner, capsys):
    """Direct call with a non-string name hits the type guard."""
    callback = cli.commands["hooks"].commands["create"].callback

    with pytest.raises(SystemExit) as excinfo:
        callback(phase="pre", name=123)

    assert excinfo.value.code == 1
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "Hook name and phase must be strings" in out


def test_hooks_delete_non_string_guard(integration_runner):
    """Direct call with a non-string name raises the ClickException guard."""
    callback = cli.commands["hooks"].commands["delete"].callback

    with pytest.raises(click.ClickException) as excinfo:
        callback(phase="pre", name=123)

    assert "Hook name and phase must be strings" in str(excinfo.value)


def test_hooks_delete_existing_and_missing(integration_runner):
    """Delete success and not-found warn paths (CLI end-to-end)."""
    created = integration_runner.invoke(cli, ["hooks", "create", "post", "deploy"])
    assert created.exit_code == 0, created.output
    assert "Created hook:" in created.output

    deleted = integration_runner.invoke(cli, ["hooks", "delete", "post", "deploy"])
    assert deleted.exit_code == 0, deleted.output
    assert "Deleted hook: post_deploy" in deleted.output

    missing = integration_runner.invoke(cli, ["hooks", "delete", "post", "deploy"])
    assert missing.exit_code == 0, missing.output
    assert "Hook not found: post_deploy" in missing.output


def test_hooks_list_output(integration_runner):
    """'hooks list' prints the available hooks table."""
    result = integration_runner.invoke(cli, ["hooks", "list"])
    assert result.exit_code == 0, result.output
    assert "Available Hooks:" in result.output
    assert "pre_switch" in result.output or "post_deploy" in result.output
