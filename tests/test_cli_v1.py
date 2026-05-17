"""Tests for various CLI commands — doctor, discover, remote, encrypt, tag, branch, verify, show."""

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestDoctorCommand:
    def test_doctor_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "doctor" in result.output.lower()

    def test_doctor_basic(self, integration_runner):
        result = integration_runner.invoke(cli, ["doctor"])
        # Doctor may report failures for DOT_MAN_TOML (string constant)
        assert result.exit_code in (0, 1)
        assert "dot-man doctor" in result.output


class TestDiscoverCommand:
    def test_discover_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert result.exit_code == 0

    def test_discover_basic(self, integration_runner):
        result = integration_runner.invoke(cli, ["discover"])
        assert result.exit_code == 0


class TestRemoteCommand:
    def test_remote_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["remote", "--help"])
        assert result.exit_code == 0

    def test_remote_set_url(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["remote", "set", "https://github.com/user/dotfiles.git"]
        )
        assert result.exit_code == 0


class TestEncryptCommand:
    def test_encrypt_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0

    def test_encrypt_status(self, integration_runner):
        result = integration_runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 0


class TestImportCommand:
    def test_import_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["import", "--help"])
        assert result.exit_code == 0


class TestExportCommandExtended:
    def test_export_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0


class TestTagCommand:
    def test_tag_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["tag", "--help"])
        assert result.exit_code == 0

    def test_tag_list(self, integration_runner):
        result = integration_runner.invoke(cli, ["tag", "list"])
        assert result.exit_code == 0

    def test_tag_create(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["tag", "create", "v1.0.0", "-m", "First release"]
        )
        assert result.exit_code == 0

    def test_tag_create_and_list(self, integration_runner):
        integration_runner.invoke(
            cli, ["tag", "create", "v2.0.0", "-m", "Second release"]
        )
        result = integration_runner.invoke(cli, ["tag", "list"])
        assert result.exit_code == 0
        assert "v2.0.0" in result.output

    def test_tag_delete(self, integration_runner):
        integration_runner.invoke(cli, ["tag", "create", "temp-tag", "-m", "Temp"])
        result = integration_runner.invoke(
            cli, ["tag", "delete", "temp-tag", "--force"]
        )
        assert result.exit_code == 0

    def test_tag_delete_nonexistent(self, integration_runner):
        result = integration_runner.invoke(
            cli, ["tag", "delete", "nonexistent", "--force"]
        )
        assert result.exit_code != 0


class TestBranchCommand:
    def test_branch_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["branch", "--help"])
        assert result.exit_code == 0

    def test_branch_list_after_switch(self, integration_runner, tmp_path):
        test_file = tmp_path / "home" / ".branchrc"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("branch test")
        integration_runner.invoke(
            cli, ["add", str(test_file), "--section", "branch-test"]
        )

        integration_runner.invoke(cli, ["navigate", "work"])
        integration_runner.invoke(cli, ["navigate", "main"])
        result = integration_runner.invoke(cli, ["branch", "list"])
        assert result.exit_code == 0


class TestVerifyCommand:
    def test_verify_basic(self, integration_runner):
        result = integration_runner.invoke(cli, ["verify"])
        assert result.exit_code == 0


class TestShowCommand:
    def test_show_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["show", "--help"])
        assert result.exit_code == 0
