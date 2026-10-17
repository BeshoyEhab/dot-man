"""Tests for section module."""

from pathlib import Path
from unittest.mock import patch

import pytest


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
        from dot_man.constants import HOOK_ALIASES
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[],
            repo_base="/test",
            pre_deploy="echo hello",
            post_deploy="quickshell_reload",
        )
        assert section.pre_deploy == "echo hello"
        # The alias name must be gone — only the command survives.
        assert "quickshell_reload" not in (section.post_deploy or "")
        assert section.post_deploy == HOOK_ALIASES["quickshell_reload"]
        # ...and the command keeps {config_name} for a later pass,
        # because this section has no paths to substitute yet.
        assert "killall qs" in (section.post_deploy or "")
        assert "{config_name}" in (section.post_deploy or "")

    def test_section_init_hook_alias_substitutes_config_name(self):
        """With paths present, quickshell_reload's {config_name} fills in.

        Pins the full command so both the alias lookup and the placeholder
        pass are verified in one shot.
        """
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/ii")],
            repo_base="/test",
            post_deploy="quickshell_reload",
        )
        assert section.post_deploy == "killall qs 2>/dev/null; sleep 0.3; qs -c ii &"

    def test_section_init_duplicate_paths_kept_in_order(self):
        """Duplicate paths are kept verbatim (no dedup), order preserved.

        Guards against a future dedup silently changing stored config and
        to_dict() output.
        """
        from dot_man.section import Section

        section = Section(name="dup", paths=["a/b", "a/b", Path("a/b")])
        assert section.paths == [Path("a/b"), Path("a/b"), Path("a/b")]
        assert section.to_dict()["paths"] == ["a/b", "a/b", "a/b"]

    def test_section_init_invalid_values_rejected(self):
        """Invalid deploy_method/update_strategy fail fast at construction.

        Section used to store garbage verbatim (e.g. deploy_method="rsync"),
        which then silently behaved like 'copy' at deploy time; reject with
        the same ConfigValidationError the config loader raises.
        """
        from dot_man.exceptions import ConfigValidationError
        from dot_man.section import Section

        with pytest.raises(
            ConfigValidationError, match=r"Invalid deploy_method 'rsync' in \[test\]"
        ):
            Section(
                name="test",
                paths=[],
                repo_base="/test",
                deploy_method="rsync",
            )

        with pytest.raises(
            ConfigValidationError,
            match=r"Invalid update_strategy 'rollback' in \[test\]",
        ):
            Section(
                name="test",
                paths=[],
                repo_base="/test",
                update_strategy="rollback",
            )

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

    @pytest.mark.parametrize(
        "raw_path,expected",
        [
            pytest.param(Path("~/.config/My Configs"), "My Configs", id="spaces"),
            pytest.param(Path("~/設定"), "設定", id="cjk"),
            pytest.param(Path("~/файл"), "файл", id="cyrillic"),
        ],
    )
    def test_generate_repo_base_unusual_last_segment(self, raw_path, expected):
        """repo_base comes from the last path segment, whatever it contains.

        Spaces and non-ASCII names are real-world config directory names;
        stripping or mangling them would corrupt the repo layout.
        """
        from dot_man.section import Section

        section = Section(name="fallback", paths=[raw_path])
        assert section._generate_repo_base() == expected
        assert section.repo_base == expected


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
        """{config_root} should be replaced with parent directory.

        Asserts the exact expanded value AND that no placeholder text
        survives — a leftover brace would break the hook at runtime.
        """
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/ii")],
        )
        result = section._resolve_hook("echo {config_root}")
        assert result == f"echo {Path.home()}/.config/quickshell"
        assert "{config_root}" not in result

    def test_resolve_paths_placeholder(self):
        """{paths} renders each shell-quoted path, space-separated.

        Values are quoted (S2) so a path containing shell metacharacters
        cannot inject commands into the hook's `sh -c` invocation.
        """
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/nvim"), Path("~/.vimrc")],
        )
        result = section._resolve_hook("echo {paths}")
        assert result == "echo '~/.config/nvim' '~/.vimrc'"

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

    def test_branch_placeholder_reads_recorded_branch_not_git(self, tmp_path):
        """{branch} comes from global.toml, never from raw git state.

        The old implementation opened REPO_DIR with
        search_parent_directories=True, so an unpatched (or not yet
        created) REPO_DIR leaked whatever repository happened to sit at or
        above it — observed as a mysterious personal branch named
        "custom" — and disagreed with operations.current_branch, the
        source deploy-time hook contexts use.
        """
        from git import Repo

        from dot_man.section import Section

        # A real git repo whose checked-out branch differs from the
        # recorded one: raw-git reads would return "git-branch".
        repo_dir = tmp_path / "nearby"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)
        with repo.config_writer() as config:
            config.set_value("user", "name", "T")
            config.set_value("user", "email", "t@t.c")
        (repo_dir / "f.txt").write_text("x")
        repo.index.add(["f.txt"])
        repo.index.commit("Initial")
        repo.create_head("git-branch").checkout()

        global_toml = tmp_path / "global.toml"
        global_toml.write_text('[dot-man]\ncurrent_branch = "work"\n')

        with (
            patch("dot_man.constants.REPO_DIR", repo_dir),
            patch("dot_man.global_config.GLOBAL_TOML", global_toml),
        ):
            section = Section(name="test", paths=[], repo_base="/test")
            assert Section._get_current_branch() == "work"
            assert section._resolve_hook("echo {branch}") == "echo work"

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

    def test_resolve_multiple_placeholders_in_one_hook(self):
        """Every placeholder in a single hook string must resolve.

        Hooks routinely mix values (name + root); a partial resolution
        would ship a broken command to the shell.
        """
        from dot_man.section import Section

        section = Section(
            name="quickshell-ii",
            paths=[Path("~/.config/quickshell/ii")],
        )
        result = section._resolve_hook("echo {section_name} @ {config_root}")
        assert result == f"echo quickshell-ii @ {Path.home()}/.config/quickshell"
        assert "{section_name}" not in result
        assert "{config_root}" not in result

    def test_resolve_multiple_placeholder_kinds_together(self):
        """section_name, config_name and branch resolve in one string.

        Hermetic variant: uses a fake branch so no real git repo is needed.
        """
        from dot_man.section import Section

        section = Section(
            name="qs-main",
            paths=[Path("~/.config/quickshell/ii")],
        )
        with patch(
            "dot_man.section.Section._get_current_branch",
            return_value="work",
        ):
            result = section._resolve_hook(
                "{section_name}/{config_name}:{branch}",
            )
        assert result == "qs-main/ii:work"

    def test_resolve_unknown_placeholder_stays_literal(self):
        """Unknown {bogus_var} must survive untouched.

        Silently blanking an unknown name would hide a typo in a hook;
        keeping the literal makes the typo visible in output.
        """
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        result = section._resolve_hook("echo {bogus_var}")
        assert result == "echo {bogus_var}"

    def test_resolve_unknown_placeholder_does_not_mask_known_one(self):
        """A known placeholder still resolves next to an unknown one."""
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        result = section._resolve_hook("{section_name} {bogus_var}")
        assert result == "test {bogus_var}"

    @pytest.mark.parametrize(
        "template",
        [
            pytest.param("echo {config_name}", id="config-name"),
            pytest.param("echo {config_root}", id="config-root"),
            pytest.param("echo {paths}", id="paths"),
        ],
    )
    def test_resolve_placeholder_without_data_stays_literal(self, template):
        """Placeholders with no backing paths must stay literal, not vanish.

        An empty substitution would yield a silently wrong shell command
        (e.g. `qs -c  &`); the literal keeps the failure loud.
        """
        from dot_man.section import Section

        section = Section(name="test", paths=[], repo_base="/test")
        assert section._resolve_hook(template) == template

    def test_resolve_alias_quickshell_substitutes_config_name(self):
        """quickshell_reload must expand to the full command for this path.

        Pins the whole command so both the alias lookup and the
        placeholder pass are verified in one shot.
        """
        from dot_man.section import Section

        section = Section(
            name="test",
            paths=[Path("~/.config/quickshell/ii")],
            repo_base="/test",
        )
        result = section._resolve_hook("quickshell_reload")
        assert result == "killall qs 2>/dev/null; sleep 0.3; qs -c ii &"
        assert "quickshell_reload" not in result

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

    def test_get_repo_path_nested_source_lands_under_repo_base(self, tmp_path):
        """A source deeper than the tracked root preserves its subdirectories.

        `~/.config/nvim/lua/mod.lua` tracked under `~/.config/nvim` must map
        to `repo/nvim/lua/mod.lua` — dropping intermediate directories would
        make same-basename files collide in the repo (silent data loss).
        """
        from dot_man.section import Section

        tracked = tmp_path / ".config" / "nvim"
        (tracked / "lua").mkdir(parents=True)
        source = tracked / "lua" / "mod.lua"
        source.write_text("--")
        section = Section(name="nvim", paths=[str(tracked)], repo_base="nvim")

        result = section.get_repo_path(source, tmp_path / "repo")

        assert str(result) == str(tmp_path / "repo" / "nvim" / "lua" / "mod.lua")

    def test_get_repo_path_rejects_escape(self, tmp_path):
        """An explicit repo_path must stay inside the repository (S6)."""
        from dot_man.exceptions import ConfigValidationError
        from dot_man.section import Section

        section = Section(
            name="evil",
            paths=["~/.bashrc"],
            repo_path="../../etc/passwd",
        )
        with pytest.raises(ConfigValidationError):
            section.get_repo_path(Path("/home/user/.bashrc"), tmp_path / "repo")

    def test_get_repo_path_rejects_absolute_repo_path(self, tmp_path):
        from dot_man.exceptions import ConfigValidationError
        from dot_man.section import Section

        section = Section(name="evil", paths=["~/.bashrc"], repo_path="/etc/passwd")
        with pytest.raises(ConfigValidationError):
            section.get_repo_path(Path("/home/user/.bashrc"), tmp_path / "repo")

    def test_get_repo_path_same_basename_different_dirs_do_not_collide(self, tmp_path):
        """Two files with the same basename in different subdirectories must
        map to distinct repo paths — the collision that basename-only
        mapping caused."""
        from dot_man.section import Section

        tracked = tmp_path / ".config" / "nvim"
        (tracked / "lua" / "a").mkdir(parents=True)
        (tracked / "lua" / "b").mkdir(parents=True)
        file_a = tracked / "lua" / "a" / "mod.lua"
        file_b = tracked / "lua" / "b" / "mod.lua"
        file_a.write_text("return a")
        file_b.write_text("return b")
        section = Section(name="nvim", paths=[str(tracked)], repo_base="nvim")

        repo_a = section.get_repo_path(file_a, tmp_path / "repo")
        repo_b = section.get_repo_path(file_b, tmp_path / "repo")

        assert repo_a != repo_b
        assert str(repo_a).endswith("nvim/lua/a/mod.lua")
        assert str(repo_b).endswith("nvim/lua/b/mod.lua")


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

    def test_to_dict_round_trip_maximal_section(self):
        """Rebuilding from to_dict() must reproduce every non-default field.

        to_dict() output is what gets persisted; a lossy round trip would
        silently drop settings on the next save.
        """
        from dot_man.section import Section

        original = Section(
            name="max",
            paths=["~/.config/nvim", "~/.vimrc"],
            repo_base="maxbase",
            secrets_filter=False,
            update_strategy="rename_old",
            include=["*.lua"],
            exclude=["*.bak"],
            inherits=["base"],
            pre_deploy="echo before",
            post_deploy="echo after",
            on_activate="echo on",
            on_deactivate="echo off",
            ignored_directories=["node_modules", ".git"],
            follow_symlinks=True,
            deploy_method="symlink",
            encrypted=True,
            encryption_method="age",
            encryption_recipient="age1xyz",
            shared=True,
        )
        data = original.to_dict()

        assert sorted(data) == [
            "deploy_method",
            "encrypted",
            "encryption_method",
            "encryption_recipient",
            "exclude",
            "follow_symlinks",
            "ignored_directories",
            "include",
            "inherits",
            "on_activate",
            "on_deactivate",
            "paths",
            "post_deploy",
            "pre_deploy",
            "repo_base",
            "secrets_filter",
            "shared",
            "update_strategy",
        ]
        assert "name" not in data  # name is the TOML key, not a field

        payload = dict(data)
        rebuilt = Section(
            name="max",
            repo_base=payload.pop("repo_base", "max"),
            **payload,
        )

        assert rebuilt.to_dict() == data
        assert rebuilt.name == "max"
        assert rebuilt.repo_base == "maxbase"
        assert rebuilt.paths == original.paths
        assert rebuilt.shared is True
        assert rebuilt.encryption_recipient == "age1xyz"

    def test_to_dict_round_trip_with_repo_path(self):
        """repo_path is serialized and makes repo_base redundant.

        The rebuilt section must produce the identical dict even though
        repo_base is absent from it (repo_path wins).
        """
        from dot_man.section import Section

        original = Section(
            name="nvim",
            paths=["~/.config/nvim"],
            repo_base="custom-base",
            repo_path="cfg/nvim",
            secrets_filter=False,
            deploy_method="symlink",
        )
        data = original.to_dict()

        assert "repo_base" not in data  # repo_path overrides it

        payload = dict(data)
        rebuilt = Section(
            name="nvim",
            repo_base=payload.pop("repo_base", "nvim"),
            **payload,
        )

        assert rebuilt.to_dict() == data
        assert rebuilt.repo_path == "cfg/nvim"
        assert rebuilt.secrets_filter is False
        assert rebuilt.deploy_method == "symlink"
