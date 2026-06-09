"""Tests for section module."""

from pathlib import Path
from unittest.mock import patch


class TestSectionInit:
    """Test Section initialization."""

    def test_section_init_basic(self):
        """Test Section with basic params."""
        from dot_man.section import Section

        section = Section(
            name="ssh",
            paths=[".ssh/id_rsa"],
            repo_base="dotfiles",
        )
        assert section.name == "ssh"
        assert section.paths == [Path(".ssh/id_rsa")]
        assert section.repo_base == "dotfiles"

    def test_section_init_defaults(self):
        """Test Section uses correct defaults."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        assert section.secrets_filter is True
        assert section.update_strategy == "replace"
        assert section.include == []
        assert section.exclude == []
        assert section.inherits == []
        assert section.follow_symlinks is False
        assert section.deploy_method == "copy"
        assert section.encrypted is False
        assert section.encryption_method == "gpg"

    def test_section_init_encryption(self):
        """Test Section encryption fields."""
        from dot_man.section import Section

        section = Section(
            name="secrets",
            paths=[],
            repo_base="/test",
            encrypted=True,
            encryption_method="age",
            encryption_recipient="age1abc123",
        )
        assert section.encrypted is True
        assert section.encryption_method == "age"
        assert section.encryption_recipient == "age1abc123"

    def test_section_init_hooks_resolved(self):
        """Test hooks are resolved via _resolve_hook."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
            pre_deploy="echo hello",
            post_deploy="quickshell_reload",
        )
        assert section.pre_deploy == "echo hello"
        # quickshell_reload is resolved via HOOK_ALIASES
        assert "killall qs" in (section.post_deploy or "")
        assert "{config_name}" in (section.post_deploy or "")

    def test_section_init_ignored_directories_custom(self):
        """Test Section with custom ignored_directories."""
        from dot_man.section import Section

        custom_ignored = ["node_modules", ".git", ".cache"]
        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
            ignored_directories=custom_ignored,
        )
        assert section.ignored_directories == custom_ignored

    def test_section_init_follow_symlinks(self):
        """Test Section with follow_symlinks enabled."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
            follow_symlinks=True,
        )
        assert section.follow_symlinks is True

    def test_section_init_deploy_method_symlink(self):
        """Test Section with symlink deploy method."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
            deploy_method="symlink",
        )
        assert section.deploy_method == "symlink"

    def test_section_init_repo_base_auto(self):
        """Test repo_base auto-generation when not provided."""
        from dot_man.section import Section

        section = Section(
            name="nvim",
            paths=[Path("~/.config/nvim")],
        )
        assert section.repo_base == "nvim"


class TestGenerateRepoBase:
    """Test _generate_repo_base method."""

    def test_generate_empty_paths(self):
        """Repo_base should fall back to section name when no paths."""
        from dot_man.section import Section

        section = Section(name="my-section", paths=[], repo_base="/test")
        result = section._generate_repo_base()
        assert result == "my-section"

    def test_generate_dotfile(self):
        """Repo_base for .bashrc should be 'bashrc'."""
        from dot_man.section import Section

        section = Section(
            name="bash",
            paths=[Path("~/.bashrc")],
        )
        result = section._generate_repo_base()
        assert result == "bashrc"

    def test_generate_dot_dir(self):
        """Repo_base for .ssh should be 'ssh'."""
        from dot_man.section import Section

        section = Section(
            name="ssh",
            paths=[Path("~/.ssh")],
        )
        result = section._generate_repo_base()
        assert result == "ssh"

    def test_generate_config_dir(self):
        """Repo_base for ~/.config/nvim should be 'nvim'."""
        from dot_man.section import Section

        section = Section(
            name="nvim",
            paths=[Path("~/.config/nvim")],
        )
        result = section._generate_repo_base()
        assert result == "nvim"


class TestResolveHook:
    """Test _resolve_hook method."""

    def test_resolve_none(self):
        """_resolve_hook(None) should return None."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        assert section._resolve_hook(None) is None

    def test_resolve_empty(self):
        """_resolve_hook('') should return None."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        assert section._resolve_hook("") is None

    def test_resolve_plain_command(self):
        """Plain command should pass through unchanged."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        result = section._resolve_hook("echo hello")
        assert result == "echo hello"

    def test_resolve_section_name_placeholder(self):
        """{section_name} should be replaced."""
        from dot_man.section import Section

        section = Section(
            name="quickshell-ii",
            paths=[Path("~/.config/quickshell/ii")],
        )
        result = section._resolve_hook("echo {section_name}")
        assert result == "echo quickshell-ii"

    def test_resolve_config_name_placeholder(self):
        """{config_name} should be replaced with last path segment."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/ii")],
        )
        result = section._resolve_hook("echo {config_name}")
        assert result == "echo ii"

    def test_resolve_config_root_placeholder(self):
        """{config_root} should be replaced with parent directory."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/ii")],
        )
        result = section._resolve_hook("echo {config_root}")
        expected = f"echo {Path.home()}/.config/quickshell"
        assert result == expected

    def test_resolve_paths_placeholder(self):
        """{paths} should be replaced with space-separated paths."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/nvim"), Path("~/.vimrc")],
        )
        result = section._resolve_hook("echo {paths}")
        assert result is not None
        assert ".config/nvim" in result
        assert ".vimrc" in result

    def test_resolve_qs_config_backward_compat(self):
        """{qs_config} should still work as alias for {config_name}."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/caelestea")],
        )
        result = section._resolve_hook("echo {qs_config}")
        assert result == "echo caelestea"

    def test_resolve_branch_placeholder(self):
        """{branch} should be replaced with current branch name."""
        from dot_man.section import Section

        with patch(
            "dot_man.section.Section._get_current_branch",
            return_value="work",
        ):
            section = Section(
                name="test",
                paths=[],
                repo_base="/test",
            )
            result = section._resolve_hook("echo {branch}")
            assert result == "echo work"

    def test_resolve_alias(self):
        """Hook aliases should be resolved to their command."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
        )
        result = section._resolve_hook("shell_reload")
        assert result == (
            "source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true"
        )

    def test_resolve_with_existing_path(self, tmp_path):
        """_resolve_hook should handle existing directories."""
        from dot_man.section import Section

        config_dir = tmp_path / "quickshell" / "ii"
        config_dir.mkdir(parents=True)
        section = Section(
            name="test",
            paths=[config_dir],
        )
        result = section._resolve_hook("echo {config_name}")
        assert result == "echo ii"

    def test_resolve_with_existing_file(self, tmp_path):
        """_resolve_hook should handle existing files."""
        from dot_man.section import Section

        config_file = tmp_path / "test.conf"
        config_file.write_text("test")
        section = Section(
            name="test",
            paths=[config_file],
        )
        result = section._resolve_hook("echo {config_name}")
        assert result == "echo test.conf"


class TestSectionProperties:
    """Test Section properties."""

    def test_section_name(self):
        """Test Section name property."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        assert section.name == "test"

    def test_section_paths(self):
        """Test Section paths property."""
        from dot_man.section import Section

        section = Section(name="test", paths=[".bashrc", ".zshrc"], repo_base="/test")
        assert section.paths == [Path(".bashrc"), Path(".zshrc")]


class TestSectionMethods:
    """Test Section methods."""

    def test_get_repo_path_default(self):
        """Test get_repo_path without explicit repo_path."""
        from dot_man.section import Section

        section = Section(
            name="nvim",
            paths=["~/.config/nvim"],
            repo_base="nvim",
        )
        result = section.get_repo_path(
            Path("/home/user/.config/nvim/init.lua"),
            Path("/home/user/.dot-man/repo"),
        )
        assert str(result) == "/home/user/.dot-man/repo/nvim/init.lua"

    def test_get_repo_path_with_repo_path(self):
        """Test get_repo_path with explicit repo_path."""
        from dot_man.section import Section

        section = Section(
            name="bashrc",
            paths=["~/.bashrc"],
            repo_path="bash/bashrc",
        )
        result = section.get_repo_path(
            Path("/home/user/.bashrc"),
            Path("/home/user/.dot-man/repo"),
        )
        assert str(result) == "/home/user/.dot-man/repo/bash/bashrc"


class TestToDict:
    """Test to_dict method."""

    def test_to_dict_minimal(self):
        """to_dict should only include paths and auto-generated repo_base by default."""
        from dot_man.section import Section

        # repo_base not passed — it'll match auto-generated, so not in dict
        section = Section(name="test", paths=["~/.bashrc"])
        result = section.to_dict()
        assert "paths" in result
        assert "secrets_filter" not in result  # Default

    def test_to_dict_with_repo_path(self):
        """to_dict should include repo_path when explicitly set."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_path="bashrc",
        )
        result = section.to_dict()
        assert result["repo_path"] == "bashrc"

    def test_to_dict_non_default_secrets_filter(self):
        """to_dict should include secrets_filter when not default."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            secrets_filter=False,
        )
        result = section.to_dict()
        assert result["secrets_filter"] is False

    def test_to_dict_non_default_update_strategy(self):
        """to_dict should include update_strategy when not default."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            update_strategy="rename_old",
        )
        result = section.to_dict()
        assert result["update_strategy"] == "rename_old"

    def test_to_dict_symlink_deploy_method(self):
        """to_dict should include deploy_method when not 'copy'."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            deploy_method="symlink",
        )
        result = section.to_dict()
        assert result["deploy_method"] == "symlink"

    def test_to_dict_follow_symlinks(self):
        """to_dict should include follow_symlinks when True."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            follow_symlinks=True,
        )
        result = section.to_dict()
        assert result["follow_symlinks"] is True

    def test_to_dict_encrypted(self):
        """to_dict should include encryption fields when non-default."""
        from dot_man.section import Section

        section = Section(
            name="secrets",
            paths=["~/.config/secrets"],
            repo_base="/test",
            encrypted=True,
            encryption_method="age",
            encryption_recipient="age1xyz",
        )
        result = section.to_dict()
        assert result["encrypted"] is True
        assert result["encryption_method"] == "age"
        assert result["encryption_recipient"] == "age1xyz"

    def test_to_dict_hooks(self):
        """to_dict should include active hooks."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            pre_deploy="echo before",
            post_deploy="echo after",
        )
        result = section.to_dict()
        assert result["pre_deploy"] == "echo before"
        assert result["post_deploy"] == "echo after"

    def test_to_dict_inherits(self):
        """to_dict should include inherits when not empty."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            inherits=["base", "server"],
        )
        result = section.to_dict()
        assert result["inherits"] == ["base", "server"]

    def test_to_dict_custom_ignored_directories(self):
        """to_dict should include custom ignored_directories."""
        from dot_man.section import Section

        custom = [".cache", "node_modules"]
        section = Section(
            name="test",
            paths=["~/.bashrc"],
            repo_base="/test",
            ignored_directories=custom,
        )
        result = section.to_dict()
        assert result["ignored_directories"] == custom

    def test_to_dict_include_exclude(self):
        """to_dict should include include/exclude globs."""
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=["~/.config/nvim"],
            repo_base="/test",
            include=["*.lua"],
            exclude=["*.bak"],
        )
        result = section.to_dict()
        assert result["include"] == ["*.lua"]
        assert result["exclude"] == ["*.bak"]
