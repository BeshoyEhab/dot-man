"""Tests for navigate_cmd.py helper functions and hook deduplication."""

from unittest.mock import MagicMock, patch

from dot_man.cli.navigate_cmd import (
    _warn_symlinks,
    generate_commit_message,
    get_changed_sections,
    run_branch_hooks,
)


class TestGenerateCommitMessage:
    """Test generate_commit_message helper."""

    def test_branch_switch(self):
        msg = generate_commit_message("main", "work", "branch", saved_count=3)
        assert "[dot-man] Save before switch to branch 'work'" in msg

    def test_tag_switch(self):
        msg = generate_commit_message("main", "v1.0", "tag")
        assert "switch to tag v1.0" in msg

    def test_commit_checkout(self):
        msg = generate_commit_message("main", "abc123def", "commit")
        assert "checkout commit abc123d" in msg

    def test_includes_saved_count(self):
        msg = generate_commit_message("main", "work", "branch", saved_count=5)
        assert "5 files" in msg

    def test_includes_sections(self):
        msg = generate_commit_message(
            "main", "work", "branch", sections=["shell", "nvim"]
        )
        assert "sections: shell, nvim" in msg

    def test_filters_defaults_and_config(self):
        msg = generate_commit_message(
            "main", "work", "branch", sections=["defaults", "config"]
        )
        assert "sections:" not in msg

    def test_truncates_many_sections(self):
        msg = generate_commit_message(
            "main", "work", "branch", sections=["a", "b", "c", "d"]
        )
        assert "+1 more" in msg

    def test_timestamp_present(self):
        msg = generate_commit_message("main", "work", "branch")
        assert "[202" in msg  # year in timestamp


class TestGetChangedSections:
    """Test get_changed_sections helper."""

    def test_no_sections(self):
        ops = MagicMock()
        ops.get_sections.return_value = []
        assert get_changed_sections(ops) == []

    def test_no_changes(self, tmp_path):
        ops = MagicMock()
        section = MagicMock()
        local = tmp_path / "file.txt"
        local.write_text("same")
        repo = tmp_path / "repo_file.txt"
        repo.write_text("same")
        section.paths = [local]
        section.get_repo_path.return_value = repo
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        with patch("dot_man.cli.navigate_cmd.compare_files", return_value=True):
            assert get_changed_sections(ops) == []

    def test_detects_changes(self, tmp_path):
        ops = MagicMock()
        section = MagicMock()
        local = tmp_path / "file.txt"
        local.write_text("new content")
        repo = tmp_path / "repo_file.txt"
        repo.write_text("old content")
        section.paths = [local]
        section.get_repo_path.return_value = repo
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        with patch("dot_man.cli.navigate_cmd.compare_files", return_value=False):
            assert get_changed_sections(ops) == ["test"]

    def test_detects_new_file(self, tmp_path):
        ops = MagicMock()
        section = MagicMock()
        local = tmp_path / "new.txt"
        local.write_text("new")
        repo = tmp_path / "repo_new.txt"
        # repo file doesn't exist - local is new/untracked
        section.paths = [local]
        section.get_repo_path.return_value = repo
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        # get_changed_sections only detects changes when repo_path.exists()
        # A new file (repo doesn't exist) won't be detected
        assert get_changed_sections(ops) == []

    def test_detects_deleted_file(self, tmp_path):
        ops = MagicMock()
        section = MagicMock()
        local = tmp_path / "deleted.txt"
        # local file doesn't exist
        repo = tmp_path / "repo_deleted.txt"
        repo.write_text("was here")
        section.paths = [local]
        section.get_repo_path.return_value = repo
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        assert get_changed_sections(ops) == ["test"]

    def test_exception_returns_empty(self):
        ops = MagicMock()
        ops.get_sections.side_effect = RuntimeError("fail")
        assert get_changed_sections(ops) == []


class TestWarnSymlinks:
    """Test _warn_symlinks helper."""

    def test_with_symlinks(self):
        with patch("dot_man.cli.navigate_cmd.ui") as mock_ui:
            _warn_symlinks({"symlinks": ["/path/to/link"]})
            assert mock_ui.console.print.call_count == 2

    def test_empty(self):
        with patch("dot_man.cli.navigate_cmd.ui") as mock_ui:
            _warn_symlinks({"symlinks": []})
            mock_ui.console.print.assert_not_called()

    def test_no_key(self):
        with patch("dot_man.cli.navigate_cmd.ui") as mock_ui:
            _warn_symlinks({})
            mock_ui.console.print.assert_not_called()


class TestRunBranchHooks:
    """Test run_branch_hooks helper."""

    def test_no_hooks(self):
        ops = MagicMock()
        section = MagicMock()
        section.on_activate = None
        section.on_deactivate = None
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        with patch("dot_man.cli.navigate_cmd.ui") as mock_ui:
            run_branch_hooks(ops, "on_activate")
            # Should not print "Running" since no hooks found
            for call in mock_ui.console.print.call_args_list:
                assert "Running" not in str(call)

    def test_runs_hooks(self):
        ops = MagicMock()
        section = MagicMock()
        section.on_activate = "echo hello"
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        with patch("dot_man.cli.navigate_cmd.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0)
            with patch("dot_man.cli.navigate_cmd.ui"):
                run_branch_hooks(ops, "on_activate")
            mock_sub.run.assert_called_once()

    def test_hook_failure_continues(self):
        ops = MagicMock()
        section = MagicMock()
        section.on_activate = "false"
        ops.get_sections.return_value = ["test"]
        ops.get_section.return_value = section
        with patch("dot_man.cli.navigate_cmd.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(
                returncode=1, stderr="error msg"
            )
            with patch("dot_man.cli.navigate_cmd.ui"):
                run_branch_hooks(ops, "on_activate")
        # Should not raise, just warn

    def test_deduplicates_hooks(self):
        ops = MagicMock()
        s1 = MagicMock()
        s1.on_activate = "echo shared"
        s2 = MagicMock()
        s2.on_activate = "echo shared"
        ops.get_sections.return_value = ["s1", "s2"]
        ops.get_section.side_effect = lambda name: {"s1": s1, "s2": s2}[name]
        with patch("dot_man.cli.navigate_cmd.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0)
            with patch("dot_man.cli.navigate_cmd.ui"):
                run_branch_hooks(ops, "on_activate")
        # Should only run once due to dedup
        assert mock_sub.run.call_count == 1
