"""Configuration parsing for dot-man using TOML format."""

import sys
from typing import Optional, Any, Union
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

try:
    import tomli_w
except ImportError:
    tomli_w = None  # Writing will use manual formatting

from .constants import (
    GLOBAL_TOML,
    REPO_DIR,
    DOT_MAN_TOML,
    DEFAULT_BRANCH,
    VALID_UPDATE_STRATEGIES,
    HOOK_ALIASES,
)
from .exceptions import ConfigurationError, ConfigValidationError


def _write_toml(path: Path, data: dict) -> None:
    """Write TOML data to file."""
    if tomli_w:
        path.write_bytes(tomli_w.dumps(data).encode())
    else:
        # Manual TOML writing for simple structures
        lines = []

        def escape_string(s: str) -> str:
            """Escape a string for TOML, handling quotes properly."""
            # Escape backslashes first, then quotes
            s = s.replace("\\", "\\\\")
            s = s.replace('"', '\\"')
            return f'"{s}"'

        def write_section(name: str, section: dict, prefix: str = ""):
            full_name = f"{prefix}.{name}" if prefix else name
            lines.append(f"[{full_name}]")
            for key, value in section.items():
                if isinstance(value, dict):
                    continue  # Handle nested dicts separately
                elif value is None:
                    continue
                elif isinstance(value, bool):
                    lines.append(f"{key} = {str(value).lower()}")
                elif isinstance(value, str):
                    lines.append(f"{key} = {escape_string(value)}")
                elif isinstance(value, datetime):
                    lines.append(f"{key} = {value.isoformat()}")
                elif isinstance(value, list):
                    items = ", ".join(
                        escape_string(v) if isinstance(v, str) else str(v)
                        for v in value
                    )
                    lines.append(f"{key} = [{items}]")
                else:
                    lines.append(f"{key} = {value}")
            lines.append("")

            # Handle nested dicts
            for key, value in section.items():
                if isinstance(value, dict):
                    write_section(key, value, full_name)

        # Collect top-level values first
        top_level_lines = []

        for name, section in data.items():
            if isinstance(section, dict):
                write_section(name, section)
            else:
                # Top-level simple value
                if isinstance(section, bool):
                    top_level_lines.append(f"{name} = {str(section).lower()}")
                elif isinstance(section, str):
                    top_level_lines.append(f"{name} = {escape_string(section)}")
                else:
                    top_level_lines.append(f"{name} = {section}")

        # Prepend top-level values
        if top_level_lines:
            top_level_lines.append("")
        path.write_text("\n".join(top_level_lines + lines))


class GlobalConfig:
    """Parser for the global.toml configuration file."""

    def __init__(self):
        self._data: dict = {}
        self._path = GLOBAL_TOML

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
        self._data = tomllib.loads(self._path.read_text())

    def _migrate_from_ini(self, old_path: Path) -> None:
        """Migrate from old INI format to TOML."""
        import configparser
        import shutil

        print(f"🔄 Migrating {old_path.name} to TOML format...")

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
            }

        # Add empty templates section
        if "templates" not in self._data:
            self._data["templates"] = {}

        # Backup old file
        backup_path = old_path.with_suffix(".conf.bak")
        shutil.copy(old_path, backup_path)
        print(f"  📦 Backed up old config to {backup_path.name}")

        # Save new TOML
        self.save()
        print(f"  ✓ Created {self._path.name}")

        # Remove old file
        old_path.unlink()
        print(f"  🗑️  Removed old {old_path.name}")

    def save(self) -> None:
        """Save the global configuration file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        _write_toml(self._path, self._data)

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
        self.save()

    @property
    def current_branch(self) -> str:
        """Get the current branch name."""
        return self._data.get("dot-man", {}).get("current_branch", DEFAULT_BRANCH)

    @current_branch.setter
    def current_branch(self, value: str) -> None:
        """Set the current branch name."""
        if "dot-man" not in self._data:
            self._data["dot-man"] = {}
        self._data["dot-man"]["current_branch"] = value

    @property
    def remote_url(self) -> str:
        """Get the remote URL."""
        return self._data.get("remote", {}).get("url", "")

    @remote_url.setter
    def remote_url(self, value: str) -> None:
        """Set the remote URL."""
        if "remote" not in self._data:
            self._data["remote"] = {}
        self._data["remote"]["url"] = value

    @property
    def editor(self) -> Optional[str]:
        """Get the configured editor."""
        return self._data.get("dot-man", {}).get("editor")

    @editor.setter
    def editor(self, value: Optional[str]) -> None:
        """Set the editor."""
        if "dot-man" not in self._data:
            self._data["dot-man"] = {}
        self._data["dot-man"]["editor"] = value

    @property
    def secrets_filter_enabled(self) -> bool:
        """Check if secrets filter is enabled by default."""
        return self._data.get("defaults", {}).get("secrets_filter", True)

    @property
    def strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        return self._data.get("security", {}).get("strict_mode", False)

    def get_defaults(self) -> dict:
        """Get default settings that apply to all sections."""
        return self._data.get("defaults", {})

    def get_template(self, name: str) -> Optional[dict[str, Any]]:
        """Get a template by name."""
        return self._data.get("templates", {}).get(name)

    def get_all_templates(self) -> dict:
        """Get all templates."""
        return self._data.get("templates", {})


class Section:
    """Represents a resolved configuration section with smart defaults."""

    def __init__(
        self,
        name: str,
        paths: list[Path],
        repo_base: Optional[str] = None,  # NOW OPTIONAL!
        repo_path: Optional[str] = None,
        secrets_filter: Optional[bool] = None,  # None = use default
        update_strategy: Optional[str] = None,  # None = use default
        include: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        pre_deploy: Optional[str] = None,
        post_deploy: Optional[str] = None,
        inherits: Optional[list[str]] = None,
    ):
        self.name = name
        self.paths = paths
        self.repo_path = repo_path

        # Smart repo_base generation if not provided
        if repo_base is None and not repo_path:
            self.repo_base = self._generate_repo_base()
        else:
            self.repo_base = repo_base or name

        # Use provided values or defaults (None means "use global default")
        self.secrets_filter = secrets_filter if secrets_filter is not None else True
        self.update_strategy = update_strategy or "replace"

        self.include = include or []
        self.exclude = exclude or []

        # Resolve hook aliases
        self.pre_deploy = self._resolve_hook(pre_deploy)
        self.post_deploy = self._resolve_hook(post_deploy)

        self.inherits = inherits or []

    def _generate_repo_base(self) -> str:
        """Auto-generate repo_base from first path.

        Examples:
            ~/.bashrc → "bashrc"
            ~/.config/nvim → "nvim"
            ~/.ssh/config → "ssh/config"
        """
        if not self.paths:
            return self.name

        first_path = self.paths[0]

        # Handle dotfiles: ~/.bashrc → "bashrc"
        if first_path.name.startswith(".") and first_path.suffix:
            # .bashrc → bashrc, .vimrc → vimrc
            return first_path.name[1:]

        if first_path.name.startswith(".") and not first_path.suffix:
            # .vim → vim, .ssh → ssh
            return first_path.name[1:]

        # Handle .config directories: ~/.config/nvim → "nvim"
        if ".config" in first_path.parts:
            return first_path.name

        # Handle subdirectories: ~/.ssh/config → "ssh/config"
        if len(first_path.parts) > 1 and first_path.is_file():
            parent_name = first_path.parent.name
            if parent_name.startswith("."):
                parent_name = parent_name[1:]
            return f"{parent_name}/{first_path.name}"

        # Fallback: use stem or name
        return first_path.stem or first_path.name

    def _resolve_hook(self, hook: str | None) -> str | None:
        """Resolve hook aliases to actual commands.

        Examples:
            "shell_reload" → "source ~/.bashrc || ..."
            "nvim_sync" → "nvim --headless +PackerSync +qa"
            "echo hello" → "echo hello" (unchanged)
        """
        if not hook:
            return None

        # Check if it's an alias
        if hook in HOOK_ALIASES:
            return HOOK_ALIASES[hook]

        return hook

    def get_repo_path(self, local_path: Path, repo_dir: Path) -> Path:
        """Get the repository path for a local path."""
        if self.repo_path:
            # Explicit repo_path for single files
            return repo_dir / self.repo_path
        # Use repo_base + filename
        return repo_dir / self.repo_base / local_path.name

    def to_dict(self) -> dict[str, Any]:
        """Convert section to dictionary (only non-default values)."""
        result: dict[str, Any] = {
            "paths": [str(p) for p in self.paths],
        }

        # Only include if non-default or explicitly set
        if self.repo_path:
            result["repo_path"] = self.repo_path
        elif self.repo_base != self._generate_repo_base():
            # Only save repo_base if it differs from auto-generated
            result["repo_base"] = self.repo_base

        if self.secrets_filter is not True:  # Only if NOT default
            result["secrets_filter"] = self.secrets_filter
        if self.update_strategy != "replace":  # Only if NOT default
            result["update_strategy"] = self.update_strategy
        if self.include:
            result["include"] = self.include
        if self.exclude:
            result["exclude"] = self.exclude
        if self.pre_deploy:
            result["pre_deploy"] = self.pre_deploy
        if self.post_deploy:
            result["post_deploy"] = self.post_deploy
        if self.inherits:
            result["inherits"] = self.inherits
        return result


class DotManConfig:
    """Parser for the dot-man.toml configuration file."""

    def __init__(
        self, repo_path: Path | None = None, global_config: GlobalConfig | None = None
    ):
        self._data: dict = {}
        self._repo_path = repo_path or REPO_DIR
        self._path = self._repo_path / DOT_MAN_TOML
        self._global_config = global_config

    @property
    def repo_path(self) -> Path:
        """Get the repository path."""
        return self._repo_path

    def load(self) -> None:
        """Load the dot-man.toml configuration file.

        If dot-man.toml doesn't exist but dot-man.ini does, automatically
        migrates the old INI format to TOML.
        """
        # Check for migration
        if not self._path.exists():
            from .constants import DOT_MAN_INI

            old_path = self._repo_path / DOT_MAN_INI
            if old_path.exists():
                self._migrate_from_ini(old_path)
                return
            raise ConfigurationError(f"Config not found: {self._path}")
        self._data = tomllib.loads(self._path.read_text())

    def _migrate_from_ini(self, old_path: Path) -> None:
        """Migrate from old INI format to TOML."""
        import configparser
        import shutil

        print(f"🔄 Migrating {old_path.name} to TOML format...")

        config = configparser.ConfigParser()
        config.read(old_path)

        # Convert INI to TOML structure
        self._data = {"templates": {}}

        for section_name in config.sections():
            if section_name == "DEFAULT":
                continue

            section_data = dict(config[section_name])

            # Convert old format to new format
            new_section = {}

            # Handle local_path -> paths
            if "local_path" in section_data:
                new_section["paths"] = [section_data["local_path"]]

            # Handle repo_path -> repo_base
            if "repo_path" in section_data:
                new_section["repo_base"] = section_data["repo_path"]

            # Copy other fields
            for key in ["pre_deploy", "post_deploy", "update_strategy"]:
                if key in section_data:
                    new_section[key] = section_data[key]

            # Convert secrets_filter boolean
            if "secrets_filter" in section_data:
                value = section_data["secrets_filter"].lower()
                if value in ("true", "false"):
                    new_section["secrets_filter"] = value == "true"

            # More robust name generation to avoid collisions
            clean_name = section_name
            for prefix in ["~/.", "~/.config/", "~/", "/"]:
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix) :]
            clean_name = clean_name.replace("/", "-").replace(".", "-")

            # Ensure uniqueness
            base_name = clean_name
            counter = 1
            while clean_name in self._data:
                clean_name = f"{base_name}_{counter}"
                counter += 1

            self._data[clean_name] = new_section

        # Backup old file
        backup_path = old_path.with_suffix(".ini.bak")
        shutil.copy(old_path, backup_path)
        print(f"  📦 Backed up old config to {backup_path.name}")

        # Save new TOML
        self.save()
        print(f"  ✓ Created {self._path.name}")

        # Remove old file
        old_path.unlink()
        print(f"  🗑️  Removed old {old_path.name}")

    def save(self) -> None:
        """Save the dot-man.toml configuration file."""
        _write_toml(self._path, self._data)

    def create_default(self) -> None:
        """Create minimal default config with helpful examples."""
        # Start with empty config - examples will be in comments
        self._data = {}
        self.save()

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

    def get_local_templates(self) -> dict:
        """Get templates defined in this file."""
        return self._data.get("templates", {})

    def _resolve_template(self, name: str) -> dict:
        """Resolve a template by name, checking local first then global."""
        # Check local templates
        local = self.get_local_templates().get(name)
        if local:
            return local

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

        # Parse paths
        paths_raw = settings.get("paths", [])
        if isinstance(paths_raw, str):
            paths_raw = [paths_raw]
        paths = [Path(p).expanduser() for p in paths_raw]

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
            inherits=inherits,
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
            "inherits",
            "repo_path",
        ]:
            if key in kwargs and kwargs[key]:
                section_data[key] = kwargs[key]

        self._data[name] = section_data

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
                    "paths", "repo_base", "repo_path", "secrets_filter",
                    "update_strategy", "include", "exclude", "pre_deploy",
                    "post_deploy", "inherits"
                }
                for key in self._data[name]:
                    if key not in valid_keys:
                        warnings.append(f"[{name}]: Unknown key '{key}'")

            except Exception as e:
                warnings.append(f"[{name}]: {e}")

        return warnings


# Backwards compatibility - legacy config support
class LegacyConfigLoader:
    """Helper to migrate from INI to TOML format."""

    @staticmethod
    def migrate_global_conf(old_path: Path, new_path: Path) -> bool:
        """Migrate global.conf to global.toml."""
        import configparser

        if not old_path.exists():
            return False

        config = configparser.ConfigParser()
        config.read(old_path)

        data = {}
        for section in config.sections():
            data[section] = dict(config[section])
            # Convert string booleans
            for key, value in data[section].items():
                if value.lower() in ("true", "false"):
                    data[section][key] = value.lower() == "true"

        _write_toml(new_path, data)
        return True
