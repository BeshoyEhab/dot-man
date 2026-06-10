"""Comprehensive tests for interactive module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from questionary import Choice, ValidationError

from dot_man.config import DotManConfig, GlobalConfig, Section
from dot_man.interactive import (
    PathValidator,
    UrlValidator,
    edit_template,
    fmt_choice,
    run_global_wizard,
    run_section_wizard,
    run_templates_wizard,
)


class TestFmtChoice:
    """Test fmt_choice utility."""

    def test_fmt_choice_returns_choice(self):
        """Test fmt_choice returns a questionary.Choice with correct attributes."""
        choice = fmt_choice("my text", "edit")
        assert isinstance(choice, Choice)
        assert choice.title == "my text"
        assert choice.value == "my text"

    def test_fmt_choice_default_action(self):
        """Test fmt_choice with default action parameter."""
        choice = fmt_choice("hello")
        assert isinstance(choice, Choice)
        assert choice.value == "hello"


class TestValidators:
    """Test custom validators."""

    def test_path_validator_valid(self):
        """Test that valid paths (or empty) are accepted."""
        validator = PathValidator()

        doc_mock = MagicMock()
        doc_mock.text = ""
        validator.validate(doc_mock)

        doc_mock.text = "/tmp/foo"
        validator.validate(doc_mock)

        doc_mock.text = "relative/path"
        validator.validate(doc_mock)

        doc_mock.text = "~/some/path"
        validator.validate(doc_mock)

    def test_url_validator_valid(self):
        """Test valid URLs."""
        validator = UrlValidator()
        valid_urls = [
            "https://github.com/user/repo",
            "http://example.com",
            "git@github.com:user/repo.git",
            "ssh://user@host/repo",
            "",
        ]
        for url in valid_urls:
            doc_mock = MagicMock()
            doc_mock.text = url
            try:
                validator.validate(doc_mock)
            except Exception as e:
                pytest.fail(f"Valid URL '{url}' raised exception: {e}")

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config():
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
    section.include = []
    section.exclude = []

    config.get_section.return_value = section
    config.add_section = MagicMock()
    config.save = MagicMock()
    return config


@pytest.fixture
def mock_global_config():
    config = MagicMock(spec=GlobalConfig)
    config.editor = "vim"
    config.remote_url = "https://github.com/user/dots"
    config.secrets_filter_enabled = True
    config._data = {"defaults": {}}
    config.get_defaults.return_value = {"secrets_filter": True}
    config.save = MagicMock()
    return config


@pytest.fixture
def mock_templates_config():
    """Config with one existing template."""
    config = MagicMock(spec=DotManConfig)
    config._data = {
        "templates": {
            "base": {
                "update_strategy": "replace",
                "pre_deploy": "echo hello",
            },
        }
    }
    config.get_local_templates.return_value = ["base"]
    config.save = MagicMock()
    return config


# ---------------------------------------------------------------------------
# run_section_wizard
# ---------------------------------------------------------------------------


class TestRunSectionWizard:
    """Test section wizard."""

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_save(self, mock_console, mock_questionary, mock_config):
        """Test editing paths and saving."""
        mock_questionary.select.return_value.ask.side_effect = ["paths", "save"]
        mock_questionary.text.return_value.ask.return_value = "/tmp/bar"

        run_section_wizard(mock_config, "test_section")

        mock_config.add_section.assert_called_once()
        call_args = mock_config.add_section.call_args[1]
        assert call_args["name"] == "test_section"
        assert call_args["paths"] == ["/tmp/bar"]
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_cancel(self, mock_console, mock_questionary, mock_config):
        """Test canceling wizard."""
        mock_questionary.select.return_value.ask.return_value = "cancel"
        run_section_wizard(mock_config, "test_section")
        mock_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_none_return(self, mock_console, mock_questionary, mock_config):
        """Test Ctrl+C (None) from select."""
        mock_questionary.select.return_value.ask.return_value = None
        run_section_wizard(mock_config, "test_section")
        mock_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_repo_base(self, mock_console, mock_questionary, mock_config):
        """Test editing repo_base."""
        mock_questionary.select.return_value.ask.side_effect = ["repo_base", "save"]
        mock_questionary.text.return_value.ask.return_value = "new_base"

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.repo_base == "new_base"
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_update_strategy(self, mock_console, mock_questionary, mock_config):
        """Test editing update_strategy."""
        mock_questionary.select.return_value.ask.side_effect = [
            "update_strategy",
            "ignore",
            "save",
        ]

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.update_strategy == "ignore"
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_toggle_secrets_filter(self, mock_console, mock_questionary, mock_config):
        """Test toggling secrets_filter."""
        assert mock_config.get_section.return_value.secrets_filter is True

        mock_questionary.select.return_value.ask.side_effect = [
            "secrets_filter",
            "save",
        ]

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.secrets_filter is False
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_inherits(self, mock_console, mock_questionary, mock_config):
        """Test editing inherits."""
        mock_questionary.select.return_value.ask.side_effect = ["inherits", "save"]
        mock_questionary.text.return_value.ask.return_value = "common, dev"

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.inherits == ["common", "dev"]
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_inherits_none_skips(
        self, mock_console, mock_questionary, mock_config
    ):
        """Test editing inherits with None return skips update."""
        mock_questionary.select.return_value.ask.side_effect = ["inherits", "save"]
        mock_questionary.text.return_value.ask.return_value = None

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.inherits == []
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_pre_deploy(self, mock_console, mock_questionary, mock_config):
        """Test editing pre_deploy hook."""
        mock_questionary.select.return_value.ask.side_effect = ["pre_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = "echo before"

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.pre_deploy == "echo before"
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_post_deploy(self, mock_console, mock_questionary, mock_config):
        """Test editing post_deploy hook."""
        mock_questionary.select.return_value.ask.side_effect = ["post_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = "echo after"

        run_section_wizard(mock_config, "test_section")

        assert mock_config.get_section.return_value.post_deploy == "echo after"
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    @patch("dot_man.interactive.Path.home")
    def test_save_with_path_fixup(
        self, mock_home, mock_console, mock_questionary, mock_config
    ):
        """Test path fixup: absolute paths under home become relative."""
        mock_home.return_value = Path("/home/user")
        section = mock_config.get_section.return_value
        section.paths = [Path("/home/user/.config/foo")]

        mock_questionary.select.return_value.ask.side_effect = ["save"]

        run_section_wizard(mock_config, "test_section")

        mock_config.add_section.assert_called_once()
        call_args = mock_config.add_section.call_args[1]
        assert call_args["paths"] == [".config/foo"]

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    @patch("dot_man.interactive.error")
    @patch("builtins.input")
    def test_save_exception(
        self, mock_input, mock_error, mock_console, mock_questionary, mock_config
    ):
        """Test exception during save is handled gracefully."""
        mock_config.add_section.side_effect = Exception("disk full")
        mock_questionary.select.return_value.ask.side_effect = ["save", "cancel"]

        run_section_wizard(mock_config, "test_section")

        mock_config.add_section.assert_called_once()
        mock_config.save.assert_not_called()
        mock_input.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_paths_empty(self, mock_console, mock_questionary, mock_config):
        """Test submitting empty path input leaves paths unchanged."""
        mock_questionary.select.return_value.ask.side_effect = ["paths", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        run_section_wizard(mock_config, "test_section")

        section = mock_config.get_section.return_value
        assert list(section.paths) == [Path("/tmp/foo")]
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_pre_deploy_empty_sets_none(
        self, mock_console, mock_questionary, mock_config
    ):
        """Test empty pre_deploy input sets hook to None."""
        section = mock_config.get_section.return_value
        section.pre_deploy = "existing hook"

        mock_questionary.select.return_value.ask.side_effect = ["pre_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        run_section_wizard(mock_config, "test_section")

        assert section.pre_deploy is None
        mock_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_post_deploy_empty_sets_none(
        self, mock_console, mock_questionary, mock_config
    ):
        """Test empty post_deploy input sets hook to None."""
        section = mock_config.get_section.return_value
        section.post_deploy = "existing hook"

        mock_questionary.select.return_value.ask.side_effect = ["post_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        run_section_wizard(mock_config, "test_section")

        assert section.post_deploy is None
        mock_config.save.assert_called_once()


# ---------------------------------------------------------------------------
# run_global_wizard
# ---------------------------------------------------------------------------


class TestRunGlobalWizard:
    """Test global config wizard."""

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_editor(self, mock_console, mock_questionary, mock_global_config):
        """Test editing global editor."""
        mock_questionary.select.return_value.ask.side_effect = ["editor", "save"]
        mock_questionary.text.return_value.ask.return_value = "nano"

        run_global_wizard(mock_global_config)

        assert mock_global_config.editor == "nano"
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_toggle_secrets(self, mock_console, mock_questionary, mock_global_config):
        """Test toggling global secrets filter."""
        mock_questionary.select.return_value.ask.side_effect = [
            "secrets_filter",
            "save",
        ]

        run_global_wizard(mock_global_config)

        assert mock_global_config._data["defaults"]["secrets_filter"] is False
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_cancel(self, mock_console, mock_questionary, mock_global_config):
        """Test cancel."""
        mock_questionary.select.return_value.ask.return_value = "cancel"
        run_global_wizard(mock_global_config)
        mock_global_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_none_return(self, mock_console, mock_questionary, mock_global_config):
        """Test Ctrl+C (None) from select."""
        mock_questionary.select.return_value.ask.return_value = None
        run_global_wizard(mock_global_config)
        mock_global_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_remote_url(self, mock_console, mock_questionary, mock_global_config):
        """Test editing remote_url."""
        mock_questionary.select.return_value.ask.side_effect = ["remote_url", "save"]
        mock_questionary.text.return_value.ask.return_value = "https://new.url/dots"

        run_global_wizard(mock_global_config)

        assert mock_global_config.remote_url == "https://new.url/dots"
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_remote_url_empty(
        self, mock_console, mock_questionary, mock_global_config
    ):
        """Test clearing remote_url (empty string)."""
        mock_questionary.select.return_value.ask.side_effect = ["remote_url", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        run_global_wizard(mock_global_config)

        assert mock_global_config.remote_url == ""
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_editor_empty(
        self, mock_console, mock_questionary, mock_global_config
    ):
        """Test clearing editor (empty input sets to None)."""
        mock_questionary.select.return_value.ask.side_effect = ["editor", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        run_global_wizard(mock_global_config)

        assert mock_global_config.editor is None
        mock_global_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_toggle_secrets_no_defaults_key(self, mock_console, mock_questionary):
        """Test toggling secrets filter when _data lacks 'defaults' key."""
        config = MagicMock(spec=GlobalConfig)
        config.editor = "vim"
        config.remote_url = ""
        config.secrets_filter_enabled = True
        config._data = {}
        config.save = MagicMock()

        mock_questionary.select.return_value.ask.side_effect = [
            "secrets_filter",
            "save",
        ]

        run_global_wizard(config)

        assert config._data["defaults"]["secrets_filter"] is False
        config.save.assert_called_once()


# ---------------------------------------------------------------------------
# run_templates_wizard
# ---------------------------------------------------------------------------


class TestRunTemplatesWizard:
    """Test templates wizard."""

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_back(self, mock_console, mock_questionary, mock_templates_config):
        """Test selecting 'Back' returns immediately."""
        mock_questionary.select.return_value.ask.return_value = "back"
        run_templates_wizard(mock_templates_config)
        mock_templates_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_none_return(self, mock_console, mock_questionary, mock_templates_config):
        """Test Ctrl+C (None) from select."""
        mock_questionary.select.return_value.ask.return_value = None
        run_templates_wizard(mock_templates_config)
        mock_templates_config.save.assert_not_called()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_add_new_edit_and_save(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test adding a new template, editing it, and saving."""
        mock_questionary.select.return_value.ask.side_effect = [
            "add_new",
            "save",
            "back",
        ]
        mock_questionary.text.return_value.ask.return_value = "new_template"

        run_templates_wizard(mock_templates_config)

        assert "new_template" in mock_templates_config._data["templates"]
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_existing_template(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test selecting an existing template to edit, then saving."""
        mock_questionary.select.return_value.ask.side_effect = [
            "base",
            "save",
            "back",
        ]

        run_templates_wizard(mock_templates_config)

        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_add_duplicate_template(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test trying to add a template with an existing name."""
        mock_questionary.select.return_value.ask.side_effect = ["add_new", "back"]
        mock_questionary.text.return_value.ask.return_value = "base"

        run_templates_wizard(mock_templates_config)

        assert "base" in mock_templates_config._data["templates"]
        assert len(mock_templates_config._data["templates"]) == 1

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_add_new_with_none_name(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test adding a template but giving no name."""
        mock_questionary.select.return_value.ask.side_effect = ["add_new", "back"]
        mock_questionary.text.return_value.ask.return_value = None

        run_templates_wizard(mock_templates_config)

        assert len(mock_templates_config._data["templates"]) == 1

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_no_templates_empty_state(self, mock_console, mock_questionary):
        """Test wizard when no templates exist."""
        config = MagicMock(spec=DotManConfig)
        config._data = {"templates": {}}
        config.get_local_templates.return_value = []
        config.save = MagicMock()

        mock_questionary.select.return_value.ask.side_effect = [
            "add_new",
            "save",
            "back",
        ]
        mock_questionary.text.return_value.ask.return_value = "my_template"

        run_templates_wizard(config)

        assert "my_template" in config._data["templates"]
        config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_display_template_with_post_deploy(self, mock_console, mock_questionary):
        """Test wizard with a template that has a post_deploy hook."""
        config = MagicMock(spec=DotManConfig)
        config._data = {
            "templates": {
                "base": {
                    "update_strategy": "replace",
                    "post_deploy": "echo after",
                },
            }
        }
        config.get_local_templates.return_value = ["base"]
        config.save = MagicMock()

        mock_questionary.select.return_value.ask.side_effect = [
            "base",
            "save",
            "back",
        ]

        run_templates_wizard(config)

        config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_add_new_templates_key_missing(self, mock_console, mock_questionary):
        """Test adding template when _data lacks 'templates' key."""
        config = MagicMock(spec=DotManConfig)
        config._data = {}
        config.get_local_templates.return_value = []
        config.save = MagicMock()

        mock_questionary.select.return_value.ask.side_effect = [
            "add_new",
            "save",
            "back",
        ]
        mock_questionary.text.return_value.ask.return_value = "my_template"

        run_templates_wizard(config)

        assert "templates" in config._data
        assert "my_template" in config._data["templates"]
        config.save.assert_called_once()


# ---------------------------------------------------------------------------
# edit_template
# ---------------------------------------------------------------------------


class TestEditTemplate:
    """Test edit_template function."""

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_save(self, mock_console, mock_questionary, mock_templates_config):
        """Test selecting Save & Return."""
        mock_questionary.select.return_value.ask.return_value = "save"

        edit_template(mock_templates_config, "base")

        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_none_return(self, mock_console, mock_questionary, mock_templates_config):
        """Test Ctrl+C (None) from select — also saves & returns."""
        mock_questionary.select.return_value.ask.return_value = None

        edit_template(mock_templates_config, "base")

        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_pre_deploy(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test editing pre_deploy hook."""
        mock_questionary.select.return_value.ask.side_effect = ["pre_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = "new pre hook"

        edit_template(mock_templates_config, "base")

        assert (
            mock_templates_config._data["templates"]["base"]["pre_deploy"]
            == "new pre hook"
        )
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_post_deploy(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test editing post_deploy hook."""
        mock_questionary.select.return_value.ask.side_effect = ["post_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = "new post hook"

        edit_template(mock_templates_config, "base")

        assert (
            mock_templates_config._data["templates"]["base"]["post_deploy"]
            == "new post hook"
        )
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_edit_update_strategy(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test editing update_strategy."""
        mock_questionary.select.return_value.ask.side_effect = [
            "update_strategy",
            "ignore",
            "save",
        ]

        edit_template(mock_templates_config, "base")

        assert (
            mock_templates_config._data["templates"]["base"]["update_strategy"]
            == "ignore"
        )
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_delete(self, mock_console, mock_questionary, mock_templates_config):
        """Test deleting a template."""
        mock_questionary.select.return_value.ask.return_value = "delete"
        mock_questionary.confirm.return_value.ask.return_value = True

        edit_template(mock_templates_config, "base")

        assert "base" not in mock_templates_config._data["templates"]
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_delete_cancelled(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test cancelling template deletion."""
        mock_questionary.select.return_value.ask.side_effect = ["delete", "save"]
        mock_questionary.confirm.return_value.ask.return_value = False

        edit_template(mock_templates_config, "base")

        assert "base" in mock_templates_config._data["templates"]
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_clear_pre_deploy(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test clearing pre_deploy hook (empty input deletes key)."""
        mock_questionary.select.return_value.ask.side_effect = ["pre_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        edit_template(mock_templates_config, "base")

        assert "pre_deploy" not in mock_templates_config._data["templates"]["base"]
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_clear_post_deploy(
        self, mock_console, mock_questionary, mock_templates_config
    ):
        """Test clearing post_deploy hook when key absent (no-op)."""
        mock_questionary.select.return_value.ask.side_effect = ["post_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        edit_template(mock_templates_config, "base")

        assert "post_deploy" not in mock_templates_config._data["templates"]["base"]
        mock_templates_config.save.assert_called_once()

    @patch("dot_man.interactive.questionary")
    @patch("dot_man.interactive.console")
    def test_clear_existing_post_deploy(self, mock_console, mock_questionary):
        """Test clearing post_deploy hook when key is present."""
        config = MagicMock(spec=DotManConfig)
        config._data = {
            "templates": {
                "base": {
                    "update_strategy": "replace",
                    "post_deploy": "echo after",
                },
            }
        }
        config.save = MagicMock()

        mock_questionary.select.return_value.ask.side_effect = ["post_deploy", "save"]
        mock_questionary.text.return_value.ask.return_value = ""

        edit_template(config, "base")

        assert "post_deploy" not in config._data["templates"]["base"]
        config.save.assert_called_once()
