"""Encryption support for sensitive dotfiles using GPG and AGE."""

import os
import subprocess
from pathlib import Path
from typing import Literal

from .exceptions import DotManError


class EncryptionError(DotManError):
    """Encryption operation failed."""

    pass


def _validate_recipient(recipient: str, tool: str) -> None:
    """Reject recipients that could be smuggled as command-line options.

    A recipient beginning with ``-`` would be interpreted by gpg/age as an
    option (e.g. ``--output /etc/passwd``); embedded newlines/controls are
    also rejected. Legitimate recipients (emails, key IDs, ``age1...``
    keys) never start with ``-``.
    """
    if not recipient:
        raise EncryptionError(f"{tool} recipient must not be empty")
    if recipient.startswith("-"):
        raise EncryptionError(
            f"Refusing {tool} recipient starting with '-': {recipient!r}"
        )
    if any(ch in recipient for ch in "\r\n\x00"):
        raise EncryptionError(f"Invalid control character in {tool} recipient")


class EncryptionManager:
    """Manage file encryption using GPG or AGE."""

    def __init__(self, method: Literal["gpg", "age"] = "gpg"):
        self.method = method

    def encrypt_file(
        self, input_path: Path, output_path: Path, recipient: str | None = None
    ) -> None:
        """Encrypt a file.

        Args:
            input_path: Path to the file to encrypt
            output_path: Path where encrypted file will be saved
            recipient: Encryption recipient (GPG key ID or AGE recipient)
        """
        if self.method == "gpg":
            self._encrypt_gpg(input_path, output_path, recipient)
        elif self.method == "age":
            self._encrypt_age(input_path, output_path, recipient)
        else:
            raise EncryptionError(f"Unknown encryption method: {self.method}")

    def decrypt_file(
        self, input_path: Path, output_path: Path, recipient: str | None = None
    ) -> None:
        """Decrypt a file.

        Args:
            input_path: Path to the encrypted file
            output_path: Path where decrypted file will be saved
            recipient: Decryption recipient (GPG key ID or AGE recipient)
        """
        if self.method == "gpg":
            self._decrypt_gpg(input_path, output_path, recipient)
        elif self.method == "age":
            self._decrypt_age(input_path, output_path, recipient)
        else:
            raise EncryptionError(f"Unknown encryption method: {self.method}")

    def _encrypt_gpg(
        self, input_path: Path, output_path: Path, recipient: str | None
    ) -> None:
        """Encrypt using GPG."""
        cmd = ["gpg", "--encrypt", "--armor", "--batch"]

        if recipient:
            _validate_recipient(recipient, "GPG")
            cmd.extend(["--recipient", recipient])
        else:
            cmd.append("--symmetric")

        cmd.extend(["--output", str(output_path), "--", str(input_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise EncryptionError(f"GPG encryption failed: {result.stderr}")
        except FileNotFoundError:
            raise EncryptionError("GPG not installed. Install with: brew install gpg")
        except subprocess.TimeoutExpired:
            raise EncryptionError("GPG encryption timed out")

    def _decrypt_gpg(
        self, input_path: Path, output_path: Path, recipient: str | None
    ) -> None:
        """Decrypt using GPG."""
        cmd = ["gpg", "--decrypt", "--armor", "--batch"]

        if recipient:
            _validate_recipient(recipient, "GPG")
            cmd.extend(["--recipient", recipient])

        cmd.extend(["--output", str(output_path), "--", str(input_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise EncryptionError(f"GPG decryption failed: {result.stderr}")
        except FileNotFoundError:
            raise EncryptionError("GPG not installed")
        except subprocess.TimeoutExpired:
            raise EncryptionError("GPG decryption timed out")

        self._restrict_output(output_path)

    def _encrypt_age(
        self, input_path: Path, output_path: Path, recipient: str | None
    ) -> None:
        """Encrypt using AGE."""
        if not recipient:
            raise EncryptionError("AGE encryption requires a recipient")
        _validate_recipient(recipient, "AGE")

        cmd = [
            "age",
            "--encrypt",
            "--output",
            str(output_path),
            "-r",
            recipient,
            "--",
            str(input_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise EncryptionError(f"AGE encryption failed: {result.stderr}")
        except FileNotFoundError:
            raise EncryptionError("AGE not installed. Install with: brew install age")
        except subprocess.TimeoutExpired:
            raise EncryptionError("AGE encryption timed out")

    def _decrypt_age(
        self, input_path: Path, output_path: Path, recipient: str | None
    ) -> None:
        """Decrypt using AGE."""
        identity = os.environ.get("AGE_IDENTITY_FILE")

        cmd = ["age", "--decrypt", "--output", str(output_path)]

        if identity:
            cmd.extend(["-i", identity])

        cmd.extend(["--", str(input_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise EncryptionError(f"AGE decryption failed: {result.stderr}")
        except FileNotFoundError:
            raise EncryptionError("AGE not installed")
        except subprocess.TimeoutExpired:
            raise EncryptionError("AGE decryption timed out")

        self._restrict_output(output_path)

    @staticmethod
    def _restrict_output(output_path: Path) -> None:
        """Decrypted files are secrets: force owner-only permissions."""
        try:
            os.chmod(output_path, 0o600)
        except OSError:
            pass


def is_gpg_available() -> bool:
    """Check if GPG is installed."""
    try:
        subprocess.run(["gpg", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_age_available() -> bool:
    """Check if AGE is installed."""
    try:
        subprocess.run(["age", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def detect_available_encryption() -> list[Literal["gpg", "age"]]:
    """Detect available encryption methods."""
    methods: list[Literal["gpg", "age"]] = []
    if is_gpg_available():
        methods.append("gpg")
    if is_age_available():
        methods.append("age")
    return methods
