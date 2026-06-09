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

# Hook aliases - canonical source of all known reload hooks.
# Placeholders ({section_name}, {config_name}, {config_root}, {paths}, {branch})
# are resolved at runtime by Section._resolve_hook().
HOOK_ALIASES = {
    # Shells
    "shell_reload": "source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true",
    "bash_reload": "source ~/.bashrc 2>/dev/null || true",
    "zsh_reload": "source ~/.zshrc 2>/dev/null || true",
    "fish_reload": "source ~/.config/fish/config.fish 2>/dev/null || true",
    # Editors
    "nvim_sync": "nvim --headless +PackerSync +qa 2>/dev/null || true",
    "vim_reload": "vim +source\\ ~/.vimrc +qa 2>/dev/null || true",
    "emacs_reload": "emacsclient -e '(load-file \"~/.emacs.d/init.el\")' 2>/dev/null || true",
    "doom_reload": "~/.emacs.d/bin/doom-refresh 2>/dev/null || true",
    # Window managers
    "hyprland_reload": "hyprctl reload 2>/dev/null || true",
    "sway_reload": "swaymsg reload 2>/dev/null || true",
    "i3_reload": "i3-msg reload 2>/dev/null || true",
    "awesome_reload": "awesome-client 'awesome.restart()' 2>/dev/null || true",
    # Terminals
    "kitty_reload": "killall -SIGUSR1 kitty 2>/dev/null || true",
    "alacritty_reload": "killall -SIGUSR1 alacritty 2>/dev/null || true",
    "wezterm_reload": "wezterm inject-term-change 'reload' 2>/dev/null || true",
    # Status bars
    "polybar_reload": "pkill polybar 2>/dev/null; sleep 0.2; polybar -c ~/.config/polybar/config.ini top 2>/dev/null &",
    "waybar_reload": "waybar-control reload 2>/dev/null || pkill waybar 2>/dev/null; sleep 0.2; waybar 2>/dev/null &",
    # Misc tools
    "tmux_reload": "tmux source-file ~/.tmux.conf 2>/dev/null || true",
    "dunst_reload": "pkill dunst 2>/dev/null; sleep 0.2; dunst 2>/dev/null &",
    "picom_reload": "pkill picom 2>/dev/null; sleep 0.2; picom -b 2>/dev/null &",
    "xreload": "xrdb -load ~/.Xresources 2>/dev/null || true",
    "gnome_reload": "gsettings reset-recursively org.gnome.shell 2>/dev/null || true",
    "kde_reload": "qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true",
    "ssh_reload": "ssh-add -l >/dev/null 2>&1 || true",
    "git_reload": "git config --global --list >/dev/null 2>&1 || true",
    "starship_reload": 'eval "$(starship config 2>/dev/null)" || true',
    "fzf_reload": "killall fzf 2>/dev/null; source ~/.fzf.bash 2>/dev/null || source ~/.fzf.zsh 2>/dev/null || true",
    "exaile_reload": "dbus-send --print-reply --dest=org.exaile.Exaile /org/exaile/Exaile org.exaile.Exaile.Quit 2>/dev/null || true",
    # Quickshell hooks
    "quickshell_reload": "killall qs 2>/dev/null; sleep 0.3; qs -c {config_name} &",
    "quickshell_restart": "killall qs 2>/dev/null; sleep 0.5; qs -c {config_name} &",
    "quickshell_validate": "qs -c {config_name} --check 2>/dev/null || true",
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
