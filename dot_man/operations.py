"""Core operations for dot-man - modular business logic.

This module provides the DotManOperations class which is the central API
for all dot-man operations. The actual business logic is split into
focused mixin modules:

    - save_deploy_ops.py: Save/deploy operations and deployment plans
    - branch_ops.py: Branch switching and file revert
    - status_ops.py: Audit, status, and orphan management

The DotManOperations class inherits from all mixins and adds:
    - Lazy-loaded properties (global_config, dotman_config, git, vault, backups)
    - Section iteration and pattern matching utilities
    - Singleton management (get_operations, reset_operations)
"""

from pathlib import Path
from typing import Iterator, Any, Optional, TypedDict
import os

from .config import GlobalConfig, DotManConfig, Section
from .core import GitManager
from .files import get_file_status
from .constants import REPO_DIR
from .vault import SecretVault
from .backups import BackupManager

# Import mixins
from .save_deploy_ops import SaveDeployMixin, LOCK_FILE  # noqa: F401 (re-exported)
from .branch_ops import BranchMixin
from .status_ops import StatusMixin
from .lock import FileLock  # noqa: F401 (re-exported for test_lock.py)


class DeploymentPlan(TypedDict):
    sections_to_deploy: list[tuple[Section, Path, Path]]
    pre_hooks: list[str]
    post_hooks: list[str]
    errors: list[str]


class DotManOperations(SaveDeployMixin, BranchMixin, StatusMixin):
    """
    Centralized operations class that handles all dot-man business logic.
    
    This provides a clean API for CLI, TUI, and any future interfaces.
    All operations go through this class to ensure consistency.
    """
    
    def __init__(self):
        self._global_config: Optional[GlobalConfig] = None
        self._dotman_config: Optional[DotManConfig] = None
        self._git: Optional[GitManager] = None
        self._vault: Optional[SecretVault] = None
        self._backups: Optional[BackupManager] = None

    @property
    def backups(self) -> BackupManager:
        """Get or load backup manager."""
        if self._backups is None:
            self._backups = BackupManager()
        return self._backups
    
    @property
    def vault(self) -> SecretVault:
        """Get or load secret vault."""
        if self._vault is None:
            self._vault = SecretVault()
        return self._vault

    @property
    def global_config(self) -> GlobalConfig:
        """Get or load global configuration."""
        if self._global_config is None:
            self._global_config = GlobalConfig()
            self._global_config.load()
        return self._global_config
    
    @property
    def dotman_config(self) -> DotManConfig:
        """Get or load dot-man configuration for current branch."""
        if self._dotman_config is None:
            self._dotman_config = DotManConfig(global_config=self.global_config)
            self._dotman_config.load()
        return self._dotman_config
    
    @property
    def git(self) -> GitManager:
        """Get git manager."""
        if self._git is None:
            self._git = GitManager()
        return self._git
    
    def reload_config(self) -> None:
        """Reload configurations (e.g., after branch switch)."""
        self._dotman_config = None  # Force reload on next access
    
    @property
    def current_branch(self) -> str:
        """Get current branch name."""
        return self.global_config.current_branch
    
    def get_sections(self) -> list[str]:
        """Get all section names in current branch."""
        return self.dotman_config.get_section_names()
    
    def get_section(self, name: str) -> Section:
        """Get a resolved section by name."""
        return self.dotman_config.get_section(name)
    
    def iter_section_paths(self, section: Section) -> Iterator[tuple[Path, Path, str]]:
        """
        Iterate over all paths in a section with their status.
        
        Yields:
            (local_path, repo_path, status)
        """
        for local_path in section.paths:
            repo_path = section.get_repo_path(local_path, REPO_DIR)
            
            if local_path.is_dir():
                # For directories, iterate over files inside
                if local_path.exists():
                    excludes = (section.exclude or []) + (section.ignored_directories or [])

                    for root, dirs, files in os.walk(local_path, followlinks=section.follow_symlinks):
                        root_path = Path(root)

                        if excludes:
                            try:
                                root_rel = root_path.relative_to(local_path)
                            except ValueError:
                                continue

                            for i in range(len(dirs) - 1, -1, -1):
                                d_name = dirs[i]
                                d_rel = root_rel / d_name
                                if self._matches_patterns(d_rel, excludes):
                                    del dirs[i]

                        for file in files:
                            local_file = root_path / file
                            rel = local_file.relative_to(local_path)

                            if excludes and self._matches_patterns(rel, excludes):
                                continue
                            if section.include and not self._matches_patterns(rel, section.include):
                                continue
                            
                            repo_file = repo_path / rel
                            status = get_file_status(local_file, repo_file)
                            yield local_file, repo_file, status
                
                # Also check repo for files that might be deleted locally
                if repo_path.exists():
                    excludes = (section.exclude or []) + (section.ignored_directories or [])

                    for repo_file in repo_path.rglob("*"):
                        if repo_file.is_file():
                            rel = repo_file.relative_to(repo_path)
                            local_file = local_path / rel
                            
                            if excludes and self._matches_patterns(rel, excludes):
                                continue
                            if section.include and not self._matches_patterns(rel, section.include):
                                continue
                                
                            if not local_file.exists():
                                yield local_file, repo_file, "DELETED"
            else:
                # Single file
                status = get_file_status(local_path, repo_path)
                yield local_path, repo_path, status
    
    def _matches_patterns(self, path: Path, patterns: list[str]) -> bool:
        """Check if path matches any pattern."""
        from fnmatch import fnmatch
        name = path.name
        for pattern in patterns:
            if fnmatch(name, pattern) or fnmatch(str(path), pattern):
                return True
        return False


# ─── Singleton Management ──────────────────────────────────

_operations: Optional[DotManOperations] = None


def get_operations() -> DotManOperations:
    """Get the shared operations instance."""
    global _operations
    if _operations is None:
        _operations = DotManOperations()
    return _operations


def reset_operations() -> None:
    """Reset the operations instance (e.g., after reinitializing)."""
    global _operations
    _operations = None
