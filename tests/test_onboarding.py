"""Comprehensive tests for the onboarding module.

Covers sentinel detection, internal helpers, tutorial sections,
init flow, branch creation, and the main run_onboarding orchestrator.
"""

from unittest.mock import MagicMock, patch

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


class TestConfirmNext:
    """Tests for _confirm_next()."""

    @patch("dot_man.cli.onboarding.Confirm.ask")
    @patch("dot_man.cli.onboarding._console")
    def test_default_prompt(self, mock_console, mock_ask):
        """Uses default prompt text when none given."""
        from dot_man.cli.onboarding import _confirm_next

        mock_ask.return_value = True
        result = _confirm_next()
        assert result is True
        prompt_text = mock_ask.call_args[0][0] if mock_ask.call_args[0] else ""
        assert "Ready for the next section" in str(prompt_text)

    @patch("dot_man.cli.onboarding.Confirm.ask")
    @patch("dot_man.cli.onboarding._console")
    def test_custom_prompt(self, mock_console, mock_ask):
        """Custom prompt text is forwarded to Confirm.ask."""
        from dot_man.cli.onboarding import _confirm_next

        mock_ask.return_value = False
        result = _confirm_next("Continue?")
        assert result is False
        assert "Continue?" in str(mock_ask.call_args[0][0])


# ──────────────────────────────────────────────────────────────────────────────
# Welcome and tutorial sections
# ──────────────────────────────────────────────────────────────────────────────


class TestShowWelcome:
    """Tests for _show_welcome()."""

    @patch("dot_man.cli.onboarding._console")
    def test_prints_welcome_art_and_menu(self, mock_console):
        """Welcome art, title, and menu options are printed."""
        from dot_man.cli.onboarding import _show_welcome

        _show_welcome()

        # Should have multiple print calls: art, welcome panel, menu
        assert mock_console.print.call_count >= 4

        # Check the welcome panel and menu panel contain expected text
        panel_texts = []
        for args, _ in mock_console.print.call_args_list:
            for arg in args:
                if hasattr(arg, "renderable"):
                    r = arg.renderable
                    txt = r.plain if hasattr(r, "plain") else str(r)
                    panel_texts.append(txt)

        combined = " ".join(panel_texts)
        assert "Welcome" in combined
        assert "Architecture" in combined
        assert "Manual" in combined
        assert "Skip tutorial" in combined


class TestSectionArchitecture:
    """Tests for _section_architecture()."""

    @patch("dot_man.cli.onboarding._pause")
    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    def test_displays_all_topics(self, mock_console, mock_rule, mock_pause):
        """All architecture topics are displayed in order."""
        from dot_man.cli.onboarding import _section_architecture

        _section_architecture()
        mock_rule.assert_called_once()
        assert "Architecture" in str(mock_rule.call_args[0][0])

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "What is dot-man" in output
        assert "Branch System" in output
        assert "Core Components" in output
        assert "Initialization Flow" in output
        assert mock_pause.call_count == 4


class TestSectionManual:
    """Tests for _section_manual()."""

    @patch("dot_man.cli.onboarding._pause")
    @patch("dot_man.cli.onboarding._section_rule")
    @patch("dot_man.cli.onboarding._console")
    def test_displays_all_steps(self, mock_console, mock_rule, mock_pause):
        """All manual steps are displayed in order."""
        from dot_man.cli.onboarding import _section_manual

        _section_manual()
        mock_rule.assert_called_once()
        assert "Manual" in str(mock_rule.call_args[0][0])

        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Initialization" in output
        assert "Adding Files" in output
        assert "Branches" in output
        assert "Full Workflow" in output
        assert mock_pause.call_count == 5


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


class TestRunOnboarding:
    """Tests for run_onboarding()."""

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._confirm_next", return_value=True)
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="1")
    @patch("dot_man.cli.onboarding._console")
    def test_choice_architecture(
        self,
        mock_console,
        mock_prompt,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """Choice 1 shows architecture, then manual on confirm, then init + branch."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_arch.assert_called_once()
        mock_confirm.assert_called_once()
        mock_manual.assert_called_once()
        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._confirm_next", return_value=True)
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="2")
    @patch("dot_man.cli.onboarding._console")
    def test_choice_manual(
        self,
        mock_console,
        mock_prompt,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """Choice 2 shows manual, then architecture on confirm, then init + branch."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_manual.assert_called_once()
        mock_confirm.assert_called_once()
        mock_arch.assert_called_once()
        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._confirm_next")
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="s")
    @patch("dot_man.cli.onboarding._console")
    def test_choice_skip(
        self,
        mock_console,
        mock_prompt,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """Skip choice skips both sections and goes straight to init."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_arch.assert_not_called()
        mock_manual.assert_not_called()
        mock_confirm.assert_not_called()
        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=False)
    @patch("dot_man.cli.onboarding._confirm_next", return_value=True)
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="1")
    @patch("dot_man.cli.onboarding._console")
    def test_init_failure_skips_branch(
        self,
        mock_console,
        mock_prompt,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """When init fails, branch creation is skipped."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_arch.assert_called_once()
        mock_manual.assert_called_once()
        mock_init.assert_called_once()
        mock_branch.assert_not_called()
        mock_onboarded.assert_called_once()

    @patch("dot_man.cli.onboarding.sys.exit")
    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct")
    @patch("dot_man.cli.onboarding._confirm_next")
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding._console")
    def test_keyboard_interrupt(
        self,
        mock_console,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
        mock_exit,
    ):
        """KeyboardInterrupt during prompt is caught, prints message, exits."""
        from dot_man.cli.onboarding import run_onboarding

        # Make Prompt.ask raise KeyboardInterrupt after welcome
        with patch("dot_man.cli.onboarding.Prompt.ask", side_effect=KeyboardInterrupt):
            run_onboarding()

        mock_exit.assert_called_once_with(0)
        output = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "interrupted" in output.lower()

    @patch("dot_man.cli.onboarding.mark_onboarded")
    @patch("dot_man.cli.onboarding._offer_first_branch")
    @patch("dot_man.cli.onboarding._run_init_direct", return_value=True)
    @patch("dot_man.cli.onboarding._confirm_next", return_value=False)
    @patch("dot_man.cli.onboarding._section_manual")
    @patch("dot_man.cli.onboarding._section_architecture")
    @patch("dot_man.cli.onboarding.Prompt.ask", return_value="1")
    @patch("dot_man.cli.onboarding._console")
    def test_confirm_false_skips_manual(
        self,
        mock_console,
        mock_prompt,
        mock_arch,
        mock_manual,
        mock_confirm,
        mock_init,
        mock_branch,
        mock_onboarded,
    ):
        """When confirm returns False, the second section is skipped."""
        from dot_man.cli.onboarding import run_onboarding

        run_onboarding()

        mock_arch.assert_called_once()
        mock_manual.assert_not_called()
        mock_confirm.assert_called_once()
        mock_init.assert_called_once()
        mock_branch.assert_called_once()
        mock_onboarded.assert_called_once()
