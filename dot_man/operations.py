"""Core operations for dot-man - modular business logic."""

from pathlib import Path
from typing import Iterator, Callable, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import GlobalConfig, DotManConfig, Section
from .core import GitManager
from .files import copy_file, copy_directory, compare_files, get_file_status, backup_file
from .secrets import SecretScanner, SecretMatch
from .constants import REPO_DIR
from .exceptions import DotManError, ConfigurationError, PermissionError, DeploymentError
from .vault import SecretVault
from .backups import BackupManager


class DotManOperations:
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
    
    def save_section(
        self, 
        section: Section,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None
    ) -> tuple[int, list[SecretMatch], list[str]]:
        """
        Save a section from local to repo.
        
        Returns:
            (files_saved, secrets_detected, errors)
        """
        saved = 0
        all_secrets: list[SecretMatch] = []
        errors: list[str] = []
        
        # Enhanced secret handler that also stashes to vault
        def wrapped_handler(match: SecretMatch) -> str:
            action = "REDACT"
            if secret_handler:
                action = secret_handler(match)

            if action == "REDACT":
                # Stash to vault
                try:
                    secret_hash = self.vault.stash_secret(
                        file_path=str(match.file),
                        line_number=match.line_number,
                        pattern_name=match.pattern_name,
                        secret_value=match.matched_text,
                        branch=self.current_branch
                    )
                    # Return formatted redaction string with hash
                    return f"***REDACTED:{secret_hash}***"
                except (OSError, IOError) as e:
                    errors.append(f"Failed to stash secret in vault: {e}")
                    # Fallback to standard redaction if vault fails
                    from .constants import SECRET_REDACTION_TEXT
                    return SECRET_REDACTION_TEXT

            return action

        for local_path in section.paths:
            if not local_path.exists():
                continue
            
            repo_path = section.get_repo_path(local_path, REPO_DIR)
            
            try:
                if local_path.is_file():
                    success, secrets = copy_file(
                        local_path, repo_path, 
                        filter_secrets_enabled=section.secrets_filter,
                        secret_handler=wrapped_handler
                    )
                    if success:
                        saved += 1
                    all_secrets.extend(secrets)
                else:
                    files_copied, files_failed, secrets = copy_directory(
                        local_path, repo_path,
                        filter_secrets_enabled=section.secrets_filter,
                        include_patterns=section.include,
                        exclude_patterns=section.exclude,
                        secret_handler=wrapped_handler,
                    )
                    saved += files_copied
                    all_secrets.extend(secrets)
                    if files_failed > 0:
                        errors.append(f"Failed to copy {files_failed} files in {local_path}")
            except (OSError, IOError, PermissionError) as e:
                errors.append(f"Error processing {local_path}: {e}")
        
        return saved, all_secrets, errors
    
    def deploy_section(self, section: Section) -> tuple[int, bool, list[str]]:
        """
        Deploy a section from repo to local.
        
        Returns:
            (files_deployed, had_changes, errors)
        """
        deployed = 0
        had_changes = False
        errors: list[str] = []
        
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
            
            # Helper to restore secrets after copy
            def restore_file_secrets(dest_path: Path):
                try:
                    content = dest_path.read_text(encoding="utf-8")
                    restored = self.vault.restore_secrets_in_content(
                        content, str(local_path), self.current_branch
                    )
                    if restored != content:
                        dest_path.write_text(restored, encoding="utf-8")
                except (OSError, UnicodeDecodeError) as e:
                    errors.append(f"Failed to restore secrets for {dest_path}: {e}")

            try:
                if repo_path.is_file():
                    success, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                    if success:
                        if section.secrets_filter:
                            restore_file_secrets(local_path)
                        deployed += 1
                else:
                    files_copied, files_failed, _ = copy_directory(
                        repo_path, local_path,
                        filter_secrets_enabled=False,
                        include_patterns=section.include,
                        exclude_patterns=section.exclude,
                    )
                    # Need to iterate deployed files to restore secrets?
                    # copy_directory doesn't return list of files.
                    # We can iterate destination if successful.
                    if section.secrets_filter:
                        for deployed_file in local_path.rglob("*"):
                            if deployed_file.is_file():
                                restore_file_secrets(deployed_file)

                    deployed += files_copied
                    if files_failed > 0:
                        errors.append(f"Failed to deploy {files_failed} files in {local_path}")
            except PermissionError as e:
                errors.append(f"Permission denied deploying {local_path}. Try running with sudo?")
            except FileNotFoundError as e:
                errors.append(f"File not found during deployment: {local_path}")
            except OSError as e:
                errors.append(f"Error deploying {local_path}: {e}")
        
        return deployed, had_changes, errors
    
    def scan_deployable_changes(self, sections: list[Section]) -> dict:
        """
        Phase 1: Scan for changes and collect hooks (Fast Scan).
        
        Returns:
            dict containing:
            - 'sections_to_deploy': list of (section, local_path, repo_path) tuples
            - 'pre_hooks': list of pre-deploy commands
            - 'post_hooks': list of post-deploy commands
            - 'errors': list of scan errors
        """
        plan = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": []
        }
        
        # Parallel scan could be implemented here, but simple iteration with cached metadata is fast enough
        for section in sections:
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                
                # Handle update strategy
                if section.update_strategy == "ignore" and local_path.exists():
                    continue
                
                try:
                    # Check if will change (using optimized compare_files)
                    will_change = not local_path.exists() or not compare_files(repo_path, local_path)
                    
                    if will_change:
                        plan["sections_to_deploy"].append((section, local_path, repo_path))
                        
                        if section.pre_deploy:
                            plan["pre_hooks"].append(section.pre_deploy)
                        if section.post_deploy:
                            plan["post_hooks"].append(section.post_deploy)
                            
                except OSError as e:
                    plan["errors"].append(f"Error scanning {local_path}: {e}")
                    
        return plan

    def execute_deployment_plan(self, plan: dict) -> dict:
        """
        Phase 2: Execute the deployment plan.
        
        Returns dict with keys: 'deployed', 'pre_hooks', 'post_hooks', 'errors'
        """
        total_deployed = 0
        all_errors: list[str] = list(plan["errors"])
        pre_hooks = list(dict.fromkeys(plan["pre_hooks"]))
        post_hooks = list(dict.fromkeys(plan["post_hooks"]))
        
        # 1. Run Pre-Hooks (BEFORE any file changes)
        # Note: We return them for the caller (CLI/TUI) to run them, OR we run them here?
        # Following existing pattern: CLI runs the hooks returned in the result dict.
        # BUT for `switch_branch` logic inside operations, we might want to know about them.
        # Limitation: operations.py currently usually returns hooks for CLI to run/display.
        # However, to fix the "too late" bug, we must ensure CLI runs them before.
        # For `deploy_all`, we just return them. The CLI code runs pre_hooks from the result.
        
        # 2. Deploy Files (Parallel)
        sections_to_deploy = plan["sections_to_deploy"]
        
        if sections_to_deploy:
             with ThreadPoolExecutor() as executor:
                # Helper to process single file/dir deployment
                def deploy_item(item_tuple):
                    section, local_path, repo_path = item_tuple
                    deployed_count = 0
                    item_errors = []
                    
                    if section.update_strategy == "rename_old" and local_path.exists():
                        backup_file(local_path)
                    
                    # Helper to restore secrets
                    def restore_file_secrets(dest_path: Path):
                        try:
                            content = dest_path.read_text(encoding="utf-8")
                            restored = self.vault.restore_secrets_in_content(
                                content, str(local_path), self.current_branch
                            )
                            if restored != content:
                                dest_path.write_text(restored, encoding="utf-8")
                        except (OSError, UnicodeDecodeError) as e:
                            item_errors.append(f"Failed to restore secrets for {dest_path}: {e}")

                    try:
                        if repo_path.is_file():
                            success, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                            if success:
                                if section.secrets_filter:
                                    restore_file_secrets(local_path)
                                deployed_count += 1
                        else:
                            files_copied, files_failed, _ = copy_directory(
                                repo_path, local_path,
                                filter_secrets_enabled=False,
                                include_patterns=section.include,
                                exclude_patterns=section.exclude,
                            )
                            # Restore secrets in directory
                            if section.secrets_filter:
                                for deployed_file in local_path.rglob("*"):
                                    if deployed_file.is_file():
                                        restore_file_secrets(deployed_file)
                                        
                            deployed_count += files_copied
                            if files_failed > 0:
                                item_errors.append(f"Failed to deploy {files_failed} files in {local_path}")
                                
                    except PermissionError as e:
                        item_errors.append(f"Permission denied deploying {local_path}. Try running with sudo?")
                    except FileNotFoundError as e:
                        item_errors.append(f"File not found during deployment: {local_path}")
                    except OSError as e:
                        item_errors.append(f"Error deploying {local_path}: {e}")
                        
                    return deployed_count, item_errors

                # Submit all tasks
                futures = [executor.submit(deploy_item, item) for item in sections_to_deploy]
                
                for future in as_completed(futures):
                    try:
                        count, errs = future.result()
                        total_deployed += count
                        all_errors.extend(errs)
                    except Exception as e:
                        all_errors.append(f"Critical error in deployment thread: {e}")

        return {
            "deployed": total_deployed,
            "pre_hooks": pre_hooks,
            "post_hooks": post_hooks,
            "errors": all_errors
        }

    
    def save_all(
        self,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None
    ) -> dict:
        """
        Save all sections from local to repo.
        Returns dict with keys: 'saved', 'secrets', 'errors'
        """
        total_saved = 0
        all_secrets: list[SecretMatch] = []
        all_errors: list[str] = []
        
        sections = [self.get_section(name) for name in self.get_sections()]
        
        # Parallel execution
        with ThreadPoolExecutor() as executor:
            future_to_section = {
                executor.submit(self.save_section, section, secret_handler): section 
                for section in sections
            }
            
            for future in as_completed(future_to_section):
                try:
                    saved, secrets, errors = future.result()
                    total_saved += saved
                    all_secrets.extend(secrets)
                    all_errors.extend(errors)
                except Exception as e:
                    all_errors.append(f"Critical error saving section: {e}")
        
        return {
            "saved": total_saved,
            "secrets": all_secrets,
            "errors": all_errors
        }
    
    def deploy_all(self) -> dict:
        """
        Deploy all sections from repo to local (Refactored Two-Phase).
        Returns dict with keys: 'deployed', 'pre_hooks', 'post_hooks', 'errors'
        """
        sections = [self.get_section(name) for name in self.get_sections()]
        
        # Phase 1: Scan
        plan = self.scan_deployable_changes(sections)
        
        # Phase 2: Execute
        result = self.execute_deployment_plan(plan)
        
        return result
    
    def switch_branch(
        self, 
        target_branch: str, 
        dry_run: bool = False,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None
    ) -> dict:
        """
        Switch to a different branch.
        
        Returns dict with:
            - saved_count: files saved from current branch
            - deployed_count: files deployed from target branch
            - secrets_redacted: number of secrets redacted
            - pre_hooks: list of pre-deploy commands
            - post_hooks: list of post-deploy commands
            - created_branch: True if branch was newly created
            - errors: list of error messages
        """
        current_branch = self.current_branch
        result: dict[str, Any] = {
            "saved_count": 0,
            "deployed_count": 0,
            "secrets_redacted": 0,
            "pre_hooks": [],
            "post_hooks": [],
            "created_branch": False,
            "errors": []
        }
        
        if current_branch == target_branch and not dry_run:
            return result
        
        # Phase 1: Save current branch
        if not dry_run:
            save_result = self.save_all(secret_handler)
            result["saved_count"] = save_result["saved"]
            result["secrets_redacted"] = len(save_result["secrets"])
            result["errors"].extend(save_result["errors"])
            
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
            # Auto-backup before potentially destructive deployment
            try:
                # Identify files that will be changed to backup them
                # For now, simplistic approach: Backup all tracked files in current config?
                # Or better: Backup files that are about to be overwritten.
                # Simplest safe bet: Backup all files tracked by the OLD branch (current state)
                # before we switch and overwrite them.
                paths_to_backup = []
                for section_name in self.get_sections():
                     section = self.get_section(section_name)
                     paths_to_backup.extend([p for p in section.paths if p.exists()])
                
                if paths_to_backup:
                    self.backups.create_backup(paths_to_backup, note=f"pre-switch-{target_branch}")
            except Exception as e:
                result["errors"].append(f"Warning: Auto-backup failed: {e}")


            # Two-Phase Deployment for Target Branch
            # Because we are inside switch_branch, we handle this manually to populate 'result' correctly
            try:
                sections = [self.get_section(name) for name in self.get_sections()]
                
                # Phase 1: Scan
                plan = self.scan_deployable_changes(sections)
                
                # Deduplicate hooks from scan
                result["pre_hooks"].extend(plan["pre_hooks"])
                result["post_hooks"].extend(plan["post_hooks"])
                result["errors"].extend(plan["errors"])
                
                # Deduplicate
                result["pre_hooks"] = list(dict.fromkeys(result["pre_hooks"]))
                result["post_hooks"] = list(dict.fromkeys(result["post_hooks"]))
                
                # Phase 2: Execute
                deploy_result = self.execute_deployment_plan(plan)
                
                result["deployed_count"] = deploy_result["deployed"]
                result["errors"].extend(deploy_result["errors"])
                
            except Exception as e:
                result["errors"].append(f"Critical error during switch deployment: {e}")
            
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

    def pre_push_audit(self) -> bool:
        """
        Check for secrets before pushing.
        Returns True if safe to push, False if secrets found.
        """
        audit_results = self.audit()

        # Check if strict mode is enabled
        strict_mode = self.global_config.strict_mode

        if not audit_results:
            return True

        print("\n🔒 Pre-push Audit: Secrets detected!")
        for section, matches in audit_results:
            print(f"  [{section}]: {len(matches)} secrets")

        if strict_mode:
            print("Strict mode enabled. Push aborted.")
            return False

        # Interactive
        from .ui import confirm
        return confirm("Secrets detected. Push anyway?", default=False)
    
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
        summary: dict[str, Any] = {
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
