"""Tests for cli/profile_cmd.py — profile create/list/switch/detect/set-branch/delete."""

import socket

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestProfileHelp:
    def test_profile_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0
        assert "profile" in result.output.lower()

    def test_profile_list_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "list", "--help"])
        assert result.exit_code == 0

    def test_profile_create_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "create", "--help"])
        assert result.exit_code == 0
        assert "--inherits" in result.output
        assert "--hostname" in result.output

    def test_profile_detect_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "detect", "--help"])
        assert result.exit_code == 0

    def test_profile_set_branch_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["profile", "set-branch", "--help"])
        assert result.exit_code == 0


class TestProfileList:
    def test_profile_list_empty(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0
        assert "No profiles defined" in result.output or "Profile" in result.output

    def test_profile_list_after_create(self, integration_runner):
        integration_runner.invoke(cli, ["profile", "create", "work"])
        result = integration_runner.invoke(cli, ["profile", "list"])
        assert result.exit_code == 0
        assert "work" in result.output


class TestProfileCreate:
    def test_profile_create_simple(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "create", "work"])
        assert result.exit_code == 0
        assert "work" in result.output

    def test_profile_create_with_hostname(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "create", "laptop", "-h", "my-laptop"]
        )
        assert result.exit_code == 0
        assert "laptop" in result.output

    def test_profile_create_with_multiple_hostnames(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "create", "dev", "-h", "laptop1", "-h", "laptop2"]
        )
        assert result.exit_code == 0

    def test_profile_create_duplicate(self, integration_runner):
        integration_runner.invoke(cli, ["profile", "create", "work"])
        result = integration_runner.invoke(cli, ["profile", "create", "work"])
        assert result.exit_code != 0

    def test_profile_create_with_inherits(self, integration_runner):
        integration_runner.invoke(cli, ["profile", "create", "base"])
        result = integration_runner.invoke(
            cli, ["profile", "create", "work", "-i", "base"]
        )
        assert result.exit_code == 0
        assert "Inherits from" in result.output

    def test_profile_create_with_invalid_inherits(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "create", "work", "-i", "nonexistent"]
        )
        assert result.exit_code != 0


class TestProfileSetBranch:
    def test_set_branch(self, integration_runner):
        integration_runner.invoke(cli, ["profile", "create", "work"])
        result = integration_runner.invoke(
            cli, ["profile", "set-branch", "work", "work-branch"]
        )
        assert result.exit_code == 0
        assert "work-branch" in result.output

    def test_set_branch_nonexistent_profile(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "set-branch", "nope", "branch"]
        )
        assert result.exit_code != 0


class TestProfileDelete:
    def test_delete_profile(self, integration_runner):
        integration_runner.invoke(cli, ["profile", "create", "temp"])
        result = integration_runner.invoke(
            cli, ["profile", "delete", "temp", "--force"]
        )
        assert result.exit_code == 0
        assert "deleted" in result.output.lower()

    def test_delete_nonexistent(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "delete", "nope", "--force"]
        )
        assert result.exit_code != 0


class TestProfileDetect:
    def test_detect_no_profiles(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "detect"])
        assert result.exit_code == 0

    def test_detect_matching_hostname(self, integration_runner):
        hostname = socket.gethostname()
        integration_runner.invoke(cli, ["profile", "create", "myhost", "-h", hostname])
        result = integration_runner.invoke(cli, ["profile", "detect"])
        assert result.exit_code == 0
        assert "myhost" in result.output

    def test_detect_partial_hostname(self, integration_runner):
        hostname = socket.gethostname()
        # Create profile with partial hostname
        partial = hostname[:4] if len(hostname) > 4 else hostname
        integration_runner.invoke(cli, ["profile", "create", "partial", "-h", partial])
        result = integration_runner.invoke(cli, ["profile", "detect"])
        assert result.exit_code == 0


class TestProfileSwitch:
    def test_switch_to_profile_success(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "create", "work"])
        assert result.exit_code == 0

        from dot_man.operations import get_operations

        ops = get_operations()
        if not ops.git.repo.heads:
            from pathlib import Path

            dummy = Path(ops.git.repo_path) / "dummy.txt"
            dummy.write_text("hello")
            ops.git.repo.index.add(["dummy.txt"])
            ops.git.repo.index.commit("Initial")

        ops.git.create_branch("work")

        result = integration_runner.invoke(cli, ["profile", "switch", "work"])
        assert result.exit_code == 0
        assert "Switched to profile 'work'" in result.output

        assert ops.global_config.current_profile == "work"
        assert ops.git.repo.active_branch.name == "work"

    def test_switch_to_profile_missing_branch(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["profile", "create", "missing-branch-profile"]
        )
        assert result.exit_code == 0

        result = integration_runner.invoke(
            cli, ["profile", "switch", "missing-branch-profile"]
        )
        assert result.exit_code == 0
        assert "does not exist" in result.output
        assert "profile saved but no branch" in result.output

        from dot_man.operations import get_operations

        ops = get_operations()
        assert ops.global_config.current_profile == "missing-branch-profile"

    def test_switch_to_profile_inheritance(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "create", "base"])
        assert result.exit_code == 0
        result = integration_runner.invoke(
            cli, ["profile", "set-branch", "base", "main-branch"]
        )
        assert result.exit_code == 0

        result = integration_runner.invoke(
            cli, ["profile", "create", "child", "--inherits", "base"]
        )
        assert result.exit_code == 0

        from dot_man.operations import get_operations

        ops = get_operations()
        if not ops.git.repo.heads:
            from pathlib import Path

            dummy = Path(ops.git.repo_path) / "dummy.txt"
            dummy.write_text("hello")
            ops.git.repo.index.add(["dummy.txt"])
            ops.git.repo.index.commit("Initial")

        ops.git.create_branch("main-branch")

        result = integration_runner.invoke(cli, ["profile", "switch", "child"])
        assert result.exit_code == 0
        assert "Switched to profile 'child'" in result.output

        assert ops.global_config.current_profile == "child"
        assert ops.git.repo.active_branch.name == "main-branch"

    def test_switch_to_nonexistent_profile(self, integration_runner):
        result = integration_runner.invoke(cli, ["profile", "switch", "nonexistent"])
        assert result.exit_code != 0
        assert "does not exist" in result.output
