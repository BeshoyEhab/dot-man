"""Configuration parsing for dot-man using TOML/YAML formats.

This module re-exports all config classes from their split modules.
New code should import from the specific modules directly:

    from dot_man.global_config import GlobalConfig
    from dot_man.section import Section
    from dot_man.dotman_config import DotManConfig
"""

# Re-export everything for backward compatibility
# Also re-export constants that were previously available via config imports
from .constants import DOT_MAN_TOML, GLOBAL_TOML, REPO_DIR  # noqa: F401
from .dotman_config import DotManConfig  # noqa: F401
from .global_config import GlobalConfig, _write_toml  # noqa: F401
from .section import Section  # noqa: F401

__all__ = [
    "GlobalConfig",
    "Section",
    "DotManConfig",
    "_write_toml",
]
