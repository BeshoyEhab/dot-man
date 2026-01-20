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
                     branch: str) -> str:
        """
        Encrypt and store a secret.
        Returns the SHA256 hash of the secret value for ID purposes.
        """
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
                # We can now match by hash primarily if we wanted, but sticking to loc for updates
                # is tricky if line numbers shifted.
                # Actually, if we are stashing, we want to update the entry for this content
                # regardless of where it is found?
                # For now let's keep the existing logic but ALSO allow matching by hash to avoid dups
                s["secret_hash"] == secret_hash and
                s["branch"] == branch):
                
                # Update location info
                self._data["secrets"][i] = entry
                self.save()
                return secret_hash

        self._data["secrets"].append(entry)
        self.save()
        return secret_hash

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
        
    def get_secret_by_hash(self, secret_hash: str) -> Optional[str]:
        """Retrieve and decrypt a secret by its hash."""
        self.load()
        f = self._get_fernet()

        # Search in reverse to find newest matching hash? 
        # Or just first match. Hash collisions matching secret value are fine - same secret.
        for s in self._data["secrets"]:
            if s["secret_hash"] == secret_hash:
                try:
                    decrypted = f.decrypt(s["encrypted_value"].encode()).decode('utf-8')
                    return decrypted
                except Exception:
                    continue
        return None

    def restore_secrets_in_content(self, content: str, file_path: str, branch: str) -> str:
        """
        Restore secrets in content by replacing placeholders with actual values from vault.
        """
        self.load()
        import re
        
        # Regex to find ***REDACTED:<HASH>***
        # We need to be careful about the exact format defined in constants/operations
        pattern = re.compile(r"\*\*\*REDACTED:([a-fA-F0-9]{64})\*\*\*")
        
        def replace_match(match):
            secret_hash = match.group(1)
            restored = self.get_secret_by_hash(secret_hash)
            if restored:
                return restored
            return match.group(0) # Keep redaction if not found
            
        return pattern.sub(replace_match, content)
