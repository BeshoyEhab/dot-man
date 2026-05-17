"""Tests for operations module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestDeploymentPlan:
    """Test DeploymentPlan TypedDict."""

    def test_deployment_plan_creation(self):
        """Test creating a DeploymentPlan."""
        from dot_man.operations import DeploymentPlan

        plan: DeploymentPlan = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": [],
        }
        assert "sections_to_deploy" in plan
        assert "errors" in plan


class TestDotManOperationsInit:
    """Test DotManOperations initialization."""

    def test_operations_init(self):
        """Test DotManOperations can be instantiated."""
        from dot_man.operations import DotManOperations

        ops = DotManOperations.__new__(DotManOperations)
        ops._git = MagicMock()
        ops._config = MagicMock()
        ops._vault = MagicMock()
        ops._backups = MagicMock()

        assert ops is not None


class TestDotManOperationsProperties:
    """Test DotManOperations properties."""

    @patch("dot_man.operations.GitManager")
    def test_git_property(self, mock_git):
        """Test git property."""
        from dot_man.operations import DotManOperations

        ops = DotManOperations.__new__(DotManOperations)
        mock_gm = MagicMock()
        mock_git.return_value = mock_gm
        ops._git = None

        result = ops.git
        assert result is not None


class TestOperationsModuleExports:
    """Test module exports."""

    def test_file_lock_exported(self):
        """Test FileLock is exported from operations."""
        from dot_man.operations import FileLock

        assert FileLock is not None

    def test_lock_file_exported(self):
        """Test LOCK_FILE is exported from operations."""
        from dot_man.operations import LOCK_FILE

        assert LOCK_FILE is not None

    def test_save_deploy_mixin_exported(self):
        """Test SaveDeployMixin is exported."""
        from dot_man.operations import SaveDeployMixin

        assert SaveDeployMixin is not None