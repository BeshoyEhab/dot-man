"""Tests for ConfigDetector's detection and quickshell helpers.

These exercise the real filesystem so the "path exists" gates and the
hidden/non-directory skips are covered deterministically.
"""


class TestDetectPopularConfigs:
    """``detect_popular_configs`` honours missing paths and real files."""

    def test_skips_entries_with_no_paths(self, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        monkeypatch.setattr(ConfigDetector, "EXTENDED_CONFIGS", {})
        monkeypatch.setattr(
            ConfigDetector,
            "POPULAR_CONFIGS",
            {
                "nowhere": {
                    "display_name": "Nowhere",
                    "section_name": "nowhere",
                    "paths": None,
                    "default_hook": None,
                }
            },
        )

        assert ConfigDetector.detect_popular_configs(include_extended=False) == []

    def test_detects_existing_paths_and_stops_at_first(self, tmp_path, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        target = tmp_path / "mytool"
        target.mkdir()
        also = tmp_path / "also-missing"

        monkeypatch.setattr(ConfigDetector, "EXTENDED_CONFIGS", {})
        monkeypatch.setattr(
            ConfigDetector,
            "POPULAR_CONFIGS",
            {
                "mytool": {
                    "display_name": "My Tool",
                    "section_name": "mytool",
                    "paths": [str(also), str(target), str(target)],
                    "default_hook": "mytool_reload",
                },
                "nohook": {
                    "display_name": "No Hook",
                    "section_name": "nohook",
                    "paths": [str(target)],
                    "default_hook": None,
                },
            },
        )

        detected = ConfigDetector.detect_popular_configs(include_extended=False)

        by_name = {entry["name"]: entry for entry in detected}
        assert set(by_name) == {"mytool", "nohook"}
        assert by_name["mytool"]["paths"] == [str(target)]
        assert by_name["mytool"]["default_hook"] == "mytool_reload"
        assert by_name["nohook"]["default_hook"] is None
        assert by_name["nohook"]["reload_cmd"] is None


class TestDetectQuickshellConfigs:
    """``detect_quickshell_configs`` walks real directories."""

    def test_skips_hidden_and_non_directory_entries(self, tmp_path, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        base = tmp_path / "quickshell"
        base.mkdir()
        (base / "ii").mkdir()
        (base / ".cache").mkdir()
        (base / "stray-file").write_text("not a config")

        monkeypatch.setattr(ConfigDetector, "QUICKSHELL_BASE_PATHS", [str(base)])

        detected = ConfigDetector.detect_quickshell_configs()

        assert [entry["name"] for entry in detected] == ["ii"]
        assert detected[0]["section_name"] == "qs-ii"
        assert detected[0]["paths"] == ["~/.config/quickshell/ii"]

    def test_missing_base_path_is_ignored(self, tmp_path, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        monkeypatch.setattr(
            ConfigDetector,
            "QUICKSHELL_BASE_PATHS",
            [str(tmp_path / "does-not-exist")],
        )

        assert ConfigDetector.detect_quickshell_configs() == []


class TestDetectAll:
    """``detect_all`` concatenates popular and quickshell results."""

    def test_combines_both_sources(self, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        monkeypatch.setattr(
            ConfigDetector,
            "detect_popular_configs",
            classmethod(lambda cls, include_extended=True: [{"name": "popular"}]),
        )
        monkeypatch.setattr(
            ConfigDetector,
            "detect_quickshell_configs",
            classmethod(lambda cls: [{"name": "quickshell"}]),
        )

        assert ConfigDetector.detect_all() == [
            {"name": "popular"},
            {"name": "quickshell"},
        ]


class TestQuickshellReloadCommand:
    """``build_quickshell_reload_cmd`` names the right instance."""

    def test_builds_reload_command(self, tmp_path, monkeypatch):
        from dot_man.config_detector import ConfigDetector

        base = tmp_path / "quickshell"
        (base / "ii").mkdir(parents=True)
        monkeypatch.setattr(ConfigDetector, "QUICKSHELL_BASE_PATHS", [str(base)])

        command = ConfigDetector.build_quickshell_reload_cmd(base / "ii")

        assert "killall qs" in command
        assert "qs -c ii" in command
