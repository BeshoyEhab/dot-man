"""Tests for branch_ops.py, status_ops.py, and save_deploy_ops.py."""


class TestBranchOpsRevertFile:
    """Test the revert_file method from BranchMixin."""

    def test_revert_untracked_file(self, integration_runner, tmp_path):
        from dot_man.cli.interface import cli

        fake_path = tmp_path / "not_tracked.txt"
        fake_path.write_text("data")
        result = integration_runner.invoke(cli, ["revert", str(fake_path)])
        assert "not tracked" in result.output.lower() or result.exit_code != 0


class TestBranchOpsDetectHooks:
    """Test hook detection for changed files."""

    def test_detect_hooks_for_bashrc(self):
        from dot_man.branch_ops import FILE_TO_HOOK_MAP

        assert ".bashrc" in FILE_TO_HOOK_MAP
        assert FILE_TO_HOOK_MAP[".bashrc"] == "bash_reload"

    def test_detect_hooks_for_nvim(self):
        from dot_man.branch_ops import FILE_TO_HOOK_MAP

        assert ".config/nvim" in FILE_TO_HOOK_MAP
        assert FILE_TO_HOOK_MAP[".config/nvim"] == "nvim_sync"

    def test_detect_hooks_for_hyprland(self):
        from dot_man.branch_ops import FILE_TO_HOOK_MAP

        assert ".config/hypr" in FILE_TO_HOOK_MAP
        assert FILE_TO_HOOK_MAP[".config/hypr"] == "hyprland_reload"

    def test_file_to_hook_map_complete(self):
        from dot_man.branch_ops import FILE_TO_HOOK_MAP

        assert ".zshrc" in FILE_TO_HOOK_MAP
        assert ".tmux.conf" in FILE_TO_HOOK_MAP
        assert ".config/kitty" in FILE_TO_HOOK_MAP
        assert ".config/sway" in FILE_TO_HOOK_MAP
        assert ".config/i3" in FILE_TO_HOOK_MAP


class TestStatusOpsAudit:
    """Test the audit method from StatusMixin."""

    def test_audit_clean_repo(self, integration_runner):
        from dot_man.cli.interface import cli

        result = integration_runner.invoke(cli, ["audit"])
        assert result.exit_code == 0


class TestStatusOpsSummary:
    """Test status summary generation."""

    def test_status_shows_info(self, integration_runner):
        from dot_man.cli.interface import cli

        result = integration_runner.invoke(cli, ["status"])
        assert result.exit_code == 0


class TestStatusOpsOrphans:
    """Test orphan file detection."""

    def test_clean_no_orphans(self, integration_runner):
        from dot_man.cli.interface import cli

        result = integration_runner.invoke(cli, ["clean", "--dry-run"])
        assert result.exit_code == 0
