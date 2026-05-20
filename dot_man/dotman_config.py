"""DotMan configuration file parser (TOML/YAML)."""

__all__ = ["DotManConfig"]

import logging
import sys
from pathlib import Path
from typing import Any, cast

# Python 3.11+ has tomllib built-in, otherwise use tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("Please install tomli: pip install tomli")

import tomlkit

from .constants import (
    CONFIG_FILE_PRIORITY,
    DOT_MAN_TOML,
    REPO_DIR,
    VALID_UPDATE_STRATEGIES,
)
from .exceptions import ConfigurationError, ConfigValidationError
from .global_config import GlobalConfig, write_config_file
from .section import Section


class DotManConfig:
    """Parser for the dot-man configuration file (TOML/YAML)."""

    def __init__(
        self, repo_path: Path | None = None, global_config: GlobalConfig | None = None
    ):
        self._data: dict = {}
        self._repo_path = repo_path or REPO_DIR

        # Find first existing config file in priority order
        config_files = [self._repo_path / f for f in CONFIG_FILE_PRIORITY]
        existing = [f for f in config_files if f.exists()]

        if len(existing) > 1:
            logging.warning(
                f"Multiple config files found: {[f.name for f in existing]}. "
                f"Using {existing[0].name} (TOML > YAML priority)"
            )

        self._path = existing[0] if existing else self._repo_path / DOT_MAN_TOML

        # Track config format for save operations
        self._config_format = self._path.suffix.replace(".", "")

        self._global_config = global_config
        self._doc: Any = None  # For preserving comments
        self._dirty: bool = False

    @property
    def repo_path(self) -> Path:
        """Get the repository path."""
        return self._repo_path

    def load(self) -> None:
        """Load the dot-man configuration file.

        Supports TOML (.toml) and YAML (.yaml/.yml) formats.
        """
        if not self._path.exists():
            raise ConfigurationError(f"Config not found: {self._path}")

        content = self._path.read_text()

        if self._path.suffix in (".yaml", ".yml"):
            try:
                from ruamel.yaml import YAML
            except ImportError:
                raise ConfigurationError(
                    "YAML support requires ruamel.yaml. Install with: pip install dotman-git[yaml]"
                )
            yaml = YAML()
            self._doc = yaml.load(content)
            import yaml as pyyaml  # type: ignore[import-untyped]

            self._data = pyyaml.safe_load(content) or {}
        else:
            self._data = tomllib.loads(content)
            self._doc = tomlkit.parse(content)

        self._dirty = False

        warnings = self._validate_schema()
        if warnings:
            for w in warnings:
                logging.warning("Config warning: {w}")

    def _validate_schema(self) -> list[str]:
        """Validate config structure on load."""
        warnings: list[str] = []
        valid_section_keys = {
            "paths",
            "repo_base",
            "repo_path",
            "secrets_filter",
            "update_strategy",
            "include",
            "exclude",
            "pre_deploy",
            "post_deploy",
            "on_activate",
            "on_deactivate",
            "inherits",
            "ignored_directories",
            "follow_symlinks",
        }

        for name, section in self._data.items():
            if name == "templates":
                continue
            if isinstance(section, dict):
                for key in section:
                    if key not in valid_section_keys:
                        warnings.append(f"[{name}]: Unknown key '{key}'")
        return warnings

    def save(self, force: bool = False) -> None:
        """Save the dot-man.toml configuration file.

        Args:
            force: Save even if not dirty
        """
        if not self._dirty and not force:
            return
        write_config_file(self._path, self._data, self._doc)
        self._dirty = False

    def create_default(self) -> None:
        """Create minimal default config with helpful examples."""
        # Start with empty config - examples will be in comments
        self._data = {}
        self._dirty = True
        self.save(force=True)

        # Append helpful comments and documentation with example sections
        with open(self._path, "a") as f:
            f.write("""
# ============================================================================
# dot-man Configuration Examples
# ============================================================================
#
# Welcome! This config file helps you track your dotfiles across machines.
# Uncomment and modify the example sections below for your setup.
#
# Quick Start:
#   1. Uncomment sections below that match your dotfiles
#   2. Run: dot-man switch main
#   3. That's it! Your configs are now tracked and can be deployed anywhere
#
# Smart defaults apply automatically - you only need to override them when needed.

# ============================================================================
# Common Dotfile Examples (uncomment and modify as needed)
# ============================================================================

# Basic bash configuration
# [bashrc]
# paths = ["~/.bashrc"]
# post_deploy = "shell_reload"

# Git configuration (secrets are auto-filtered)
# [gitconfig]
# paths = ["~/.gitconfig"]

# Neovim configuration with plugin exclusions
# [nvim]
# paths = ["~/.config/nvim"]
# exclude = ["*.log", "plugin/packer_compiled.lua"]
# post_deploy = "nvim_sync"

# SSH client configuration (be careful with secrets!)
# [ssh-config]
# paths = ["~/.ssh/config"]
# secrets_filter = true
# update_strategy = "rename_old"

# Multiple shell configurations in one section
# [shell-configs]
# paths = ["~/.bashrc", "~/.zshrc", "~/.profile"]
# post_deploy = "shell_reload"

# Kitty terminal configuration
# [kitty]
# paths = ["~/.config/kitty"]
# post_deploy = "kitty_reload"

# Tmux configuration
# [tmux]
# paths = ["~/.tmux.conf"]
# post_deploy = "tmux_reload"

# Fish shell configuration
# [fish]
# paths = ["~/.config/fish"]
# post_deploy = "fish_reload"

# ============================================================================
# How to Add Your Own Files
# ============================================================================
#
# Basic format for custom files:
# [my-custom-config]
# paths = ["~/.some-config-file", "~/another-file"]
# # Optional: repo_base = "custom-repo-name"
# # Optional: post_deploy = "some-command-to-run-after-deploy"

# ============================================================================
# Available Hook Aliases (use these instead of full commands)
# ============================================================================
#
# shell_reload    → source ~/.bashrc || source ~/.zshrc
# nvim_sync       → nvim --headless +PackerSync +qa
# hyprland_reload → hyprctl reload
# fish_reload     → source ~/.config/fish/config.fish
# tmux_reload     → tmux source-file ~/.tmux.conf
# kitty_reload    → killall -SIGUSR1 kitty
#
# Custom commands work too:
# post_deploy = "systemctl --user restart some-service"
# post_deploy = "notify-send 'Config updated!'"

# ============================================================================
# Advanced Features
# ============================================================================
#
# Templates for shared settings:
# [templates.linux-desktop]
# post_deploy = "notify-send 'Config updated'"
#
# [hyprland]
# paths = ["~/.config/hypr"]
# inherits = ["linux-desktop"]
#
# Include/exclude patterns:
# include = ["*.conf", "*.lua"]  # Only track these patterns
# exclude = ["*.log", "cache/"]  # Skip these files/directories
#
# Update strategies:
# update_strategy = "replace"      # Overwrite (default)
# update_strategy = "rename_old"   # Backup before overwrite
# update_strategy = "ignore"       # Skip if file exists
#
# Full documentation: https://github.com/BeshoyEhab/dot-man#configuration
""")

    def get_section_names(self) -> list[str]:
        """Get all section names (excluding templates)."""
        return [
            name
            for name in self._data.keys()
            if name != "templates" and isinstance(self._data[name], dict)
        ]

    def get_local_templates(self) -> dict[str, Any]:
        """Get templates defined in this file."""
        return cast(dict[str, Any], self._data.get("templates", {}))

    def _resolve_template(self, name: str) -> dict[str, Any]:
        """Resolve a template by name, checking local first then global."""
        # Check local templates
        local = self.get_local_templates().get(name)
        if local:
            return cast(dict[str, Any], local)

        # Check global templates
        if self._global_config:
            global_template = self._global_config.get_template(name)
            if global_template:
                return global_template

        return {}

    def _merge_settings(self, base: dict, override: dict) -> dict:
        """Merge settings, with override taking precedence."""
        result = base.copy()
        for key, value in override.items():
            if key == "inherits":
                continue  # Don't inherit the inherits key
            result[key] = value
        return result

    def get_section(self, name: str) -> Section:
        """Get a fully resolved section with inheritance applied."""
        if name not in self._data or name == "templates":
            raise ConfigurationError(f"Section not found: {name}")

        raw = self._data[name]

        # Start with global defaults
        settings = {}
        if self._global_config:
            settings = self._global_config.get_defaults().copy()

        # Apply inherited templates (in order)
        inherits = raw.get("inherits", [])
        if isinstance(inherits, str):
            inherits = [inherits]  # Support single string for convenience

        for template_name in inherits:
            template = self._resolve_template(template_name)
            settings = self._merge_settings(settings, template)

        # Apply section-specific settings
        settings = self._merge_settings(settings, raw)

        # Parse paths with environment variable expansion
        import os

        paths_raw = settings.get("paths", [])
        if isinstance(paths_raw, str):
            paths_raw = [paths_raw]
        paths = [Path(os.path.expandvars(os.path.expanduser(p))) for p in paths_raw]

        if not paths:
            raise ConfigValidationError(f"Section [{name}] must have at least one path")

        # Validate update_strategy
        strategy = settings.get("update_strategy", "replace")
        if strategy not in VALID_UPDATE_STRATEGIES:
            raise ConfigValidationError(
                f"Invalid update_strategy '{strategy}' in [{name}]. "
                f"Valid options: {VALID_UPDATE_STRATEGIES}"
            )

        # Build Section object
        return Section(
            name=name,
            paths=paths,
            repo_base=settings.get("repo_base", name),
            repo_path=settings.get("repo_path"),
            secrets_filter=settings.get("secrets_filter", True),
            update_strategy=strategy,
            include=settings.get("include", []),
            exclude=settings.get("exclude", []),
            pre_deploy=settings.get("pre_deploy"),
            post_deploy=settings.get("post_deploy"),
            on_activate=settings.get("on_activate"),
            on_deactivate=settings.get("on_deactivate"),
            inherits=inherits,
            ignored_directories=settings.get("ignored_directories"),
            follow_symlinks=settings.get("follow_symlinks"),
        )

    def add_section(
        self,
        name: str,
        paths: list[str],
        repo_base: str | None = None,
        overwrite: bool = False,
        **kwargs,
    ) -> None:
        """Add a new section to the configuration."""
        if name in self._data and not overwrite:
            raise ConfigurationError(f"Section already exists: {name}")

        if not paths:
            raise ConfigurationError("Section must have at least one path")

        # Validate paths
        cleaned_paths = []
        for p in paths:
            if not isinstance(p, str) or not p.strip():
                raise ConfigurationError("Paths must be non-empty strings")

            clean_p = p.strip()
            if Path(clean_p).is_absolute():
                raise ConfigurationError(
                    f"Paths must be relative (to home or checkout): {clean_p}"
                )
            cleaned_paths.append(clean_p)
        paths = cleaned_paths

        if name == "templates":
            raise ConfigurationError("'templates' is a reserved section name")

        section_data = {
            "paths": paths,
            "repo_base": repo_base or name,
        }

        # Add optional fields
        for key in [
            "secrets_filter",
            "update_strategy",
            "include",
            "exclude",
            "pre_deploy",
            "post_deploy",
            "on_activate",
            "on_deactivate",
            "inherits",
            "repo_path",
            "ignored_directories",
            "follow_symlinks",
        ]:
            if key in kwargs and kwargs[key]:
                section_data[key] = kwargs[key]

        self._data[name] = section_data
        self._dirty = True

    def update_section(self, name: str, **kwargs) -> None:
        """Update an existing section's properties.

        Args:
            name: Section name to update
            **kwargs: Properties to update (set to None to remove a property)

        Raises:
            ConfigurationError: If section doesn't exist or invalid key provided
        """
        if name not in self._data or name == "templates":
            raise ConfigurationError(f"Section not found: {name}")

        valid_keys = {
            "paths",
            "repo_base",
            "repo_path",
            "secrets_filter",
            "update_strategy",
            "include",
            "exclude",
            "pre_deploy",
            "post_deploy",
            "on_activate",
            "on_deactivate",
            "inherits",
            "ignored_directories",
            "follow_symlinks",
        }

        for key, value in kwargs.items():
            if key not in valid_keys:
                raise ConfigurationError(f"Unknown key: {key}")
            if value is None:
                # Remove the key if set to None
                self._data[name].pop(key, None)
            else:
                self._data[name][key] = value

        self._dirty = True

    def remove_section(self, name: str) -> None:
        """Remove a section from the configuration.

        Args:
            name: Section name to remove

        Raises:
            ConfigurationError: If section doesn't exist
        """
        if name not in self._data or name == "templates":
            raise ConfigurationError(f"Section not found: {name}")
        del self._data[name]
        self._dirty = True

    def validate(self) -> list[str]:
        """Validate the configuration file. Returns list of warnings."""
        warnings = []

        for name in self.get_section_names():
            try:
                section = self.get_section(name)

                # Check paths exist
                for path in section.paths:
                    if not path.exists():
                        warnings.append(f"[{name}]: Path does not exist: {path}")

                # Check inherits resolve
                for template in section.inherits:
                    # Check if template exists (empty template is valid)
                    local_templates = self.get_local_templates()
                    global_templates = (
                        self._global_config.get_all_templates()
                        if self._global_config
                        else {}
                    )
                    if (
                        template not in local_templates
                        and template not in global_templates
                    ):
                        warnings.append(f"[{name}]: Template not found: {template}")

                # Check for invalid keys
                valid_keys = {
                    "paths",
                    "repo_base",
                    "repo_path",
                    "secrets_filter",
                    "update_strategy",
                    "include",
                    "exclude",
                    "pre_deploy",
                    "post_deploy",
                    "on_activate",
                    "on_deactivate",
                    "inherits",
                    "ignored_directories",
                    "follow_symlinks",
                }
                for key in self._data[name]:
                    if key not in valid_keys:
                        warnings.append(f"[{name}]: Unknown key '{key}'")

            except Exception as e:
                warnings.append(f"[{name}]: {e}")

        return warnings
