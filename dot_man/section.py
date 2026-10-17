"""Section configuration for dot-man."""

__all__ = ["Section"]

import os
from pathlib import Path
from typing import Any, Optional

from . import constants as _constants
from .constants import (
    DEFAULT_IGNORED_DIRECTORIES,
)
from .exceptions import ConfigValidationError
from .hook_engine import HookContext, resolve_hook


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
        shared: Optional[bool] = None,
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
        self.update_strategy = (
            update_strategy if update_strategy is not None else "replace"
        )
        if self.update_strategy not in _constants.VALID_UPDATE_STRATEGIES:
            raise ConfigValidationError(
                f"Invalid update_strategy '{self.update_strategy}' in [{self.name}]. "
                f"Valid options: {_constants.VALID_UPDATE_STRATEGIES}"
            )

        self.include = include or []
        self.exclude = exclude or []

        # Resolve hook aliases
        self.pre_deploy = self._resolve_hook(pre_deploy)
        self.post_deploy = self._resolve_hook(post_deploy)
        self.on_activate = self._resolve_hook(on_activate)
        self.on_deactivate = self._resolve_hook(on_deactivate)

        self.inherits = inherits or []

        self.ignored_directories = (
            ignored_directories
            if ignored_directories is not None
            else DEFAULT_IGNORED_DIRECTORIES
        )
        self.follow_symlinks = follow_symlinks if follow_symlinks is not None else False
        self.deploy_method = deploy_method if deploy_method is not None else "copy"
        if self.deploy_method not in VALID_DEPLOY_METHODS:
            raise ConfigValidationError(
                f"Invalid deploy_method '{self.deploy_method}' in [{self.name}]. "
                f"Valid options: {VALID_DEPLOY_METHODS}"
            )

        # Encryption options
        self.encrypted = encrypted if encrypted is not None else False
        self.encryption_method = encryption_method or "gpg"
        self.encryption_recipient = encryption_recipient

        # Shared sections propagate edits to every branch that does not
        # define its own override for this section name.
        self.shared = shared if shared is not None else False

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

        expanded = _constants.HOOK_ALIASES.get(hook, hook)

        context = HookContext(section_name=self.name)
        if "{" in expanded:
            context = HookContext(
                section_name=self.name,
                branch=self._get_current_branch(),
                paths=tuple(str(p) for p in self.paths),
                **self._config_names(),
            )
        return resolve_hook(hook, context)

    def _config_names(self) -> dict[str, str]:
        """Derive config_root/config_name from the first tracked path."""
        if not self.paths:
            return {}
        first = self.paths[0]
        if first.exists() and first.is_dir():
            return {"config_root": str(first.parent), "config_name": first.name}
        if first.exists() and first.is_file():
            return {"config_root": str(first.parent), "config_name": first.name}
        expanded = first.expanduser()
        return {"config_root": str(expanded.parent), "config_name": expanded.name}

    @staticmethod
    def _get_current_branch() -> str:
        """Current configuration branch as recorded in global.toml.

        Same source as operations.current_branch, so {branch} and
        {{branch}} always agree with navigate (and with deploy-time hook
        contexts). Reading raw git instead opened REPO_DIR with
        search_parent_directories=True, leaking whatever repository sat
        at or above it — e.g. a personal branch named "custom".
        """
        from .global_config import GlobalConfig

        try:
            global_config = GlobalConfig()
            global_config.load()
            return global_config.current_branch
        except Exception:
            return "unknown"

    def get_repo_path(self, local_path: Path, repo_dir: Path) -> Path:
        """Get the repository path for a local path.

        Files that live inside one of the section's tracked paths keep their
        subdirectory structure relative to that root, so same-basename files
        in different directories never collide in the repo. Anything else
        (a tracked path itself, or a path outside every tracked root) falls
        back to the basename under ``repo_base``.
        """
        if self.repo_path:
            # Explicit repo_path for single files — must stay inside the repo,
            # otherwise a crafted config could read/write arbitrary paths.
            target = repo_dir / self.repo_path
            try:
                inside = target.resolve().is_relative_to(repo_dir.resolve())
            except (OSError, RuntimeError):
                inside = False
            if not inside:
                raise ConfigValidationError(
                    f"repo_path {self.repo_path!r} escapes the repository."
                )
            return target
        for tracked in self.paths:
            for root in (tracked, Path(tracked.expanduser())):
                try:
                    rel = local_path.relative_to(root)
                except ValueError:
                    continue
                if str(rel) == ".":
                    break  # local_path IS this tracked root — fall through to name
                return repo_dir / self.repo_base / rel
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
        if self.shared:
            result["shared"] = True

        return result
