"""dot-man CLI package.

This package provides the CLI entry point for dot-man.
It exposes the modular CLI implementation.
"""

from .add_cmd import add
from .audit_cmd import audit
from .backup_cmd import backup
from .branch_cmd import branch
from .clean_cmd import clean
from .common import (
    DotManGroup,
    complete_branches,
    error,
    get_secret_handler,
    require_init,
    success,
    warn,
)
from .config_cmd import config
from .deploy_cmd import deploy
from .doctor_cmd import doctor
from .edit_cmd import edit

# Import commands for easier access and backward compatibility
from .init_cmd import init
from .interface import cli
from .log_cmd import checkout, diff, log
from .main import main
from .navigate_cmd import hooks, navigate
from .profile_cmd import profile
from .remote_cmd import remote, sync
from .restore_cmd import restore
from .revert_cmd import revert
from .show_cmd import show
from .status_cmd import status
from .switch_cmd import switch
from .tag_cmd import tag
from .template_cmd import template
from .tui_cmd import tui
from .verify_cmd import verify

__all__ = [
    "main",
    "cli",
    "error",
    "success",
    "warn",
    "require_init",
    "DotManGroup",
    "complete_branches",
    "get_secret_handler",
    "init",
    "add",
    "status",
    "switch",
    "deploy",
    "edit",
    "audit",
    "backup",
    "branch",
    "remote",
    "sync",
    "tui",
    "config",
    "revert",
    "restore",
    "clean",
    "doctor",
    "verify",
    "log",
    "show",
    "checkout",
    "diff",
    "tag",
    "template",
    "profile",
    "navigate",
    "hooks",
]
