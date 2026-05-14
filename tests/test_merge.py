"""Tests for the merge module (universal file merge system)."""

from dot_man.merge import (
    UniversalMergeManager,
    get_hook_command,
    get_hook_for_config,
    list_all_hooks,
    merge_files,
    reload_all_dots,
)


class TestUniversalMergeManager:
    """Tests for UniversalMergeManager class."""

    def test_inject_content_append(self, tmp_path):
        """Test injecting content at the end of a file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("existing content\n")

        manager = UniversalMergeManager()
        result = manager.inject_content(
            file_path, "# my alias\nexport A=1", marker="aliases"
        )

        assert "# >>> dot-man:start <<< aliases" in result
        assert "# >>> dot-man:end <<<" in result
        assert "# my alias" in result
        assert "export A=1" in result
        assert "existing content" in result

    def test_inject_content_prepend(self, tmp_path):
        """Test injecting content at the beginning of a file."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("existing content\n")

        manager = UniversalMergeManager()
        result = manager.inject_content(file_path, "# header", position="prepend")

        lines = result.split("\n")
        assert lines[0] == "# >>> dot-man:start <<<"
        assert lines[1] == "# header"
        assert "existing content" in result

    def test_inject_content_idempotent(self, tmp_path):
        """Test that injecting same content twice is idempotent."""
        file_path = tmp_path / "test.txt"
        file_path.write_text("")

        manager = UniversalMergeManager()
        result1 = manager.inject_content(file_path, "# content")
        result2 = manager.inject_content(file_path, "# content")

        assert result1 == result2
        assert result2.count("# >>> dot-man:start <<<") == 1

    def test_get_regions(self, tmp_path):
        """Test extracting merge regions from a file."""
        file_path = tmp_path / "test.txt"
        content = """#!/bin/bash
# >>> dot-man:start <<< aliases
export A=1
export B=2
# >>> dot-man:end <<<
# rest of file
"""
        file_path.write_text(content)

        manager = UniversalMergeManager()
        regions = manager.get_regions(file_path)

        assert len(regions) == 1
        assert regions[0]["start_line"] == 1
        assert regions[0]["end_line"] == 4
        assert "export A=1" in regions[0]["content"]
        assert "export B=2" in regions[0]["content"]

    def test_get_regions_multiple(self, tmp_path):
        """Test extracting multiple merge regions."""
        file_path = tmp_path / "test.txt"
        content = """# >>> dot-man:start <<< aliases
export A=1
# >>> dot-man:end <<<
# >>> dot-man:start <<< functions
echo hello
# >>> dot-man:end <<<
"""
        file_path.write_text(content)

        manager = UniversalMergeManager()
        regions = manager.get_regions(file_path)

        assert len(regions) == 2

    def test_remove_content(self, tmp_path):
        """Test removing managed content from a file."""
        file_path = tmp_path / "test.txt"
        content = """#!/bin/bash
# >>> dot-man:start <<< aliases
export A=1
# >>> dot-man:end <<<
# rest of file
"""
        file_path.write_text(content)

        manager = UniversalMergeManager()
        result = manager.remove_content(file_path)

        assert "# >>> dot-man:start <<<" not in result
        assert "# >>> dot-man:end <<<" not in result
        assert "export A=1" not in result
        assert "# rest of file" in result

    def test_remove_content_specific_marker(self, tmp_path):
        """Test removing only specific marker."""
        file_path = tmp_path / "test.txt"
        content = """# >>> dot-man:start <<< aliases
export A=1
# >>> dot-man:end <<<
# >>> dot-man:start <<< functions
echo hello
# >>> dot-man:end <<<
"""
        file_path.write_text(content)

        manager = UniversalMergeManager()
        result = manager.remove_content(file_path, marker="aliases")

        assert "export A=1" not in result
        assert "echo hello" in result

    def test_list_universal_files(self, tmp_path):
        """Test listing files with merge markers."""
        dir_path = tmp_path / ".config"
        dir_path.mkdir()

        (dir_path / "shell").write_text("# no markers here\n")
        (dir_path / "bashrc").write_text("""# >>> dot-man:start <<< aliases
export A=1
# >>> dot-man:end <<<
""")

        manager = UniversalMergeManager()
        results = manager.list_universal_files([str(dir_path)])

        assert any("bashrc" in r for r in results)
        assert not any("shell" in r for r in results)


class TestHooks:
    """Tests for hook-related functions."""

    def test_get_hook_for_config_nvim(self):
        """Test getting hook for nvim config."""
        hook = get_hook_for_config("nvim")
        assert hook is not None
        assert "nvim" in hook.lower() or "packer" in hook.lower()

    def test_get_hook_for_config_hyprland(self):
        """Test getting hook for hyprland."""
        hook = get_hook_for_config("hyprland")
        assert hook is not None
        assert "hypr" in hook.lower()

    def test_get_hook_for_config_shell(self):
        """Test getting hook for shell configs."""
        hook = get_hook_for_config("zshrc")
        assert hook is not None

    def test_get_hook_for_config_quickshell(self):
        """Test quickshell uses custom reload."""
        hook = get_hook_for_config("quickshell")
        assert hook is None

    def test_get_hook_for_config_unknown(self):
        """Test unknown config returns None."""
        hook = get_hook_for_config("unknown_config_xyz")
        assert hook is None

    def test_list_all_hooks(self):
        """Test listing all hooks by category."""
        hooks = list_all_hooks()

        assert "shells" in hooks
        assert "window_managers" in hooks
        assert "terminals" in hooks
        assert "bars" in hooks
        assert "editors" in hooks
        assert "tools" in hooks

        assert "shell_reload" in hooks["shells"]
        assert "hyprland_reload" in hooks["window_managers"]

    def test_get_hook_command(self):
        """Test getting hook command by name."""
        hook = get_hook_command("nvim_sync")
        assert hook is not None
        assert "nvim" in hook.lower()

    def test_get_hook_command_unknown(self):
        """Test unknown hook returns None."""
        hook = get_hook_command("nonexistent_hook")
        assert hook is None

    def test_reload_all_dots(self):
        """Test generating reload commands for all configs."""
        commands = reload_all_dots()

        assert len(commands) > 0
        for cmd in commands:
            assert isinstance(cmd, str)
            assert "||" in cmd or "&" in cmd or "true" in cmd


class TestMergeFiles:
    """Tests for merge_files function."""

    def test_merge_replace_strategy(self, tmp_path):
        """Test merge with replace strategy."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        source.write_text("new content")
        target.write_text("old content")

        result = merge_files(str(source), str(target), strategy="replace")

        assert result == "new content"

    def test_merge_target_not_exists(self, tmp_path):
        """Test merge when target doesn't exist."""
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"

        source.write_text("content")

        result = merge_files(str(source), str(target))

        assert result == "content"

    def test_merge_source_not_exists(self, tmp_path):
        """Test merge when source doesn't exist."""
        target = tmp_path / "target.txt"
        target.write_text("target content")

        result = merge_files("/nonexistent", str(target))

        assert result == ""
