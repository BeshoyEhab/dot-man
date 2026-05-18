"""Watch command for dot-man — auto-save on file changes."""

import threading
import time
from pathlib import Path
from typing import Optional

import click

from .. import ui
from ..exceptions import DotManError
from .common import AliasedCommand, error, require_init, warn
from .interface import cli as main

# Try to import watchdog; fall back to polling if unavailable
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# Polling fallback (no dependencies)
# ──────────────────────────────────────────────────────────────────────────────


class _PollingWatcher:
    """Simple mtime-based polling watcher used when watchdog is absent."""

    def __init__(self, paths: list[Path], callback, interval: float = 2.0):
        self._paths = paths
        self._callback = callback
        self._interval = interval
        self._mtimes: dict[Path, float] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []
        for p in self._paths:
            if p.is_file():
                files.append(p)
            elif p.is_dir():
                files.extend(f for f in p.rglob("*") if f.is_file())
        return files

    def _snapshot(self) -> dict[Path, float]:
        result: dict[Path, float] = {}
        for f in self._collect_files():
            try:
                result[f] = f.stat().st_mtime
            except OSError:
                pass
        return result

    def _loop(self) -> None:
        self._mtimes = self._snapshot()
        while not self._stop.is_set():
            time.sleep(self._interval)
            current = self._snapshot()

            changed: list[Path] = []
            for f, mtime in current.items():
                if self._mtimes.get(f) != mtime:
                    changed.append(f)
            # Detect deletions
            for f in set(self._mtimes) - set(current):
                changed.append(f)

            if changed:
                self._mtimes = current
                self._callback(changed)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


# ──────────────────────────────────────────────────────────────────────────────
# Watchdog handler (used when watchdog IS available)
# ──────────────────────────────────────────────────────────────────────────────

if _WATCHDOG_AVAILABLE:

    class _DotManEventHandler(FileSystemEventHandler):
        """Watchdog handler that debounces rapid changes."""

        DEBOUNCE_SECONDS = 1.5

        def __init__(self, tracked_paths: list[Path], callback):
            super().__init__()
            self._tracked = set(tracked_paths)
            self._callback = callback
            self._pending: set[Path] = set()
            self._timer: Optional[threading.Timer] = None
            self._lock = threading.Lock()

        def _is_tracked(self, path_str: str) -> bool:
            p = Path(path_str)
            for t in self._tracked:
                if t == p or (t.is_dir() and t in p.parents):
                    return True
            return False

        def _schedule_flush(self, path: Path) -> None:
            with self._lock:
                self._pending.add(path)
                if self._timer is not None:
                    self._timer.cancel()
                self._timer = threading.Timer(self.DEBOUNCE_SECONDS, self._flush)
                self._timer.daemon = True
                self._timer.start()

        def _flush(self) -> None:
            with self._lock:
                changed = list(self._pending)
                self._pending.clear()
            if changed:
                self._callback(changed)

        def on_modified(self, event: "FileSystemEvent") -> None:
            src = str(event.src_path)
            if not event.is_directory and self._is_tracked(src):
                self._schedule_flush(Path(src))

        def on_created(self, event: "FileSystemEvent") -> None:
            src = str(event.src_path)
            if not event.is_directory and self._is_tracked(src):
                self._schedule_flush(Path(src))

        def on_deleted(self, event: "FileSystemEvent") -> None:
            src = str(event.src_path)
            if self._is_tracked(src):
                self._schedule_flush(Path(src))


# ──────────────────────────────────────────────────────────────────────────────
# CLI command
# ──────────────────────────────────────────────────────────────────────────────


@main.command("watch", cls=AliasedCommand, aliases=["wat"])
@click.option(
    "--interval",
    "-i",
    default=2.0,
    show_default=True,
    type=float,
    help="Polling interval in seconds (used when watchdog is not installed)",
)
@click.option(
    "--commit/--no-commit",
    default=True,
    show_default=True,
    help="Commit to git after each auto-save",
)
@click.option(
    "--message",
    "-m",
    default="auto",
    help="Commit message prefix. Use 'auto' for timestamp-based messages.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be saved without writing anything",
)
@require_init
def watch(interval: float, commit: bool, message: str, dry_run: bool):
    """Watch tracked dotfiles and auto-save on change.

    Monitors all files configured in dot-man.toml. When a change is
    detected, the affected section is saved to the repository and
    optionally committed.

    Requires the 'watchdog' package for efficient event-based watching:

        pip install watchdog

    Falls back to polling (every --interval seconds) when watchdog is
    not installed.

    Examples:
        dot-man watch                         # watch + auto-commit
        dot-man watch --no-commit             # watch, save but don't commit
        dot-man watch --interval 5            # poll every 5 s
        dot-man watch -m "wip: "              # custom commit prefix
        dot-man watch --dry-run               # preview only
    """
    try:
        from ..operations import get_operations

        ops = get_operations()
        sections = [ops.get_section(n) for n in ops.get_sections()]

        if not sections:
            warn("No sections configured. Run 'dot-man add <path>' first.")
            return

        # Collect all tracked root paths
        tracked_paths: list[Path] = []
        for section in sections:
            tracked_paths.extend(section.paths)

        if not tracked_paths:
            warn("No paths to watch.")
            return

        backend = "watchdog" if _WATCHDOG_AVAILABLE else "polling"
        ui.console.print(
            f"[bold]👁  dot-man watch[/bold]  [dim]({backend} backend)[/dim]"
        )
        ui.console.print()

        for p in tracked_paths:
            exists = "[green]✓[/green]" if p.exists() else "[yellow]?[/yellow]"
            ui.console.print(f"  {exists} {p}")

        ui.console.print()
        ui.console.print("[dim]Watching for changes… Press Ctrl+C to stop.[/dim]")
        ui.console.print()

        save_count = [0]

        def on_change(changed_files: list[Path]) -> None:
            if dry_run:
                ui.console.print(
                    f"[dim][dry-run] Would save: "
                    f"{', '.join(str(f) for f in changed_files[:3])}"
                    f"{'...' if len(changed_files) > 3 else ''}[/dim]"
                )
                return

            try:
                result = ops.save_all()
                saved = result["saved"]
                secrets = len(result["secrets"])
                errors = result["errors"]

                if saved == 0:
                    return  # Nothing actually changed on disk

                save_count[0] += 1
                timestamp = time.strftime("%H:%M:%S")
                summary = f"[{timestamp}] Saved {saved} file(s)"
                if secrets:
                    summary += f", {secrets} secret(s) redacted"
                ui.console.print(f"  [green]✓[/green] {summary}")

                if errors:
                    for e in errors:
                        warn(f"    {e}")

                if commit:
                    if message == "auto":
                        msg = f"[dot-man] auto-save {timestamp} ({saved} files)"
                    else:
                        msg = f"{message}{timestamp}"
                    sha = ops.git.commit(msg)
                    if sha:
                        ui.console.print(f"  [dim]  committed {sha[:7]}[/dim]")

            except DotManError as exc:
                warn(f"Save failed: {exc}")
            except Exception as exc:  # noqa: BLE001
                warn(f"Unexpected error during save: {exc}")

        # Start watcher
        if _WATCHDOG_AVAILABLE:
            handler = _DotManEventHandler(tracked_paths, on_change)
            observer = Observer()
            # Watch unique parent directories
            watched_dirs: set[Path] = set()
            for p in tracked_paths:
                watch_dir = p if p.is_dir() else p.parent
                if watch_dir not in watched_dirs:
                    observer.schedule(handler, str(watch_dir), recursive=True)
                    watched_dirs.add(watch_dir)
            observer.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
            observer.join()
        else:
            watcher = _PollingWatcher(tracked_paths, on_change, interval=interval)
            watcher.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                watcher.stop()

        ui.console.print()
        ui.console.print(
            f"[dim]Stopped. {save_count[0]} auto-save(s) made this session.[/dim]"
        )

    except DotManError as exc:
        error(str(exc), exc.exit_code)
    except Exception as exc:
        error(f"Watch failed: {exc}")
