"""
File watcher for auto-reload of ChucK files.

Provides automatic reloading of ChucK files when they change on disk,
useful for live coding workflows where you edit files in an external editor.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

from .constants import FILE_DEBOUNCE_MS, FILE_OBSERVER_SHUTDOWN_TIMEOUT

if TYPE_CHECKING:
    from .tui.session import ChuckSession
    from .api import Chuck


@dataclass
class WatchedFile:
    """Information about a watched file."""

    filepath: Path
    shred_id: int | None = None
    last_modified: float = 0.0
    last_content_hash: int = 0


@dataclass
class FileWatcher:
    """Watches ChucK files for changes and auto-reloads them.

    When a watched file is modified, the watcher will:
    1. Remove the old shred (if any)
    2. Recompile the file
    3. Spork the new shred

    This enables a live coding workflow where you edit files in an
    external editor and see changes reflected immediately.

    Args:
        chuck: ChucK instance for compilation
        session: ChuckSession for shred tracking
        on_reload: Optional callback called when a file is reloaded
        on_error: Optional callback called when reload fails
        debounce_ms: Debounce time in milliseconds (default: 100)

    Example:
        >>> watcher = FileWatcher(chuck, session)
        >>> watcher.watch_file("synth.ck")
        >>> watcher.start()
        >>> # Edit synth.ck in external editor - changes auto-reload
        >>> watcher.stop()
    """

    chuck: Chuck
    session: ChuckSession
    on_reload: Callable[[Path, int], None] | None = None
    on_error: Callable[[Path, str], None] | None = None
    debounce_ms: int = FILE_DEBOUNCE_MS
    _watched_files: dict[str, WatchedFile] = field(default_factory=dict)
    _observer: BaseObserver | None = field(default=None, repr=False)
    _handler: _FileChangeHandler | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _debounce_timers: dict[str, threading.Timer] = field(
        default_factory=dict, repr=False
    )

    def watch_file(self, filepath: str | Path, shred_id: int | None = None) -> bool:
        """Start watching a file for changes.

        Args:
            filepath: Path to the ChucK file to watch
            shred_id: Optional existing shred ID to track for replacement

        Returns:
            True if file was added to watch list, False if already watched

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        str_path = str(path)
        with self._lock:
            if str_path in self._watched_files:
                # Update shred_id if provided
                if shred_id is not None:
                    self._watched_files[str_path].shred_id = shred_id
                return False

            # Get initial file state
            content_hash = hash(path.read_text())

            self._watched_files[str_path] = WatchedFile(
                filepath=path,
                shred_id=shred_id,
                last_modified=path.stat().st_mtime,
                last_content_hash=content_hash,
            )

            # If already running, add directory to observer
            if (
                self._running
                and self._observer is not None
                and self._handler is not None
            ):
                parent_dir = str(path.parent)
                # Observer will watch the parent directory
                self._observer.schedule(self._handler, parent_dir, recursive=False)

            return True

    def unwatch_file(self, filepath: str | Path) -> bool:
        """Stop watching a file.

        Args:
            filepath: Path to the ChucK file to unwatch

        Returns:
            True if file was removed from watch list, False if not found
        """
        path = Path(filepath).resolve()
        str_path = str(path)

        with self._lock:
            if str_path in self._watched_files:
                del self._watched_files[str_path]
                return True
            return False

    def get_watched_files(self) -> list[WatchedFile]:
        """Get list of currently watched files.

        Returns:
            List of WatchedFile objects
        """
        with self._lock:
            return list(self._watched_files.values())

    def start(self) -> None:
        """Start the file watcher.

        Begins watching all registered files for changes.
        """
        if self._running:
            return

        self._handler = _FileChangeHandler(self)
        self._observer = Observer()

        # Get unique parent directories to watch
        with self._lock:
            parent_dirs = set()
            for str_path in self._watched_files:
                parent_dirs.add(str(Path(str_path).parent))

        # Schedule watches for each parent directory
        for parent_dir in parent_dirs:
            self._observer.schedule(self._handler, parent_dir, recursive=False)

        self._observer.start()
        self._running = True

    def stop(self) -> None:
        """Stop the file watcher.

        Stops watching all files and cleans up resources.
        """
        if not self._running:
            return

        # Cancel any pending debounce timers
        with self._lock:
            for timer in self._debounce_timers.values():
                timer.cancel()
            self._debounce_timers.clear()

        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=FILE_OBSERVER_SHUTDOWN_TIMEOUT)
            self._observer = None

        self._handler = None
        self._running = False

    def _handle_file_modified(self, filepath: str) -> None:
        """Handle file modification event (internal).

        Args:
            filepath: Path to the modified file
        """
        path = Path(filepath).resolve()
        str_path = str(path)

        with self._lock:
            if str_path not in self._watched_files:
                return

            # Cancel any existing debounce timer for this file
            if str_path in self._debounce_timers:
                self._debounce_timers[str_path].cancel()

            # Set up debounce timer
            timer = threading.Timer(
                self.debounce_ms / 1000.0,
                self._reload_file,
                args=[str_path],
            )
            self._debounce_timers[str_path] = timer
            timer.start()

    def _reload_file(self, str_path: str) -> None:
        """Reload a file after debounce (internal).

        Args:
            str_path: String path to the file to reload
        """
        with self._lock:
            if str_path not in self._watched_files:
                return

            watched = self._watched_files[str_path]
            path = watched.filepath

            # Check if file actually changed (by content hash)
            try:
                new_content = path.read_text()
                new_hash = hash(new_content)

                if new_hash == watched.last_content_hash:
                    # Content didn't actually change
                    return

                watched.last_content_hash = new_hash
                watched.last_modified = time.time()

            except (OSError, UnicodeDecodeError) as e:
                if self.on_error:
                    self.on_error(path, f"Failed to read file: {e}")
                return

            # Remove old shred if exists
            old_shred_id = watched.shred_id
            if old_shred_id is not None:
                try:
                    self.chuck.remove_shred(old_shred_id)
                    self.session.remove_shred(old_shred_id)
                except (RuntimeError, KeyError):
                    pass  # Shred might already be gone

            # Compile and spork the new version
            try:
                success, shred_ids = self.chuck.compile_file(str(path))
                if success and shred_ids:
                    new_shred_id = shred_ids[0]
                    watched.shred_id = new_shred_id
                    self.session.add_shred(
                        new_shred_id,
                        str(path),
                        content=new_content,
                        shred_type="file",
                    )

                    if self.on_reload:
                        self.on_reload(path, new_shred_id)
                else:
                    if self.on_error:
                        self.on_error(path, "Compilation failed")

            except Exception as e:
                if self.on_error:
                    self.on_error(path, str(e))

    @property
    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running


class _FileChangeHandler(FileSystemEventHandler):
    """Internal watchdog event handler."""

    def __init__(self, watcher: FileWatcher) -> None:
        self.watcher = watcher
        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event."""
        if event.is_directory:
            return

        # Get path as string
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")

        # Only handle .ck files
        if not src_path.endswith(".ck"):
            return

        self.watcher._handle_file_modified(src_path)
