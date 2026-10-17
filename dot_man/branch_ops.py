"""Branch and revert operations mixin for DotManOperations."""

import logging
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from git import GitCommandError

from .constants import REPO_DIR
from .exceptions import DotManError
from .files import atomic_write_text, copy_file
from .hook_engine import (
    FILE_TO_HOOK_MAP,  # noqa: F401 (re-exported for tests)
    get_hook_for_file,
)
from .secrets import SecretMatch
from .ui import warn

if TYPE_CHECKING:
    pass


class BranchMixin:
    """Mixin providing branch switch and file revert operations."""

    @property
    @abstractmethod
    def current_branch(self) -> str: ...

    @abstractmethod
    def save_all(
        self,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None,
        symlink_ignore: Optional[set[Path]] = None,
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

    def get_changed_files_between_branches(
        self, source_branch: str, target_branch: str
    ) -> list[str]:
        """Get list of files that differ between two branches.

        Args:
            source_branch: The source branch name
            target_branch: The target branch name

        Returns:
            List of file paths that changed
        """
        try:
            diff_output = self.git.repo.git.diff(
                f"{source_branch}...{target_branch}", "--name-only"
            )
            if diff_output.strip():
                return [f.strip() for f in diff_output.strip().split("\n") if f.strip()]
        except GitCommandError as e:
            logging.debug(
                "git diff %s...%s failed: %s", source_branch, target_branch, e
            )
        return []

    def detect_hooks_for_changed_files(self, changed_files: list[str]) -> list[str]:
        """Determine which hooks to run based on changed files.

        Args:
            changed_files: List of file paths that changed

        Returns:
            List of hook commands to execute (deduplicated)
        """
        from .hook_engine import HookContext, resolve_hook

        hooks_to_run = set()

        for file_path in changed_files:
            file_str = str(file_path)

            section_name = self._find_section_for_file(file_str)
            section = None
            if section_name:
                try:
                    section = self.get_section(section_name)
                except Exception:
                    section = None
            try:
                branch = self.current_branch
            except Exception:
                branch = ""
            if section is not None:
                first = str(section.paths[0]) if section.paths else ""
                context = HookContext(
                    section_name=section_name or "",
                    config_name=Path(first).name if first else "",
                    config_root=str(Path(first).parent) if first else "",
                    paths=tuple(str(p) for p in section.paths),
                    branch=branch if isinstance(branch, str) else "",
                )
            else:
                context = HookContext(branch=branch if isinstance(branch, str) else "")

            hook_name = get_hook_for_file(file_str)
            if hook_name:
                resolved = resolve_hook(hook_name, context)
                if resolved:
                    hooks_to_run.add(resolved)

            if section is not None:
                if section.pre_deploy:
                    hooks_to_run.add(section.pre_deploy)
                if section.post_deploy:
                    hooks_to_run.add(section.post_deploy)

        return list(hooks_to_run)

    def _find_section_for_file(self, file_path: str) -> str | None:
        """Find which section tracks a given file path.

        Args:
            file_path: Path to search for

        Returns:
            Section name or None
        """
        path = (
            Path(file_path).expanduser()
            if file_path.startswith("~")
            else Path(file_path)
        )

        for section_name in self.get_sections():
            section = self.get_section(section_name)
            for section_path in section.paths:
                if path == section_path or (
                    section_path.is_dir() and self._is_subpath(path, section_path)
                ):
                    return section_name
        return None

    def _is_subpath(self, path: Path, parent: Path) -> bool:
        """Check if path is under parent directory."""
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False
