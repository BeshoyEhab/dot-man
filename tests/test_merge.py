"""Tests for the config-name to reload-hook resolver."""

from dot_man.constants import HOOK_ALIASES
from dot_man.hook_engine import get_hook_for_config


class TestGetHookForConfig:
    """Tests for the get_hook_for_config resolver."""

    def test_nvim(self):
        hook = get_hook_for_config("nvim")
        assert hook == HOOK_ALIASES["nvim_sync"]

    def test_hyprland(self):
        assert get_hook_for_config("hyprland") == HOOK_ALIASES["hyprland_reload"]

    def test_hypr_is_alias_for_hyprland(self):
        assert get_hook_for_config("hypr") == HOOK_ALIASES["hyprland_reload"]

    def test_shell_configs(self):
        assert get_hook_for_config("zshrc") == HOOK_ALIASES["zsh_reload"]
        assert get_hook_for_config("bashrc") == HOOK_ALIASES["bash_reload"]

    def test_substring_match(self):
        assert (
            get_hook_for_config("~/.config/kitty/kitty.conf")
            == HOOK_ALIASES["kitty_reload"]
        )

    def test_quickshell_has_no_universal_hook(self):
        assert get_hook_for_config("quickshell") is None

    def test_unknown_returns_none(self):
        assert get_hook_for_config("unknown_config_xyz") is None
