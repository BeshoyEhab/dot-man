"""Tests for encryption wiring into save/deploy (S3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dot_man.config import Section
from dot_man.save_deploy_ops import SaveDeployMixin
from dot_man.vault import SecretVault


class FakeOps(SaveDeployMixin):
    def __init__(self, current_branch="main"):
        self._vault = MagicMock(spec=SecretVault)
        self._current_branch = current_branch

    @property
    def vault(self):
        return self._vault

    @property
    def current_branch(self):
        return self._current_branch

    def get_section(self, name):
        raise KeyError(name)

    def get_sections(self):
        return []


class FakeEncryptionManager:
    """Deterministic stand-in for GPG/AGE (no external tools in tests)."""

    def __init__(self, method="gpg"):
        self.method = method

    def encrypt_file(self, input_path, output_path, recipient=None):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"ENC:" + Path(input_path).read_bytes())

    def decrypt_file(self, input_path, output_path, recipient=None):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(Path(input_path).read_bytes()[4:])


def _section(secret: Path, repo_base="ssh") -> Section:
    return Section(
        name="ssh",
        paths=[secret],
        repo_base=repo_base,
        encrypted=True,
        encryption_method="gpg",
        encryption_recipient="me@example.com",
    )


class TestEncryptedSave:
    def test_save_encrypts_and_never_writes_plaintext(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        secret.write_text("PRIVATE KEY")
        section = _section(secret)
        repo_plain = section.get_repo_path(secret, repo)

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo),
            patch("dot_man.encryption.EncryptionManager", FakeEncryptionManager),
        ):
            saved, _secrets, errors, _symlinks = FakeOps().save_section(section)

        assert saved == 1, errors
        assert not repo_plain.exists()
        encrypted = repo_plain.with_suffix(repo_plain.suffix + ".gpg")
        assert encrypted.read_bytes() == b"ENC:PRIVATE KEY"


class TestEncryptedDeploy:
    def test_deploy_decrypts_to_local(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        section = _section(secret)
        repo_plain = section.get_repo_path(secret, repo)
        encrypted = repo_plain.with_suffix(repo_plain.suffix + ".gpg")
        encrypted.parent.mkdir(parents=True, exist_ok=True)
        encrypted.write_bytes(b"ENC:PRIVATE KEY")

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo),
            patch("dot_man.encryption.EncryptionManager", FakeEncryptionManager),
        ):
            deployed, _changed, errors = FakeOps().deploy_section(section)

        assert deployed == 1, errors
        assert secret.read_text() == "PRIVATE KEY"

    def test_deploy_fails_closed_without_ciphertext(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        secret.write_text("LOCAL SECRET")
        section = _section(secret)

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo),
            patch("dot_man.encryption.EncryptionManager", FakeEncryptionManager),
        ):
            deployed, _changed, errors = FakeOps().deploy_section(section)

        assert deployed == 0
        assert any("encrypted" in e.lower() for e in errors)
        assert secret.read_text() == "LOCAL SECRET"

    def test_scan_detects_encrypted_file(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        section = _section(secret)
        repo_plain = section.get_repo_path(secret, repo)
        encrypted = repo_plain.with_suffix(repo_plain.suffix + ".gpg")
        encrypted.parent.mkdir(parents=True, exist_ok=True)
        encrypted.write_bytes(b"ENC:PRIVATE KEY")

        with patch("dot_man.save_deploy_ops.REPO_DIR", repo):
            plan = FakeOps().scan_deployable_changes([section])

        assert plan["sections_to_deploy"]


class FailingEncryptionManager:
    """EncryptionManager stand-in whose operations always fail."""

    def __init__(self, method="gpg"):
        self.method = method

    def encrypt_file(self, input_path, output_path, recipient=None):
        from dot_man.encryption import EncryptionError

        raise EncryptionError("gpg boom")

    def decrypt_file(self, input_path, output_path, recipient=None):
        from dot_man.encryption import EncryptionError

        raise EncryptionError("gpg boom")


class TestEncryptionErrors:
    """Encryption failures must be recorded, never crash the save/deploy."""

    def test_save_encryption_failure_records_error(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        secret.write_text("PRIVATE KEY")
        section = _section(secret)

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo),
            patch("dot_man.encryption.EncryptionManager", FailingEncryptionManager),
        ):
            saved, _secrets, errors, _symlinks = FakeOps().save_section(section)

        assert saved == 0
        assert any("Failed to encrypt" in e for e in errors)

    def test_deploy_decryption_failure_records_error(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        secret = tmp_path / "id_rsa"
        section = _section(secret)
        repo_plain = section.get_repo_path(secret, repo)
        encrypted = repo_plain.with_suffix(repo_plain.suffix + ".gpg")
        encrypted.parent.mkdir(parents=True, exist_ok=True)
        encrypted.write_bytes(b"ENC:PRIVATE KEY")

        with (
            patch("dot_man.save_deploy_ops.REPO_DIR", repo),
            patch("dot_man.encryption.EncryptionManager", FailingEncryptionManager),
        ):
            deployed, _changed, errors = FakeOps().deploy_section(section)

        assert deployed == 0
        assert any("Failed to decrypt" in e for e in errors)
