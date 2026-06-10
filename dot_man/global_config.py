"""Global configuration management for dot-man."""

__all__ = [
    "GlobalConfig",
    "load_config_file",
    "write_config_file",
    "_write_toml",
    "substitute_templates",
]

import logging
import os
import platform
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

# System variables that can be auto-detected
SYSTEM_VARS = {
    "HOSTNAME": lambda: socket.gethostname(),
    "USER": lambda: os.environ.get("USER", os.environ.get("USERNAME", "unknown")),
    "HOME": lambda: str(Path.home()),
    "OS": lambda: platform.system(),
    "OS_VERSION": lambda: platform.version(),
    "ARCH": lambda: platform.machine(),
    "SHELL": lambda: os.environ.get("SHELL", "/bin/sh"),
    "EDITOR": lambda: os.environ.get("EDITOR", os.environ.get("VISUAL", "vim")),
    "EMAIL": lambda: None,
    "DOMAIN": lambda: socket.getfqdn(),
}


def substitute_templates(text: str, user_templates: dict | None = None) -> str:
    """Substitute template variables in a string.

    Args:
        text: String containing template placeholders like {{HOSTNAME}}
        user_templates: Optional dict of user-defined templates

    Returns:
        String with all substitutions applied
    """
    if not text:
        return text

    result = text

    # First replace system variables
    for var_name, getter in SYSTEM_VARS.items():
        placeholder = f"{{{{{var_name}}}}}"
        if placeholder in result:
            try:
                val = getter()
                if val:
                    result = result.replace(placeholder, str(val))
            except Exception as e:
                logging.debug(f"Could not get system variable {var_name}: {e}")

    # Then replace user-defined templates
    if user_templates:
        for key, value in user_templates.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))

    return result


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
    DEFAULT_BRANCH,
    DEFAULT_IGNORED_DIRECTORIES,
    GLOBAL_TOML,
)
from .exceptions import ConfigurationError


def update_config_doc(doc: Any, data: dict) -> None:
    """Recursively update a tomlkit/ruamel.yaml config document (doc) with dict data,
    preserving comments and deleting stale keys.
    """
    # Remove keys in doc that are not in data
    keys_to_remove = [k for k in doc if k not in data]
    for k in keys_to_remove:
        del doc[k]

    # Update or add keys from data
    for k, v in data.items():
        if k in doc:
            if isinstance(v, dict) and isinstance(doc[k], dict):
                update_config_doc(doc[k], v)
            elif doc[k] == v:
                # Avoid re-assignment to preserve comments/formatting
                pass
            else:
                doc[k] = v
        else:
            doc[k] = v


def load_config_file(path: Path, label: str = "Config") -> tuple[dict, Any]:
    """Load a TOML/YAML configuration file.

    Args:
        path: Path to the config file.
        label: Label for error messages (e.g. "Global config", "dot-man config").

    Returns:
        (data_dict, doc_for_preserving_comments)
    """
    if not path.exists():
        raise ConfigurationError(f"{label} not found: {path}")

    content = path.read_text()

    if path.suffix in (".yaml", ".yml"):
        try:
            from ruamel.yaml import YAML
        except ImportError:
            raise ConfigurationError(
                "YAML support requires ruamel.yaml. Install with: pip install dotman-git[yaml]"
            )
        yaml = YAML()
        doc = yaml.load(content)
        import yaml as pyyaml  # type: ignore[import-untyped]

        data = pyyaml.safe_load(content) or {}
    else:
        data = tomllib.loads(content)
        doc = tomlkit.parse(content)

    return data, doc


def write_config_file(path: Path, data: dict, preserve_doc: Any = None) -> None:
    """Write TOML/YAML configuration data to file, preserving comments when possible.

    Args:
        path: File path to write to
        data: Dictionary of data to write
        preserve_doc: Optional existing TOML/YAML document to update (preserves comments)
    """
    if path.suffix in (".yaml", ".yml"):
        from ruamel.yaml import YAML

        yaml = YAML()
        if preserve_doc is not None:
            update_config_doc(preserve_doc, data)
            with open(path, "w") as f:
                yaml.dump(preserve_doc, f)
        else:
            with open(path, "w") as f:
                yaml.dump(data, f)
    else:
        # TOML
        if preserve_doc is not None:
            update_config_doc(preserve_doc, data)
            path.write_text(tomlkit.dumps(preserve_doc))
        else:
            path.write_text(tomlkit.dumps(data))


def _write_toml(path: Path, data: dict, preserve_doc: Any = None) -> None:
    """Compatibility wrapper for write_config_file."""
    write_config_file(path, data, preserve_doc)


class GlobalConfig:
    """Parser for the global.toml configuration file."""

    def __init__(self):
        self._data: dict = {}
        self._path = GLOBAL_TOML
        self._doc: Any = None  # For preserving comments
        self._dirty: bool = False

    def load(self) -> None:
        """Load the global configuration file.

        Supports TOML (.toml) and YAML (.yaml/.yml) formats.
        """
        self._data, self._doc = load_config_file(self._path, label="Global config")
        self._dirty = False

    def save(self, force: bool = True) -> None:
        """Save the global configuration file.

        Args:
            force: Save even if not dirty
        """
        if not self._dirty and not force:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        write_config_file(self._path, self._data, self._doc)
        self._dirty = False

    def create_default(self) -> None:
        """Create a default global configuration."""
        self._data = {
            "dot-man": {
                "current_branch": DEFAULT_BRANCH,
                "initialized_date": datetime.now().isoformat(),
                "version": "1.0.0",
            },
            "remote": {
                "url": "",
                "auto_sync": False,
            },
            "defaults": {
                "secrets_filter": True,
                "update_strategy": "replace",
                "ignored_directories": DEFAULT_IGNORED_DIRECTORIES,
                "follow_symlinks": False,
            },
            "security": {
                "strict_mode": False,
                "audit_on_commit": True,
            },
            "switch": {
                "default_behavior": "save",
            },
            # Example template
            "templates": {
                "example": {
                    "post_deploy": "echo 'Deployed!'",
                    "update_strategy": "replace",
                }
            },
        }
        self._dirty = True
        self.save(force=True)

    @property
    def current_branch(self) -> str:
        """Get the current branch name."""
        return cast(
            str, self._data.get("dot-man", {}).get("current_branch", DEFAULT_BRANCH)
        )

    @current_branch.setter
    def current_branch(self, value: str) -> None:
        """Set the current branch name."""
        if "dot-man" not in self._data:
            self._data["dot-man"] = {}
        self._data["dot-man"]["current_branch"] = value
        self._dirty = True

    @property
    def remote_url(self) -> str:
        """Get the remote URL."""
        return cast(str, self._data.get("remote", {}).get("url", ""))

    @remote_url.setter
    def remote_url(self, value: str) -> None:
        """Set the remote URL."""
        if "remote" not in self._data:
            self._data["remote"] = {}
        self._data["remote"]["url"] = value
        self._dirty = True

    @property
    def editor(self) -> Optional[str]:
        """Get the configured editor."""
        return cast(Optional[str], self._data.get("dot-man", {}).get("editor"))

    @editor.setter
    def editor(self, value: Optional[str]) -> None:
        """Set the editor."""
        if "dot-man" not in self._data:
            self._data["dot-man"] = {}
        self._data["dot-man"]["editor"] = value
        self._dirty = True

    @property
    def secrets_filter_enabled(self) -> bool:
        """Check if secrets filter is enabled by default."""
        return cast(bool, self._data.get("defaults", {}).get("secrets_filter", True))

    @secrets_filter_enabled.setter
    def secrets_filter_enabled(self, value: bool) -> None:
        """Set whether secrets filter is enabled by default."""
        if "defaults" not in self._data:
            self._data["defaults"] = {}
        self._data["defaults"]["secrets_filter"] = value
        self._dirty = True

    @property
    def strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        return cast(bool, self._data.get("security", {}).get("strict_mode", False))

    @strict_mode.setter
    def strict_mode(self, value: bool) -> None:
        """Set whether strict mode is enabled."""
        if "security" not in self._data:
            self._data["security"] = {}
        self._data["security"]["strict_mode"] = value
        self._dirty = True

    def get_defaults(self) -> dict[str, Any]:
        """Get default settings that apply to all sections."""
        defaults = cast(dict[str, Any], self._data.get("defaults", {}))
        # Ensure default ignored directories are present if not specified
        if "ignored_directories" not in defaults:
            defaults["ignored_directories"] = DEFAULT_IGNORED_DIRECTORIES
        if "follow_symlinks" not in defaults:
            defaults["follow_symlinks"] = False
        return defaults

    def get_template(self, name: str) -> Optional[dict[str, Any]]:
        """Get a template by name."""
        templates = self._data.get("templates", {})
        return cast(Optional[dict[str, Any]], templates.get(name))

    @property
    def switch_default_behavior(self) -> str:
        """Get default switch behavior (save or no-save)."""
        return cast(str, self._data.get("switch", {}).get("default_behavior", "save"))

    @switch_default_behavior.setter
    def switch_default_behavior(self, value: str) -> None:
        """Set default switch behavior."""
        if value not in ("save", "no-save"):
            raise ConfigurationError(
                "switch.default_behavior must be 'save' or 'no-save'"
            )
        if "switch" not in self._data:
            self._data["switch"] = {}
        self._data["switch"]["default_behavior"] = value
        self._dirty = True

    def get_all_templates(self) -> dict[str, Any]:
        """Get all templates."""
        return cast(dict[str, Any], self._data.get("templates", {}))

    @property
    def profiles(self) -> dict[str, Any]:
        """Get all profiles."""
        return cast(dict[str, Any], self._data.get("profiles", {}))

    @property
    def current_profile(self) -> str | None:
        """Get the current profile name."""
        return cast(Optional[str], self._data.get("dot-man", {}).get("current_profile"))

    @current_profile.setter
    def current_profile(self, value: str) -> None:
        """Set the current profile."""
        if "dot-man" not in self._data:
            self._data["dot-man"] = {}
        self._data["dot-man"]["current_profile"] = value
        self._dirty = True
