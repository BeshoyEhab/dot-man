"""Custom exceptions for dot-man."""


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
