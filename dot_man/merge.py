"""Universal file merge system for dot-man.

This module provides functionality to manage files that exist across all
branches with content that should be merged rather than replaced.
Use cases:
- Shell aliases that should exist on all branches
- Global environment variables
- Common utility functions

The system uses markers in files to identify merge regions:
    # >>> dot-man:start <<< ...
    # >>> dot-man:end <<< ...

Content between markers is managed by dot-man and will be preserved
across branch switches.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class MergeRegion(TypedDict):
    """A managed merge region in a file."""

    start_line: int
    end_line: int
    content: str
    marker: str


class MergeConfig(TypedDict):
    """Configuration for a universal file."""

    path: str
    marker: str
    content: str
    append_only: bool


class UniversalMergeManager:
    """Manages files with universal content that spans all branches."""

    DEFAULT_MARKER = "# >>> dot-man:start <<<"
    DEFAULT_END_MARKER = "# >>> dot-man:end <<<"

    MARKER_START = "# >>> dot-man:start"
    MARKER_END = "# >>> dot-man:end"

    def _extract_marker_name(self, line: str) -> str:
        """Extract marker name from a start line."""
        if self.MARKER_START in line:
            rest = line[len(self.MARKER_START) :].strip()
            if rest.startswith("<<<"):
                rest = rest[3:].strip()
            return rest if rest else ""
        return ""

    def _is_start_marker(self, line: str) -> bool:
        """Check if line is a start marker."""
        return self.MARKER_START in line

    def _is_end_marker(self, line: str) -> bool:
        """Check if line is an end marker."""
        return self.MARKER_END in line

    def __init__(self, markers: dict[str, str] | None = None):
        """Initialize the merge manager.

        Args:
            markers: Optional dict with custom start/end markers
        """
        self.start_marker = (
            markers.get("start", self.DEFAULT_MARKER)
            if markers
            else self.DEFAULT_MARKER
        )
        self.end_marker = (
            markers.get("end", self.DEFAULT_END_MARKER)
            if markers
            else self.DEFAULT_END_MARKER
        )

    def get_regions(self, file_path: Path) -> list[MergeRegion]:
        """Extract merge regions from a file.

        Args:
            file_path: Path to the file

        Returns:
            List of merge regions found in the file
        """
        if not file_path.exists():
            return []

        content = file_path.read_text()
        lines = content.split("\n")
        regions = []

        stack: list[tuple[int, list[str]]] = []  # (start_line, content_lines)
        for i, line in enumerate(lines):
            if self._is_start_marker(line):
                stack.append((i, []))
            elif self._is_end_marker(line) and stack:
                start_line, content_lines = stack.pop()
                regions.append(
                    MergeRegion(
                        {
                            "start_line": start_line,
                            "end_line": i,
                            "content": "\n".join(content_lines),
                            "marker": f"{self.start_marker}\n{content_lines}\n{self.end_marker}",
                        }
                    )
                )
            elif stack:
                content_lines = stack[-1][1]
                content_lines.append(line)

        return regions

    def inject_content(
        self,
        file_path: Path,
        content: str,
        marker: str | None = None,
        position: str = "append",
    ) -> str:
        """Inject content into a file with merge markers.

        Args:
            file_path: Path to the file
            content: Content to inject
            marker: Custom marker name (will use default if None)
            position: Where to inject ('append', 'prepend', 'replace')

        Returns:
            The updated file content
        """
        start = f"{self.start_marker}"
        if marker and marker != "default":
            start = f"{self.start_marker} {marker}"
        end = self.end_marker

        existing = file_path.read_text() if file_path.exists() else ""

        if f"{start}\n" in existing or start in existing:
            return existing

        new_block = f"{start}\n{content}\n{end}\n"

        if position == "prepend":
            return new_block + existing
        elif position == "append":
            return existing + "\n" + new_block
        else:
            return new_block

    def extract_managed_content(self, file_path: Path) -> dict[str, str]:
        """Extract all managed content blocks from a file.

        Args:
            file_path: Path to the file

        Returns:
            Dict mapping marker names to content
        """
        regions = self.get_regions(file_path)
        result = {}
        for region in regions:
            marker_name = "default"
            for line in region["content"].split("\n"):
                if ":start" in line:
                    marker_name = self._extract_marker_name(line) or "default"
                    break
            result[marker_name] = region["content"]
        return result

    def remove_content(
        self,
        file_path: Path,
        marker: str | None = None,
    ) -> str:
        """Remove managed content from a file.

        Args:
            file_path: Path to the file
            marker: Marker name to remove (None = remove all)

        Returns:
            Updated file content
        """
        if not file_path.exists():
            return ""

        content = file_path.read_text()
        lines = content.split("\n")
        new_lines = []
        in_remove_block = False

        for line in lines:
            if self._is_start_marker(line):
                marker_name = self._extract_marker_name(line)

                if marker is None or marker == marker_name:
                    in_remove_block = True
                    continue
                else:
                    new_lines.append(line)
            elif self._is_end_marker(line):
                if in_remove_block:
                    in_remove_block = False
                    continue
                else:
                    new_lines.append(line)
            elif not in_remove_block:
                new_lines.append(line)

        return "\n".join(new_lines)

    def list_universal_files(self, config_paths: list[str]) -> list[str]:
        """List files that have dot-man merge markers.

        Args:
            config_paths: List of paths to check

        Returns:
            List of file paths with merge markers
        """
        results = []
        for path_str in config_paths:
            path = Path(path_str).expanduser()
            if path.exists():
                if path.is_file():
                    regions = self.get_regions(path)
                    if regions:
                        results.append(path_str)
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file():
                            regions = self.get_regions(file)
                            if regions:
                                results.append(str(file))
        return results


def get_universal_additions(
    file_path: str,
    content: str,
    marker: str | None = None,
) -> str:
    """Convenience function to add universal content to a file.

    Args:
        file_path: Path to the file
        content: Content to add (should include full managed block)
        marker: Optional marker name

    Returns:
        Updated file content
    """
    path = Path(file_path).expanduser()
    manager = UniversalMergeManager()
    return manager.inject_content(path, content, marker)


def merge_files(
    source_path: str,
    target_path: str,
    strategy: str = "replace",
) -> str:
    """Merge content from source to target file.

    Args:
        source_path: Path to source file (in repo)
        target_path: Path to target file (in home)
        strategy: How to handle conflicts ('replace', 'merge', 'prompt')

    Returns:
        The merged content
    """
    src = Path(source_path).expanduser()
    tgt = Path(target_path).expanduser()

    if not src.exists():
        return ""

    if not tgt.exists():
        return src.read_text()

    manager = UniversalMergeManager()

    managed_in_src = manager.get_regions(src)

    if strategy == "replace":
        return src.read_text()

    elif strategy == "merge":
        result = tgt.read_text()
        for region in managed_in_src:
            block = region["content"]

            existing = manager.get_regions(tgt)
            for ex_reg in existing:
                if ex_reg["content"] == block:
                    break
            else:
                result += "\n" + block

        return result

    return tgt.read_text()


UNIVERSAL_HOOKS = {
    "shell_reload": "source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true",
    "fish_reload": "source ~/.config/fish/config.fish 2>/dev/null || true",
    "zsh_reload": "source ~/.zshrc 2>/dev/null || true",
    "bash_reload": "source ~/.bashrc 2>/dev/null || true",
    "tmux_reload": "tmux source-file ~/.tmux.conf 2>/dev/null || true",
    "nvim_sync": "nvim --headless +PackerSync +qa 2>/dev/null || true",
    "kitty_reload": "killall -SIGUSR1 kitty 2>/dev/null || true",
    "hyprland_reload": "hyprctl reload 2>/dev/null || true",
    "sway_reload": "swaymsg reload 2>/dev/null || true",
    "i3_reload": "i3-msg reload 2>/dev/null || true",
    "awesome_reload": "awesome-client 'awesome.restart()' 2>/dev/null || true",
    "polybar_reload": "pkill polybar 2>/dev/null; sleep 0.2; polybar -c ~/.config/polybar/config.ini top 2>/dev/null &",
    "waybar_reload": "waybar-control reload 2>/dev/null || pkill waybar 2>/dev/null; sleep 0.2; waybar 2>/dev/null &",
    "dunst_reload": "pkill dunst 2>/dev/null; sleep 0.2; dunst 2>/dev/null &",
    "picom_reload": "pkill picom 2>/dev/null; sleep 0.2; picom -b 2>/dev/null &",
    "alacritty_reload": "killall -SIGUSR1 alacritty 2>/dev/null || true",
    "wezterm_reload": "wezterm inject-term-change 'reload' 2>/dev/null || true",
    "xreload": "xrdb -load ~/.Xresources 2>/dev/null || true",
    "gnome_reload": "gsettings reset-recursively org.gnome.shell 2>/dev/null || true",
    "kde_reload": "qdbus org.kde.KWin /KWin reconfigure 2>/dev/null || true",
    "ssh_reload": "ssh-add -l >/dev/null 2>&1 || true",
    "git_reload": "git config --global --list >/dev/null 2>&1 || true",
    "vim_reload": "vim +source\\ ~/.vimrc +qa 2>/dev/null || true",
    "emacs_reload": "emacsclient -e '(load-file \"~/.emacs.d/init.el\")' 2>/dev/null || true",
    "doom_reload": "~/.emacs.d/bin/doom-refresh 2>/dev/null || true",
    "starship_reload": 'eval "$(starship config 2>/dev/null)" || true',
    "fzf_reload": "killall fzf 2>/dev/null; source ~/.fzf.bash 2>/dev/null || source ~/.fzf.zsh 2>/dev/null || true",
    "exaile_reload": "dbus-send --print-reply --dest=org.exaile.Exaile /org/exaile/Exaile org.exaile.Exaile.Quit 2>/dev/null || true",
}

HOOK_CATEGORIES = {
    "shells": ["shell_reload", "bash_reload", "zsh_reload", "fish_reload"],
    "window_managers": [
        "hyprland_reload",
        "sway_reload",
        "i3_reload",
        "awesome_reload",
    ],
    "terminals": ["kitty_reload", "alacritty_reload", "wezterm_reload"],
    "bars": ["polybar_reload", "waybar_reload"],
    "editors": ["nvim_sync", "vim_reload", "emacs_reload", "doom_reload"],
    "tools": ["tmux_reload", "starship_reload", "fzf_reload", "git_reload"],
}


def get_hook_for_config(config_name: str) -> str | None:
    """Get the appropriate reload hook for a config name.

    Args:
        config_name: Name of the config (e.g., 'nvim', 'hyprland', 'kitty')

    Returns:
        Command to reload the config, or None if not found
    """
    config_lower = config_name.lower()

    hook_map = {
        "nvim": UNIVERSAL_HOOKS["nvim_sync"],
        "vim": UNIVERSAL_HOOKS["vim_reload"],
        "fish": UNIVERSAL_HOOKS["fish_reload"],
        "bashrc": UNIVERSAL_HOOKS["bash_reload"],
        "zshrc": UNIVERSAL_HOOKS["zsh_reload"],
        "zsh": UNIVERSAL_HOOKS["zsh_reload"],
        "tmux": UNIVERSAL_HOOKS["tmux_reload"],
        "kitty": UNIVERSAL_HOOKS["kitty_reload"],
        "alacritty": UNIVERSAL_HOOKS["alacritty_reload"],
        "wezterm": UNIVERSAL_HOOKS["wezterm_reload"],
        "hyprland": UNIVERSAL_HOOKS["hyprland_reload"],
        "hypr": UNIVERSAL_HOOKS["hyprland_reload"],
        "sway": UNIVERSAL_HOOKS["sway_reload"],
        "i3": UNIVERSAL_HOOKS["i3_reload"],
        "awesome": UNIVERSAL_HOOKS["awesome_reload"],
        "polybar": UNIVERSAL_HOOKS["polybar_reload"],
        "waybar": UNIVERSAL_HOOKS["waybar_reload"],
        "starship": UNIVERSAL_HOOKS["starship_reload"],
        "fzf": UNIVERSAL_HOOKS["fzf_reload"],
        "emacs": UNIVERSAL_HOOKS["emacs_reload"],
        "doom": UNIVERSAL_HOOKS["doom_reload"],
        "xresources": UNIVERSAL_HOOKS["xreload"],
        "ssh": UNIVERSAL_HOOKS["ssh_reload"],
        "git": UNIVERSAL_HOOKS["git_reload"],
        "quickshell": None,
        "qs": None,
    }

    for key, hook in hook_map.items():
        if key in config_lower:
            return hook

    return None


def list_all_hooks() -> dict[str, list[str]]:
    """List all available hooks by category.

    Returns:
        Dict mapping category names to hook names
    """
    return HOOK_CATEGORIES


def get_hook_command(hook_name: str) -> str | None:
    """Get the command for a hook by name.

    Args:
        hook_name: Name of the hook

    Returns:
        Command string or None if not found
    """
    return UNIVERSAL_HOOKS.get(hook_name)


def reload_all_dots() -> list[str]:
    """Generate commands to reload all common dotfile configs.

    Returns:
        List of commands to run
    """
    commands = []
    for hook in UNIVERSAL_HOOKS.values():
        if hook and hook not in commands:
            commands.append(hook)
    return commands
