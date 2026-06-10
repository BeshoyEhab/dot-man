"""Comprehensive tests for encrypt command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_man.cli.interface import cli
from dot_man.encryption import EncryptionError


class TestEncryptHelp:
    """Test encrypt command help."""

    def test_encrypt_help(self):
        """Test encrypt help displays."""
        result = CliRunner().invoke(cli, ["encrypt", "--help"])
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower()
        assert "decrypt" in result.output.lower()

    def test_encrypt_encrypt_help(self):
        """Test encrypt encrypt subcommand help."""
        result = CliRunner().invoke(cli, ["encrypt", "encrypt", "--help"])
        assert result.exit_code == 0
        assert "--recipient" in result.output or "-r" in result.output

    def test_encrypt_decrypt_help(self):
        """Test encrypt decrypt subcommand help."""
        result = CliRunner().invoke(cli, ["encrypt", "decrypt", "--help"])
        assert result.exit_code == 0
        assert "--recipient" in result.output or "-r" in result.output

    def test_encrypt_status_help(self):
        """Test encrypt status subcommand help."""
        result = CliRunner().invoke(cli, ["encrypt", "status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_encrypt_method_option(self):
        """Test --method option is recognized."""
        result = CliRunner().invoke(cli, ["encrypt", "--help"])
        assert "--method" in result.output or "-m" in result.output

    def test_encrypt_recipient_option(self):
        """Test --recipient option is recognized."""
        result = CliRunner().invoke(cli, ["encrypt", "--help"])
        assert "--recipient" in result.output or "-r" in result.output

    def test_invalid_action(self):
        """Test that invalid action is rejected."""
        result = CliRunner().invoke(cli, ["encrypt", "invalid"])
        assert result.exit_code == 2
        assert "invalid" in result.output.lower()


class TestEncryptNoTools:
    """Test encrypt command behavior when no encryption tools available."""

    def test_encrypt_status_no_tools(self):
        """Test status fails when no encryption tools available."""
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption", return_value=[]
        ):
            result = CliRunner().invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 1
        assert "No encryption tools available" in result.output

    def test_encrypt_encrypt_no_tools(self):
        """Test encrypt action fails when no encryption tools available."""
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption", return_value=[]
        ):
            result = CliRunner().invoke(cli, ["encrypt", "encrypt", "test-section"])
        assert result.exit_code == 1
        assert "No encryption tools available" in result.output

    def test_encrypt_decrypt_no_tools(self):
        """Test decrypt action fails when no encryption tools available."""
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption", return_value=[]
        ):
            result = CliRunner().invoke(cli, ["encrypt", "decrypt", "test-section"])
        assert result.exit_code == 1
        assert "No encryption tools available" in result.output


class TestEncryptMethodFallback:
    """Test encryption method fallback behavior."""

    def test_encrypt_method_unavailable_fallback(self, integration_runner):
        """Test fallback when chosen method is unavailable."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["age"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
            patch("dot_man.cli.encrypt_cmd.EncryptionManager"),
            patch("dot_man.dotman_config.DotManConfig"),
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = []
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "encrypt",
                    "ssh-config",
                    "--method",
                    "gpg",
                    "--recipient",
                    "test@test.com",
                ],
            )

        assert (
            "not available" in result.output.lower() or "age" in result.output.lower()
        )


class TestEncryptStatus:
    """Test encryption status display."""

    def test_show_status_no_sections(self, integration_runner):
        """Test status with no sections configured."""
        runner = integration_runner
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption",
            return_value=["gpg"],
        ):
            result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 0
        assert "Encryption Status" in result.output
        assert "No encrypted sections configured" in result.output

    def test_show_status_with_unencrypted_section(self, integration_runner):
        """Test status shows unencrypted sections."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_ops.get_sections.return_value = ["ssh-config", "bashrc"]

            mock_ssh = MagicMock()
            mock_ssh.encrypted = False

            mock_bashrc = MagicMock()
            mock_bashrc.encrypted = False

            def get_section(name):
                sections = {"ssh-config": mock_ssh, "bashrc": mock_bashrc}
                return sections[name]

            mock_ops.get_section.side_effect = get_section
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 0
        # Rich strips [section_name] brackets; verify content by its other markers
        assert result.output.count("not encrypted") >= 2
        assert "No encrypted sections configured" in result.output

    def test_show_status_with_encrypted_section(self, integration_runner):
        """Test status shows encrypted sections with details."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_ops.get_sections.return_value = ["ssh-config"]

            mock_ssh = MagicMock()
            mock_ssh.encrypted = True
            mock_ssh.encryption_method = "gpg"
            mock_ssh.encryption_recipient = "test@example.com"

            mock_ops.get_section.return_value = mock_ssh
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 0
        # Rich strips [section_name] brackets; check method/recipient details
        assert "Method: gpg" in result.output
        assert "Recipient: test@example.com" in result.output
        assert "not encrypted" not in result.output

    def test_show_status_mixed_encrypted(self, integration_runner):
        """Test status with mix of encrypted and unencrypted sections."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_ops.get_sections.return_value = ["secrets", "bashrc"]

            mock_secrets = MagicMock()
            mock_secrets.encrypted = True
            mock_secrets.encryption_method = "age"
            mock_secrets.encryption_recipient = "age1abc123"

            mock_bashrc = MagicMock()
            mock_bashrc.encrypted = False

            def get_section(name):
                sections = {"secrets": mock_secrets, "bashrc": mock_bashrc}
                return sections[name]

            mock_ops.get_section.side_effect = get_section
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(cli, ["encrypt", "status"])
        assert result.exit_code == 0
        # Rich strips [section_name] brackets; check via method/other markers
        assert "Method: age" in result.output
        assert "Recipient: age1abc123" in result.output
        assert "not encrypted" in result.output


class TestEncryptSection:
    """Test encryption of a section."""

    def test_encrypt_encrypt_no_section_name(self, integration_runner):
        """Test encrypt requires section name."""
        runner = integration_runner
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption",
            return_value=["gpg"],
        ):
            result = runner.invoke(cli, ["encrypt", "encrypt"])
        assert result.exit_code == 1
        assert "Section name required for encryption" in result.output

    def test_encrypt_encrypt_section_not_found(self, integration_runner):
        """Test encrypt fails for non-existent section."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_ops.get_section.return_value = None
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(
                cli,
                ["encrypt", "encrypt", "nonexistent", "--recipient", "test@test.com"],
            )
        assert result.exit_code == 1
        assert "Section not found" in result.output

    def test_encrypt_encrypt_no_recipient(self, integration_runner):
        """Test encrypt fails when no recipient specified and none in config."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.encryption_recipient = None
            mock_ops.get_section.return_value = mock_section
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(cli, ["encrypt", "encrypt", "ssh-config"])
        assert result.exit_code == 1
        assert "No recipient specified" in result.output

    def test_encrypt_encrypt_recipient_from_config(self, integration_runner, tmp_path):
        """Test encrypt uses recipient from section config when not provided via CLI."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = "config-recipient@test.com"
            mock_section.get_repo_path.return_value = Path("/repo") / "ssh" / "config"
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(cli, ["encrypt", "encrypt", "ssh-config"])
        assert result.exit_code == 0
        assert "Encrypted" in result.output
        mock_enc.encrypt_file.assert_called_once()
        recipient_arg = mock_enc.encrypt_file.call_args[0][2]
        assert recipient_arg == "config-recipient@test.com"
        mock_config.update_section.assert_called_once_with(
            "ssh-config",
            encrypted=True,
            encryption_method="gpg",
            encryption_recipient="config-recipient@test.com",
        )

    def test_encrypt_encrypt_file_not_found(self, integration_runner, tmp_path):
        """Test encrypt warns when source file is missing."""
        runner = integration_runner

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = ["/nonexistent/file.txt"]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = Path("/repo") / "file.txt"
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                ["encrypt", "encrypt", "ssh-config", "--recipient", "test@test.com"],
            )
        assert result.exit_code == 0
        assert "File not found" in result.output

    def test_encrypt_encrypt_gpg_success(self, integration_runner, tmp_path):
        """Test successful GPG encryption of a section file."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = Path("/repo") / "ssh" / "config"
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "encrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 0
        assert "Encrypted" in result.output
        mock_enc.encrypt_file.assert_called_once()
        call_args = mock_enc.encrypt_file.call_args[0]
        assert str(call_args[0]) == str(real_file)
        assert str(call_args[1]) == "/repo/ssh/config.gpg"
        assert call_args[2] == "test@example.com"
        mock_config.update_section.assert_called_once_with(
            "ssh-config",
            encrypted=True,
            encryption_method="gpg",
            encryption_recipient="test@example.com",
        )

    def test_encrypt_encrypt_gpg_failure(self, integration_runner, tmp_path):
        """Test encrypt handles GPG failure gracefully."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = Path("/repo") / "ssh" / "config"
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc.encrypt_file.side_effect = EncryptionError("GPG encryption failed")
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "encrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 0
        assert "Failed to encrypt" in result.output
        assert "GPG encryption failed" in result.output

    def test_encrypt_encrypt_working_dir_none(self, integration_runner, tmp_path):
        """Test encrypt handles None working directory."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = None
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "encrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 1
        assert "Failed to determine repo working directory" in result.output


class TestDecryptSection:
    """Test decryption of a section."""

    def test_decrypt_decrypt_no_section_name(self, integration_runner):
        """Test decrypt requires section name."""
        runner = integration_runner
        with patch(
            "dot_man.cli.encrypt_cmd.detect_available_encryption",
            return_value=["gpg"],
        ):
            result = runner.invoke(cli, ["encrypt", "decrypt"])
        assert result.exit_code == 1
        assert "Section name required for decryption" in result.output

    def test_decrypt_decrypt_section_not_found(self, integration_runner):
        """Test decrypt fails for non-existent section."""
        runner = integration_runner
        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_ops.get_section.return_value = None
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(
                cli,
                ["encrypt", "decrypt", "nonexistent", "--recipient", "test@test.com"],
            )
        assert result.exit_code == 1
        assert "Section not found" in result.output

    def test_decrypt_decrypt_encrypted_file_not_found(
        self, integration_runner, tmp_path
    ):
        """Test decrypt warns when encrypted file is missing."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = Path("/repo") / "ssh" / "config"
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                ["encrypt", "decrypt", "ssh-config", "--recipient", "test@test.com"],
            )
        assert result.exit_code == 0
        assert "Encrypted file not found" in result.output

    def test_decrypt_decrypt_gpg_success(self, integration_runner, tmp_path):
        """Test successful GPG decryption of a section file."""
        runner = integration_runner
        enc_file = tmp_path / "repo" / "ssh" / "config.gpg"
        enc_file.parent.mkdir(parents=True, exist_ok=True)
        enc_file.write_text("encrypted content")

        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = enc_file.parent / enc_file.stem
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = str(enc_file.parent.parent)
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "decrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 0
        assert "Decrypted" in result.output
        mock_enc.decrypt_file.assert_called_once()
        mock_config.update_section.assert_called_once_with(
            "ssh-config", encrypted=False
        )

    def test_decrypt_decrypt_gpg_failure(self, integration_runner, tmp_path):
        """Test decrypt handles GPG failure gracefully."""
        runner = integration_runner
        enc_file = tmp_path / "repo" / "ssh" / "config.gpg"
        enc_file.parent.mkdir(parents=True, exist_ok=True)
        enc_file.write_text("encrypted content")

        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = enc_file.parent / enc_file.stem
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = str(enc_file.parent.parent)
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc.decrypt_file.side_effect = EncryptionError("GPG decryption failed")
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "decrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 0
        assert "Failed to decrypt" in result.output
        assert "GPG decryption failed" in result.output

    def test_decrypt_decrypt_working_dir_none(self, integration_runner, tmp_path):
        """Test decrypt handles None working directory."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".ssh" / "config"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("ssh config content")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["gpg"],
            ),
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = None
            mock_get_ops.return_value = mock_ops

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "decrypt",
                    "ssh-config",
                    "--recipient",
                    "test@example.com",
                ],
            )
        assert result.exit_code == 1
        assert "Failed to determine repo working directory" in result.output


class TestEncryptAgeMethod:
    """Test encryption/decryption with AGE method."""

    def test_encrypt_encrypt_age_success(self, integration_runner, tmp_path):
        """Test successful AGE encryption."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".config" / "secrets" / "token"
        real_file.parent.mkdir(parents=True, exist_ok=True)
        real_file.write_text("super-secret-token")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["age"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = (
                Path("/repo") / "secrets" / "token"
            )
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = "/repo"
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "encrypt",
                    "secrets",
                    "--method",
                    "age",
                    "--recipient",
                    "age1abc123def456",
                ],
            )
        assert result.exit_code == 0
        assert "Encrypted" in result.output
        mock_enc.encrypt_file.assert_called_once()
        assert mock_enc.encrypt_file.call_args[0][2] == "age1abc123def456"
        mock_config.update_section.assert_called_once_with(
            "secrets",
            encrypted=True,
            encryption_method="age",
            encryption_recipient="age1abc123def456",
        )

    def test_encrypt_decrypt_age_success(self, integration_runner, tmp_path):
        """Test successful AGE decryption."""
        runner = integration_runner
        real_file = tmp_path / "home" / ".config" / "secrets" / "token"
        real_file.parent.mkdir(parents=True, exist_ok=True)

        enc_file = tmp_path / "repo" / "secrets" / "token.gpg"
        enc_file.parent.mkdir(parents=True, exist_ok=True)
        enc_file.write_text("encrypted-token")

        with (
            patch(
                "dot_man.cli.encrypt_cmd.detect_available_encryption",
                return_value=["age"],
            ),
            patch("dot_man.cli.encrypt_cmd.EncryptionManager") as mock_enc_cls,
            patch("dot_man.dotman_config.DotManConfig") as mock_config_cls,
            patch("dot_man.operations.get_operations") as mock_get_ops,
        ):
            mock_ops = MagicMock()
            mock_section = MagicMock()
            mock_section.paths = [str(real_file)]
            mock_section.encryption_recipient = None
            mock_section.get_repo_path.return_value = enc_file.parent / enc_file.stem
            mock_ops.get_section.return_value = mock_section
            mock_ops.git.repo.working_dir = str(enc_file.parent.parent)
            mock_get_ops.return_value = mock_ops

            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            mock_enc = MagicMock()
            mock_enc_cls.return_value = mock_enc

            result = runner.invoke(
                cli,
                [
                    "encrypt",
                    "decrypt",
                    "secrets",
                    "--method",
                    "age",
                    "--recipient",
                    "age1abc123def456",
                ],
            )
        assert result.exit_code == 0
        assert "Decrypted" in result.output
        mock_enc.decrypt_file.assert_called_once()
        mock_config.update_section.assert_called_once_with("secrets", encrypted=False)


class TestEncryptCLIBasic:
    """Basic CLI tests for the encrypt command."""

    def test_encrypt_alias(self):
        """Test the 'enc' alias works."""
        result = CliRunner().invoke(cli, ["enc", "--help"])
        assert result.exit_code == 0
        assert "encrypt" in result.output.lower() or "decrypt" in result.output.lower()

    def test_encrypt_method_choices(self):
        """Test method choices appear in help."""
        result = CliRunner().invoke(cli, ["encrypt", "--help"])
        assert "gpg" in result.output
        assert "age" in result.output
