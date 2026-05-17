"""Tests for exceptions module."""


class TestDotManError:
    """Test base DotManError exception."""

    def test_dotman_error_base(self):
        """Test DotManError can be instantiated."""
        from dot_man.exceptions import DotManError

        error = DotManError("Test error")
        assert str(error) == "Test error"

    def test_dotman_error_inheritance(self):
        """Test DotManError is Exception subclass."""
        from dot_man.exceptions import DotManError

        error = DotManError("Test")
        assert isinstance(error, Exception)


class TestNotInitializedError:
    """Test NotInitializedError exception."""

    def test_not_initialized_error(self):
        """Test NotInitializedError can be raised."""
        from dot_man.exceptions import DotManError, NotInitializedError

        error = NotInitializedError("Not initialized")
        assert isinstance(error, DotManError)
        assert "Not initialized" in str(error)


class TestBranchNotFoundError:
    """Test BranchNotFoundError exception."""

    def test_branch_not_found_error(self):
        """Test BranchNotFoundError can be raised."""
        from dot_man.exceptions import BranchNotFoundError, DotManError

        error = BranchNotFoundError("main")
        assert isinstance(error, DotManError)
        assert "main" in str(error)


class TestGitOperationError:
    """Test GitOperationError exception."""

    def test_git_operation_error(self):
        """Test GitOperationError can be raised."""
        from dot_man.exceptions import DotManError, GitOperationError

        error = GitOperationError("Git failed")
        assert isinstance(error, DotManError)
        assert "Git failed" in str(error)


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_configuration_error(self):
        """Test ConfigurationError can be raised."""
        from dot_man.exceptions import ConfigurationError, DotManError

        error = ConfigurationError("Invalid config")
        assert isinstance(error, DotManError)
        assert "Invalid config" in str(error)


class TestConfigValidationError:
    """Test ConfigValidationError exception."""

    def test_config_validation_error(self):
        """Test ConfigValidationError can be raised."""
        from dot_man.exceptions import ConfigValidationError, DotManError

        error = ConfigValidationError("Validation failed")
        assert isinstance(error, DotManError)
        assert "Validation" in str(error)


class TestBackupError:
    """Test BackupError exception."""

    def test_backup_error(self):
        """Test BackupError can be raised."""
        from dot_man.exceptions import BackupError, DotManError

        error = BackupError("Backup failed")
        assert isinstance(error, DotManError)
        assert "Backup" in str(error)


class TestErrorDiagnostic:
    """Test ErrorDiagnostic dataclass."""

    def test_error_diagnostic(self):
        """Test ErrorDiagnostic can be created."""
        from dot_man.exceptions import ErrorCategory, ErrorDiagnostic

        diag = ErrorDiagnostic(
            category=ErrorCategory.CONFIG,
            title="Test Error",
            details="Test details",
            suggestion="Test suggestion",
        )
        assert diag.category == ErrorCategory.CONFIG
        assert diag.title == "Test Error"


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_error_category_values(self):
        """Test ErrorCategory has expected values."""
        from dot_man.exceptions import ErrorCategory

        assert ErrorCategory.SECRETS.value == "secrets"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.GIT_CONFLICT.value == "git_conflict"
        assert ErrorCategory.CONFIG.value == "config"
        assert ErrorCategory.DISK.value == "disk"
        assert ErrorCategory.NETWORK.value == "network"
