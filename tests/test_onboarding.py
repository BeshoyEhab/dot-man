"""Tests for onboarding module."""

from unittest.mock import MagicMock, patch


class TestOnboardingSentinel:
    """Test onboarding sentinel functions."""

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_is_first_run_no_dir(self, mock_sentinel, mock_dir):
        """Test first run detection when dot-man dir doesn't exist."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = False
        result = is_first_run()
        assert result is True

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_is_first_run_dir_exists_no_sentinel(self, mock_sentinel, mock_dir):
        """Test first run when dir exists but no sentinel."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = True
        mock_sentinel.exists.return_value = False
        result = is_first_run()
        assert result is True

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_is_first_run_not_first(self, mock_sentinel, mock_dir):
        """Test not first run when sentinel exists."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = True
        mock_sentinel.exists.return_value = True
        result = is_first_run()
        assert result is False


class TestOnboardingMarkOnboarded:
    """Test mark_onboarded function."""

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_mark_onboarded_creates_sentinel(self, mock_sentinel, mock_dir):
        """Test that mark_onboarded creates sentinel file."""
        from dot_man.cli.onboarding import mark_onboarded

        mock_dir.mkdir = MagicMock()
        mock_sentinel.touch = MagicMock()

        mark_onboarded()

        mock_dir.mkdir.assert_called_once()
        mock_sentinel.touch.assert_called_once()


class TestOnboardingInternal:
    """Test onboarding internal functions."""

    @patch("dot_man.cli.onboarding._console")
    def test_section_rule(self, mock_console):
        """Test _section_rule prints a rule."""
        from dot_man.cli.onboarding import _section_rule

        _section_rule("Test Section")

        mock_console.print.assert_called()

    @patch("dot_man.cli.onboarding._console")
    def test_code_block(self, mock_console):
        """Test _code_block renders a code block."""
        from dot_man.cli.onboarding import _code_block

        _code_block("echo test")

        assert mock_console.print.called

    @patch("dot_man.cli.onboarding._console")
    @patch("builtins.input", return_value="")
    def test_pause(self, mock_input, mock_console):
        """Test _pause waits for input."""
        from dot_man.cli.onboarding import _pause

        _pause()

        mock_console.print.assert_called()


class TestOnboardingTutorial:
    """Test onboarding tutorial content."""

    @patch("dot_man.cli.onboarding._pause")
    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._code_block")
    @patch("dot_man.cli.onboarding._console")
    def test_section_architecture(
        self, mock_console, mock_code, mock_section, mock_pause
    ):
        """Test architecture section displays."""
        from dot_man.cli.onboarding import _section_architecture

        _section_architecture()

        assert mock_section.called or mock_console.print.called

    @patch("dot_man.cli.onboarding._pause")
    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._code_block")
    @patch("dot_man.cli.onboarding._console")
    def test_section_manual(self, mock_console, mock_code, mock_section, mock_pause):
        """Test manual section displays."""
        from dot_man.cli.onboarding import _section_manual

        _section_manual()

        assert mock_section.called or mock_console.print.called
