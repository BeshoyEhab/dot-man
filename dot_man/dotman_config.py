"""DotMan configuration file parser (TOML/YAML)."""

__all__ = ["DotManConfig", "VALID_SECTION_KEYS"]

import logging
from pathlib import Path
from typing import Any, cast

from . import ui
from .constants import (
    CONFIG_FILE_PRIORITY,
    DOT_MAN_TOML,
    REPO_DIR,
)
from .exceptions import ConfigurationError, ConfigValidationError
from .global_config import (
    GlobalConfig,
    load_config_file,
    substitute_templates,
    write_config_file,
)
from .section import Section

VALID_SECTION_KEYS = {
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
    "deploy_method",
    "encrypted",
    "encryption_method",
    "encryption_recipient",
    "shared",
}
"""Canonical set of valid keys for section config."""


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
        self._data, self._doc = load_config_file(self._path)
        self._dirty = False

        warnings = self._validate_schema()
        for w in warnings:
            logging.warning(f"Config warning: {w}")
            # Surface on the console too: nothing reads the log file during
            # normal runs, so a logging-only warning stays invisible.
            ui.warn(f"Config warning: {w}")

    def _validate_schema(self) -> list[str]:
        """Validate config structure on load."""
        warnings: list[str] = []

        for name, section in self._data.items():
            if name in ("templates", "secrets"):
                continue
            if isinstance(section, dict):
                for key in section:
                    if key not in VALID_SECTION_KEYS:
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

        # Append a short pointer: two examples, current commands, docs link.
        # (Smart defaults cover everything else — see `dot-man config defaults`.)
        with open(self._path, "a") as f:
            f.write("""
# dot-man — track files with `dot-man add <path>`, switch with `dot-man navigate <branch>`.
# Uncomment an example to start; smart defaults cover the rest.
#
# [bashrc]
# paths = ["~/.bashrc"]
#
# [nvim]
# paths = ["~/.config/nvim"]
#
# Full reference: https://beshoyehab.github.io/dot-man/
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

    def _render_section_templates(self, name: str, settings: dict) -> dict:
        """Render `{{VAR}}` templates in string settings (two passes).

        Pass 1 renders `paths` with section name, branch, and machine
        variables; pass 2 derives `config_name`/`config_root` from the
        rendered first path and renders every other string value (and
        string items in lists) with the full context. Unknown variables
        pass through literally.
        """
        import os

        base = {"section_name": name, "branch": Section._get_current_branch()}

        rendered = dict(settings)
        paths_raw = rendered.get("paths", [])
        single = isinstance(paths_raw, str)
        rendered_paths = [
            substitute_templates(p, dict(base))
            for p in ([paths_raw] if single else paths_raw)
        ]
        rendered["paths"] = rendered_paths[0] if single else rendered_paths

        first = rendered_paths[0] if rendered_paths else ""
        expanded = os.path.expandvars(os.path.expanduser(first))
        full = {
            **base,
            "config_name": Path(expanded).name,
            "config_root": str(Path(expanded).parent),
            "paths": " ".join(rendered_paths),
        }

        for key, value in rendered.items():
            if key == "paths":
                continue
            if isinstance(value, str):
                rendered[key] = substitute_templates(value, dict(full))
            elif isinstance(value, list):
                rendered[key] = [
                    substitute_templates(v, dict(full)) if isinstance(v, str) else v
                    for v in value
                ]
        return rendered

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

        # Render {{ }} template variables with section context so values
        # like hooks and paths can use {{section_name}}/{{config_name}}.
        settings = self._render_section_templates(name, settings)

        # Parse paths with environment variable expansion
        import os

        paths_raw = settings.get("paths", [])
        if isinstance(paths_raw, str):
            raise ConfigValidationError(
                f"Section [{name}] paths must be a list of strings, not a "
                f'bare string: set paths = ["{paths_raw}"]'
            )
        paths = [Path(os.path.expandvars(os.path.expanduser(p))) for p in paths_raw]

        if not paths:
            raise ConfigValidationError(f"Section [{name}] must have at least one path")

        # update_strategy and deploy_method are validated by Section itself,
        # so invalid values fail with ConfigValidationError either way.

        # Build Section object
        return Section(
            name=name,
            paths=paths,
            repo_base=settings.get("repo_base", name),
            repo_path=settings.get("repo_path"),
            secrets_filter=settings.get("secrets_filter", True),
            update_strategy=settings.get("update_strategy", "replace"),
            include=settings.get("include", []),
            exclude=settings.get("exclude", []),
            pre_deploy=settings.get("pre_deploy"),
            post_deploy=settings.get("post_deploy"),
            on_activate=settings.get("on_activate"),
            on_deactivate=settings.get("on_deactivate"),
            inherits=inherits,
            ignored_directories=settings.get("ignored_directories"),
            follow_symlinks=settings.get("follow_symlinks"),
            deploy_method=settings.get("deploy_method", "copy"),
            shared=settings.get("shared", False),
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
        for key in VALID_SECTION_KEYS - {"paths", "repo_base"}:
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

        for key, value in kwargs.items():
            if key not in VALID_SECTION_KEYS:
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
                for key in self._data[name]:
                    if key not in VALID_SECTION_KEYS:
                        warnings.append(f"[{name}]: Unknown key '{key}'")

            except Exception as e:
                warnings.append(f"[{name}]: {e}")

        return warnings
