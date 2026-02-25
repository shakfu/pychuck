"""
ChucK file executor for command-line execution.

Provides non-interactive execution of ChucK files with options for:
- Audio output or silent mode
- Custom sample rate and channel count
- Timed execution
"""

import sys
import time
import signal
from pathlib import Path
from types import FrameType
from typing import List, Optional

from ..constants import DEFAULT_OUTPUT_CHANNELS, DEFAULT_SAMPLE_RATE, POLL_INTERVAL


class ExecutionError(Exception):
    """Raised when ChucK file execution fails."""

    pass


def execute_files(
    files: List[str],
    srate: int = DEFAULT_SAMPLE_RATE,
    channels: int = DEFAULT_OUTPUT_CHANNELS,
    silent: bool = False,
    duration: Optional[float] = None,
    otf_enable: bool = False,
    otf_port: int = 8888,
) -> None:
    """
    Execute ChucK files from command line.

    Args:
        files: List of ChucK file paths to execute
        srate: Sample rate (default: 44100)
        channels: Number of audio channels (default: 2)
        silent: If True, run without audio output
        duration: If specified, run for this many seconds then exit
        otf_enable: If True, enable on-the-fly programming listener
        otf_port: OTF listener port (default: 8888)

    Raises:
        ExecutionError: If compilation or execution fails
    """
    from ..api import Chuck
    from ..services import AudioService

    # Validate files exist
    missing_files = []
    for filepath in files:
        if not Path(filepath).exists():
            missing_files.append(filepath)

    if missing_files:
        print("Error: Files not found:", file=sys.stderr)
        for f in missing_files:
            print(f"  {f}", file=sys.stderr)
        raise ExecutionError("One or more files not found")

    # Initialize ChucK VM using high-level API
    try:
        chuck = Chuck(
            sample_rate=srate,
            output_channels=channels,
            input_channels=0,
            otf_enable=otf_enable,
            otf_port=otf_port,
        )
    except Exception as e:
        print(f"Error: Failed to create ChucK VM: {e}", file=sys.stderr)
        raise ExecutionError(f"ChucK initialization failed: {e}")

    # Set up audio service
    audio = AudioService(chuck.raw) if not silent else None
    if audio:
        if not audio.start():
            print("Warning: Failed to start audio", file=sys.stderr)
            print("Continuing in silent mode...", file=sys.stderr)
            audio = None

    # Setup signal handler for graceful shutdown
    shutdown_requested = [False]  # Use list to allow modification in nested function

    def signal_handler(sig: int, frame: FrameType | None) -> None:
        print("\nShutdown requested...", file=sys.stderr)
        shutdown_requested[0] = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Compile and run files
    shred_ids = []
    for filepath in files:
        try:
            # Compile and run file
            success, new_shred_ids = chuck.compile_file(filepath)
            if not success or not new_shred_ids:
                raise ExecutionError(f"Failed to compile {filepath}")

            shred_ids.extend(new_shred_ids)
            for sid in new_shred_ids:
                print(f"[shred {sid}] {filepath}")

        except ExecutionError:
            raise
        except Exception as e:
            print(f"Error compiling {filepath}: {e}", file=sys.stderr)
            # Cleanup
            if audio:
                audio.stop()
            chuck.close()
            raise ExecutionError(f"Compilation failed: {e}")

    # Run for specified duration or until interrupted
    try:
        start_time = time.time()

        if duration is not None:
            # Run for specified duration
            print(f"Running for {duration} seconds...")
            while time.time() - start_time < duration:
                if shutdown_requested[0]:
                    break
                time.sleep(POLL_INTERVAL)
        else:
            # Run indefinitely
            print("Running... (Ctrl-C to stop)")
            while not shutdown_requested[0]:
                time.sleep(POLL_INTERVAL)

    finally:
        # Cleanup
        print("Cleaning up...")

        # Remove all shreds
        for shred_id in shred_ids:
            try:
                chuck.remove_shred(shred_id)
            except Exception:
                pass

        # Stop audio
        if audio:
            audio.stop()

        # Close ChucK instance
        chuck.close()

        print("Done.")


if __name__ == "__main__":
    # For testing
    import sys

    if len(sys.argv) > 1:
        execute_files(sys.argv[1:])
    else:
        print("Usage: python -m numchuck.cli.executor <file.ck> [file2.ck ...]")
