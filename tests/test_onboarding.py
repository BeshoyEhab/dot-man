"""Comprehensive tests for the onboarding module.

Covers sentinel detection, internal helpers, welcome banner,
init flow, branch creation, and the main run_onboarding orchestrator.
"""

from unittest.mock import MagicMock, patch

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Sentinel functions
# ──────────────────────────────────────────────────────────────────────────────


class TestIsFirstRun:
    """Tests for is_first_run()."""

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_no_directory(self, mock_sentinel, mock_dir):
        """Returns True when DOT_MAN_DIR doesn't exist."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = False
        assert is_first_run() is True

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_dir_no_sentinel(self, mock_sentinel, mock_dir):
        """Returns True when dir exists but sentinel is missing."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = True
        mock_sentinel.exists.return_value = False
        assert is_first_run() is True

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_not_first_run(self, mock_sentinel, mock_dir):
        """Returns False when sentinel exists."""
        from dot_man.cli.onboarding import is_first_run

        mock_dir.exists.return_value = True
        mock_sentinel.exists.return_value = True
        assert is_first_run() is False


class TestMarkOnboarded:
    """Tests for mark_onboarded()."""

    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.cli.onboarding.SENTINEL")
    def test_creates_sentinel(self, mock_sentinel, mock_dir):
        """Sentinel file is created with correct args."""
        from dot_man.cli.onboarding import mark_onboarded

        mock_dir.mkdir = MagicMock()
        mock_sentinel.touch = MagicMock()

        mark_onboarded()

        mock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_sentinel.touch.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestPause:
    """Tests for _pause()."""

    @patch("dot_man.cli.onboarding._console")
    @patch("builtins.input", return_value="")
    def test_default_label(self, mock_input, mock_console):
        """Prints default label and waits for Enter."""
        from dot_man.cli.onboarding import _pause

        _pause()
        assert mock_console.print.call_count == 2
        mock_input.assert_called_once_with()

    @patch("dot_man.cli.onboarding._console")
    @patch("builtins.input", side_effect=EOFError)
    def test_eoferror_handled(self, mock_input, mock_console):
        """EOFError is caught gracefully."""
        from dot_man.cli.onboarding import _pause

        _pause()
        assert mock_console.print.call_count == 2

    @patch("dot_man.cli.onboarding._console")
    @patch("builtins.input", return_value="")
    def test_custom_label(self, mock_input, mock_console):
        """Custom label text appears in output."""
        from dot_man.cli.onboarding import _pause

        _pause("Press Enter to continue")
        args_concat = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Press Enter to continue" in args_concat


class TestSectionRule:
    """Tests for _section_rule()."""

    @patch("dot_man.cli.onboarding._console")
    def test_prints_rule_with_title(self, mock_console):
        """Rule is rendered with the given title."""
        from dot_man.cli.onboarding import _section_rule

        _section_rule("My Title")
        assert mock_console.print.call_count == 3
        rule_arg = mock_console.print.call_args_list[1][0][0]
        assert "My Title" in str(rule_arg)


class TestCodeBlock:
    """Tests for _code_block()."""

    @patch("dot_man.cli.onboarding._console")
    def test_renders_code_in_panel(self, mock_console):
        """Code text is rendered inside a panel."""
        from dot_man.cli.onboarding import _code_block

        _code_block("echo hello")
        assert mock_console.print.call_count == 1
        panel_arg = mock_console.print.call_args[0][0]
        assert hasattr(panel_arg, "renderable")
        assert "echo hello" in str(panel_arg.renderable)


class TestAsciiPanel:
    """Tests for _ascii_panel()."""

    @patch("dot_man.cli.onboarding._console")
    def test_renders_title_and_art(self, mock_console):
        """Panel includes title and ASCII art content."""
        from dot_man.cli.onboarding import _ascii_panel

        _ascii_panel("Diagram", "some art")
        assert mock_console.print.call_count == 1
        panel_arg = mock_console.print.call_args[0][0]
        assert hasattr(panel_arg, "renderable")
        assert hasattr(panel_arg, "title")
        assert "Diagram" in str(panel_arg.title)
        assert "some art" in str(panel_arg.renderable)


# ──────────────────────────────────────────────────────────────────────────────
# Welcome banner
# ──────────────────────────────────────────────────────────────────────────────


class TestShowWelcome:
    """Tests for _show_welcome()."""

    @patch("dot_man.cli.onboarding._console")
    def test_prints_welcome_art_without_menu(self, mock_console):
        """Welcome art and title print; the Tutorial Menu panel is gone."""
        from dot_man.cli.onboarding import WELCOME_ART, _show_welcome

        _show_welcome()

        # Check the welcome panel contains expected text
        panel_texts = []
        for args, _ in mock_console.print.call_args_list:
            for arg in args:
                if hasattr(arg, "renderable"):
                    r = arg.renderable
                    txt = r.plain if hasattr(r, "plain") else str(r)
                    panel_texts.append(txt)

        combined = " ".join(panel_texts)
        assert "Welcome" in combined
        assert "Tutorial Menu" not in combined
        assert "Architecture" not in combined
        assert "Skip tutorial" not in combined

        # Art itself still renders
        art_calls = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "████" in art_calls or "Welcome" in combined
        assert WELCOME_ART.strip()[:10] in art_calls


# ──────────────────────────────────────────────────────────────────────────────
# _run_init_direct
# ──────────────────────────────────────────────────────────────────────────────


class TestRunInitDirect:
    """Tests for _run_init_direct()."""

    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.utils.is_git_installed", return_value=False)
    def test_returns_false_when_git_missing(self, mock_git, mock_console):
        """Returns False and prints error when git is not installed."""
        from dot_man.cli.onboarding import _run_init_direct

        result = _run_init_direct()
        assert result is False
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Git not found" in output

    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.ui.print_banner")
    @patch("dot_man.ui.console")
    @patch("dot_man.cli.init_cmd.run_setup_wizard")
    @patch("dot_man.config.DotManConfig")
    @patch("dot_man.config.GlobalConfig")
    @patch("dot_man.core.GitManager")
    @patch("dot_man.constants.BACKUPS_DIR")
    @patch("dot_man.constants.REPO_DIR")
    @patch("dot_man.cli.onboarding.DOT_MAN_DIR")
    @patch("dot_man.constants.FILE_PERMISSIONS", 0o700)
    @patch("dot_man.utils.is_git_installed", return_value=True)
    def test_full_init_success(
        self,
        mock_git_installed,
        mock_dotman_dir,
        mock_repo_dir,
        mock_backups_dir,
        mock_git_manager_cls,
        mock_global_config_cls,
        mock_dotman_config_cls,
        mock_wizard,
        mock_ui_console,
        mock_ui_banner,
        mock_console,
    ):
        """All init steps execute successfully and return True."""
        from dot_man.cli.onboarding import _run_init_direct

        git_instance = MagicMock()
        mock_git_manager_cls.return_value = git_instance

        global_instance = MagicMock()
        mock_global_config_cls.return_value = global_instance

        dotman_instance = MagicMock()
        mock_dotman_config_cls.return_value = dotman_instance

        result = _run_init_direct()

        assert result is True

        # Directory creation
        mock_dotman_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_dotman_dir.chmod.assert_called_once_with(0o700)
        mock_repo_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_backups_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Git init
        git_instance.init.assert_called_once()

        # Config creation
        global_instance.create_default.assert_called_once()
        dotman_instance.create_default.assert_called_once()

        # Initial commit
        git_instance.commit.assert_called_once_with("dot-man: Initial commit")

        # Wizard
        mock_wizard.assert_called_once_with(
            global_instance, dotman_instance, git_instance
        )

        # UI feedback
        mock_ui_banner.assert_called_once()

    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.utils.is_git_installed", return_value=True)
    @patch("dot_man.core.GitManager", side_effect=RuntimeError("test error"))
    def test_exception_handled_gracefully(self, mock_git, mock_installed, mock_console):
        """Exceptions are caught and printed, returns False."""
        from dot_man.cli.onboarding import _run_init_direct

        result = _run_init_direct()
        assert result is False
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Initialization failed" in output
        assert "test error" in output


# ──────────────────────────────────────────────────────────────────────────────
# _offer_first_branch
# ──────────────────────────────────────────────────────────────────────────────


class TestOfferFirstBranch:
    """Tests for _offer_first_branch()."""

    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.cli.onboarding.Confirm.ask", return_value=False)
    def test_user_declines(self, mock_ask, mock_console, mock_rule):
        """Prints hint about creating branches later when user declines."""
        from dot_man.cli.onboarding import _offer_first_branch

        _offer_first_branch()
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "create one later" in output

    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.cli.onboarding.Confirm.ask", return_value=True)
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="")
    def test_empty_name_skips(self, mock_prompt, mock_confirm, mock_console, mock_rule):
        """Empty branch name prints a warning and returns."""
        from dot_man.cli.onboarding import _offer_first_branch

        _offer_first_branch()
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Empty name" in output

    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.cli.onboarding.Confirm.ask", return_value=True)
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="work")
    @patch("dot_man.operations.get_operations")
    def test_creates_new_branch(
        self, mock_ops, mock_prompt, mock_confirm, mock_console, mock_rule
    ):
        """New branch is created and set as active when it doesn't exist."""
        from dot_man.cli.onboarding import _offer_first_branch

        git = MagicMock()
        git.branch_exists.return_value = False
        global_config = MagicMock()
        ops = MagicMock()
        ops.git = git
        ops.global_config = global_config
        mock_ops.return_value = ops

        _offer_first_branch()

        git.checkout.assert_called_once_with("work", create=True)
        global_config.current_branch = "work"
        global_config.save.assert_called_once()
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "created and set as active" in output

    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    @patch("dot_man.cli.onboarding.Confirm.ask", return_value=True)
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="work")
    @patch("dot_man.operations.get_operations", side_effect=Exception("branch error"))
    def test_exception_during_create(
        self, mock_ops, mock_prompt, mock_confirm, mock_console, mock_rule
    ):
        """Exception during branch creation is caught and displayed."""
        from dot_man.cli.onboarding import _offer_first_branch

        _offer_first_branch()
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Could not create branch" in output
        assert "branch error" in output


# ──────────────────────────────────────────────────────────────────────────────
# run_onboarding — main entry point
# ──────────────────────────────────────────────────────────────────────────────


def _printed_text(mock_console) -> str:
    """Extract printable text from console.print calls, unwrapping Panels."""
    parts = []
    for call in mock_console.print.call_args_list:
        for arg in call.args:
            parts.append(str(getattr(arg, "renderable", arg)))
    return " ".join(parts)


class TestRunOnboarding:
    """Tests for run_onboarding()."""

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._console")
    def test_straight_through_runs_wizard_and_branch(
        self, mock_console, mock_init, mock_branch, mock_onboarded
    ):
        """No menu: welcome goes straight to init, branch, sentinel."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=False)
    @patch("dot_man.cli.onboarding._console")
    def test_init_failure_skips_branch(
        self,
        mock_console,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """When init fails, branch creation is skipped."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_init.assert_called_once()
        mock_branch.assert_not_called()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch(
        "dot_man.cli.onboarding._run_init_direct",
        side_effect=KeyboardInterrupt,
    )
    @patch("dot_man.cli.onboarding._console")
    def test_keyboard_interrupt(
        self,
        mock_console,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """KeyboardInterrupt mid-flow is caught, prints message, exits."""
        from dot_man.cli.onboarding import run_onboarding

        with pytest.raises(SystemExit) as exc_info:
            run_onboarding()

        assert exc_info.value.code == 0
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "interrupted" in output.lower()
        mock_onboarded.assert_not_called()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._console")
    def test_finale_teaches_navigate_and_help_all(
        self, mock_console, mock_init, mock_branch, mock_onboarded
    ):
        """Finale panel teaches navigate/help-all, never switch."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        output = _printed_text(mock_console)
        assert "dot-man navigate" in output
        assert "help-all" in output
        assert "dot-man switch" not in output
