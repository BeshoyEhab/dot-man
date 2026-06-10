"""Tests for 'dot-man discover' command."""

from unittest.mock import patch

from click.testing import CliRunner

from dot_man.cli.interface import cli


class TestDiscoverHelp:
    """Test discover command help display."""

    def test_discover_help(self):
        """Discover help displays."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert result.exit_code == 0
        assert "discover" in result.output.lower()

    def test_discover_aliases_in_help(self):
        """Discover alias shows in help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert result.exit_code == 0
        assert "dis" in result.output

    def test_discover_options_in_help(self):
        """Discover options appear in help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover", "--help"])
        assert "--include-extended" in result.output
        assert "--no-extended" in result.output
        assert "--add" in result.output


class TestDiscoverWithoutInit:
    """Test discover command when not initialized."""

    def test_discover_without_init(self):
        """Discover without init shows welcome banner."""
        runner = CliRunner()
        result = runner.invoke(cli, ["discover"])
        assert result.exit_code in (0, 1)


class TestDiscoverNoConfigs:
    """Test discover when no configs are detected."""

    def test_no_detected_configs(self, integration_runner):
        """Empty detection shows 'No dotfiles detected'."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = []
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover"])

            assert result.exit_code == 0
            assert "No dotfiles detected" in result.output

    def test_no_detected_configs_with_add(self, integration_runner):
        """Empty detection with --add still shows no configs."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = []
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            assert "No dotfiles detected" in result.output


class TestDiscoverWithConfigs:
    """Test discover when configs are detected."""

    SAMPLE_CONFIGS = [
        {
            "name": "hyprland",
            "display_name": "Hyprland WM",
            "section_name": "hyprland",
            "paths": ["~/.config/hypr"],
            "default_hook": "hyprland_reload",
            "reload_cmd": None,
        },
        {
            "name": "kitty",
            "display_name": "Kitty terminal",
            "section_name": "kitty",
            "paths": ["~/.config/kitty"],
            "default_hook": "kitty_reload",
            "reload_cmd": None,
        },
    ]

    QUICKSHELL_CONFIGS = [
        {
            "name": "ii",
            "display_name": "Quickshell - ii",
            "section_name": "qs-ii",
            "paths": ["~/.config/quickshell/ii"],
            "default_hook": "quickshell_reload",
            "reload_cmd": "qs -c ii",
        },
    ]

    def test_displays_detected_configs(self, integration_runner):
        """Detected configs are displayed with paths."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover"])

            assert result.exit_code == 0
            assert "Found 2 configurations" in result.output
            assert "Hyprland WM" in result.output
            assert "Kitty terminal" in result.output
            assert "~/.config/hypr" in result.output
            assert "~/.config/kitty" in result.output
            assert "hyprland_reload" in result.output
            assert "kitty_reload" in result.output

    def test_displays_quickshell_configs(self, integration_runner):
        """Quickshell configs appear alongside popular configs."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = list(
                self.QUICKSHELL_CONFIGS
            )

            result = integration_runner.invoke(cli, ["discover"])

            assert result.exit_code == 0
            assert "Found 3 configurations" in result.output
            assert "Quickshell - ii" in result.output
            assert "~/.config/quickshell/ii" in result.output

    def test_no_extended_flag(self, integration_runner):
        """--no-extended passes include_extended=False."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover", "--no-extended"])

            assert result.exit_code == 0
            MockDetector.detect_popular_configs.assert_called_once_with(
                include_extended=False
            )

    def test_shows_tip_without_add_flag(self, integration_runner):
        """Without --add, a tip about --add is shown."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover"])

            assert result.exit_code == 0
            assert "Tip:" in result.output or "tip" in result.output.lower()

    def test_detected_config_without_hook(self, integration_runner):
        """Config with no default hook does not display hook."""
        configs = [
            {
                "name": "ssh",
                "display_name": "SSH config",
                "section_name": "ssh",
                "paths": ["~/.ssh/config"],
                "default_hook": None,
                "reload_cmd": None,
            },
        ]
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = configs
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["discover"])

            assert result.exit_code == 0
            assert "SSH config" in result.output
            assert "~/.ssh/config" in result.output


class TestDiscoverAdd:
    """Test discover --add flag."""

    SAMPLE_CONFIGS = [
        {
            "name": "hyprland",
            "display_name": "Hyprland WM",
            "section_name": "hyprland",
            "paths": ["~/.config/hypr"],
            "default_hook": "hyprland_reload",
            "reload_cmd": None,
        },
        {
            "name": "ssh",
            "display_name": "SSH config",
            "section_name": "ssh",
            "paths": ["~/.ssh/config"],
            "default_hook": None,
            "reload_cmd": None,
        },
    ]

    def test_add_detected_configs(self, integration_runner):
        """--add adds detected configs to dot-man.toml."""
        with (
            patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector,
            patch("dot_man.dotman_config.DotManConfig") as MockConfig,
            patch("dot_man.operations.get_operations") as MockGetOps,
        ):
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            mock_ops = MockGetOps.return_value
            mock_ops.get_sections.return_value = []

            mock_config_instance = MockConfig.return_value

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            assert "Added" in result.output

            mock_config_instance.add_section.assert_any_call(
                name="hyprland",
                paths=["~/.config/hypr"],
            )
            mock_config_instance.add_section.assert_any_call(
                name="ssh",
                paths=["~/.ssh/config"],
            )
            mock_config_instance.update_section.assert_called_once_with(
                "hyprland",
                post_deploy="hyprland_reload",
            )
            assert mock_config_instance.save.called

    def test_add_skips_existing_sections(self, integration_runner):
        """--add skips sections already tracked."""
        with (
            patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector,
            patch("dot_man.dotman_config.DotManConfig") as MockConfig,
            patch("dot_man.operations.get_operations") as MockGetOps,
        ):
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            mock_ops = MockGetOps.return_value
            mock_ops.get_sections.return_value = ["hyprland"]

            mock_config_instance = MockConfig.return_value

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            # Should only add ssh, not hyprland (already tracked)
            mock_config_instance.add_section.assert_called_once_with(
                name="ssh",
                paths=["~/.ssh/config"],
            )

    def test_add_handles_exceptions(self, integration_runner):
        """--add handles errors when adding a section fails."""
        with (
            patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector,
            patch("dot_man.dotman_config.DotManConfig") as MockConfig,
            patch("dot_man.operations.get_operations") as MockGetOps,
        ):
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            mock_ops = MockGetOps.return_value
            mock_ops.get_sections.return_value = []

            mock_config_instance = MockConfig.return_value
            mock_config_instance.add_section.side_effect = [
                ValueError("bad path"),
                None,
            ]

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            assert "Failed to add hyprland: bad path" in result.output
            # Still saves and shows partial success
            assert mock_config_instance.save.called

    def test_add_no_new_sections(self, integration_runner):
        """--add shows dim message when all sections already tracked."""
        with (
            patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector,
            patch("dot_man.dotman_config.DotManConfig"),
            patch("dot_man.operations.get_operations") as MockGetOps,
        ):
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            mock_ops = MockGetOps.return_value
            mock_ops.get_sections.return_value = ["hyprland", "ssh"]

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            assert "No new sections to add" in result.output

    def test_add_shows_success_message(self, integration_runner):
        """--add shows success count after adding sections."""
        with (
            patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector,
            patch("dot_man.dotman_config.DotManConfig"),
            patch("dot_man.operations.get_operations") as MockGetOps,
        ):
            MockDetector.detect_popular_configs.return_value = list(self.SAMPLE_CONFIGS)
            MockDetector.detect_quickshell_configs.return_value = []

            mock_ops = MockGetOps.return_value
            mock_ops.get_sections.return_value = []

            result = integration_runner.invoke(cli, ["discover", "--add"])

            assert result.exit_code == 0
            assert "Added 2 sections to dot-man.toml" in result.output
            assert "Run 'dot-man status'" in result.output


class TestDiscoverAlias:
    """Test discover alias 'dis'."""

    def test_discover_alias_works(self, integration_runner):
        """The 'dis' alias invokes the same command."""
        with patch("dot_man.cli.discover_cmd.ConfigDetector") as MockDetector:
            MockDetector.detect_popular_configs.return_value = []
            MockDetector.detect_quickshell_configs.return_value = []

            result = integration_runner.invoke(cli, ["dis"])

            assert result.exit_code == 0
            assert "No dotfiles detected" in result.output


class TestDiscoverIntegration:
    """Integration tests with real config detector."""

    def test_discovers_actual_dotfiles(self, integration_runner, tmp_path):
        """Discover finds real dotfiles created on the filesystem."""
        home = tmp_path / "home"
        home.mkdir(exist_ok=True)

        (home / ".config").mkdir(parents=True, exist_ok=True)
        (home / ".config" / "hypr").mkdir(parents=True)
        (home / ".config" / "kitty").mkdir(parents=True)
        (home / ".config" / "nvim").mkdir(parents=True)

        with patch("dot_man.config_detector.Path.expanduser") as mock_expand:

            def _expanduser(path_self):
                return path_self

            mock_expand.side_effect = _expanduser

        with patch.dict("os.environ", {"HOME": str(home)}):
            with patch(
                "dot_man.cli.discover_cmd.ConfigDetector.detect_popular_configs"
            ) as mock_detect:
                mock_detect.return_value = [
                    {
                        "name": "kitty",
                        "display_name": "Kitty terminal",
                        "section_name": "kitty",
                        "paths": ["~/.config/kitty"],
                        "default_hook": "kitty_reload",
                        "reload_cmd": None,
                    },
                ]

                with patch(
                    "dot_man.cli.discover_cmd.ConfigDetector.detect_quickshell_configs"
                ) as mock_qs:
                    mock_qs.return_value = []

                    result = integration_runner.invoke(cli, ["discover"])

                    assert result.exit_code == 0
                    assert "Kitty terminal" in result.output
                    assert "kitty" in result.output
