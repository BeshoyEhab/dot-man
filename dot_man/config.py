"""Configuration parsing for dot-man.ini files."""

import configparser
from pathlib import Path
from typing import Any

from .constants import (
    DOT_MAN_DIR,
    GLOBAL_CONF,
    REPO_DIR,
    DOT_MAN_INI,
    DEFAULT_BRANCH,
    VALID_UPDATE_STRATEGIES,
)
from .exceptions import ConfigurationError, ConfigValidationError


class GlobalConfig:
    """Parser for the global.conf configuration file."""

    def __init__(self):
        self._config = configparser.ConfigParser()
        self._path = GLOBAL_CONF

    def load(self) -> None:
        """Load the global configuration file."""
        if not self._path.exists():
            raise ConfigurationError(f"Global config not found: {self._path}")
        self._config.read(self._path)

    def save(self) -> None:
        """Save the global configuration file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            self._config.write(f)

    def create_default(self) -> None:
        """Create a default global configuration."""
        from datetime import datetime

        self._config["dot-man"] = {
            "current_branch": DEFAULT_BRANCH,
            "initialized_date": datetime.now().isoformat(),
            "version": "1.0.0",
        }
        self._config["remote"] = {
            "url": "",
            "auto_sync": "false",
        }
        self._config["security"] = {
            "secrets_filter": "true",
            "audit_on_commit": "true",
            "strict_mode": "false",
        }
        self.save()

    @property
    def current_branch(self) -> str:
        """Get the current branch name."""
        return self._config.get("dot-man", "current_branch", fallback=DEFAULT_BRANCH)

    @current_branch.setter
    def current_branch(self, value: str) -> None:
        """Set the current branch name."""
        if "dot-man" not in self._config:
            self._config["dot-man"] = {}
        self._config["dot-man"]["current_branch"] = value

    @property
    def remote_url(self) -> str:
        """Get the remote URL."""
        return self._config.get("remote", "url", fallback="")

    @remote_url.setter
    def remote_url(self, value: str) -> None:
        """Set the remote URL."""
        if "remote" not in self._config:
            self._config["remote"] = {}
        self._config["remote"]["url"] = value

    @property
    def secrets_filter_enabled(self) -> bool:
        """Check if secrets filter is enabled."""
        return self._config.getboolean("security", "secrets_filter", fallback=True)

    @property
    def strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        return self._config.getboolean("security", "strict_mode", fallback=False)


class DotManConfig:
    """Parser for the dot-man.ini configuration file."""

    def __init__(self, repo_path: Path | None = None):
        self._config = configparser.ConfigParser()
        self._repo_path = repo_path or REPO_DIR
        self._path = self._repo_path / DOT_MAN_INI

    def load(self) -> None:
        """Load the dot-man.ini configuration file."""
        if not self._path.exists():
            raise ConfigurationError(f"Config not found: {self._path}")
        self._config.read(self._path)

    def save(self) -> None:
        """Save the dot-man.ini configuration file."""
        with open(self._path, "w") as f:
            self._config.write(f)

    def create_default(self) -> None:
        """Create a default dot-man.ini configuration."""
        self._config["DEFAULT"] = {
            "secrets_filter": "true",
            "update_strategy": "replace",
        }
        # Add example section as comment
        self.save()

        # Append example as comments
        with open(self._path, "a") as f:
            f.write("\n# Example configuration - uncomment and modify:\n")
            f.write("# [~/.bashrc]\n")
            f.write("# local_path = ~/.bashrc\n")
            f.write("# repo_path = .bashrc\n")
            f.write("# pre_deploy = echo 'Deploying bashrc...'\n")
            f.write("# post_deploy = source ~/.bashrc\n")

    def get_sections(self) -> list[str]:
        """Get all section names (excluding DEFAULT)."""
        return [s for s in self._config.sections() if s != "DEFAULT"]

    def get_section(self, name: str) -> dict[str, Any]:
        """Get a section's configuration."""
        if not self._config.has_section(name):
            raise ConfigurationError(f"Section not found: {name}")

        section = dict(self._config[name])

        # Expand ~ in paths
        if "local_path" in section:
            section["local_path"] = Path(section["local_path"]).expanduser()
        if "repo_path" in section:
            section["repo_path"] = self._repo_path / section["repo_path"]

        # Parse booleans
        section["secrets_filter"] = self._config.getboolean(
            name, "secrets_filter", fallback=True
        )

        # Validate update_strategy
        strategy = section.get("update_strategy", "replace")
        if strategy not in VALID_UPDATE_STRATEGIES:
            raise ConfigValidationError(
                f"Invalid update_strategy '{strategy}' in [{name}]. "
                f"Valid options: {VALID_UPDATE_STRATEGIES}"
            )
        section["update_strategy"] = strategy

        # Clean command strings
        if "post_deploy" in section:
            section["post_deploy"] = section["post_deploy"].strip()
        if "pre_deploy" in section:
            section["pre_deploy"] = section["pre_deploy"].strip()

        return section

    def add_section(
        self,
        name: str,
        local_path: str,
        repo_path: str,
        secrets_filter: bool = True,
        update_strategy: str = "replace",
        post_deploy: str = "",
        pre_deploy: str = "",
    ) -> None:
        """Add a new section to the configuration."""
        if self._config.has_section(name):
            raise ConfigurationError(f"Section already exists: {name}")

        self._config.add_section(name)
        self._config.set(name, "local_path", local_path)
        self._config.set(name, "repo_path", repo_path)
        self._config.set(name, "secrets_filter", str(secrets_filter).lower())
        self._config.set(name, "update_strategy", update_strategy)
        if post_deploy:
            self._config.set(name, "post_deploy", post_deploy)
        if pre_deploy:
            self._config.set(name, "pre_deploy", pre_deploy)

    def validate(self) -> list[str]:
        """Validate the configuration file. Returns list of warnings."""
        warnings = []

        for section in self.get_sections():
            config = dict(self._config[section])

            # Check required fields
            if "local_path" not in config:
                warnings.append(f"[{section}]: Missing 'local_path'")
            if "repo_path" not in config:
                warnings.append(f"[{section}]: Missing 'repo_path'")

            # Validate update_strategy
            strategy = config.get("update_strategy", "replace")
            if strategy not in VALID_UPDATE_STRATEGIES:
                warnings.append(
                    f"[{section}]: Invalid update_strategy '{strategy}'"
                )

            # Check if local_path is resolvable
            if "local_path" in config:
                try:
                    path = Path(config["local_path"]).expanduser()
                    if not path.is_absolute():
                        warnings.append(
                            f"[{section}]: local_path should be absolute"
                        )
                except Exception as e:
                    warnings.append(f"[{section}]: Invalid local_path: {e}")

        return warnings
