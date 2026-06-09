"""Tests for dot_man.encryption — EncryptionManager."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from dot_man.encryption import (
    EncryptionError,
    EncryptionManager,
    detect_available_encryption,
    is_age_available,
    is_gpg_available,
)


class TestEncryptionManager:
    def test_encrypt_gpg(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.asc"
        inp.write_text("secret data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mgr.encrypt_file(inp, out, recipient="test@example.com")

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "gpg" in args
        assert "--encrypt" in args
        assert "--recipient" in args
        assert "test@example.com" in args

    def test_encrypt_gpg_symmetric(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.asc"
        inp.write_text("secret data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mgr.encrypt_file(inp, out)

        args = mock_run.call_args[0][0]
        assert "--symmetric" in args
        assert "--recipient" not in args

    def test_encrypt_gpg_error(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.asc"
        inp.write_text("data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="bad key")
            with pytest.raises(EncryptionError, match="GPG encryption failed"):
                mgr.encrypt_file(inp, out)

    def test_encrypt_gpg_not_found(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.asc"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(EncryptionError, match="GPG not installed"):
                mgr.encrypt_file(inp, out)

    def test_encrypt_gpg_timeout(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.asc"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gpg", 30)):
            with pytest.raises(EncryptionError, match="timed out"):
                mgr.encrypt_file(inp, out)

    def test_encrypt_age(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.age"
        inp.write_text("secret")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mgr.encrypt_file(inp, out, recipient="age1test")

        args = mock_run.call_args[0][0]
        assert "age" in args
        assert "--encrypt" in args
        assert "-r" in args
        assert "age1test" in args

    def test_encrypt_age_no_recipient(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.age"
        with pytest.raises(EncryptionError, match="requires a recipient"):
            mgr.encrypt_file(inp, out)

    def test_encrypt_age_error(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.age"
        inp.write_text("data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="bad key")
            with pytest.raises(EncryptionError, match="AGE encryption failed"):
                mgr.encrypt_file(inp, out, recipient="age1test")

    def test_encrypt_age_not_found(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.age"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(EncryptionError, match="AGE not installed"):
                mgr.encrypt_file(inp, out, recipient="age1test")

    def test_encrypt_age_timeout(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "encrypted.age"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("age", 30)):
            with pytest.raises(EncryptionError, match="timed out"):
                mgr.encrypt_file(inp, out, recipient="age1test")

    def test_encrypt_unknown_method(self, tmp_path):
        mgr = EncryptionManager(method="invalid")
        inp = tmp_path / "plain.txt"
        out = tmp_path / "out"
        with pytest.raises(EncryptionError, match="Unknown encryption method"):
            mgr.encrypt_file(inp, out)

    def test_decrypt_gpg(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        inp.write_text("encrypted data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mgr.decrypt_file(inp, out)

        args = mock_run.call_args[0][0]
        assert "gpg" in args
        assert "--decrypt" in args

    def test_decrypt_gpg_with_recipient(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mgr.decrypt_file(inp, out, recipient="key-id")

        args = mock_run.call_args[0][0]
        assert "--recipient" in args
        assert "key-id" in args

    def test_decrypt_gpg_error(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="bad pass")
            with pytest.raises(EncryptionError, match="GPG decryption failed"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_gpg_not_found(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(EncryptionError, match="GPG not installed"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_gpg_timeout(self, tmp_path):
        mgr = EncryptionManager(method="gpg")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gpg", 30)):
            with pytest.raises(EncryptionError, match="timed out"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_age(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "encrypted.age"
        out = tmp_path / "decrypted.txt"
        inp.write_text("encrypted")

        with (
            patch("subprocess.run") as mock_run,
            patch.dict(os.environ, {}, clear=True),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            mgr.decrypt_file(inp, out)

        args = mock_run.call_args[0][0]
        assert "age" in args
        assert "--decrypt" in args
        assert "-i" not in args

    def test_decrypt_age_with_identity(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "encrypted.age"
        out = tmp_path / "decrypted.txt"
        inp.write_text("encrypted")

        with (
            patch("subprocess.run") as mock_run,
            patch.dict(os.environ, {"AGE_IDENTITY_FILE": "/key.txt"}),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            mgr.decrypt_file(inp, out)

        args = mock_run.call_args[0][0]
        assert "-i" in args
        assert "/key.txt" in args

    def test_decrypt_age_error(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "encrypted.age"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="bad key")
            with pytest.raises(EncryptionError, match="AGE decryption failed"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_age_not_found(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "encrypted.age"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(EncryptionError, match="AGE not installed"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_age_timeout(self, tmp_path):
        mgr = EncryptionManager(method="age")
        inp = tmp_path / "encrypted.age"
        out = tmp_path / "decrypted.txt"
        inp.write_text("data")

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("age", 30)):
            with pytest.raises(EncryptionError, match="timed out"):
                mgr.decrypt_file(inp, out)

    def test_decrypt_unknown_method(self, tmp_path):
        mgr = EncryptionManager(method="invalid")
        inp = tmp_path / "encrypted.asc"
        out = tmp_path / "decrypted.txt"
        with pytest.raises(EncryptionError, match="Unknown encryption method"):
            mgr.decrypt_file(inp, out)


class TestIsGpgAvailable:
    def test_available(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            assert is_gpg_available() is True

    def test_not_available(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert is_gpg_available() is False

    def test_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("gpg", 5)):
            assert is_gpg_available() is False


class TestIsAgeAvailable:
    def test_available(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            assert is_age_available() is True

    def test_not_available(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert is_age_available() is False

    def test_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("age", 5)):
            assert is_age_available() is False


class TestDetectAvailableEncryption:
    def test_both_available(self):
        with (
            patch("dot_man.encryption.is_gpg_available", return_value=True),
            patch("dot_man.encryption.is_age_available", return_value=True),
        ):
            result = detect_available_encryption()
        assert result == ["gpg", "age"]

    def test_only_gpg(self):
        with (
            patch("dot_man.encryption.is_gpg_available", return_value=True),
            patch("dot_man.encryption.is_age_available", return_value=False),
        ):
            result = detect_available_encryption()
        assert result == ["gpg"]

    def test_only_age(self):
        with (
            patch("dot_man.encryption.is_gpg_available", return_value=False),
            patch("dot_man.encryption.is_age_available", return_value=True),
        ):
            result = detect_available_encryption()
        assert result == ["age"]

    def test_none_available(self):
        with (
            patch("dot_man.encryption.is_gpg_available", return_value=False),
            patch("dot_man.encryption.is_age_available", return_value=False),
        ):
            result = detect_available_encryption()
        assert result == []
