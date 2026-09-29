"""Tests for auto-detection coverage: new tools resolve to real reloads."""

HOOK_TOOLS = {
    "foot": ".config/foot",
    "bspwm": ".config/bspwm",
    "qtile": ".config/qtile",
    "eww": ".config/eww",
    "mako": ".config/mako",
}

DETECT_ONLY_TOOLS = {
    "helix": ".config/helix",
    "zed": ".config/zed",
    "yazi": ".config/yazi",
    "ghostty": ".config/ghostty",
    "river": ".config/river",
    "niri": ".config/niri",
}


class TestHookToolCoverage:
    """Every hookable tool has alias + file mapping + resolver entry."""

    def test_aliases_exist_with_real_commands(self):
        from dot_man.constants import HOOK_ALIASES

        binaries = {
            "foot": "foot",
            "bspwm": "bspc",
            "qtile": "qtile",
            "eww": "eww",
            "mako": "makoctl",
        }
        for tool, binary in binaries.items():
            command = HOOK_ALIASES[f"{tool}_reload"]
            assert binary in command
            assert "|| true" in command

    def test_file_patterns_map_to_aliases(self):
        from dot_man.branch_ops import FILE_TO_HOOK_MAP

        for tool, pattern in HOOK_TOOLS.items():
            assert FILE_TO_HOOK_MAP[pattern] == f"{tool}_reload"

    def test_resolver_covers_tools(self):
        from dot_man.constants import HOOK_ALIASES
        from dot_man.merge import get_hook_for_config

        for tool in HOOK_TOOLS:
            assert get_hook_for_config(tool) == HOOK_ALIASES[f"{tool}_reload"]


class TestPopularConfigsCoverage:
    """Detection database covers the new tools with correct paths."""

    def test_popular_configs_cover_new_tools(self):
        from dot_man.config_detector import ConfigDetector

        expected_paths = {**HOOK_TOOLS, **DETECT_ONLY_TOOLS}
        for tool, path_suffix in expected_paths.items():
            entry = ConfigDetector.POPULAR_CONFIGS[tool]
            assert entry["paths"] == [f"~/{path_suffix}"]
