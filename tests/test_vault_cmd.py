"""Tests for vault_cmd.py — vault rotate-key and status commands."""

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.vault_cmd import vault_cmd


class TestVaultStatus:
    """Test vault status subcommand."""

    def test_vault_status_empty(self, tmp_path):
        """Vault status with no vault file."""
        with (
            patch("dot_man.vault.DOT_MAN_DIR", tmp_path),
            patch("dot_man.vault.SecretVault") as MockVault,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": []}

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["status"])

            assert result.exit_code == 0
            vault.load.assert_called_once()

    def test_vault_status_with_secrets(self, tmp_path):
        """Vault status shows secrets count and branches."""
        key_file = tmp_path / ".key"
        key_file.write_bytes(b"test-key")

        with (
            patch("dot_man.vault.DOT_MAN_DIR", tmp_path),
            patch("dot_man.vault.SecretVault") as MockVault,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": [{"branch": "main"}, {"branch": "work"}]}

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["status"])

            assert result.exit_code == 0

    def test_vault_status_no_vault_file(self, tmp_path):
        """Vault status when vault file doesn't exist."""
        with (
            patch("dot_man.vault.DOT_MAN_DIR", tmp_path),
            patch("dot_man.vault.SecretVault") as MockVault,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": []}

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["status"])

            assert result.exit_code == 0

    def test_vault_status_with_backup_key(self, tmp_path):
        """Vault status shows backup key if it exists."""
        key_file = tmp_path / ".key"
        key_file.write_bytes(b"test-key")
        backup_file = tmp_path / ".key.bak"
        backup_file.write_bytes(b"old-key")

        with (
            patch("dot_man.vault.DOT_MAN_DIR", tmp_path),
            patch("dot_man.vault.SecretVault") as MockVault,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": []}

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["status"])

            assert result.exit_code == 0


class TestVaultRotateKey:
    """Test vault rotate-key subcommand."""

    def test_rotate_key_empty_vault(self):
        """Rotate key when vault is empty shows warning."""
        with patch("dot_man.vault.SecretVault") as MockVault:
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": []}

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["rotate-key"])

            assert result.exit_code == 0
            vault.rotate_key.assert_not_called()

    def test_rotate_key_user_aborts(self):
        """Rotate key when user declines confirmation."""
        with (
            patch("dot_man.vault.SecretVault") as MockVault,
            patch("dot_man.cli.vault_cmd.ui") as mock_ui,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": [{"branch": "main"}]}
            mock_ui.confirm.return_value = False

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["rotate-key"])

            assert result.exit_code == 0
            vault.rotate_key.assert_not_called()

    def test_rotate_key_success(self):
        """Rotate key succeeds and reports count."""
        with (
            patch("dot_man.vault.SecretVault") as MockVault,
            patch("dot_man.cli.vault_cmd.ui") as mock_ui,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": [{"branch": "main"}]}
            mock_ui.confirm.return_value = True
            vault.rotate_key.return_value = 3

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["rotate-key"])

            assert result.exit_code == 0
            vault.rotate_key.assert_called_once()

    def test_rotate_key_failure(self):
        """Rotate key handles exceptions."""
        with (
            patch("dot_man.vault.SecretVault") as MockVault,
            patch("dot_man.cli.vault_cmd.ui") as mock_ui,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": [{"branch": "main"}]}
            mock_ui.confirm.return_value = True
            vault.rotate_key.side_effect = Exception("decryption failed")

            runner = CliRunner()
            result = runner.invoke(vault_cmd, ["rotate-key"])

            assert result.exit_code == 1


class TestVaultCmdDispatch:
    """Test vault command dispatches to correct subcommand."""

    def test_vault_invalid_action(self):
        """Vault with invalid action shows error."""
        runner = CliRunner()
        result = runner.invoke(vault_cmd, ["invalid"])
        assert result.exit_code != 0

    def test_vault_no_action(self):
        """Vault with no action shows usage."""
        runner = CliRunner()
        result = runner.invoke(vault_cmd, [])
        assert result.exit_code != 0
