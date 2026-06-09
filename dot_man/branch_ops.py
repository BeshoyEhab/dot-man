"""Branch and revert operations mixin for DotManOperations."""

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from .constants import LOCK_FILE, REPO_DIR
from .exceptions import DotManError
from .files import atomic_write_text, clear_comparison_cache, copy_file
from .lock import FileLock
from .merge import get_hook_for_config
from .secrets import SecretMatch
from .ui import warn

if TYPE_CHECKING:
    pass

FILE_TO_HOOK_MAP = {
    ".bashrc": "bash_reload",
    ".zshrc": "zsh_reload",
    ".bash_profile": "bash_reload",
    ".zprofile": "zsh_reload",
    ".config/fish": "fish_reload",
    ".tmux.conf": "tmux_reload",
    ".config/nvim": "nvim_sync",
    ".config/kitty": "kitty_reload",
    ".config/alacritty": "alacritty_reload",
    ".config/wezterm": "wezterm_reload",
    ".config/hypr": "hyprland_reload",
    ".config/hyprland": "hyprland_reload",
    ".config/sway": "sway_reload",
    ".config/i3": "i3_reload",
    ".config/awesome": "awesome_reload",
    ".config/polybar": "polybar_reload",
    ".config/waybar": "waybar_reload",
    ".config/dunst": "dunst_reload",
    ".config/picom": "picom_reload",
    ".Xresources": "xreload",
    ".config/starship": "starship_reload",
    ".fzf.bash": "fzf_reload",
    ".fzf.zsh": "fzf_reload",
    ".emacs.d": "emacs_reload",
    ".vimrc": "vim_reload",
    ".gitconfig": "git_reload",
}


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
                # Warn about symlinked paths
                symlinks: list[Path] = save_result.get("symlinks", [])
                for sym_path in symlinks:
                    result["errors"].append(
                        f"⚠ {sym_path} is a symlink → {sym_path.resolve()}. "
                        f"Edits affect the symlink target, not the config folder."
                    )

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

                    # Auto-detect hooks based on changed files
                    changed_files = self.get_changed_files_between_branches(
                        current_branch, target_branch
                    )
                    if changed_files:
                        auto_hooks = self.detect_hooks_for_changed_files(changed_files)
                        for hook in auto_hooks:
                            if hook and hook not in result["post_hooks"]:
                                result["post_hooks"].append(hook)

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
        except Exception:
            pass
        return []

    def detect_hooks_for_changed_files(self, changed_files: list[str]) -> list[str]:
        """Determine which hooks to run based on changed files.

        Args:
            changed_files: List of file paths that changed

        Returns:
            List of hook commands to execute (deduplicated)
        """
        hooks_to_run = set()

        for file_path in changed_files:
            file_str = str(file_path)

            for pattern, hook_name in FILE_TO_HOOK_MAP.items():
                if pattern in file_str or file_str.endswith(pattern):
                    # Try to resolve the hook alias first
                    from .constants import HOOK_ALIASES

                    if hook_name in HOOK_ALIASES:
                        resolved_cmd: str = HOOK_ALIASES[hook_name]
                        hooks_to_run.add(resolved_cmd)
                    else:
                        # Fallback to get_hook_for_config
                        fallback_cmd = get_hook_for_config(pattern)
                        if fallback_cmd:
                            hooks_to_run.add(fallback_cmd)
                    break

            section_name = self._find_section_for_file(file_path)
            if section_name:
                section = self.get_section(section_name)
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
