"""
CLI watch command for auto-reloading ChucK files.

Provides a command-line interface for watching ChucK files and
auto-reloading them when they change, with real-time audio playback.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class WatchError(Exception):
    """Error during watch mode."""


def watch_files(
    files: Sequence[str | Path],
    sample_rate: int = 44100,
    channels: int = 2,
    verbose: bool = True,
) -> None:
    """Watch ChucK files and auto-reload on changes.

    This function starts real-time audio playback and watches the specified
    files for changes. When a file is modified, it is automatically reloaded
    (old shred removed, new shred sporked).

    Args:
        files: List of ChucK files to watch
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of output channels (default: 2)
        verbose: Print status messages (default: True)

    Raises:
        WatchError: If no files provided or files don't exist
        KeyboardInterrupt: When user presses Ctrl+C to exit
    """
    from ..api import Chuck
    from ..tui.session import ChuckSession
    from ..watcher import FileWatcher
    from .._numchuck import start_audio, stop_audio

    if not files:
        raise WatchError("No files provided to watch")

    # Validate all files exist
    paths: list[Path] = []
    for f in files:
        path = Path(f).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.suffix == ".ck":
            raise WatchError(f"Not a ChucK file: {path}")
        paths.append(path)

    # Create ChucK instance
    chuck = Chuck(
        sample_rate=sample_rate,
        output_channels=channels,
    )

    # Create session for tracking
    session = ChuckSession(chuck)

    def on_reload(path: Path, shred_id: int) -> None:
        if verbose:
            print(f"[reload] {path.name} -> shred {shred_id}")

    def on_error(path: Path, error: str) -> None:
        if verbose:
            print(f"[error] {path.name}: {error}", file=sys.stderr)

    # Create file watcher
    watcher = FileWatcher(
        chuck=chuck,
        session=session,
        on_reload=on_reload,
        on_error=on_error,
    )

    try:
        # Initial compilation of all files
        if verbose:
            print(f"Watching {len(paths)} file(s)...")
            print("Press Ctrl+C to stop")
            print()

        for path in paths:
            if verbose:
                print(f"  Loading {path.name}...", end=" ")

            success, shred_ids = chuck.compile_file(str(path))
            if success and shred_ids:
                shred_id = shred_ids[0]
                content = path.read_text()
                session.add_shred(
                    shred_id, str(path), content=content, shred_type="file"
                )
                watcher.watch_file(path, shred_id=shred_id)
                if verbose:
                    print(f"shred {shred_id}")
            else:
                if verbose:
                    print("FAILED")
                    print(f"    Compilation error in {path.name}", file=sys.stderr)

        if verbose:
            print()

        # Start audio
        start_audio(chuck)
        session.audio_running = True
        if verbose:
            print("Audio started")
            print()

        # Start watching
        watcher.start()

        # Main loop - wait for Ctrl+C
        while True:
            time.sleep(0.5)

            # Print status periodically if verbose
            if verbose:
                shred_count = len(chuck.shreds)
                watched_count = len(watcher.get_watched_files())
                print(
                    f"\r[watching] {watched_count} files | "
                    f"{shred_count} shreds active",
                    end="",
                    flush=True,
                )

    except KeyboardInterrupt:
        if verbose:
            print("\n\nStopping...")

    finally:
        # Cleanup
        watcher.stop()
        try:
            stop_audio()
        except RuntimeError:
            pass
        chuck.close()

        if verbose:
            print("Done")


def cmd_watch(
    files: Sequence[str],
    sample_rate: int = 44100,
    channels: int = 2,
    quiet: bool = False,
) -> None:
    """CLI entry point for watch command.

    Args:
        files: List of file paths to watch
        sample_rate: Sample rate in Hz
        channels: Number of channels
        quiet: Suppress status messages
    """
    try:
        watch_files(
            files=files,
            sample_rate=sample_rate,
            channels=channels,
            verbose=not quiet,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except WatchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
