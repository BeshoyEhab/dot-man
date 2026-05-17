"""Tests for ui module."""


class TestUIConsole:
    """Test ui.console functionality."""

    def test_ui_console_exists(self):
        """Test ui.console exists."""
        from dot_man import ui

        assert hasattr(ui, "console")


class TestUIFunctions:
    """Test ui module functions."""

    def test_ui_success_exists(self):
        """Test ui.success function exists."""
        from dot_man import ui

        assert callable(ui.success)

    def test_ui_error_exists(self):
        """Test ui.error function exists."""
        from dot_man import ui

        assert callable(ui.error)

    def test_ui_warn_exists(self):
        """Test ui.warn function exists."""
        from dot_man import ui

        assert callable(ui.warn)

    def test_ui_info_exists(self):
        """Test ui.info function exists."""
        from dot_man import ui

        assert callable(ui.info)


class TestUIConfirm:
    """Test ui.Confirm function."""

    def test_ui_confirm_exists(self):
        """Test ui.Confirm class exists."""
        from dot_man import ui

        assert hasattr(ui, "Confirm")


class TestUIPrompt:
    """Test ui.Prompt function."""

    def test_ui_prompt_exists(self):
        """Test ui.Prompt class exists."""
        from dot_man import ui

        assert hasattr(ui, "Prompt")
