"""Custom exceptions for dot-man."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ErrorCategory(Enum):
    """Categorizes errors for user-friendly diagnostics."""
    SECRETS = "secrets"           # Secrets detected / redaction issues
    PERMISSION = "permission"     # File permission denied
    GIT_CONFLICT = "git_conflict" # Git merge/rebase conflict
    INTERRUPTED = "interrupted"   # KeyboardInterrupt / SIGTERM
    COMMAND = "command"           # Hook command failed / not found
    CONFIG = "config"             # Configuration errors
    DISK = "disk"                 # Disk space / I/O errors
    NETWORK = "network"           # Remote sync failures
    UNKNOWN = "unknown"           # Fallback


@dataclass
class ErrorDiagnostic:
    """Rich error diagnostic for user display."""
    category: ErrorCategory
    title: str
    details: str
    suggestion: str

    @classmethod
    def from_exception(cls, exc: Exception) -> "ErrorDiagnostic":
        """Factory to create diagnostics from common exceptions."""
        import builtins
        from .exceptions import (
            SecretsDetectedError, GitOperationError,
            ConfigurationError, DiskSpaceError
        )
        
        if isinstance(exc, KeyboardInterrupt):
            return cls(
                ErrorCategory.INTERRUPTED,
                "Operation interrupted",
                "User cancelled the operation",
                "Run the command again to retry"
            )
        # Check for built-in PermissionError first
        if isinstance(exc, builtins.PermissionError) or "permission denied" in str(exc).lower():
            return cls(
                ErrorCategory.PERMISSION,
                "Permission denied",
                str(exc),
                "Try running with sudo or check file permissions"
            )
        if isinstance(exc, SecretsDetectedError):
            return cls(
                ErrorCategory.SECRETS,
                "Secrets detected",
                str(exc),
                "Use 'dot-man audit' to review secrets, or add them to the ignore list"
            )
        if isinstance(exc, GitOperationError):
            msg = str(exc).lower()
            if "conflict" in msg:
                return cls(
                    ErrorCategory.GIT_CONFLICT,
                    "Git conflict detected",
                    str(exc),
                    "Resolve conflicts in ~/.config/dot-man/repo, then retry"
                )
            return cls(
                ErrorCategory.UNKNOWN,
                "Git operation failed",
                str(exc),
                "Check git status in ~/.config/dot-man/repo"
            )
        if isinstance(exc, ConfigurationError):
            return cls(
                ErrorCategory.CONFIG,
                "Configuration error",
                str(exc),
                "Run 'dot-man edit' to fix configuration issues"
            )
        if isinstance(exc, DiskSpaceError):
            return cls(
                ErrorCategory.DISK,
                "Disk space issue",
                str(exc),
                "Free up disk space and retry"
            )
        if "command not found" in str(exc).lower() or isinstance(exc, FileNotFoundError):
            return cls(
                ErrorCategory.COMMAND,
                "Command not found",
                str(exc),
                "Check that the required program is installed and in PATH"
            )
        
        # Fallback
        return cls(
            ErrorCategory.UNKNOWN,
            "Unexpected error",
            str(exc),
            "Check logs or run with --verbose for details"
        )

class DotManError(Exception):
    """Base exception for all dot-man errors."""

    exit_code = 1

    def __init__(self, message: str, exit_code: int | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


# ============================================================================
# Initialization Errors (1-10)
# ============================================================================


class AlreadyInitializedError(DotManError):
    """Repository already initialized."""

    exit_code = 1


class NotInitializedError(DotManError):
    """Repository not initialized."""

    exit_code = 1


class GitNotFoundError(DotManError):
    """Git is not installed or not in PATH."""

    exit_code = 2


class PermissionError(DotManError):
    """Permission denied for file/directory operation."""

    exit_code = 3


class DiskSpaceError(DotManError):
    """Insufficient disk space."""

    exit_code = 4


# ============================================================================
# Git Errors (5-10)
# ============================================================================


class GitOperationError(DotManError):
    """Git operation failed."""

    exit_code = 5


class BranchNotFoundError(DotManError):
    """Branch does not exist."""

    exit_code = 1


class BranchNotMergedError(DotManError):
    """Branch is not fully merged."""

    exit_code = 1


# ============================================================================
# Configuration Errors (7, 30-35)
# ============================================================================


class ConfigurationError(DotManError):
    """Configuration file is invalid or missing."""

    exit_code = 7


class ConfigValidationError(DotManError):
    """Configuration validation failed."""

    exit_code = 30


class EditorNotFoundError(DotManError):
    """Editor not found."""

    exit_code = 31


# ============================================================================
# Security Errors (10, 50-55)
# ============================================================================


class SecretsDetectedError(DotManError):
    """Secrets detected in strict mode."""

    exit_code = 10


class AuditSecretFoundError(DotManError):
    """Secrets found during audit in strict mode."""

    exit_code = 50


# ============================================================================
# File Operation Errors (6, 40-45)
# ============================================================================


class FileOperationError(DotManError):
    """File operation failed."""

    exit_code = 6


class DeploymentError(DotManError):
    """Deployment failed."""

    exit_code = 40


class BackupError(DotManError):
    """Backup operation failed."""

    exit_code = 41
