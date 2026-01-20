from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from questionary import ValidationError

from dot_man.config import DotManConfig, GlobalConfig, Section
from dot_man.interactive import (
    PathValidator,
    UrlValidator,
    run_global_wizard,
    run_section_wizard,
)


class TestValidators:
    """Test custom validators."""

    def test_path_validator_valid(self):
        """Test that valid paths (or empty) are accepted."""
        validator = PathValidator()
        
        # Empty is allowed (skipped)
        doc_mock = MagicMock()
        doc_mock.text = ""
        validator.validate(doc_mock)

        # Absolute or relative paths technically passed by our simple validator
        doc_mock.text = "/tmp/foo"
        validator.validate(doc_mock)

    def test_url_validator_valid(self):
        """Test valid URLs."""
        validator = UrlValidator()
        valid_urls = [
            "https://github.com/user/repo",
            "http://example.com",
            "git@github.com:user/repo.git",
            "ssh://user@host/repo",
            "", # Empty often allowed as skip
        ]
        for url in valid_urls:
            doc_mock = MagicMock()
            doc_mock.text = url
            validator.validate(doc_mock)

    def test_url_validator_invalid(self):
        """Test invalid URLs raise ValidationError."""
        validator = UrlValidator()
        invalid_urls = [
            "ftp://example.com",
            "just_a_string",
            "/local/path",
        ]
        for url in invalid_urls:
            doc_mock = MagicMock()
            doc_mock.text = url
            with pytest.raises(ValidationError):
                validator.validate(doc_mock)


class TestWizards:
    """Test interactive wizards using mocks."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=DotManConfig)
        section = MagicMock(spec=Section)
        section.name = "test_section"
        section.paths = [Path("/tmp/foo")]
        section.repo_base = "foo_base"
        section.update_strategy = "replace"
        section.secrets_filter = True
        section.inherits = []
        section.pre_deploy = None
        section.post_deploy = None
        # include/exclude are lists
        section.include = []
        section.exclude = []
        
        config.get_section.return_value = section
        config.add_section = MagicMock()
        config.save = MagicMock()
        return config

    @pytest.fixture
    def mock_global_config(self):
        config = MagicMock(spec=GlobalConfig)
        config.editor = "vim"
        config.remote_url = "https://github.com/user/dots"
        config.secrets_filter_enabled = True
        
        # Internal data mock for secrets filter update logic
        config._data = {"defaults": {}}
        
        config.get_defaults.return_value = {"secrets_filter": True}
        config.save = MagicMock()
        return config

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")  # Mock UI calls
    def test_run_section_wizard_save(self, mock_console, mock_questionary, mock_config):
        """Test editing a section and saving."""
        # 1. Select "paths" to edit
        # 2. Select "save"
        mock_questionary.select.return_value.ask.side_effect = ["paths", "save"]
        
        # When editing paths, enter new path
        mock_questionary.text.return_value.ask.return_value = "/tmp/bar"

        run_section_wizard(mock_config, "test_section")

        # Verify config was updated and saved
        # section.paths should have been updated mock-side? 
        # Actually in our code: section.paths = ...
        # Since 'section' is a mock, we can check if it was modified or if add_section was called with new values.
        
        # Ideally, we check add_section call
        mock_config.add_section.assert_called_once()
        call_args = mock_config.add_section.call_args[1]
        assert call_args["name"] == "test_section"
        assert call_args["paths"] == ["/tmp/bar"] # It was updated to string
        
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_run_section_wizard_cancel(self, mock_console, mock_questionary, mock_config):
        """Test canceling wizard."""
        mock_questionary.select.return_value.ask.return_value = "cancel"
        
        run_section_wizard(mock_config, "test_section")
        
        mock_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_run_global_wizard_edit_editor(self, mock_console, mock_questionary, mock_global_config):
        """Test editing global editor."""
        # 1. Select "editor"
        # 2. Select "save"
        mock_questionary.select.return_value.ask.side_effect = ["editor", "save"]
        
        # Enter new editor
        mock_questionary.text.return_value.ask.return_value = "nano"
        
        run_global_wizard(mock_global_config)
        
        assert mock_global_config.editor == "nano"
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_run_global_wizard_toggle_secrets(self, mock_console, mock_questionary, mock_global_config):
        """Test toggling global secrets filter."""
        # 1. Select "secrets_filter" to toggle
        # 2. Select "save"
        mock_questionary.select.return_value.ask.side_effect = ["secrets_filter", "save"]
        
        # Initial state is True (from fixture)
        # So after toggle it should be False
        
        run_global_wizard(mock_global_config)
        
        # Check internal data update
        assert mock_global_config._data["defaults"]["secrets_filter"] is False
        mock_global_config.save.assert_called_once()
