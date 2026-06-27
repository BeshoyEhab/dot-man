"""Section configuration for dot-man."""

__all__ = ["Section"]

import os
from pathlib import Path
from typing import Any, Optional

from .constants import (
    DEFAULT_IGNORED_DIRECTORIES,
    HOOK_ALIASES,
)


def _expand_path(path_str: str) -> Path:
    """Expand environment variables and ~ in a path string."""
    expanded = os.path.expandvars(os.path.expanduser(path_str))
    return Path(expanded)


VALID_DEPLOY_METHODS = ["copy", "symlink"]


class Section:
    """Represents a resolved configuration section with smart defaults."""

    def __init__(
        self,
        name: str,
        paths: list[Path],
        repo_base: Optional[str] = None,  # NOW OPTIONAL!
        repo_path: Optional[str] = None,
        secrets_filter: Optional[bool] = None,  # None = use default
        update_strategy: Optional[str] = None,  # None = use default
        include: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        pre_deploy: Optional[str] = None,
        post_deploy: Optional[str] = None,
        on_activate: Optional[str] = None,
        on_deactivate: Optional[str] = None,
        inherits: Optional[list[str]] = None,
        ignored_directories: Optional[list[str]] = None,
        follow_symlinks: Optional[bool] = None,
        deploy_method: Optional[str] = None,
        encrypted: Optional[bool] = None,
        encryption_method: Optional[str] = None,
        encryption_recipient: Optional[str] = None,
    ):
        self.name = name
        # Expand environment variables in paths
        self.paths = [_expand_path(str(p)) if isinstance(p, str) else p for p in paths]
        self.repo_path = repo_path

        # Smart repo_base generation if not provided
        if repo_base is None and not repo_path:
            self.repo_base = self._generate_repo_base()
        else:
            self.repo_base = repo_base or name

        # Use provided values or defaults (None means "use global default")
        self.secrets_filter = secrets_filter if secrets_filter is not None else True
        self.update_strategy = update_strategy or "replace"

        self.include = include or []
        self.exclude = exclude or []

        # Resolve hook aliases
        self.pre_deploy = self._resolve_hook(pre_deploy)
        self.post_deploy = self._resolve_hook(post_deploy)
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate

        self.inherits = inherits or []

        self.ignored_directories = (
            ignored_directories
            if ignored_directories is not None
            else DEFAULT_IGNORED_DIRECTORIES
        )
        self.follow_symlinks = follow_symlinks if follow_symlinks is not None else False
        self.deploy_method = deploy_method if deploy_method is not None else "copy"

        # Encryption options
        self.encrypted = encrypted if encrypted is not None else False
        self.encryption_method = encryption_method or "gpg"
        self.encryption_recipient = encryption_recipient

        # Template rendering ({{VAR}} substitution + conditionals)
        self.render_templates = True

    def _generate_repo_base(self) -> str:
        """Auto-generate repo_base from first path.

        Examples:
            ~/.bashrc → "bashrc"
            ~/.config/nvim → "nvim"
            ~/.ssh/config → "ssh/config"
        """
        if not self.paths:
            return self.name

        first_path = self.paths[0]

        # Handle dotfiles: ~/.bashrc → "bashrc"
        if first_path.name.startswith(".") and first_path.suffix:
            # .bashrc → bashrc, .vimrc → vimrc
            return first_path.name[1:]

        if first_path.name.startswith(".") and not first_path.suffix:
            # .vim → vim, .ssh → ssh
            return first_path.name[1:]

        # Handle .config directories: ~/.config/nvim → "nvim"
        if ".config" in first_path.parts:
            return first_path.name

        # Handle subdirectories: ~/.ssh/config → "ssh/config"
        if len(first_path.parts) > 1 and first_path.is_file():
            parent_name = first_path.parent.name
            if parent_name.startswith("."):
                parent_name = parent_name[1:]
            return f"{parent_name}/{first_path.name}"

        # Fallback: use stem or name
        return first_path.stem or first_path.name

    def _resolve_hook(self, hook: str | None) -> str | None:
        """Resolve hook aliases to actual commands, replacing placeholders.

        Placeholders:
            {section_name}  — the section's config name (e.g., "nvim", "quickshell-ii")
            {config_root}   — base directory of the first tracked path
            {config_name}   — last path segment of the first tracked path (e.g., "ii")
            {paths}         — space-separated list of all tracked paths
            {branch}        — current branch name
            {qs_config}     — alias for {config_name} (backward compat)

        Examples:
            "shell_reload" → "source ~/.bashrc || ..."
            "nvim_sync" → "nvim --headless +PackerSync +qa"
            "qs -c {config_name}" → "qs -c ii"
            "echo hello" → "echo hello" (unchanged)
        """
        if not hook:
            return None

        resolved = HOOK_ALIASES.get(hook, hook)

        if "{" in resolved:
            resolved = resolved.replace("{section_name}", self.name)
            resolved = resolved.replace("{branch}", self._get_current_branch())
            resolved = resolved.replace("{paths}", " ".join(str(p) for p in self.paths))

            if self.paths:
                first = self.paths[0]
                config_root = str(first.parent)
                config_name = first.name
                if first.exists() and first.is_dir():
                    config_name = first.name
                elif first.exists() and first.is_file():
                    config_root = str(first.parent)
                else:
                    config_root = str(first.expanduser().parent)
                    config_name = first.expanduser().name
                resolved = resolved.replace("{config_root}", config_root)
                resolved = resolved.replace("{config_name}", config_name)
                resolved = resolved.replace("{qs_config}", config_name)

        return resolved

    @staticmethod
    def _get_current_branch() -> str:
        """Get current branch name from global config."""
        try:
            from .global_config import GlobalConfig

            gc = GlobalConfig()
            gc.load()
            return gc.current_branch or "unknown"
        except Exception:
            return "unknown"

    def get_repo_path(self, local_path: Path, repo_dir: Path) -> Path:
        """Get the repository path for a local path."""
        if self.repo_path:
            # Explicit repo_path for single files
            return repo_dir / self.repo_path
        # Use repo_base + filename
        return repo_dir / self.repo_base / local_path.name

    def to_dict(self) -> dict[str, Any]:
        """Convert section to dictionary (only non-default values)."""
        result: dict[str, Any] = {
            "paths": [str(p) for p in self.paths],
        }

        # Only include if non-default or explicitly set
        if self.repo_path:
            result["repo_path"] = self.repo_path
        elif self.repo_base != self._generate_repo_base():
            # Only save repo_base if it differs from auto-generated
            result["repo_base"] = self.repo_base

        if self.secrets_filter is not True:  # Only if NOT default
            result["secrets_filter"] = self.secrets_filter
        if self.update_strategy != "replace":  # Only if NOT default
            result["update_strategy"] = self.update_strategy
        if self.include:
            result["include"] = self.include
        if self.exclude:
            result["exclude"] = self.exclude
        if self.pre_deploy:
            result["pre_deploy"] = self.pre_deploy
        if self.post_deploy:
            result["post_deploy"] = self.post_deploy
        if self.on_activate:
            result["on_activate"] = self.on_activate
        if self.on_deactivate:
            result["on_deactivate"] = self.on_deactivate
        if self.inherits:
            result["inherits"] = self.inherits

        if self.ignored_directories != DEFAULT_IGNORED_DIRECTORIES:
            result["ignored_directories"] = self.ignored_directories
        if self.follow_symlinks is not False:
            result["follow_symlinks"] = self.follow_symlinks
        if self.deploy_method != "copy":
            result["deploy_method"] = self.deploy_method
        if self.encrypted:
            result["encrypted"] = self.encrypted
        if self.encryption_method != "gpg":
            result["encryption_method"] = self.encryption_method
        if self.encryption_recipient:
            result["encryption_recipient"] = self.encryption_recipient

        return result
