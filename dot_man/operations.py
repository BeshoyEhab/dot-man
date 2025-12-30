"""Core operations for dot-man - modular business logic."""

from pathlib import Path
from typing import Iterator

from .config import GlobalConfig, DotManConfig, Section
from .core import GitManager
from .files import copy_file, copy_directory, compare_files, get_file_status, backup_file
from .secrets import SecretScanner, SecretMatch
from .constants import REPO_DIR
from .exceptions import DotManError, ConfigurationError


class DotManOperations:
    """
    Centralized operations class that handles all dot-man business logic.
    
    This provides a clean API for CLI, TUI, and any future interfaces.
    All operations go through this class to ensure consistency.
    """
    
    def __init__(self):
        self._global_config: GlobalConfig | None = None
        self._dotman_config: DotManConfig | None = None
        self._git: GitManager | None = None
    
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
                    for local_file in local_path.rglob("*"):
                        if local_file.is_file():
                            # Apply include/exclude patterns
                            rel = local_file.relative_to(local_path)
                            if section.exclude and self._matches_patterns(rel, section.exclude):
                                continue
                            if section.include and not self._matches_patterns(rel, section.include):
                                continue
                            
                            repo_file = repo_path / rel
                            status = get_file_status(local_file, repo_file)
                            yield local_file, repo_file, status
                
                # Also check repo for files that might be deleted locally
                if repo_path.exists():
                    for repo_file in repo_path.rglob("*"):
                        if repo_file.is_file():
                            rel = repo_file.relative_to(repo_path)
                            local_file = local_path / rel
                            
                            if section.exclude and self._matches_patterns(rel, section.exclude):
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
    
    def save_section(self, section: Section) -> tuple[int, list[SecretMatch]]:
        """
        Save a section from local to repo.
        
        Returns:
            (files_saved, secrets_detected)
        """
        saved = 0
        all_secrets: list[SecretMatch] = []
        
        for local_path in section.paths:
            if not local_path.exists():
                continue
            
            repo_path = section.get_repo_path(local_path, REPO_DIR)
            
            if local_path.is_file():
                success, secrets = copy_file(
                    local_path, repo_path, 
                    filter_secrets_enabled=section.secrets_filter
                )
                if success:
                    saved += 1
                all_secrets.extend(secrets)
            else:
                files_copied, _, secrets = copy_directory(
                    local_path, repo_path,
                    filter_secrets_enabled=section.secrets_filter,
                    include_patterns=section.include,
                    exclude_patterns=section.exclude,
                )
                saved += files_copied
                all_secrets.extend(secrets)
        
        return saved, all_secrets
    
    def deploy_section(self, section: Section) -> tuple[int, bool]:
        """
        Deploy a section from repo to local.
        
        Returns:
            (files_deployed, had_changes)
        """
        deployed = 0
        had_changes = False
        
        for local_path in section.paths:
            repo_path = section.get_repo_path(local_path, REPO_DIR)
            # Handle update strategy
            if section.update_strategy == "ignore" and local_path.exists():
                continue
            
            # Check if will change (after strategy filtering)
            will_change = not local_path.exists() or not compare_files(repo_path, local_path)
            if will_change:
                had_changes = True
            
            if section.update_strategy == "rename_old" and local_path.exists():
                backup_file(local_path)
            
            if repo_path.is_file():
                success, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                if success:
                    deployed += 1
            else:
                files_copied, _, _ = copy_directory(
                    repo_path, local_path,
                    filter_secrets_enabled=False,
                    include_patterns=section.include,
                    exclude_patterns=section.exclude,
                )
                deployed += files_copied
        
        return deployed, had_changes
    
    def save_all(self) -> tuple[int, list[SecretMatch]]:
        """Save all sections from local to repo."""
        total_saved = 0
        all_secrets: list[SecretMatch] = []
        
        for section_name in self.get_sections():
            section = self.get_section(section_name)
            saved, secrets = self.save_section(section)
            total_saved += saved
            all_secrets.extend(secrets)
        
        return total_saved, all_secrets
    
    def deploy_all(self) -> tuple[int, list[str], list[str]]:
        """
        Deploy all sections from repo to local.
        
        Returns:
            (files_deployed, pre_hooks, post_hooks)
        """
        total_deployed = 0
        pre_hooks: list[str] = []
        post_hooks: list[str] = []
        
        for section_name in self.get_sections():
            section = self.get_section(section_name)
            deployed, had_changes = self.deploy_section(section)
            total_deployed += deployed
            
            if had_changes:
                if section.pre_deploy:
                    pre_hooks.append(section.pre_deploy)
                if section.post_deploy:
                    post_hooks.append(section.post_deploy)
        
        return total_deployed, list(dict.fromkeys(pre_hooks)), list(dict.fromkeys(post_hooks))
    
    def switch_branch(self, target_branch: str, dry_run: bool = False) -> dict:
        """
        Switch to a different branch.
        
        Returns dict with:
            - saved_count: files saved from current branch
            - deployed_count: files deployed from target branch
            - secrets_redacted: number of secrets redacted
            - pre_hooks: list of pre-deploy commands
            - post_hooks: list of post-deploy commands
            - created_branch: True if branch was newly created
        """
        current_branch = self.current_branch
        result = {
            "saved_count": 0,
            "deployed_count": 0,
            "secrets_redacted": 0,
            "pre_hooks": [],
            "post_hooks": [],
            "created_branch": False,
        }
        
        if current_branch == target_branch and not dry_run:
            return result
        
        # Phase 1: Save current branch
        if not dry_run:
            saved, secrets = self.save_all()
            result["saved_count"] = saved
            result["secrets_redacted"] = len(secrets)
            
            # Commit
            commit_msg = f"Auto-save from '{current_branch}' before switch to '{target_branch}'"
            self.git.commit(commit_msg)
        
        # Phase 2: Switch git branch
        branch_exists = self.git.branch_exists(target_branch)
        result["created_branch"] = not branch_exists
        
        if not dry_run:
            self.git.checkout(target_branch, create=not branch_exists)
            
            # Reload config for new branch
            self.reload_config()
        
        # Phase 3: Deploy target branch
        if not dry_run:
            # Collect hooks for sections that will change
            for section_name in self.get_sections():
                section = self.get_section(section_name)
                for local_path in section.paths:
                    repo_path = section.get_repo_path(local_path, REPO_DIR)
                    if repo_path.exists():
                        will_change = not local_path.exists() or not compare_files(repo_path, local_path)
                        if will_change:
                            if section.pre_deploy:
                                result["pre_hooks"].append(section.pre_deploy)
                            if section.post_deploy:
                                result["post_hooks"].append(section.post_deploy)
            
            # Deduplicate hooks
            result["pre_hooks"] = list(dict.fromkeys(result["pre_hooks"]))
            result["post_hooks"] = list(dict.fromkeys(result["post_hooks"]))
            
            # Deploy
            deployed, _, _ = self.deploy_all()
            result["deployed_count"] = deployed
            
            # Update global config
            self.global_config.current_branch = target_branch
            self.global_config.save()
        
        return result
    
    def audit(self) -> list[tuple[str, list[SecretMatch]]]:
        """
        Scan all sections for secrets.
        
        Returns:
            List of (section_name, matches) tuples
        """
        scanner = SecretScanner()
        results: list[tuple[str, list[SecretMatch]]] = []
        
        for section_name in self.get_sections():
            section = self.get_section(section_name)
            section_matches: list[SecretMatch] = []
            
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                
                if repo_path.is_file() and repo_path.exists():
                    matches = list(scanner.scan_file(repo_path))
                    section_matches.extend(matches)
                elif repo_path.is_dir() and repo_path.exists():
                    matches = list(scanner.scan_directory(repo_path))
                    section_matches.extend(matches)
            
            if section_matches:
                results.append((section_name, section_matches))
        
        return results
    
    def get_status_summary(self) -> dict:
        """
        Get a summary of current status.
        
        Returns dict with:
            - branch: current branch name
            - sections: number of sections
            - total_paths: total paths tracked
            - modified: number of modified files
            - new: number of new files
            - deleted: number of deleted files
        """
        summary = {
            "branch": self.current_branch,
            "sections": 0,
            "total_paths": 0,
            "modified": 0,
            "new": 0,
            "deleted": 0,
            "identical": 0,
        }
        
        section_names = self.get_sections()
        summary["sections"] = len(section_names)
        
        for section_name in section_names:
            section = self.get_section(section_name)
            summary["total_paths"] += len(section.paths)
            
            for _, _, status in self.iter_section_paths(section):
                if status == "MODIFIED":
                    summary["modified"] += 1
                elif status == "NEW":
                    summary["new"] += 1
                elif status == "DELETED":
                    summary["deleted"] += 1
                else:
                    summary["identical"] += 1
        
        return summary


# Singleton instance for convenience
_operations: DotManOperations | None = None


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
