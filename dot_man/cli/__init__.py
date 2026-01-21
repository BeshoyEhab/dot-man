"""dot-man CLI package.

This package provides the CLI entry point for dot-man.
It exposes the modular CLI implementation.
"""

from .main import main
from .interface import cli
from .common import (
    error,
    success,
    warn,
    require_init,
    DotManGroup,
    complete_branches,
    get_secret_handler,
)

# Import commands for easier access and backward compatibility
from .init_cmd import init
from .add_cmd import add
from .status_cmd import status
from .switch_cmd import switch
from .deploy_cmd import deploy
from .edit_cmd import edit
from .audit_cmd import audit
from .backup_cmd import backup
from .branch_cmd import branch
from .remote_cmd import remote, sync
from .tui_cmd import tui
from .config_cmd import config

__all__ = [
    'main',
    'cli',
    'error',
    'success',
    'warn',
    'require_init',
    'DotManGroup',
    'complete_branches',
    'get_secret_handler',
    # Commands
    'init',
    'add',
    'status',
    'switch',
    'deploy',
    'edit',
    'audit',
    'backup',
    'branch',
    'remote',
    'sync',
    'tui',
    'config',
]
