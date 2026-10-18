"""Tests for dot_man.config — GlobalConfig, Section, DotManConfig."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest

from dot_man.config import DotManConfig, GlobalConfig, Section
from dot_man.constants import DEFAULT_BRANCH, DEFAULT_IGNORED_DIRECTORIES, HOOK_ALIASES
from dot_man.exceptions import ConfigurationError, ConfigValidationError


def _section_to_toml(data: dict) -> str:
    """Serialize a flat section dict to TOML lines for round-trip tests."""
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        elif isinstance(value, list):
            inner = ", ".join(f'"{item}"' for item in value)
            lines.append(f"{key} = [{inner}]")
    return "\n".join(lines) + "\n"


# ─── GlobalConfig ──────────────────────────────────────────


@pytest.fixture
def global_cfg(tmp_path):
    """Create a GlobalConfig pointing at a temp directory."""
    toml_path = tmp_path / "global.toml"
    with patch("dot_man.constants.GLOBAL_TOML", toml_path):
        gc = GlobalConfig()
        gc.create_default()
        gc.load()
        yield gc


class TestGlobalConfig:
    def test_load_creates_file(self, global_cfg):
        assert global_cfg.current_branch == DEFAULT_BRANCH

    def test_current_branch_get_set(self, global_cfg):
        global_cfg.current_branch = "work"
        assert global_cfg.current_branch == "work"

    def test_remote_url_get_set(self, global_cfg):
        assert global_cfg.remote_url == ""
        global_cfg.remote_url = "https://github.com/test/repo.git"
        assert global_cfg.remote_url == "https://github.com/test/repo.git"

    def test_editor_get_set(self, global_cfg):
        """create_default leaves editor unset; setting it must round-trip in memory."""
        assert global_cfg.editor is None
        global_cfg.editor = "nvim"
        assert global_cfg.editor == "nvim"

    def test_secrets_filter_get_set(self, global_cfg):
        assert global_cfg.secrets_filter_enabled is True
        global_cfg.secrets_filter_enabled = False
        assert global_cfg.secrets_filter_enabled is False

    def test_strict_mode_get_set(self, global_cfg):
        assert global_cfg.strict_mode is False
        global_cfg.strict_mode = True
        assert global_cfg.strict_mode is True

    def test_switch_default_behavior_get_set(self, global_cfg):
        """switch.default_behavior is 'save' by default; 'no-save' is the only other value."""
        assert global_cfg.switch_default_behavior == "save"
        global_cfg.switch_default_behavior = "no-save"
        assert global_cfg.switch_default_behavior == "no-save"

    def test_switch_default_behavior_invalid_raises(self, global_cfg):
        """Any value other than save/no-save must be rejected, not silently stored."""
        with pytest.raises(ConfigurationError, match="default_behavior"):
            global_cfg.switch_default_behavior = "backup"

    def test_get_defaults(self, global_cfg):
        """get_defaults must expose the exact default schema, not just keys."""
        defaults = global_cfg.get_defaults()
        assert defaults == {
            "secrets_filter": True,
            "update_strategy": "replace",
            "ignored_directories": DEFAULT_IGNORED_DIRECTORIES,
            "follow_symlinks": False,
        }

    def test_get_template_nonexistent(self, global_cfg):
        assert global_cfg.get_template("nope") is None

    def test_get_all_templates(self, global_cfg):
        """create_default seeds an example template; pin its exact shape."""
        templates = global_cfg.get_all_templates()
        assert templates == {
            "example": {
                "post_deploy": "echo 'Deployed!'",
                "update_strategy": "replace",
            }
        }
        assert global_cfg.get_template("example") == templates["example"]

    def test_save_persistence(self, tmp_path):
        toml_path = tmp_path / "global.toml"
        with patch("dot_man.constants.GLOBAL_TOML", toml_path):
            gc = GlobalConfig()
            gc.create_default()
            gc.current_branch = "test-persist"
            gc.save(force=True)

            gc2 = GlobalConfig()
            gc2.load()
            assert gc2.current_branch == "test-persist"

    def test_full_property_round_trip(self, tmp_path):
        """Every settable property must survive save → reload with its exact value."""
        toml_path = tmp_path / "global.toml"
        with patch("dot_man.constants.GLOBAL_TOML", toml_path):
            gc = GlobalConfig()
            gc.create_default()
            gc.current_branch = "work"
            gc.remote_url = "https://github.com/u/r.git"
            gc.editor = "nvim"
            gc.strict_mode = True
            gc.secrets_filter_enabled = False
            gc.switch_default_behavior = "no-save"
            gc.save(force=True)

            gc2 = GlobalConfig()
            gc2.load()
            assert gc2.current_branch == "work"
            assert gc2.remote_url == "https://github.com/u/r.git"
            assert gc2.editor == "nvim"
            assert gc2.strict_mode is True
            assert gc2.secrets_filter_enabled is False
            assert gc2.switch_default_behavior == "no-save"

    def test_load_missing_raises(self, tmp_path):
        toml_path = tmp_path / "nonexistent.toml"
        with patch("dot_man.constants.GLOBAL_TOML", toml_path):
            gc = GlobalConfig()
            with pytest.raises(ConfigurationError):
                gc.load()


# ─── Section ───────────────────────────────────────────────


class TestSection:
    def test_basic_creation(self):
        s = Section(name="test", paths=[Path("/home/user/.bashrc")])
        assert s.name == "test"
        assert s.secrets_filter is True
        assert s.update_strategy == "replace"
        assert s.follow_symlinks is False

    def test_defaults(self):
        s = Section(name="s", paths=[Path("/tmp/f")])
        assert s.include == []
        assert s.exclude == []
        assert s.inherits == []
        assert s.ignored_directories == DEFAULT_IGNORED_DIRECTORIES

    def test_repo_base_auto_dotfile(self):
        s = Section(name="bash", paths=[Path("/home/user/.bashrc")])
        assert s.repo_base == "bashrc"

    def test_repo_base_auto_dotdir(self):
        s = Section(name="vim", paths=[Path("/home/user/.vim")])
        assert s.repo_base == "vim"

    def test_repo_base_auto_config_dir(self):
        s = Section(name="nvim", paths=[Path("/home/user/.config/nvim")])
        assert s.repo_base == "nvim"

    def test_repo_base_explicit(self):
        s = Section(name="test", paths=[Path("/tmp/f")], repo_base="custom")
        assert s.repo_base == "custom"

    def test_repo_base_empty_paths(self):
        s = Section(name="empty", paths=[])
        assert s.repo_base == "empty"

    def test_get_repo_path_with_repo_base(self):
        s = Section(name="test", paths=[Path("/tmp/f")], repo_base="mybase")
        result = s.get_repo_path(Path("/tmp/f"), Path("/repo"))
        assert result == Path("/repo/mybase/f")

    def test_get_repo_path_with_repo_path(self):
        """repo_path is the single-file form: get_repo_path uses it verbatim."""
        s = Section(name="test", paths=[Path("/tmp/f")], repo_path="explicit/dest")
        result = s.get_repo_path(Path("/tmp/f"), Path("/repo"))
        assert result == Path("/repo/explicit/dest")

    def test_to_dict_minimal(self):
        s = Section(name="test", paths=[Path("/tmp/f")])
        d = s.to_dict()
        assert "paths" in d
        # Default values should NOT be in dict
        assert "secrets_filter" not in d
        assert "update_strategy" not in d

    def test_to_dict_non_defaults(self):
        s = Section(
            name="test",
            paths=[Path("/tmp/f")],
            secrets_filter=False,
            update_strategy="rename_old",
            include=["*.conf"],
            exclude=["*.log"],
            pre_deploy="echo pre",
            post_deploy="echo post",
            inherits=["base"],
            follow_symlinks=True,
        )
        d = s.to_dict()
        assert d["secrets_filter"] is False
        assert d["update_strategy"] == "rename_old"
        assert d["include"] == ["*.conf"]
        assert d["exclude"] == ["*.log"]
        assert d["pre_deploy"] == "echo pre"
        assert d["post_deploy"] == "echo post"
        assert d["inherits"] == ["base"]
        assert d["follow_symlinks"] is True

    def test_resolve_hook_none(self):
        s = Section(name="test", paths=[Path("/tmp/f")])
        assert s.pre_deploy is None

    def test_resolve_hook_custom(self):
        s = Section(name="test", paths=[Path("/tmp/f")], post_deploy="echo hello")
        assert s.post_deploy == "echo hello"

    def test_resolve_hook_alias(self):
        s = Section(name="test", paths=[Path("/tmp/f")], post_deploy="shell_reload")
        assert s.post_deploy == HOOK_ALIASES["shell_reload"]

    def test_custom_ignored_directories(self):
        s = Section(name="test", paths=[Path("/tmp/f")], ignored_directories=["custom"])
        assert s.ignored_directories == ["custom"]

    @pytest.mark.parametrize(
        "name",
        ["sëction", "a.b"],
        ids=["unicode-name", "dotted-name"],
    )
    def test_unicode_and_dotted_names(self, name, load_from_toml):
        """Names with unicode or dots must derive paths and survive a TOML round-trip.

        TOML requires quoted keys for these names, and repo derivation must not
        mangle them into invalid section lookups.
        """
        s = Section(name=name, paths=[Path("/tmp/f")])
        assert s.get_repo_path(Path("/tmp/f"), Path("/repo")) == Path("/repo/f/f")
        assert s.to_dict() == {"paths": ["/tmp/f"]}

        dc = load_from_toml(f'["{name}"]\n{_section_to_toml(s.to_dict())}')
        loaded = dc.get_section(name)
        assert loaded.name == name
        assert loaded.paths == [Path("/tmp/f")]

    def test_to_dict_round_trip_preserves_non_defaults(self, load_from_toml):
        """to_dict → TOML file → load must preserve every non-default field.

        This guards the serializer boundary: anything Section can emit must be
        re-readable with identical public values.
        """
        original = Section(
            name="nd",
            paths=[Path("/tmp/f")],
            secrets_filter=False,
            update_strategy="rename_old",
            include=["*.conf"],
            exclude=["*.log"],
            pre_deploy="echo pre",
            post_deploy="echo post",
            inherits=["base"],
            follow_symlinks=True,
            ignored_directories=["onlythis"],
        )
        dc = load_from_toml("[nd]\n" + _section_to_toml(original.to_dict()))

        loaded = dc.get_section("nd")
        assert loaded.paths == [Path("/tmp/f")]
        assert loaded.secrets_filter is False
        assert loaded.update_strategy == "rename_old"
        assert loaded.include == ["*.conf"]
        assert loaded.exclude == ["*.log"]
        assert loaded.pre_deploy == "echo pre"
        assert loaded.post_deploy == "echo post"
        assert loaded.inherits == ["base"]
        assert loaded.follow_symlinks is True
        assert loaded.ignored_directories == ["onlythis"]


# ─── DotManConfig ──────────────────────────────────────────


@pytest.fixture
def dotman_cfg(tmp_path):
    """Create a DotManConfig with a sample toml."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    toml_content = """
[myconfig]
paths = ["/tmp/test.conf"]

[shell]
paths = ["~/.bashrc", "~/.zshrc"]
post_deploy = "shell_reload"
secrets_filter = false

[templates.base]
update_strategy = "rename_old"
"""
    (repo_dir / "dot-man.toml").write_text(toml_content)

    global_toml = tmp_path / "global.toml"
    with (
        patch("dot_man.constants.GLOBAL_TOML", global_toml),
        patch("dot_man.constants.REPO_DIR", repo_dir),
    ):
        gc = GlobalConfig()
        gc.create_default()
        gc.load()

        dc = DotManConfig(repo_path=repo_dir, global_config=gc)
        dc.load()
        yield dc


@pytest.fixture
def load_from_toml(tmp_path):
    """Factory: load a DotManConfig from TOML text with patched repo/global paths.

    Patches stay active until test teardown so later get_section calls observe
    the same environment as load did.
    """
    stacks = []

    def _load(toml_content: str) -> DotManConfig:
        stack = ExitStack()
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir(exist_ok=True)
        (repo_dir / "dot-man.toml").write_text(toml_content)
        stack.enter_context(
            patch("dot_man.constants.GLOBAL_TOML", tmp_path / "global.toml")
        )
        stack.enter_context(patch("dot_man.constants.REPO_DIR", repo_dir))
        gc = GlobalConfig()
        gc.create_default()
        gc.load()
        dc = DotManConfig(repo_path=repo_dir, global_config=gc)
        dc.load()
        stacks.append(stack)
        return dc

    yield _load
    for stack in stacks:
        stack.close()


class TestDotManConfig:
    def test_get_section_names(self, dotman_cfg):
        names = dotman_cfg.get_section_names()
        assert "myconfig" in names
        assert "shell" in names
        assert "templates" not in names

    def test_get_section(self, dotman_cfg):
        s = dotman_cfg.get_section("myconfig")
        assert s.name == "myconfig"
        assert len(s.paths) == 1

    def test_get_section_with_overrides(self, dotman_cfg):
        s = dotman_cfg.get_section("shell")
        assert s.secrets_filter is False
        assert s.post_deploy == HOOK_ALIASES["shell_reload"]
        assert len(s.paths) == 2

    def test_get_section_nonexistent(self, dotman_cfg):
        with pytest.raises(ConfigurationError):
            dotman_cfg.get_section("nope")

    def test_repo_path_property(self, dotman_cfg):
        assert dotman_cfg.repo_path.exists()

    def test_get_local_templates(self, dotman_cfg):
        templates = dotman_cfg.get_local_templates()
        assert "base" in templates

    def test_save_and_reload(self, dotman_cfg):
        """A section injected into _data and saved must be readable via get_section."""
        dotman_cfg._data["newsection"] = {"paths": ["/tmp/new"]}
        dotman_cfg._dirty = True
        dotman_cfg.save(force=True)

        dc2 = DotManConfig(
            repo_path=dotman_cfg.repo_path,
            global_config=dotman_cfg._global_config,
        )
        dc2.load()
        assert "newsection" in dc2.get_section_names()
        saved = dc2.get_section("newsection")
        assert saved.name == "newsection"
        assert saved.paths == [Path("/tmp/new")]

    def test_validate_schema_warns(self, load_from_toml, caplog, capsys):
        """Unknown keys warn on the console AND in the log, without aborting.

        Logging alone hid them — nothing shows the logfile during normal
        runs — so a typo'd key went unnoticed and its setting silently
        never applied. The console warning makes the typo visible.
        """
        dc = load_from_toml('[bad]\npaths = ["/tmp/f"]\nunknown_key = "oops"\n')
        assert "Unknown key 'unknown_key'" in caplog.text
        # The console warning is a diagnostic, so it goes to stderr.
        assert "Unknown key 'unknown_key'" in capsys.readouterr().err
        s = dc.get_section("bad")
        assert s.paths == [Path("/tmp/f")]

    def test_invalid_update_strategy(self, load_from_toml):
        """An invalid update_strategy must raise on section materialization."""
        dc = load_from_toml('[bad]\npaths = ["/tmp/f"]\nupdate_strategy = "invalid"\n')
        with pytest.raises(ConfigValidationError):
            dc.get_section("bad")

    def test_section_no_paths_raises(self, load_from_toml):
        """A section without paths must raise on section materialization."""
        dc = load_from_toml("[empty]\n")
        with pytest.raises(ConfigValidationError):
            dc.get_section("empty")

    def test_paths_as_string_rejected(self, load_from_toml):
        """paths written as a bare string is a schema error, not coercion.

        Silently wrapping ``paths = "~/a ~/b"`` into one Path hides a typo
        behind a confusing "file not found" later; reject it with the same
        ConfigValidationError the other schema violations raise.
        """
        dc = load_from_toml('[strpaths]\npaths = "/tmp/f"\n')
        with pytest.raises(ConfigValidationError, match=r"\[strpaths\].*paths"):
            dc.get_section("strpaths")

    def test_inheritance(self, dotman_cfg):
        """Test that inherits applies template settings."""
        # Add a section that inherits from 'base' template
        dotman_cfg._data["child"] = {
            "paths": ["/tmp/child"],
            "inherits": ["base"],
        }
        s = dotman_cfg.get_section("child")
        assert s.update_strategy == "rename_old"  # From template

    def test_inheritance_propagates_multiple_template_fields(self, load_from_toml):
        """A template setting several fields must propagate them all to the child."""
        dc = load_from_toml("""
[templates.base]
update_strategy = "rename_old"
secrets_filter = false

[child]
paths = ["/tmp/child"]
inherits = ["base"]
""")
        s = dc.get_section("child")
        assert s.update_strategy == "rename_old"
        assert s.secrets_filter is False

    def test_get_section_honors_explicit_repo_path(self, load_from_toml):
        """repo_path in TOML is the single-file form; get_repo_path must use it."""
        dc = load_from_toml(
            '[single]\npaths = ["/home/u/.bashrc"]\nrepo_path = "bash/dotfiles/bashrc"\n'
        )
        s = dc.get_section("single")
        assert s.repo_path == "bash/dotfiles/bashrc"
        assert s.get_repo_path(Path("/home/u/.bashrc"), dc.repo_path) == (
            dc.repo_path / "bash/dotfiles/bashrc"
        )

    def test_create_default(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        global_toml = tmp_path / "global.toml"
        with (
            patch("dot_man.constants.GLOBAL_TOML", global_toml),
            patch("dot_man.constants.REPO_DIR", repo_dir),
        ):
            gc = GlobalConfig()
            gc.create_default()
            gc.load()
            dc = DotManConfig(repo_path=repo_dir, global_config=gc)
            dc.create_default()
            assert (repo_dir / "dot-man.toml").exists()

    def test_load_missing_raises(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with patch("dot_man.constants.REPO_DIR", repo_dir):
            dc = DotManConfig(repo_path=repo_dir)
            with pytest.raises(ConfigurationError):
                dc.load()


class TestDotManConfigModulePath:
    """dot_man.dotman_config.DotManConfig uses the positional repo_dir signature.

    This import path is the module the rest of the codebase reads its config
    from; its constructor differs from dot_man.config's keyword form and must
    stay covered independently.
    """

    def test_positional_constructor_and_load(self, tmp_path):
        """Positional repo_dir construction must load sections into the public API."""
        from dot_man.dotman_config import DotManConfig as ModuleDotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        (repo_dir / "dot-man.toml").write_text(
            '[test_section]\npaths = ["/home/test"]\nrepo_base = "test"\n'
            'update_strategy = "replace"\n'
        )

        config = ModuleDotManConfig(repo_dir)
        config.load()

        assert config.get_section_names() == ["test_section"]
        s = config.get_section("test_section")
        assert s.name == "test_section"
        assert s.paths == [Path("/home/test")]
        assert s.repo_base == "test"
        assert s.update_strategy == "replace"

    def test_load_missing_raises(self, tmp_path):
        """Missing toml on the positional form must raise ConfigurationError."""
        from dot_man.dotman_config import DotManConfig as ModuleDotManConfig

        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        with (
            patch("dot_man.constants.GLOBAL_TOML", tmp_path / "global.toml"),
            patch("dot_man.constants.REPO_DIR", repo_dir),
        ):
            config = ModuleDotManConfig(repo_dir)
            with pytest.raises(ConfigurationError):
                config.load()
