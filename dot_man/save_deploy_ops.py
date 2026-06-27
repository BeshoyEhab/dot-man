"""Save and deploy operations mixin for DotManOperations."""

from __future__ import annotations

from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from .constants import LOCK_FILE, REPO_DIR
from .files import (
    atomic_write_text,
    backup_file,
    clear_comparison_cache,
    compare_files,
    copy_directory,
    copy_file,
    deploy_directory_with_symlinks,
    deploy_file_or_symlink,
)
from .lock import FileLock
from .secrets import SecretMatch

if TYPE_CHECKING:
    from .config import Section

# Binary file extensions that can't contain text secrets
_BINARY_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".ico",
    ".webp",
    ".svg",
    ".mp4",
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".avi",
    ".mkv",
    ".webm",
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".dat",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
    ".eot",
}


class SaveDeployMixin:
    """Mixin providing save/deploy operations for DotManOperations."""

    @property
    @abstractmethod
    def vault(self) -> Any: ...

    @property
    @abstractmethod
    def current_branch(self) -> str: ...

    @abstractmethod
    def get_section(self, name: str) -> Any: ...

    @abstractmethod
    def get_sections(self) -> list[str]: ...

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

    @staticmethod
    def _build_final_excludes(section: Section) -> list[str]:
        """Merge section exclude patterns with ignored directories."""
        return (section.exclude or []) + (section.ignored_directories or [])

    def _deploy_repo_path(
        self,
        repo_path: Path,
        local_path: Path,
        section: Section,
        final_excludes: list[str],
        errors: list[str],
    ) -> int:
        """
        Deploy a single repo_path (file or directory) to local_path.

        Handles symlink and copy deploy methods, including secret restoration.
        Appends error messages to the provided errors list.

        Returns count of files deployed.
        """
        deployed = 0
        try:
            if repo_path.is_file():
                if section.deploy_method == "symlink":
                    symlinked, _ = deploy_file_or_symlink(
                        repo_path, local_path, deploy_method="symlink"
                    )
                    if symlinked:
                        deployed += 1
                    else:
                        errors.append(f"Failed to symlink {repo_path} to {local_path}")
                else:
                    success, _ = copy_file(
                        repo_path, local_path, filter_secrets_enabled=False
                    )
                    if success:
                        if section.render_templates:
                            self._render_templates_inplace(local_path, errors)
                        if section.secrets_filter:
                            self._restore_file_secrets_inplace(
                                local_path, str(local_path), errors
                            )
                        deployed += 1
                    else:
                        errors.append(f"Failed to copy {repo_path} to {local_path}")
            elif repo_path.is_dir():
                if section.deploy_method == "symlink":
                    files_symlinked, files_failed = deploy_directory_with_symlinks(
                        repo_path,
                        local_path,
                        include_patterns=section.include,
                        exclude_patterns=final_excludes,
                    )
                    deployed += files_symlinked
                else:
                    files_copied, files_failed, _ = copy_directory(
                        repo_path,
                        local_path,
                        filter_secrets_enabled=False,
                        include_patterns=section.include,
                        exclude_patterns=final_excludes,
                        follow_symlinks=section.follow_symlinks,
                    )
                    if section.render_templates:
                        for deployed_file in local_path.rglob("*"):
                            if deployed_file.is_file():
                                self._render_templates_inplace(deployed_file, errors)
                    if section.secrets_filter:
                        for deployed_file in local_path.rglob("*"):
                            if deployed_file.is_file():
                                self._restore_file_secrets_inplace(
                                    deployed_file, str(local_path), errors
                                )
                    deployed += files_copied
                if files_failed > 0:
                    errors.append(
                        f"Failed to deploy {files_failed} files in {local_path}"
                    )
            else:
                errors.append(f"Source not found in repo: {repo_path}")
        except PermissionError:
            errors.append(
                f"Permission denied deploying {local_path}. Try running with sudo?"
            )
        except FileNotFoundError:
            errors.append(f"File not found during deployment: {repo_path}")
        except OSError as e:
            errors.append(f"Error deploying {local_path}: {e}")
        return deployed

    def _render_templates_inplace(
        self,
        file_path: Path,
        errors: list[str],
    ) -> None:
        """Render {{VAR}} template variables in a deployed file in-place."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            from .global_config import substitute_templates

            rendered = substitute_templates(content)
            if rendered != content:
                atomic_write_text(file_path, rendered)
        except Exception as e:
            errors.append(f"Warning: template rendering failed for {file_path}: {e}")

    def _restore_file_secrets_inplace(
        self,
        dest_path: Path,
        original_path: str,
        errors: list[str],
    ) -> None:
        """Restore secrets and append error message to the provided list if any."""
        err = self._restore_file_secrets(dest_path, original_path, self.current_branch)
        if err:
            errors.append(err)

    def save_section(
        self,
        section: Section,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None,
        symlink_ignore: Optional[set[Path]] = None,
    ) -> tuple[int, list[SecretMatch], list[str], list[Path]]:
        """
        Save a section from local to repo.

        Args:
            section: Section to save.
            secret_handler: Optional callback for secret handling.
            symlink_ignore: Set of symlinked paths to skip (ignore).

        Returns:
            (files_saved, secrets_detected, errors, symlink_paths)
        """
        saved = 0
        all_secrets: list[SecretMatch] = []
        errors: list[str] = []
        symlink_paths: list[Path] = []

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
                        branch=self.current_branch,
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
        final_excludes = self._build_final_excludes(section)

        symlink_ignore = symlink_ignore or set()

        for local_path in section.paths:
            if not local_path.exists():
                continue

            # If path is a symlink, check if user chose to ignore it
            if local_path.is_symlink():
                symlink_paths.append(local_path)
                if local_path in symlink_ignore:
                    continue

            repo_path = section.get_repo_path(local_path, REPO_DIR)

            try:
                if local_path.is_file():
                    success, secrets = copy_file(
                        local_path,
                        repo_path,
                        filter_secrets_enabled=section.secrets_filter,
                        secret_handler=wrapped_handler,
                    )
                    if success:
                        saved += 1
                    all_secrets.extend(secrets)
                else:
                    files_copied, files_failed, secrets = copy_directory(
                        local_path,
                        repo_path,
                        filter_secrets_enabled=section.secrets_filter,
                        include_patterns=section.include,
                        exclude_patterns=final_excludes,
                        secret_handler=wrapped_handler,
                        follow_symlinks=section.follow_symlinks,
                    )
                    saved += files_copied
                    all_secrets.extend(secrets)
                    if files_failed > 0:
                        errors.append(
                            f"Failed to copy {files_failed} files in {local_path}"
                        )
            except (OSError, IOError) as e:
                errors.append(f"Error processing {local_path}: {e}")

        return saved, all_secrets, errors, symlink_paths

    def deploy_section(self, section: Section) -> tuple[int, bool, list[str]]:
        """
        Deploy a section from repo to local.

        Returns:
            (files_deployed, had_changes, errors)
        """
        deployed = 0
        had_changes = False
        errors: list[str] = []

        final_excludes = self._build_final_excludes(section)

        for local_path in section.paths:
            repo_path = section.get_repo_path(local_path, REPO_DIR)

            if local_path.is_symlink():
                errors.append(
                    f"⚠ {local_path} is a symlink → {local_path.resolve()}. "
                    f"Deploy will overwrite it with a regular file."
                )

            if section.update_strategy == "ignore" and local_path.exists():
                continue

            will_change = not local_path.exists() or not compare_files(
                repo_path, local_path
            )
            if will_change:
                had_changes = True

            if section.update_strategy == "rename_old" and local_path.exists():
                backup_file(local_path)

            deployed += self._deploy_repo_path(
                repo_path, local_path, section, final_excludes, errors
            )

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
            "errors": [],
        }

        for section in sections:
            for local_path in section.paths:
                repo_path = section.get_repo_path(local_path, REPO_DIR)

                if section.update_strategy == "ignore" and local_path.exists():
                    continue

                try:
                    if not repo_path.exists():
                        continue

                    will_change = not local_path.exists() or not compare_files(
                        repo_path, local_path
                    )

                    if will_change:
                        plan["sections_to_deploy"].append(
                            (section, local_path, repo_path)
                        )

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

                    final_excludes = self._build_final_excludes(section)
                    deployed_count = self._deploy_repo_path(
                        repo_path, local_path, section, final_excludes, item_errors
                    )
                    return deployed_count, item_errors

                futures = [
                    executor.submit(deploy_item, item) for item in sections_to_deploy
                ]

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
            "errors": all_errors,
        }

    def save_all(
        self,
        secret_handler: Optional[Callable[[SecretMatch], str]] = None,
        symlink_ignore: Optional[set[Path]] = None,
    ) -> dict:
        """
        Save all sections from local to repo.
        Returns dict with keys: 'saved', 'secrets', 'errors', 'symlinks'
        """
        with FileLock(LOCK_FILE):
            total_saved = 0
            all_secrets: list[SecretMatch] = []
            all_errors: list[str] = []
            all_symlinks: list[Path] = []

            sections = [self.get_section(name) for name in self.get_sections()]

            with self.vault.batch(), ThreadPoolExecutor() as executor:
                future_to_section = {
                    executor.submit(
                        self.save_section, section, secret_handler, symlink_ignore
                    ): section
                    for section in sections
                }

                for future in as_completed(future_to_section):
                    try:
                        saved, secrets, errors, symlinks = future.result()
                        total_saved += saved
                        all_secrets.extend(secrets)
                        all_errors.extend(errors)
                        all_symlinks.extend(symlinks)
                    except Exception as e:
                        all_errors.append(f"Critical error saving section: {e}")

            return {
                "saved": total_saved,
                "secrets": all_secrets,
                "errors": all_errors,
                "symlinks": all_symlinks,
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
