"""Tests for vault_cmd.py — vault rotate-key and status commands."""

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.vault_cmd import vault as vault_group


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
            result = runner.invoke(vault_group, ["status"])

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
            result = runner.invoke(vault_group, ["status"])

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
            result = runner.invoke(vault_group, ["status"])

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
            result = runner.invoke(vault_group, ["status"])

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
            result = runner.invoke(vault_group, ["rotate-key"])

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
            result = runner.invoke(vault_group, ["rotate-key"])

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
            result = runner.invoke(vault_group, ["rotate-key"])

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
            result = runner.invoke(vault_group, ["rotate-key"])

            assert result.exit_code == 1


class TestVaultRotateKeyDryRun:
    """--dry-run previews the rotation without re-encrypting or prompting."""

    def test_dry_run_skips_rotation_and_confirmation(self, tmp_path):
        from dot_man.cli import vault_cmd

        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        with (
            patch("dot_man.cli.common.DOT_MAN_DIR", repo),
            patch("dot_man.cli.common.REPO_DIR", repo),
            patch("dot_man.vault.SecretVault") as MockVault,
            patch("dot_man.cli.vault_cmd.ui.confirm") as mock_confirm,
        ):
            vault = MockVault.return_value
            vault.load.return_value = None
            vault._data = {"secrets": [{"branch": "main"}, {"branch": "work"}]}

            result = CliRunner().invoke(vault_cmd.vault, ["rotate-key", "--dry-run"])

        assert result.exit_code == 0, result.output
        vault.rotate_key.assert_not_called()
        mock_confirm.assert_not_called()
        assert "dry-run" in result.output.lower()

    def test_rotate_key_help_lists_dry_run(self):
        result = CliRunner().invoke(vault_group, ["rotate-key", "--help"])

        assert result.exit_code == 0, result.output
        assert "--dry-run" in result.output


class TestVaultCmdDispatch:
    """Test vault command dispatches to correct subcommand."""

    def test_vault_invalid_action(self):
        """Vault with invalid action shows error."""
        runner = CliRunner()
        result = runner.invoke(vault_group, ["invalid"])
        assert result.exit_code != 0

    def test_vault_no_action(self):
        """Vault with no action shows usage."""
        runner = CliRunner()
        result = runner.invoke(vault_group, [])
        assert result.exit_code != 0


class TestVaultRegistration:
    """Regression: the vault group must be reachable from the main CLI."""

    def test_vault_is_registered_on_main_cli(self):
        """'dot-man vault' must exist on the root group."""
        from dot_man.cli.interface import cli

        assert "vault" in cli.commands

    def test_vault_help_lists_subcommands(self):
        """'dot-man vault --help' lists rotate-key and status."""
        from dot_man.cli.interface import cli

        result = CliRunner().invoke(cli, ["vault", "--help"])

        assert result.exit_code == 0, result.output
        assert "rotate-key" in result.output
        assert "status" in result.output
