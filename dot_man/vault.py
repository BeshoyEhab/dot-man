"""Secure vault for stashing and restoring secrets."""

import json
import base64
import hashlib
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .constants import DOT_MAN_DIR
from .exceptions import DotManError
from .files import atomic_write_text
from .lock import FileLock, LockError

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
        self.lock_file_path = self.config_dir / ".vault.lock"
        self._fernet: Optional[Fernet] = None
        self._data: Dict[str, Any] = {"secrets": []}

        # Concurrency and Batching
        self._lock = threading.RLock()
        self._batch_mode = False
        self._dirty = False
        self._last_loaded_mtime = 0.0

    def _get_fernet(self) -> Fernet:
        """Get or create the encryption suite."""
        with self._lock:
            if self._fernet:
                return self._fernet

            if not self.key_file.exists():
                self._generate_key()

            try:
                key = self.key_file.read_bytes()
                self._fernet = Fernet(key)
                return self._fernet
            except (ValueError, OSError) as e:
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
        """Load vault data from disk if changed."""
        with self._lock:
            # If we have unsaved changes, we trust our memory over disk
            if self._dirty:
                return

            if not self.vault_file.exists():
                self._data = {"secrets": []}
                self._last_loaded_mtime = 0.0
                return

            try:
                # Check mtime to avoid unnecessary reads
                current_mtime = self.vault_file.stat().st_mtime
                if current_mtime <= self._last_loaded_mtime and self._data["secrets"]:
                    return

                content = self.vault_file.read_text(encoding="utf-8")
                self._data = json.loads(content)
                self._last_loaded_mtime = current_mtime
            except (OSError, json.JSONDecodeError):
                self._data = {"secrets": []}
                self._last_loaded_mtime = 0.0

    def save(self) -> None:
        """Save vault data to disk."""
        with self._lock:
            try:
                content = json.dumps(self._data, indent=2)

                # Use atomic write for robustness
                atomic_write_text(self.vault_file, content)
                self.vault_file.chmod(0o600)  # Restricted permissions

                # Update mtime cache so we don't reload our own write
                try:
                    self._last_loaded_mtime = self.vault_file.stat().st_mtime
                except OSError:
                    self._last_loaded_mtime = 0.0

                self._dirty = False
            except OSError as e:
                raise VaultError(f"Failed to save vault: {e}")

    @contextmanager
    def batch(self) -> Generator[None, None, None]:
        """
        Context manager to batch vault operations.
        Saves only once at the end if changes occurred.
        """
        # Acquire Process Lock
        with FileLock(self.lock_file_path):
            # Enable batch mode
            with self._lock:
                previous_mode = self._batch_mode
                self._batch_mode = True

            try:
                yield
            finally:
                # Disable batch mode and flush
                with self._lock:
                    self._batch_mode = previous_mode
                    # Only save if we are exiting the outermost batch context
                    if not self._batch_mode and self._dirty:
                        self.save()

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
        # If in batch mode, we assume lock is held by batch() (and re-entrant for threads).
        # We need thread lock to check batch mode.
        with self._lock:
            if self._batch_mode:
                return self._perform_stash(file_path, line_number, pattern_name, secret_value, branch)

        # If not batch mode, we must acquire FileLock to prevent inter-process races.
        # Retry logic for lock contention
        import time
        import random
        retries = 0
        max_retries = 50

        while True:
            try:
                with FileLock(self.lock_file_path):
                    with self._lock:
                        return self._perform_stash(file_path, line_number, pattern_name, secret_value, branch)
            except LockError:
                if retries >= max_retries:
                    raise
                retries += 1
                # Sleep between 0.05s and 0.15s
                time.sleep(0.05 + random.random() * 0.1)

    def _perform_stash(self,
                       file_path: str,
                       line_number: int,
                       pattern_name: str,
                       secret_value: str,
                       branch: str) -> str:
        """Internal stash logic, assumes locks are held."""
        self.load()
        f = self._get_fernet()

        # Compute hash for identification (to avoid duplicates or find later)
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
        updated = False
        for i, s in enumerate(self._data["secrets"]):
            if (s["file_path"] == str(file_path) and
                s["secret_hash"] == secret_hash and
                s["branch"] == branch):
                
                # Update location info
                self._data["secrets"][i] = entry
                updated = True
                break

        if not updated:
            self._data["secrets"].append(entry)

        if self._batch_mode:
            self._dirty = True
        else:
            self.save()

        return secret_hash

    def get_secret(self, file_path: str, line_number: int, branch: str) -> Optional[str]:
        """Retrieve and decrypt a secret."""
        with self._lock:
            self.load()
            f = self._get_fernet()

            for s in self._data["secrets"]:
                if (s["file_path"] == str(file_path) and
                    s["line_number"] == line_number and
                    s["branch"] == branch):
                    try:
                        decrypted = f.decrypt(s["encrypted_value"].encode()).decode('utf-8')
                        return decrypted
                    except (ValueError, TypeError): # + cryptography exceptions if imported
                        return None
            return None
        
    def get_secret_by_hash(self, secret_hash: str) -> Optional[str]:
        """Retrieve and decrypt a secret by its hash."""
        with self._lock:
            self.load()
            f = self._get_fernet()

            for s in self._data["secrets"]:
                if s["secret_hash"] == secret_hash:
                    try:
                        decrypted = f.decrypt(s["encrypted_value"].encode()).decode('utf-8')
                        return decrypted
                    except (ValueError, TypeError):
                        continue
            return None

    def restore_secrets_in_content(self, content: str, file_path: str, branch: str) -> str:
        """
        Restore secrets in content by replacing placeholders with actual values from vault.
        """
        # Lock provided by get_secret_by_hash calls, but we should probably lock the whole operation
        # to prevent reloading in loop if file changes (unlikely)
        # But get_secret_by_hash does its own locking and loading.
        
        # Regex to find ***REDACTED:<HASH>***
        import re
        pattern = re.compile(r"\*\*\*REDACTED:([a-fA-F0-9]{64})\*\*\*")
        
        def replace_match(match):
            secret_hash = match.group(1)
            restored = self.get_secret_by_hash(secret_hash)
            if restored:
                return restored
            return match.group(0) # Keep redaction if not found
            
        return pattern.sub(replace_match, content)
