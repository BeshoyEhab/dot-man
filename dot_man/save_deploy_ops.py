"""Save and deploy operations mixin for DotManOperations."""

from __future__ import annotations
from pathlib import Path
from typing import Callable, Optional, TYPE_CHECKING
from concurrent.futures import ThreadPoolExecutor, as_completed

from .files import copy_file, copy_directory, compare_files, backup_file, atomic_write_text, clear_comparison_cache
from .secrets import SecretMatch
from .constants import REPO_DIR
from .lock import FileLock

if TYPE_CHECKING:
    from .config import Section

LOCK_FILE = REPO_DIR.parent / ".lock"

# Binary file extensions that can't contain text secrets
_BINARY_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.webp', '.svg',
    '.mp4', '.mp3', '.wav', '.ogg', '.flac', '.avi', '.mkv', '.webm',
    '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin', '.dat',
    '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
}


class SaveDeployMixin:
    """Mixin providing save/deploy operations for DotManOperations."""

    def _restore_file_secrets(
        self, dest_path: Path, original_path: str, branch: str
    ) -> Optional[str]:
        """
        Restore redacted secrets in a deployed file from the vault.

        Args:
            dest_path: Path to the file on disk to restore secrets into.
            original_path: The original local path string (used as vault key).
            branch: The branch name for vault lookup.

        Returns:
            Error message string if an OS error occurred, None on success.
        """
        if dest_path.suffix.lower() in _BINARY_EXTENSIONS:
            return None  # Skip binary files silently

        try:
            content = dest_path.read_text(encoding="utf-8")
            restored = self.vault.restore_secrets_in_content(
                content, original_path, branch
            )
            if restored != content:
                atomic_write_text(dest_path, restored)
        except UnicodeDecodeError:
            pass  # Skip binary files silently
        except OSError as e:
            return f"Failed to restore secrets for {dest_path}: {e}"
        return None

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

        # Merge exclude patterns with ignored directories
        final_excludes = (section.exclude or []) + (section.ignored_directories or [])

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
                        exclude_patterns=final_excludes,
                        secret_handler=wrapped_handler,
                        follow_symlinks=section.follow_symlinks,
                    )
                    saved += files_copied
                    all_secrets.extend(secrets)
                    if files_failed > 0:
                        errors.append(f"Failed to copy {files_failed} files in {local_path}")
            except (OSError, IOError) as e:
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
        
        # Merge exclude patterns with ignored directories
        final_excludes = (section.exclude or []) + (section.ignored_directories or [])

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
            def restore_file_secrets(dest_path: Path) -> None:
                err = self._restore_file_secrets(dest_path, str(local_path), self.current_branch)
                if err:
                    errors.append(err)

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
                        exclude_patterns=final_excludes,
                        follow_symlinks=section.follow_symlinks,
                    )
                    if section.secrets_filter:
                        for deployed_file in local_path.rglob("*"):
                            if deployed_file.is_file():
                                restore_file_secrets(deployed_file)

                    deployed += files_copied
                    if files_failed > 0:
                        errors.append(f"Failed to deploy {files_failed} files in {local_path}")
            except PermissionError:
                errors.append(f"Permission denied deploying {local_path}. Try running with sudo?")
            except FileNotFoundError:
                errors.append(f"File not found during deployment: {local_path}")
            except OSError as e:
                errors.append(f"Error deploying {local_path}: {e}")
        
        return deployed, had_changes, errors
    
    def scan_deployable_changes(self, sections: list[Section]) -> dict:
        """
        Phase 1: Scan for changes and collect hooks (Fast Scan).
        
        Returns:
            DeploymentPlan dict
        """
        plan: dict = {
            "sections_to_deploy": [],
            "pre_hooks": [],
            "post_hooks": [],
            "errors": []
        }
        
        for section in sections:
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)
                
                if section.update_strategy == "ignore" and local_path.exists():
                    continue
                
                try:
                    if not repo_path.exists():
                        continue
                    
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

        sections_to_deploy = plan["sections_to_deploy"]
        
        if sections_to_deploy:
             with ThreadPoolExecutor() as executor:
                def deploy_item(item_tuple):
                    section, local_path, repo_path = item_tuple
                    deployed_count = 0
                    item_errors = []
                    
                    if section.update_strategy == "rename_old" and local_path.exists():
                        backup_file(local_path)
                    
                    def restore_file_secrets(dest_path: Path) -> None:
                        err = self._restore_file_secrets(dest_path, str(local_path), self.current_branch)
                        if err:
                            item_errors.append(err)

                    final_excludes = (section.exclude or []) + (section.ignored_directories or [])

                    try:
                        if repo_path.is_file():
                            success, _ = copy_file(repo_path, local_path, filter_secrets_enabled=False)
                            if success:
                                if section.secrets_filter:
                                    restore_file_secrets(local_path)
                                deployed_count += 1
                            else:
                                item_errors.append(f"Failed to copy {repo_path} to {local_path}")
                        elif repo_path.is_dir():
                            files_copied, files_failed, _ = copy_directory(
                                repo_path, local_path,
                                filter_secrets_enabled=False,
                                include_patterns=section.include,
                                exclude_patterns=final_excludes,
                                follow_symlinks=section.follow_symlinks,
                            )
                            if section.secrets_filter:
                                for deployed_file in local_path.rglob("*"):
                                    if deployed_file.is_file():
                                        restore_file_secrets(deployed_file)
                                        
                            deployed_count += files_copied
                            if files_failed > 0:
                                item_errors.append(f"Failed to deploy {files_failed} files in {local_path}")
                        else:
                            item_errors.append(f"Source not found in repo: {repo_path}")
                                
                    except PermissionError:
                        item_errors.append(f"Permission denied deploying {local_path}. Try running with sudo?")
                    except FileNotFoundError:
                        item_errors.append(f"File not found during deployment: {repo_path}")
                    except OSError as e:
                        item_errors.append(f"Error deploying {local_path}: {e}")
                        
                    return deployed_count, item_errors

                futures = [executor.submit(deploy_item, item) for item in sections_to_deploy]
                
                for future in as_completed(futures):
                    try:
                        count, errs = future.result()
                        total_deployed += count
                        all_errors.extend(errs)
                    except Exception as e:
                        all_errors.append(f"Critical error in deployment thread: {e}")

        # Clear comparison cache after deploying changed files
        clear_comparison_cache()

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
        with FileLock(LOCK_FILE):
            total_saved = 0
            all_secrets: list[SecretMatch] = []
            all_errors: list[str] = []
            
            sections = [self.get_section(name) for name in self.get_sections()]
            
            with self.vault.batch(), ThreadPoolExecutor() as executor:
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
        Deploy all sections from repo to local (Two-Phase).
        Returns dict with keys: 'deployed', 'pre_hooks', 'post_hooks', 'errors'
        """
        with FileLock(LOCK_FILE):
            sections = [self.get_section(name) for name in self.get_sections()]
            plan = self.scan_deployable_changes(sections)
            result = self.execute_deployment_plan(plan)
            return result
