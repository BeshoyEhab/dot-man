"""Constants and default values for dot-man."""

import os
from pathlib import Path

# ============================================================================
# Paths
# ============================================================================

# Base directory for dot-man data (can override with DOT_MAN_DIR env var)
_dot_man_dir = os.environ.get("DOT_MAN_DIR") or str(Path.home() / ".config" / "dot-man")
DOT_MAN_DIR = Path(_dot_man_dir)

# Repository directory (git-backed)
REPO_DIR = DOT_MAN_DIR / "repo"

# Backups directory
BACKUPS_DIR = DOT_MAN_DIR / "backups"

# Global configuration file
GLOBAL_TOML = DOT_MAN_DIR / "global.toml"

# Branch-specific configuration file (inside repo)
DOT_MAN_TOML = "dot-man.toml"
DOT_MAN_YAML = "dot-man.yaml"
DOT_MAN_YML = "dot-man.yml"

# Priority order for config files (first match wins)
CONFIG_FILE_PRIORITY = [DOT_MAN_TOML, DOT_MAN_YAML, DOT_MAN_YML]

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

# Default ignored directories for file operations
DEFAULT_IGNORED_DIRECTORIES = [
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "target",
    "venv",
    "env",
    ".env",
    ".idea",
    ".vscode",
]

# Hook aliases - short names for common commands
# Placeholders:
#   {qs_config} - Quickshell config directory name (e.g., "ii", "caelestea")
HOOK_ALIASES = {
    "shell_reload": "source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true",
    "nvim_sync": "nvim --headless +PackerSync +qa 2>/dev/null || true",
    "hyprland_reload": "hyprctl reload 2>/dev/null || true",
    "fish_reload": "source ~/.config/fish/config.fish 2>/dev/null || true",
    "tmux_reload": "tmux source-file ~/.tmux.conf 2>/dev/null || true",
    "kitty_reload": "killall -SIGUSR1 kitty 2>/dev/null || true",
    # Quickshell hooks - use {qs_config} for auto-detected config directory
    "quickshell_reload": "killall qs 2>/dev/null; sleep 0.3; qs -c {qs_config} &",
    "quickshell_restart": "killall qs 2>/dev/null; sleep 0.5; qs -c {qs_config} &",
    "quickshell_validate": "qs -c {qs_config} --check 2>/dev/null || true",
}

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

# Lock file to prevent concurrent operations
LOCK_FILE = DOT_MAN_DIR / ".lock"
