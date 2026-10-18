"""Tests for shell completion functions."""

import importlib
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from dot_man import constants
from dot_man.cli.common import _clear_all_caches, _set_git_runner, complete_sections

comp = importlib.import_module("dot_man.cli.completions")


@pytest.fixture(autouse=True)
def _isolated_completion_cache(tmp_path, monkeypatch):
    """Redirect the completion cache file away from the real repo.

    NOTE: patch("dot_man.cli.completions.*") silently targets the
    `completions` command (it shadows the module) — patch `comp` instead.
    """
    monkeypatch.setattr(
        comp, "COMPLETION_CACHE_FILE", tmp_path / "completion_cache.json"
    )
    monkeypatch.setattr(constants, "REPO_DIR", tmp_path)
    _clear_all_caches()
    yield
    _clear_all_caches()


def make_mock_result(stdout="", returncode=0):
    """Create a mock subprocess result."""
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


def make_navigate_runner(
    branches="main\nwork\n",
    head="main\n",
    tags="",
    log="",
    rev_parse_map=None,
):
    """Build a fake git runner dispatching on argv for navigate completions."""
    rev_parse_map = rev_parse_map or {}

    def runner(args, cwd=None, timeout=2):
        if "branch" in args:
            return make_mock_result(branches)
        if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return make_mock_result(head)
        if args == ["git", "tag", "-l"]:
            return make_mock_result(tags)
        if (
            len(args) == 3
            and args[:2] == ["git", "rev-parse"]
            and args[2].endswith("^{commit}")
        ):
            return make_mock_result(rev_parse_map.get(args[2][:-9], "abc1234567890"))
        if "log" in args:
            return make_mock_result(log)
        return make_mock_result("")

    return runner


@pytest.fixture
def clean_completion_state():
    """Reset completions module state before and after each test."""
    comp._clear_all_caches()
    comp._set_git_runner(None)
    comp._template_cache = None
    comp._config_keys_cache = None
    comp._profiles_cache = None
    yield comp
    comp._clear_all_caches()
    comp._set_git_runner(None)
    comp._template_cache = None
    comp._config_keys_cache = None
    comp._profiles_cache = None


class TestCompleteSections:
    """Test complete_sections shell completion function."""

    def _make_config(self, tmp_path, content):
        """Create a dot-man config at the standard location."""
        repo_dir = tmp_path / ".dot-man" / "repo"
        repo_dir.mkdir(parents=True)
        config_file = repo_dir / "dot-man.toml"
        config_file.write_text(content)
        return repo_dir

    def test_complete_sections_returns_all(self, tmp_path):
        """complete_sections should return all section names."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]

[kitty]
paths = ["~/.config/kitty"]
""",
        )

        with patch("dot_man.constants.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert "nvim" in result
            assert "kitty" in result

    def test_complete_sections_filters_by_prefix(self, tmp_path):
        """complete_sections should filter by incomplete prefix."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]

[kitty]
paths = ["~/.config/kitty"]

[neovim]
paths = ["~/.config/neovim"]
""",
        )

        with patch("dot_man.constants.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "ki")
            assert result == ["kitty"]

            result = complete_sections(None, None, "ne")
            assert result == ["neovim"]

    def test_complete_sections_no_match_returns_empty(self, tmp_path):
        """complete_sections should return empty list when no match."""
        repo_dir = self._make_config(
            tmp_path,
            """
[nvim]
paths = ["~/.config/nvim"]
""",
        )

        with patch("dot_man.constants.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "z")
            assert result == []

    def test_complete_sections_empty_config(self, tmp_path):
        """complete_sections should return empty list when no sections."""
        repo_dir = self._make_config(tmp_path, "")

        with patch("dot_man.constants.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert result == []

    def test_complete_sections_missing_config(self, tmp_path):
        """complete_sections should return empty list when config missing."""
        repo_dir = tmp_path / ".dot-man" / "repo"
        repo_dir.mkdir(parents=True)

        with patch("dot_man.constants.REPO_DIR", repo_dir):
            _clear_all_caches()
            result = complete_sections(None, None, "")
            assert result == []


class TestCompleteCommits:
    """Test complete_commits shell completion on rollback target."""

    def test_complete_commits_returns_list(self):
        """complete_commits should return commit SHAs."""
        from dot_man.cli.common import complete_commits

        def mock_runner(args, cwd=None, timeout=2):
            return make_mock_result("abc1234\ndef5678\n")

        _set_git_runner(mock_runner)
        result = complete_commits(None, None, "")
        assert "abc1234" in result
        assert "def5678" in result
        _set_git_runner(None)

    def test_complete_commits_filters(self):
        """complete_commits should filter by prefix."""
        from dot_man.cli.common import complete_commits

        def mock_runner(args, cwd=None, timeout=2):
            return make_mock_result("abc1234\ndef5678\n")

        _set_git_runner(mock_runner)
        result = complete_commits(None, None, "abc")
        assert result == ["abc1234"]

        result = complete_commits(None, None, "xyz")
        assert result == []
        _set_git_runner(None)


class TestRunGit:
    """Test _run_git dispatches to subprocess when no runner is set."""

    def test_real_subprocess_git_version(self, tmp_path, clean_completion_state):
        """_run_git should run real git when no custom runner is set."""
        result = comp._run_git(["git", "--version"], cwd=tmp_path, timeout=5)
        assert result.returncode == 0
        assert "git version" in result.stdout

    def test_custom_runner_used(self, tmp_path, clean_completion_state):
        """_run_git should delegate to the custom runner when set."""
        seen = {}

        def runner(args, cwd=None, timeout=2):
            seen["args"] = args
            return make_mock_result("custom\n")

        comp._set_git_runner(runner)
        result = comp._run_git(["git", "branch"], cwd=tmp_path)
        assert result.stdout == "custom\n"
        assert seen["args"] == ["git", "branch"]


class TestCompletionFileCache:
    """Test file-backed completion cache load/save/clear paths."""

    def test_missing_repo_dir_returns_empty(self, tmp_path, clean_completion_state):
        """_get_completion_cache should return {} when REPO_DIR is absent."""
        with patch.object(constants, "REPO_DIR", tmp_path / "nope"):
            assert comp._get_completion_cache() == {}

    def test_loads_fresh_cache_file(self, tmp_path, clean_completion_state):
        """_get_completion_cache should load a fresh cache file from disk."""
        cache_file = tmp_path / "completion_cache.json"
        cache_file.write_text('{"branches": ["cached-branch"]}')
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            assert comp._get_completion_cache() == {"branches": ["cached-branch"]}

    def test_corrupt_cache_file_returns_empty(self, tmp_path, clean_completion_state):
        """_get_completion_cache should return {} for unparseable cache files."""
        cache_file = tmp_path / "completion_cache.json"
        cache_file.write_text("not json{{{")
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            assert comp._get_completion_cache() == {}

    def test_memory_cache_returned_when_fresh(self, tmp_path, clean_completion_state):
        """_get_completion_cache should prefer fresh in-memory data."""
        cache_file = tmp_path / "completion_cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._save_completion_cache({"branches": ["mem"]})
            assert comp._get_completion_cache() == {"branches": ["mem"]}

    def test_save_skips_write_when_repo_missing(self, tmp_path, clean_completion_state):
        """_save_completion_cache should keep memory cache without repo dir."""
        with patch.object(constants, "REPO_DIR", tmp_path / "nope"):
            comp._save_completion_cache({"a": 1})
            assert comp._memory_cache == {"a": 1}

    def test_save_failure_keeps_memory_cache(self, tmp_path, clean_completion_state):
        """_save_completion_cache should swallow filesystem errors."""
        blocker = tmp_path / "blocker"
        blocker.write_text("x")
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(
                comp,
                "COMPLETION_CACHE_FILE",
                blocker / "cache.json",
            ),
        ):
            comp._save_completion_cache({"a": 2})
            assert comp._memory_cache == {"a": 2}

    def test_clear_cache_unlink_failure(self, clean_completion_state):
        """_clear_completion_cache should survive unlink errors."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.unlink.side_effect = OSError("nope")
        with patch.object(comp, "COMPLETION_CACHE_FILE", mock_file):
            comp._clear_completion_cache()
            assert comp._memory_cache is None

    def test_clear_all_caches_unlink_failure(self, clean_completion_state):
        """_clear_all_caches should survive unlink errors."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.unlink.side_effect = OSError("nope")
        with patch.object(comp, "COMPLETION_CACHE_FILE", mock_file):
            comp._clear_all_caches()
            assert comp._memory_cache is None
            assert comp._template_cache is None


class TestCompleteSwitchArgs:
    """Test complete_switch_args success and failure paths."""

    def test_success_returns_navigate_items(self, clean_completion_state):
        """complete_switch_args should return branch completion items."""
        comp._set_git_runner(make_navigate_runner())
        items = comp.complete_switch_args(None, None, "")
        assert [i.value for i in items] == ["main", "work"]

    def test_error_returns_empty(self, clean_completion_state):
        """complete_switch_args should return [] when completion explodes."""
        with patch.object(
            comp,
            "_complete_navigate_items",
            side_effect=RuntimeError("boom"),
        ):
            assert comp.complete_switch_args(None, None, "") == []


class TestCompleteNavigateItems:
    """Test _complete_navigate_items branch/tag/commit/@ coverage."""

    def test_marks_current_branch(self, tmp_path, clean_completion_state):
        """Current branch should carry the 'current branch' help text."""
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(make_navigate_runner())
            items = comp._complete_navigate_items("")
        by_value = {i.value: i.help for i in items}
        assert by_value["main"] == "current branch"
        assert by_value["work"] == "branch"

    def test_uses_cached_branches_tags_commits(self, tmp_path, clean_completion_state):
        """Cached branches/tags/commits should avoid all git calls."""

        def exploding_runner(args, cwd=None, timeout=2):
            if (
                len(args) == 3
                and args[:2] == ["git", "rev-parse"]
                and args[2].endswith("^{commit}")
            ):
                return make_mock_result("abc1234567890")
            raise AssertionError(f"git should not be called: {args}")

        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._save_completion_cache(
                {
                    "branches": ["main", "work"],
                    "current_branch": "main",
                    "tags": ["v1.0"],
                    "commits": [{"sha": "abc1234", "message": "hello world"}],
                }
            )
            comp._set_git_runner(exploding_runner)
            items = comp._complete_navigate_items("")
        assert sorted(i.value for i in items) == [
            "abc1234",
            "main",
            "v1.0",
            "work",
        ]

    def test_tag_help_includes_short_hash(self, tmp_path, clean_completion_state):
        """Tag items should show the short commit hash in help."""
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(
                make_navigate_runner(
                    tags="v1.0\n", rev_parse_map={"v1.0": "deadbeef1234"}
                )
            )
            items = comp._complete_navigate_items("")
        tag_items = [i for i in items if i.value == "v1.0"]
        assert len(tag_items) == 1
        assert tag_items[0].help == "tag → deadbee"

    def test_tag_rev_parse_failure_has_empty_hash(
        self, tmp_path, clean_completion_state
    ):
        """Tag items should tolerate rev-parse failures with empty hash."""

        def runner(args, cwd=None, timeout=2):
            if "branch" in args:
                return make_mock_result("main\n")
            if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return make_mock_result("main\n")
            if args == ["git", "tag", "-l"]:
                return make_mock_result("v9.9\n")
            if args[:2] == ["git", "rev-parse"]:
                return make_mock_result("", returncode=1)
            return make_mock_result("")

        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(runner)
            items = comp._complete_navigate_items("")
        tag_items = [i for i in items if i.value == "v9.9"]
        assert len(tag_items) == 1
        assert tag_items[0].help == "tag → "

    def test_commit_items_filtered_by_prefix(self, tmp_path, clean_completion_state):
        """Commit SHAs should filter on the incomplete prefix."""
        log = "abc1234def5678 Fix the thing that was broken\n"
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(make_navigate_runner(log=log))
            items = comp._complete_navigate_items("abc")
        commit_items = [i for i in items if i.value == "abc1234"]
        assert len(commit_items) == 1
        assert "Fix the thing" in (commit_items[0].help or "")

    def test_commit_log_skips_malformed_lines(self, tmp_path, clean_completion_state):
        """Malformed log lines without a message should be skipped."""
        log = "lonelytoken\nabc1234def5678 Real message here\n"
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(make_navigate_runner(log=log))
            items = comp._complete_navigate_items("")
        assert [i.value for i in items if len(i.value) == 7] == ["abc1234"]

    def test_branch_at_tag_completion(self, tmp_path, clean_completion_state):
        """branch@tag inputs should complete tags scoped to that branch."""
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._set_git_runner(
                make_navigate_runner(
                    tags="v1.0\nv2.0\n",
                    rev_parse_map={"v1.0": "1111111aaa", "v2.0": "2222222bbb"},
                )
            )
            items = comp._complete_navigate_items("main@v")
        scoped = sorted(i.value for i in items if i.value.startswith("main@"))
        assert scoped == ["main@v1.0", "main@v2.0"]
        assert all(i.help.startswith("tag at ") for i in items if "@" in i.value)

    def test_outer_exception_returns_empty(self, clean_completion_state):
        """_complete_navigate_items should return [] when cache explodes."""
        with patch.object(
            comp,
            "_get_completion_cache",
            side_effect=RuntimeError("boom"),
        ):
            assert comp._complete_navigate_items("") == []


class TestCompleteTagsCommitsErrors:
    """Test cached and error paths for tag/commit completions."""

    def test_complete_tags_uses_cache(self, tmp_path, clean_completion_state):
        """complete_tags should serve cached tags without git."""
        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._save_completion_cache({"tags": ["v1.0", "v2.0"]})

            def exploding_runner(args, cwd=None, timeout=2):
                raise AssertionError("git should not be called")

            comp._set_git_runner(exploding_runner)
            assert comp.complete_tags(None, None, "v") == ["v1.0", "v2.0"]
            assert comp.complete_tags(None, None, "v1") == ["v1.0"]

    def test_complete_tags_error_returns_empty(self, clean_completion_state):
        """complete_tags should return [] when cache explodes."""
        with patch.object(
            comp,
            "_get_completion_cache",
            side_effect=RuntimeError("boom"),
        ):
            assert comp.complete_tags(None, None, "") == []

    def test_complete_branches_error_returns_empty(self, clean_completion_state):
        """complete_branches should return [] when git explodes."""
        comp._set_git_runner(make_navigate_runner())
        first = comp.complete_branches(None, None, "")
        assert first == ["main", "work"]
        with patch.object(
            comp,
            "_get_completion_cache",
            side_effect=RuntimeError("boom"),
        ):
            assert comp.complete_branches(None, None, "") == []

    def test_complete_commits_uses_cache(self, tmp_path, clean_completion_state):
        """complete_commits should serve cached SHAs without git."""
        from dot_man.cli.common import complete_commits

        cache_file = tmp_path / "cache.json"
        with (
            patch.object(constants, "REPO_DIR", tmp_path),
            patch.object(comp, "COMPLETION_CACHE_FILE", cache_file),
        ):
            comp._save_completion_cache({"commits_all": ["abc1234", "def5678"]})

            def exploding_runner(args, cwd=None, timeout=2):
                raise AssertionError("git should not be called")

            comp._set_git_runner(exploding_runner)
            assert complete_commits(None, None, "") == ["abc1234", "def5678"]
            assert complete_commits(None, None, "def") == ["def5678"]

    def test_complete_commits_error_returns_empty(self, clean_completion_state):
        """complete_commits should return [] when cache explodes."""
        from dot_man.cli.common import complete_commits

        with patch.object(
            comp,
            "_get_completion_cache",
            side_effect=RuntimeError("boom"),
        ):
            assert complete_commits(None, None, "") == []


class TestCompleteTemplateKeys:
    """Test template key completion cache and GlobalConfig paths."""

    def test_cache_hit_filters(self, clean_completion_state):
        """Cached template keys should filter on the incomplete prefix."""
        comp._template_cache = ["alpha", "beta"]
        assert comp.complete_template_keys(None, None, "a") == ["alpha"]
        assert comp.complete_template_keys(None, None, "") == ["alpha", "beta"]

    def test_loads_from_global_config(self, clean_completion_state):
        """Template keys should load from GlobalConfig on cache miss."""
        assert comp._template_cache is None
        mock_gc = MagicMock()
        mock_gc.get_all_templates.return_value = {"mykey": {}, "other": {}}
        with patch("dot_man.global_config.GlobalConfig", return_value=mock_gc):
            assert comp.complete_template_keys(None, None, "my") == ["mykey"]
            assert comp._template_cache == ["mykey", "other"]

    def test_error_returns_empty(self, clean_completion_state):
        """Template keys should return [] when GlobalConfig explodes."""
        assert comp._template_cache is None
        with patch(
            "dot_man.global_config.GlobalConfig", side_effect=RuntimeError("boom")
        ):
            assert comp.complete_template_keys(None, None, "") == []


class TestCompleteConfigKeys:
    """Test config key completion cache and static key list."""

    def test_cache_hit_filters(self, clean_completion_state):
        """Cached config keys should filter on the incomplete prefix."""
        comp._config_keys_cache = ["dot-man.current_branch", "remote.url"]
        assert comp.complete_config_keys(None, None, "remote") == ["remote.url"]

    def test_static_keys_filtered(self, clean_completion_state):
        """Config keys should return the static key list on cache miss."""
        assert comp._config_keys_cache is None
        all_keys = comp.complete_config_keys(None, None, "")
        assert all_keys == [
            "dot-man.current_branch",
            "remote.url",
            "security.strict_mode",
            "switch.default_behavior",
            "secrets_filter_enabled",
        ]
        assert comp.complete_config_keys(None, None, "security") == [
            "security.strict_mode"
        ]


class TestCompleteProfiles:
    """Test profile completion cache and GlobalConfig paths."""

    def test_cache_hit_filters(self, clean_completion_state):
        """Cached profiles should filter on the incomplete prefix."""
        comp._profiles_cache = ["laptop", "work"]
        assert comp.complete_profiles(None, None, "lap") == ["laptop"]

    def test_loads_from_global_config(self, clean_completion_state):
        """Profiles should load from GlobalConfig data on cache miss."""
        assert comp._profiles_cache is None
        mock_gc = MagicMock()
        mock_gc._data = {"profiles": {"laptop": {}, "work": {}}}
        with patch("dot_man.global_config.GlobalConfig", return_value=mock_gc):
            assert comp.complete_profiles(None, None, "") == ["laptop", "work"]
            assert comp.complete_profiles(None, None, "wo") == ["work"]

    def test_error_returns_empty(self, clean_completion_state):
        """Profiles should return [] when GlobalConfig explodes."""
        assert comp._profiles_cache is None
        with patch(
            "dot_man.global_config.GlobalConfig", side_effect=RuntimeError("boom")
        ):
            assert comp.complete_profiles(None, None, "") == []
