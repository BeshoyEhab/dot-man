"""Configuration parsing for dot-man using TOML format.

This module re-exports all config classes from their split modules
for backward compatibility. New code should import from the specific
modules directly:

    from dot_man.global_config import GlobalConfig
    from dot_man.section import Section
    from dot_man.dotman_config import DotManConfig, LegacyConfigLoader
"""

# Re-export everything for backward compatibility
from .global_config import GlobalConfig, _write_toml  # noqa: F401
from .section import Section  # noqa: F401
from .dotman_config import DotManConfig, LegacyConfigLoader  # noqa: F401

# Also re-export constants that were previously available via config imports
from .constants import REPO_DIR, GLOBAL_TOML, DOT_MAN_TOML  # noqa: F401

__all__ = [
    "GlobalConfig",
    "Section",
    "DotManConfig",
    "LegacyConfigLoader",
    "_write_toml",
]
