"""Secure vault for stashing and restoring secrets."""

import json
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .constants import DOT_MAN_DIR
from .exceptions import DotManError

class VaultError(DotManError):
    """Vault operation failed."""
    pass

class SecretVault:
    """
    Secure storage for redacted secrets.

    Secrets are encrypted using Fernet (symmetric encryption).
    The key is stored locally in a restricted file.

    Structure of vault.json:
    {
        "secrets": [
            {
                "file_path": "relative/path/to/file",
                "line_number": 10,
                "pattern_name": "AWS Key",
                "secret_hash": "sha256...",  # For identifying the secret
                "encrypted_value": "base64...",
                "branch": "work",
                "added_at": "iso-date"
            }
        ]
    }
    """

    def __init__(self):
        self.config_dir = DOT_MAN_DIR
        self.vault_file = self.config_dir / "vault.json"
        self.key_file = self.config_dir / ".key"
        self._fernet: Optional[Fernet] = None
        self._data: Dict[str, Any] = {"secrets": []}

    def _get_fernet(self) -> Fernet:
        """Get or create the encryption suite."""
        if self._fernet:
            return self._fernet

        if not self.key_file.exists():
            self._generate_key()

        try:
            key = self.key_file.read_bytes()
            self._fernet = Fernet(key)
            return self._fernet
        except Exception as e:
            raise VaultError(f"Failed to load encryption key: {e}")

    def _generate_key(self) -> None:
        """Generate a new encryption key."""
        key = Fernet.generate_key()

        # Ensure config dir exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Save key with restricted permissions
        self.key_file.write_bytes(key)
        self.key_file.chmod(0o600)  # Read/write for owner only

    def load(self) -> None:
        """Load vault data from disk."""
        if not self.vault_file.exists():
            self._data = {"secrets": []}
            return

        try:
            content = self.vault_file.read_text(encoding="utf-8")
            self._data = json.loads(content)
        except Exception:
            self._data = {"secrets": []}

    def save(self) -> None:
        """Save vault data to disk."""
        try:
            content = json.dumps(self._data, indent=2)
            self.vault_file.write_text(content, encoding="utf-8")
            self.vault_file.chmod(0o600)  # Restricted permissions
        except Exception as e:
            raise VaultError(f"Failed to save vault: {e}")

    def stash_secret(self,
                     file_path: str,
                     line_number: int,
                     pattern_name: str,
                     secret_value: str,
                     branch: str) -> None:
        """Encrypt and store a secret."""
        self.load()
        f = self._get_fernet()

        # Compute hash for identification (to avoid duplicates or find later)
        import hashlib
        secret_hash = hashlib.sha256(secret_value.encode()).hexdigest()

        # Encrypt
        encrypted = f.encrypt(secret_value.encode()).decode('utf-8')

        entry = {
            "file_path": str(file_path),
            "line_number": line_number,
            "pattern_name": pattern_name,
            "secret_hash": secret_hash,
            "encrypted_value": encrypted,
            "branch": branch,
            "added_at": datetime.now().isoformat()
        }

        # Check if already exists (update if so)
        for i, s in enumerate(self._data["secrets"]):
            if (s["file_path"] == str(file_path) and
                s["line_number"] == line_number and
                s["branch"] == branch):
                self._data["secrets"][i] = entry
                self.save()
                return

        self._data["secrets"].append(entry)
        self.save()

    def get_secret(self, file_path: str, line_number: int, branch: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        self.load()
        f = self._get_fernet()

        for s in self._data["secrets"]:
            if (s["file_path"] == str(file_path) and
                s["line_number"] == line_number and
                s["branch"] == branch):
                try:
                    decrypted = f.decrypt(s["encrypted_value"].encode()).decode('utf-8')
                    return decrypted
                except Exception:
                    return None
        return None

    def restore_secrets_in_content(self, content: str, file_path: str, branch: str) -> str:
        """
        Restore secrets in content by replacing placeholders with actual values from vault.
        Note: This assumes the content has redacted markers or we match by line number.
        Matching by line number is fragile if file changed.

        Better approach:
        If we saved the *redacted* line structure or hash of context, we could match better.
        For now, let's try line number matching but be careful.

        Actually, a robust way is to look for the REDACTED marker and check if we have a secret
        recorded for this file/line in the vault.
        """
        self.load()
        from .constants import SECRET_REDACTION_TEXT

        lines = content.splitlines()
        modified = False

        # Get secrets for this file/branch
        file_secrets = [
            s for s in self._data["secrets"]
            if s["file_path"] == str(file_path) and s["branch"] == branch
        ]

        if not file_secrets:
            return content

        f = self._get_fernet()

        # We need to map line numbers. If file didn't change length, line numbers match.
        # But if we are restoring to a deployed file that came from repo, line numbers should match
        # the version we scanned when saving?
        # When we SAVE, we record line numbers.
        # When we DEPLOY, we get the file from repo (which has redactions).
        # So line numbers in repo file should match what we recorded.

        new_lines = []
        for i, line in enumerate(lines, start=1):
            current_line = line
            # Check if this line has a recorded secret
            matching_secret = next((s for s in file_secrets if s["line_number"] == i), None)

            if matching_secret and SECRET_REDACTION_TEXT in line:
                try:
                    decrypted = f.decrypt(matching_secret["encrypted_value"].encode()).decode('utf-8')
                    # Replace the redaction marker with the secret
                    # Note: This is simple replacement. If multiple secrets on one line, it gets complex.
                    # Currently we assume one secret or simple replacement.
                    # But the marker is fixed "***REDACTED***".
                    # And `decrypted` is the *raw secret value*.
                    # So we need to reconstruct the line.

                    # But wait, `redact_content` in secrets.py replaced the MATCHED pattern text with marker.
                    # So `pattern_name` tells us what matched.
                    # We don't easily know exactly WHERE in the line it was if there are multiple similar parts.

                    # However, stashing the *entire line* might be safer but risks stashing non-secrets.
                    # Let's assume the vault stores the *secret value*.
                    # And we blindly replace the FIRST instance of the redaction marker with the secret value?
                    # That might be wrong if there are multiple.

                    # Optimization: If we only support one secret per line or simple cases.
                    current_line = current_line.replace(SECRET_REDACTION_TEXT, decrypted, 1)
                    modified = True
                except Exception:
                    pass

            new_lines.append(current_line)

        return "\n".join(new_lines) if modified else content
