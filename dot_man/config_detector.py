"""Config detection for popular dotfile configurations.

This module provides auto-detection for popular configuration frameworks
and their associated reload/restart hooks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .merge import get_hook_for_config


class ConfigInfo(TypedDict):
    """Information about a detected config."""

    name: str
    display_name: str
    section_name: str
    paths: list[str]
    default_hook: str | None
    reload_cmd: str | None


ConfigInfoList = list[ConfigInfo]


class ConfigDetector:
    """Detects popular configuration frameworks and their hooks."""

    QUICKSHELL_CONFIGS = [
        ("ii", "Quickshell - ii"),
        ("caelestea", "Quickshell - Caelestea"),
        ("end-4", "Quickshell - End-4"),
        ("illogical-impulse", "Quickshell - Illogical Impulse"),
        ("euphoria", "Quickshell - Euphoria"),
        ("celestial", "Quickshell - Celestial"),
        ("stellar", "Quickshell - Stellar"),
        ("aurora", "Quickshell - Aurora"),
        ("nebula", "Quickshell - Nebula"),
        ("cosmic", "Quickshell - Cosmic"),
        ("prism", "Quickshell - Prism"),
        ("lunar", "Quickshell - Lunar"),
        ("solar", "Quickshell - Solar"),
        ("nova", "Quickshell - Nova"),
        ("zen", "Quickshell - Zen"),
        ("minimal", "Quickshell - Minimal"),
        ("custom", "Quickshell - Custom"),
    ]

    QUICKSHELL_BASE_PATHS = [
        "~/.config/quickshell",
        "~/.config/qs",
    ]

    _PopularConfigEntry = dict[str, str | list[str] | None]

    POPULAR_CONFIGS: dict[str, _PopularConfigEntry] = {
        "hyprland": {
            "display_name": "Hyprland WM",
            "section_name": "hyprland",
            "paths": ["~/.config/hypr"],
            "default_hook": "hyprland_reload",
        },
        "sway": {
            "display_name": "Sway WM",
            "section_name": "sway",
            "paths": ["~/.config/sway"],
            "default_hook": "sway_reload",
        },
        "i3": {
            "display_name": "i3 Window Manager",
            "section_name": "i3",
            "paths": ["~/.config/i3"],
            "default_hook": "i3_reload",
        },
        "awesome": {
            "display_name": "Awesome WM",
            "section_name": "awesome",
            "paths": ["~/.config/awesome"],
            "default_hook": "awesome_restart",
        },
        "kitty": {
            "display_name": "Kitty terminal",
            "section_name": "kitty",
            "paths": ["~/.config/kitty"],
            "default_hook": "kitty_reload",
        },
        "alacritty": {
            "display_name": "Alacritty terminal",
            "section_name": "alacritty",
            "paths": ["~/.config/alacritty"],
            "default_hook": "alacritty_reload",
        },
        "wezterm": {
            "display_name": "WezTerm terminal",
            "section_name": "wezterm",
            "paths": ["~/.config/wezterm"],
            "default_hook": "wezterm_reload",
        },
        "fish": {
            "display_name": "Fish shell",
            "section_name": "fish",
            "paths": ["~/.config/fish"],
            "default_hook": "fish_reload",
        },
        "nvim": {
            "display_name": "Neovim",
            "section_name": "nvim",
            "paths": ["~/.config/nvim"],
            "default_hook": "nvim_sync",
        },
        "vim": {
            "display_name": "Vim",
            "section_name": "vim",
            "paths": ["~/.vimrc", "~/.vim"],
            "default_hook": "vim_reload",
        },
        "emacs": {
            "display_name": "Emacs",
            "section_name": "emacs",
            "paths": ["~/.emacs.d"],
            "default_hook": "emacs_reload",
        },
        "tmux": {
            "display_name": "tmux",
            "section_name": "tmux",
            "paths": ["~/.tmux.conf"],
            "default_hook": "tmux_reload",
        },
        "zsh": {
            "display_name": "Zsh shell",
            "section_name": "zsh",
            "paths": ["~/.zshrc", "~/.zshrc"],
            "default_hook": "shell_reload",
        },
        "bash": {
            "display_name": "Bash shell",
            "section_name": "bashrc",
            "paths": ["~/.bashrc", "~/.bashrc"],
            "default_hook": "shell_reload",
        },
        "polybar": {
            "display_name": "Polybar",
            "section_name": "polybar",
            "paths": ["~/.config/polybar"],
            "default_hook": "polybar_reload",
        },
        "waybar": {
            "display_name": "Waybar",
            "section_name": "waybar",
            "paths": ["~/.config/waybar"],
            "default_hook": "waybar_reload",
        },
        "dunst": {
            "display_name": "Dunst notification daemon",
            "section_name": "dunst",
            "paths": ["~/.config/dunst"],
            "default_hook": "dunst_reload",
        },
        "picom": {
            "display_name": "Picom compositor",
            "section_name": "picom",
            "paths": ["~/.config/picom"],
            "default_hook": "picom_reload",
        },
        "rofi": {
            "display_name": "Rofi launcher",
            "section_name": "rofi",
            "paths": ["~/.config/rofi"],
            "default_hook": "rofi_reload",
        },
        "ssh": {
            "display_name": "SSH config",
            "section_name": "ssh",
            "paths": ["~/.ssh/config"],
            "default_hook": None,
        },
        "git": {
            "display_name": "Git config",
            "section_name": "git",
            "paths": ["~/.gitconfig"],
            "default_hook": None,
        },
        "starship": {
            "display_name": "Starship prompt",
            "section_name": "starship",
            "paths": ["~/.config/starship.toml"],
            "default_hook": "shell_reload",
        },
        "fzf": {
            "display_name": "FZF",
            "section_name": "fzf",
            "paths": ["~/.fzf"],
            "default_hook": "fzf_reload",
        },
    }

    EXTENDED_CONFIGS: dict[str, _PopularConfigEntry] = {
        "code": {
            "display_name": "VS Code",
            "section_name": "vscode",
            "paths": ["~/.config/Code/User"],
            "default_hook": None,
        },
        "sublime": {
            "display_name": "Sublime Text",
            "section_name": "sublime",
            "paths": ["~/.config/sublime-text"],
            "default_hook": None,
        },
        "flatpak": {
            "display_name": "Flatpak",
            "section_name": "flatpak",
            "paths": ["~/.config/flatpak"],
            "default_hook": None,
        },
        "gtk": {
            "display_name": "GTK settings",
            "section_name": "gtk",
            "paths": ["~/.config/gtk-3.0"],
            "default_hook": None,
        },
        "qt": {
            "display_name": "Qt settings",
            "section_name": "qt",
            "paths": ["~/.config/qt5ct", "~/.config/qt6ct"],
            "default_hook": None,
        },
        "ranger": {
            "display_name": "Ranger file manager",
            "section_name": "ranger",
            "paths": ["~/.config/ranger"],
            "default_hook": None,
        },
        "lf": {
            "display_name": "LF file manager",
            "section_name": "lf",
            "paths": ["~/.config/lf"],
            "default_hook": None,
        },
        "aria2": {
            "display_name": "Aria2 download manager",
            "section_name": "aria2",
            "paths": ["~/.aria2"],
            "default_hook": None,
        },
        "doom": {
            "display_name": "Doom Emacs",
            "section_name": "doom",
            "paths": ["~/.doom.d"],
            "default_hook": "emacs_reload",
        },
        "alacritty-extra": {
            "display_name": "Alacritty extra themes",
            "section_name": "alacritty-themes",
            "paths": ["~/.config/alacritty-themes"],
            "default_hook": "alacritty_reload",
        },
    }

    @classmethod
    def detect_quickshell_configs(cls) -> list[ConfigInfo]:
        """Detect all quickshell configurations on the system.

        Returns:
            List of ConfigInfo dicts for detected quickshell configs
        """
        detected: list[ConfigInfo] = []

        for base_path_str in cls.QUICKSHELL_BASE_PATHS:
            base_path = Path(base_path_str).expanduser()
            if not base_path.exists():
                continue

            for subdir in base_path.iterdir():
                if not subdir.is_dir() or subdir.name.startswith("."):
                    continue

                config_name = subdir.name
                display_name = f"Quickshell - {config_name}"

                detected.append(
                    ConfigInfo(
                        {
                            "name": config_name,
                            "display_name": display_name,
                            "section_name": f"qs-{config_name}",
                            "paths": [f"~/.config/quickshell/{config_name}"],
                            "default_hook": "quickshell_reload",
                            "reload_cmd": f"qs -c {config_name}",
                        }
                    )
                )

        return detected

    @classmethod
    def detect_popular_configs(cls, include_extended: bool = True) -> list[ConfigInfo]:
        """Detect all popular configurations on the system.

        Args:
            include_extended: Include less common configs like VS Code, Sublime, etc.

        Returns:
            List of ConfigInfo dicts for detected configs
        """
        detected: list[ConfigInfo] = []

        configs = dict(cls.POPULAR_CONFIGS)
        if include_extended:
            configs.update(cls.EXTENDED_CONFIGS)

        for config_key, config_info in configs.items():
            paths_value = config_info["paths"]
            if paths_value is None:
                continue
            for path_str in paths_value:
                path = Path(path_str).expanduser()
                if path.exists():
                    detected.append(
                        ConfigInfo(
                            {
                                "name": config_key,
                                "display_name": str(config_info["display_name"]),
                                "section_name": str(config_info["section_name"]),
                                "paths": [path_str],
                                "default_hook": (
                                    str(config_info["default_hook"])
                                    if config_info["default_hook"]
                                    else None
                                ),
                                "reload_cmd": None,
                            }
                        )
                    )
                    break

        return detected

    @classmethod
    def detect_all(cls) -> list[ConfigInfo]:
        """Detect all configurations (both quickshell and popular).

        Returns:
            Combined list of all detected configs
        """
        results = []
        results.extend(cls.detect_popular_configs())
        results.extend(cls.detect_quickshell_configs())
        return results

    @classmethod
    def get_quickshell_config_name(cls, config_path: Path) -> str:
        """Extract quickshell config name from a path.

        Args:
            config_path: Path to quickshell config

        Returns:
            Config directory name (e.g., "ii", "caelestea")
        """
        path_str = str(config_path)

        for base_path_str in cls.QUICKSHELL_BASE_PATHS:
            base_path = Path(base_path_str).expanduser()
            base_str = str(base_path)

            if base_str in path_str:
                rel = path_str.replace(base_str, "")
                rel = rel.lstrip("/")
                if rel:
                    return rel.split("/")[0]

        return ""

    @classmethod
    def build_quickshell_reload_cmd(cls, config_path: Path) -> str:
        """Build reload command for a quickshell config.

        Args:
            config_path: Path to quickshell config directory

        Returns:
            Command to reload quickshell with the specific config
        """
        config_name = cls.get_quickshell_config_name(config_path)
        return f"killall qs 2>/dev/null; sleep 0.3; qs -c {config_name} &"


def get_auto_hooks_for_config(
    section_name: str, paths: list[str]
) -> dict[str, str] | None:
    """Get suggested hooks based on config name and paths.

    Uses the comprehensive hook system from merge.py for all popular
    configurations including shells, window managers, terminals, bars,
    editors, and tools.

    Args:
        section_name: The section name (e.g., "qs-caelestea", "hyprland")
        paths: List of paths in the section

    Returns:
        Dict with "pre_deploy" and/or "post_deploy" hooks, or None
    """
    paths_str = " ".join(str(p) for p in paths)

    if any(q in paths_str for q in ["quickshell", "qs-", ".config/qs"]):
        for path in paths:
            p = Path(path).expanduser()
            if p.exists():
                config_name = ConfigDetector.get_quickshell_config_name(p)
                if config_name:
                    return {
                        "post_deploy": f"killall qs 2>/dev/null; sleep 0.3; qs -c {config_name} &"
                    }

    for path in paths:
        p = Path(path).expanduser()
        hook = get_hook_for_config(p.name or section_name)
        if hook:
            return {"post_deploy": hook}

    return None
