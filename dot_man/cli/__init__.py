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
    BRANCH,
    DotManGroup,
    _clear_completion_cache,
    _set_git_runner,
    complete_branches,
    complete_commits,
    complete_config_keys,
    complete_profiles,
    complete_sections,
    complete_switch_args,
    complete_tags,
    complete_template_keys,
    error,
    get_secret_handler,
    parse_branch_arg,
    require_init,
    success,
    warn,
)
from .completions_cmd import completions
from .config_cmd import config
from .deploy_cmd import deploy
from .discover_cmd import discover_cmd
from .doctor_cmd import doctor
from .edit_cmd import edit
from .encrypt_cmd import encrypt_cmd
from .export_cmd import export_cmd
from .import_cmd import import_cmd

# Import commands for easier access and backward compatibility
from .init_cmd import init
from .interface import cli
from .log_cmd import checkout, diff, log
from .main import main
from .navigate_cmd import hooks, navigate
from .onboarding import is_first_run, mark_onboarded, run_onboarding
from .profile_cmd import profile
from .remote_cmd import remote, sync
from .restore_cmd import restore
from .revert_cmd import revert
from .rollback_cmd import rollback
from .show_cmd import show
from .status_cmd import status
from .switch_cmd import switch
from .tag_cmd import tag
from .template_cmd import template
from .tui_cmd import tui
from .verify_cmd import verify
from .watch_cmd import watch

__all__ = [
    "main",
    "cli",
    "error",
    "success",
    "warn",
    "require_init",
    "DotManGroup",
    "complete_branches",
    "complete_tags",
    "complete_commits",
    "complete_template_keys",
    "complete_config_keys",
    "complete_profiles",
    "complete_sections",
    "complete_switch_args",
    "BRANCH",
    "parse_branch_arg",
    "get_secret_handler",
    "_set_git_runner",
    "_clear_completion_cache",
    "run_onboarding",
    "is_first_run",
    "mark_onboarded",
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
    "import_cmd",
    "export_cmd",
    "encrypt_cmd",
    "discover_cmd",
    "completions",
    "watch",
    "rollback",
]
