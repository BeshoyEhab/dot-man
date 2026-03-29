"""Branch and revert operations mixin for DotManOperations."""

from abc import abstractmethod, abstractproperty
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

from .files import copy_file, atomic_write_text, clear_comparison_cache
from .secrets import SecretMatch
from .constants import REPO_DIR
from .exceptions import DotManError
from .lock import FileLock
from .ui import warn

if TYPE_CHECKING:
    from .config import Section

LOCK_FILE = REPO_DIR.parent / ".lock"


class BranchMixin:
    """Mixin providing branch switch and file revert operations."""

    @property
    @abstractmethod
    def current_branch(self) -> str: ...

    @abstractmethod
    def save_all(
        self, secret_handler: Optional[Callable[[SecretMatch], str]] = None
    ) -> dict[str, Any]: ...

    @property
    @abstractmethod
    def git(self) -> Any: ...

    @abstractmethod
    def reload_config(self) -> None: ...

    @abstractmethod
    def get_sections(self) -> list[str]: ...

    @abstractmethod
    def get_section(self, name: str) -> Any: ...

    @property
    @abstractmethod
    def backups(self) -> Any: ...

    @abstractmethod
    def scan_deployable_changes(self, sections: list[Any]) -> Any: ...

    @abstractmethod
    def execute_deployment_plan(self, plan: Any) -> dict[str, Any]: ...

    @property
    @abstractmethod
    def global_config(self) -> Any: ...

    @property
    @abstractmethod
    def vault(self) -> Any: ...

    def switch_branch(
        self,
        target_branch: str,
        dry_run: bool = False,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None,
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
            "errors": [],
        }

        if current_branch == target_branch and not dry_run:
            return result

        import contextlib

        lock_context = FileLock(LOCK_FILE) if not dry_run else contextlib.nullcontext()

        with lock_context:
            # Phase 1: Save current branch
            if not dry_run:
                save_result = self.save_all(secret_handler)
                result["saved_count"] = save_result["saved"]
                result["secrets_redacted"] = len(save_result["secrets"])
                result["errors"].extend(save_result["errors"])

                commit_msg = f"Auto-save from '{current_branch}' before switch to '{target_branch}'"
                self.git.commit(commit_msg)

            # Phase 2: Switch git branch
            branch_exists = self.git.branch_exists(target_branch)
            result["created_branch"] = not branch_exists

            if not dry_run:
                self.git.checkout(target_branch, create=not branch_exists)
                self.reload_config()

            # Phase 3: Deploy target branch
            if not dry_run:
                # Auto-backup before potentially destructive deployment
                try:
                    paths_to_backup = []
                    for section_name in self.get_sections():
                        section = self.get_section(section_name)
                        paths_to_backup.extend([p for p in section.paths if p.exists()])

                    if paths_to_backup:
                        self.backups.create_backup(
                            paths_to_backup, note=f"pre-switch-{target_branch}"
                        )
                except Exception as e:
                    result["errors"].append(f"Warning: Auto-backup failed: {e}")

                # Two-Phase Deployment for Target Branch
                try:
                    sections = [self.get_section(name) for name in self.get_sections()]

                    plan = self.scan_deployable_changes(sections)

                    result["pre_hooks"].extend(plan["pre_hooks"])
                    result["post_hooks"].extend(plan["post_hooks"])
                    result["errors"].extend(plan["errors"])

                    result["pre_hooks"] = list(dict.fromkeys(result["pre_hooks"]))
                    result["post_hooks"] = list(dict.fromkeys(result["post_hooks"]))

                    deploy_result = self.execute_deployment_plan(plan)

                    result["deployed_count"] = deploy_result["deployed"]
                    result["errors"].extend(deploy_result["errors"])

                except Exception as e:
                    result["errors"].append(
                        f"Critical error during switch deployment: {e}"
                    )

                self.global_config.current_branch = target_branch
                self.global_config.save()

            # Clear file comparison cache since files have likely changed
            clear_comparison_cache()

        return result

    def revert_file(self, path: Path) -> bool:
        """
        Revert a specific file to its repository version.

        Args:
            path: Absolute path to the file to revert.

        Returns:
            True if successful, False if file not tracked or not found in repo.
        """
        path = path.resolve()

        # Find which section tracks this file
        target_section = None
        repo_source = None

        for section_name in self.get_sections():
            section = self.get_section(section_name)
            if path in section.paths:
                target_section = section
                repo_source = section.get_repo_path(path, REPO_DIR)
                break

            for p in section.paths:
                if p.is_dir() and p in path.parents:
                    target_section = section
                    repo_source = section.get_repo_path(path, REPO_DIR)
                    break

            if target_section:
                break

        if not target_section or not repo_source:
            warn(f"File not tracked by any section: {path}")
            return False

        if not repo_source.exists():
            warn(
                f"File not found in repository (branch: {self.current_branch}): {repo_source}"
            )
            return False

        try:
            success, _ = copy_file(repo_source, path, filter_secrets_enabled=False)

            if success and target_section.secrets_filter:
                try:
                    content = path.read_text(encoding="utf-8")
                    restored = self.vault.restore_secrets_in_content(
                        content, str(path), self.current_branch
                    )
                    if restored != content:
                        atomic_write_text(path, restored)
                except (OSError, UnicodeDecodeError):
                    pass

            return success

        except Exception as e:
            raise DotManError(f"Failed to revert {path}: {e}")
