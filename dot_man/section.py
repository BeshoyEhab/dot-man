"""Section configuration for dot-man."""

__all__ = ["Section"]

from typing import Optional, Any
from pathlib import Path

from .constants import (
    VALID_UPDATE_STRATEGIES,
    HOOK_ALIASES,
    DEFAULT_IGNORED_DIRECTORIES,
)


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
        inherits: Optional[list[str]] = None,
        ignored_directories: Optional[list[str]] = None,
        follow_symlinks: Optional[bool] = None,
    ):
        self.name = name
        self.paths = paths
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

        self.inherits = inherits or []

        self.ignored_directories = ignored_directories if ignored_directories is not None else DEFAULT_IGNORED_DIRECTORIES
        self.follow_symlinks = follow_symlinks if follow_symlinks is not None else False

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
        """Resolve hook aliases to actual commands.

        Examples:
            "shell_reload" → "source ~/.bashrc || ..."
            "nvim_sync" → "nvim --headless +PackerSync +qa"
            "quickshell_reload" → "killall qs; qs -c ii &" (with detected config)
            "echo hello" → "echo hello" (unchanged)
        """
        if not hook:
            return None

        # Check if it's an alias
        resolved = HOOK_ALIASES.get(hook, hook)
        
        # Replace {qs_config} placeholder with detected quickshell config dir
        if "{qs_config}" in resolved:
            qs_config = self._detect_quickshell_config()
            resolved = resolved.replace("{qs_config}", qs_config)
        
        return resolved
    
    def _detect_quickshell_config(self) -> str:
        """Detect the quickshell config directory name from section paths.
        
        Looks for paths like ~/.config/quickshell/<config_name> or
        subdirectories of quickshell config.
        
        Returns:
            Config directory name (e.g., "ii", "caelestea") or empty string if not found.
        """
        quickshell_base = Path("~/.config/quickshell").expanduser()
        
        for path in self.paths:
            path_resolved = path.resolve() if path.exists() else path.expanduser()
            
            # Check if path is under ~/.config/quickshell
            try:
                rel = path_resolved.relative_to(quickshell_base)
                # Get the first part of the relative path (the config dir)
                parts = rel.parts
                if parts:
                    return parts[0]
            except ValueError:
                # Not under quickshell_base, try checking if the path contains 'quickshell'
                str_path = str(path_resolved)
                if "quickshell" in str_path.lower():
                    # Try to extract config dir from path like /some/path/quickshell/ii/...
                    parts = path_resolved.parts
                    for i, part in enumerate(parts):
                        if part.lower() == "quickshell" and i + 1 < len(parts):
                            return parts[i + 1]
        
        # Fallback: check if any subdirectory exists in quickshell base
        if quickshell_base.exists():
            for subdir in quickshell_base.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    return subdir.name
        
        # Ultimate fallback
        return ""

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
        if self.inherits:
            result["inherits"] = self.inherits

        if self.ignored_directories != DEFAULT_IGNORED_DIRECTORIES:
             result["ignored_directories"] = self.ignored_directories
        if self.follow_symlinks is not False:
             result["follow_symlinks"] = self.follow_symlinks

        return result
