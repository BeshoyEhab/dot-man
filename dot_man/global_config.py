"""Global configuration management for dot-man."""

__all__ = ["GlobalConfig", "_write_toml"]

import sys
import logging
from typing import Optional, Any, cast
from pathlib import Path
from datetime import datetime

# Python 3.11+ has tomllib built-in, otherwise use tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError("Please install tomli: pip install tomli")

import tomlkit
from tomlkit import TOMLDocument

from .constants import (
    GLOBAL_TOML,
    DEFAULT_BRANCH,
    DEFAULT_IGNORED_DIRECTORIES,
)
from .exceptions import ConfigurationError


def _write_toml(path: Path, data: dict, preserve_doc: TOMLDocument | None = None) -> None:
    """Write TOML data to file, preserving comments when possible.
    
    Args:
        path: File path to write to
        data: Dictionary of data to write
        preserve_doc: Optional existing TOMLDocument to update (preserves comments)
    """
    if preserve_doc is not None:
        # Update existing document in-place to preserve comments
        for key, value in data.items():
            preserve_doc[key] = value
        path.write_text(tomlkit.dumps(preserve_doc))
    else:
        # Create new document from dict
        path.write_text(tomlkit.dumps(data))


class GlobalConfig:
    """Parser for the global.toml configuration file."""

    def __init__(self):
        self._data: dict = {}
        self._path = GLOBAL_TOML
        self._doc: TOMLDocument | None = None  # For preserving comments
        self._dirty: bool = False

    def load(self) -> None:
        """Load the global configuration file.

        If global.toml doesn't exist but global.conf does, automatically
        migrates the old INI format to TOML.
        """
        # Check for migration
        if not self._path.exists():
            from .constants import GLOBAL_CONF

            if GLOBAL_CONF.exists():
                self._migrate_from_ini(GLOBAL_CONF)
                return
            raise ConfigurationError(f"Global config not found: {self._path}")
        
        content = self._path.read_text()
        self._data = tomllib.loads(content)
        # Also parse with tomlkit to preserve comments
        self._doc = tomlkit.parse(content)
        self._dirty = False

    def _migrate_from_ini(self, old_path: Path) -> None:
        """Migrate from old INI format to TOML."""
        import configparser
        import shutil

        logging.info("Migrating %s to TOML format...", old_path.name)

        config = configparser.ConfigParser()
        config.read(old_path)

        # Convert INI to TOML structure
        self._data = {}
        for section in config.sections():
            self._data[section] = {}
            for key, value in config[section].items():
                # Convert string booleans
                if value.lower() in ("true", "false"):
                    self._data[section][key] = value.lower() == "true"
                else:
                    self._data[section][key] = value

        # Add defaults section if not present
        if "defaults" not in self._data:
            self._data["defaults"] = {
                "secrets_filter": True,
                "update_strategy": "replace",
                "ignored_directories": DEFAULT_IGNORED_DIRECTORIES,
                "follow_symlinks": False,
            }

        # Add empty templates section
        if "templates" not in self._data:
            self._data["templates"] = {}

        # Backup old file
        backup_path = old_path.with_suffix(".conf.bak")
        shutil.copy(old_path, backup_path)
        logging.info("  Backed up old config to %s", backup_path.name)

        # Save new TOML
        self._dirty = True
        self.save()
        logging.info("  Created %s", self._path.name)

        # Remove old file
        old_path.unlink()
        logging.info("  Removed old %s", old_path.name)

    def save(self, force: bool = False) -> None:
        """Save the global configuration file.
        
        Args:
            force: Save even if not dirty
        """
        if not self._dirty and not force:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        _write_toml(self._path, self._data, self._doc)
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
        return cast(str, self._data.get("dot-man", {}).get("current_branch", DEFAULT_BRANCH))

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

    def get_all_templates(self) -> dict[str, Any]:
        """Get all templates."""
        return cast(dict[str, Any], self._data.get("templates", {}))
