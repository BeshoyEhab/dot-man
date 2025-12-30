"""Constants and default values for dot-man."""

from pathlib import Path

# ============================================================================
# Paths
# ============================================================================

# Base directory for dot-man data
DOT_MAN_DIR = Path.home() / ".config" / "dot-man"

# Repository directory (git-backed)
REPO_DIR = DOT_MAN_DIR / "repo"

# Backups directory
BACKUPS_DIR = DOT_MAN_DIR / "backups"

# Global configuration file
GLOBAL_TOML = DOT_MAN_DIR / "global.toml"

# Legacy config file (for migration)
GLOBAL_CONF = DOT_MAN_DIR / "global.conf"

# Branch-specific configuration file (inside repo)
DOT_MAN_TOML = "dot-man.toml"

# Legacy config file (for migration)  
DOT_MAN_INI = "dot-man.ini"

# Template variables storage
TEMPLATE_VARS_FILE = DOT_MAN_DIR / "template_vars.json"

# ============================================================================
# Git Configuration
# ============================================================================

DEFAULT_BRANCH = "main"
DEFAULT_REMOTE = "origin"

# Files to ignore in git
GIT_IGNORE_PATTERNS = [
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*~",
    "*.pyc",
    "__pycache__/",
]

# ============================================================================
# Configuration Defaults
# ============================================================================

DEFAULT_UPDATE_STRATEGY = "replace"  # replace, rename_old, ignore
VALID_UPDATE_STRATEGIES = ["replace", "rename_old", "ignore"]

# ============================================================================
# Secret Detection Patterns
# ============================================================================

# See secrets.py for full implementation
SECRET_REDACTION_TEXT = "***REDACTED***"
DOTMAN_REDACTION_TEXT = "***REDACTED_BY_DOTMAN***"

# ============================================================================
# UI/Output
# ============================================================================

MAX_BACKUPS = 5
FILE_PERMISSIONS = 0o700  # Secure directory permissions
